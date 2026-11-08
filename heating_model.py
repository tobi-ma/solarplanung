"""Hourly PV/load/battery simulation. Household and thermal loads are assumptions.

PV weather timing and temperature: PVGIS 2023; PV monthly totals normalized to
the previously used long-term mean. One-hour model, no intra-hour peaks.
"""
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
import csv
import math
from pathlib import Path
from zoneinfo import ZoneInfo

VARIANTS = ("Splits + kleine Wasser-WP", "Zentrale Luft-Wasser-WP", "Zentrale WP + einzelne Splits")


@dataclass(frozen=True)
class Heating:
    household: float = 3500.
    heat: float = 16000.
    hot_water: float = 2500.
    cooling: float = 1000.
    split_jaz: float = 3.5
    water_jaz: float = 3.2
    dhw_jaz: float = 2.5
    seer: float = 4.
    water_fraction: float = 25.
    hybrid_split_fraction: float = 20.
    household_profile: str = "Morgens und abends"
    dhw_schedule: str = "Mittags"
    central_cooling: bool = False
    battery: bool = True
    capacity: float = 6.9
    charge_power: float = 3.5
    discharge_power: float = 3.5
    round_trip: float = 90.


def validate_heating(h):
    for value in vars(h).values():
        if isinstance(value, (float, int)) and not math.isfinite(value):
            raise ValueError("Nur endliche Eingabewerte erlaubt.")
    if min(h.household, h.heat, h.hot_water, h.cooling, h.capacity, h.charge_power, h.discharge_power) < 0:
        raise ValueError("Energie und Speichergrößen dürfen nicht negativ sein.")
    if min(h.split_jaz, h.water_jaz, h.dhw_jaz, h.seer) < 1:
        raise ValueError("JAZ und SEER müssen mindestens 1 sein.")
    if not 0 < h.round_trip <= 100 or not 0 <= h.water_fraction <= 100 or not 0 <= h.hybrid_split_fraction <= 100:
        raise ValueError("Ungültige Wirkungsgrade oder Wärmeanteile.")
    if h.household_profile not in ("Morgens und abends", "Tagsüber anwesend", "Gleichmäßig") or h.dhw_schedule not in ("Mittags", "Morgens und abends"):
        raise ValueError("Unbekanntes Lastprofil.")


@lru_cache(maxsize=1)
def weather():
    with Path(__file__).with_name("weather_2023.csv").open() as file:
        return tuple((datetime.fromisoformat(r["time_utc"]).astimezone(ZoneInfo("Europe/Berlin")),
                      float(r["roof_kwh"]), float(r["wall_kwh"]), float(r["temperature_c"]))
                     for r in csv.DictReader(file))


def scaled(weights, annual):
    total = sum(weights)
    return [x * annual / total if total else 0. for x in weights]


@lru_cache(maxsize=64)
def profiles(h):
    validate_heating(h)
    house, heat, dhw, cool = [], [], [], []
    for dt, roof, wall, temp in weather():
        hour = dt.hour
        if h.household_profile == "Gleichmäßig":
            house.append(1.)
        elif h.household_profile == "Tagsüber anwesend":
            house.append(1.4 if 8 <= hour <= 21 else .6)
        else:
            house.append(2. if hour in (6,7,8,17,18,19,20,21) else (.8 if 9 <= hour <= 16 else .5))
        # Degree-hour load proxy; annual useful heat and annual JAZ remain user inputs.
        heat.append(max(18-temp, 0.) * max(.7, min(1.5, 1+.02*(7-temp))) if temp < 15 else 0.)
        dhw.append(1. if (11 <= hour <= 14 if h.dhw_schedule == "Mittags" else hour in (6,7,18,19)) else 0.)
        cool.append(max(temp-22, 0.) if 10 <= hour <= 22 else 0.)
    return (scaled(house, h.household), scaled(heat, 1.), scaled(dhw, 1.), scaled(cool, 1.))


def simulate(h, variant, generation=7060., shading=0., detail=False):
    validate_heating(h)
    if variant not in VARIANTS or not math.isfinite(generation) or generation < 0 or not 0 <= shading <= 100:
        raise ValueError("Ungültige Variante oder Erzeugung.")
    hh, hw, dw, cw = profiles(h)
    if variant == VARIANTS[0]:
        split_share = 1-h.water_fraction/100
    elif variant == VARIANTS[1]:
        split_share = 0.
    else:
        split_share = h.hybrid_split_fraction/100
    heat_electric = h.heat * (split_share/h.split_jaz + (1-split_share)/h.water_jaz)
    dhw_electric = h.hot_water / h.dhw_jaz
    cooling_delivered = h.cooling if variant != VARIANTS[1] or h.central_cooling else 0.
    cool_electric = cooling_delivered / h.seer
    base = sum(x[1]+x[2] for x in weather())
    pv_factor = generation * (1-shading/100) / base
    efficiency = math.sqrt(h.round_trip/100)
    capacity = h.capacity if h.battery else 0.
    soc = 0.
    keys = ("pv", "household", "heat", "dhw", "cool", "load", "direct", "charge", "discharge", "loss", "export", "grid")
    totals = dict.fromkeys(keys, 0.)
    monthly = [dict(month=i+1, **dict.fromkeys(keys, 0.)) for i in range(12)]
    hourly = []
    for i, (dt, roof, wall, temp) in enumerate(weather()):
        pv = (roof+wall)*pv_factor
        heating, dhw, cooling = hw[i]*heat_electric, dw[i]*dhw_electric, cw[i]*cool_electric
        load = hh[i]+heating+dhw+cooling
        direct = min(pv, load)
        charge = min(max(pv-load, 0.), h.charge_power, max(0., capacity-soc)/efficiency) if capacity else 0.
        soc += charge*efficiency
        discharge = min(max(load-pv, 0.), h.discharge_power, soc*efficiency) if capacity else 0.
        soc -= discharge/efficiency
        loss = charge*(1-efficiency) + discharge*(1/efficiency-1)
        row = dict(pv=pv, household=hh[i], heat=heating, dhw=dhw, cool=cooling, load=load,
                   direct=direct, charge=charge, discharge=discharge, loss=loss,
                   export=max(0., pv-direct-charge), grid=max(0., load-direct-discharge))
        for k, v in row.items():
            totals[k] += v
            monthly[dt.month-1][k] += v
        if detail:
            hourly.append(dict(time=dt.isoformat(), temperature=temp, soc=soc, **row))
    used = totals["direct"]+totals["discharge"]
    return dict(totals=totals, monthly=monthly, hourly=hourly, end_soc=soc,
                own_pct=100*used/totals["pv"] if totals["pv"] else 0.,
                autonomy_pct=100*used/totals["load"] if totals["load"] else 0.,
                cooling_delivered=cooling_delivered)


@lru_cache(maxsize=64)
def annual_totals(h, variant, generation, shading, degradation, years):
    return tuple(simulate(h, variant, generation*(1-degradation/100)**year, shading)["totals"]
                 for year in range(years))


def financial(h, variant, a, shading, extra_annual=0., extra_replacement=0., extra_replacement_year=13):
    """Re-simulate battery dispatch as PV degrades, with unchanged useful heat."""
    from model import sustained_payback
    balance = discounted = -a.investment
    rows = [dict(year=0, net=-a.investment, balance=balance, discounted_balance=discounted)]
    for year, t in enumerate(annual_totals(h, variant, a.generation, shading, a.degradation, a.years), 1):
        avoided = (t["direct"]+t["discharge"])*a.power_price/100*(1+a.power_growth/100)**(year-1)
        feed = t["export"]*a.feed_price/100*(1-a.feed_discount/100) if year <= a.feed_years else 0.
        operating = (a.annual_cost+extra_annual)*(1+a.cost_growth/100)**(year-1)
        replacement = a.replacement_cost if a.replacement_mode == "Mit Ersatzkosten" and year == a.replacement_year else 0.
        if year == extra_replacement_year:
            replacement += extra_replacement
        net = avoided+feed-operating-replacement
        balance += net
        discounted += net/(1+a.discount/100)**year
        rows.append(dict(year=year, net=net, avoided=avoided, feed=feed, operating=operating,
                         replacement=replacement, balance=balance, discounted_balance=discounted))
    return dict(rows=rows, payback=sustained_payback(rows, "balance"), npv=discounted)
