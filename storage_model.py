"""Incremental storage economics, separate from total PV amortization."""
from dataclasses import dataclass, replace
import math
from heating_model import simulate, financial
from model import sustained_payback

SIZES = {7: (6.9, 3.5), 14: (13.8, 7.), 21: (20.7, 10.)}


@dataclass(frozen=True)
class Storage:
    size: int = 7
    discount: float = 3650.
    upgrade14: float = 0.
    upgrade21: float = 0.
    annual_extra: float = 0.
    replacement_extra: float = 0.
    replacement_year: int = 13

    @property
    def upgrade(self):
        return {7: 0., 14: self.upgrade14, 21: self.upgrade21}[self.size]


def validate_storage(s, a):
    if s.size not in SIZES or not isinstance(s.replacement_year, int) or not 1 <= s.replacement_year <= 50:
        raise ValueError("Speicherklasse muss 7, 14 oder 21 kWh sein; Ersatzjahr 1–50.")
    if any(not math.isfinite(v) or not 0 <= v <= 1000000 for v in
           (s.discount, s.upgrade14, s.upgrade21, s.annual_extra, s.replacement_extra)):
        raise ValueError("Speicherkosten müssen endliche Werte zwischen 0 und 1.000.000 € sein.")
    if s.discount > a.offer or a.investment-s.discount <= 0:
        raise ValueError("Minderpreis darf den Angebotspreis nicht übersteigen; die Investition ohne Speicher muss positiv bleiben.")


def priced_assumptions(a, s, enabled):
    validate_storage(s, a)
    return replace(a, offer=a.offer + (s.upgrade if enabled else -s.discount))


def storage_financial(h, variant, a, shade, s):
    priced = priced_assumptions(a, s, h.battery)
    return financial(h, variant, priced, shade,
                     extra_annual=s.annual_extra if h.battery else 0.,
                     extra_replacement=s.replacement_extra if h.battery else 0.,
                     extra_replacement_year=s.replacement_year)


def compare_storage(h, variant, a, shade, s):
    validate_storage(s, a)
    on, off = replace(h, battery=True), replace(h, battery=False)
    with_sim = simulate(on, variant, a.generation, shade)
    without_sim = simulate(off, variant, a.generation, shade)
    with_fin = storage_financial(on, variant, a, shade, s)
    without_fin = storage_financial(off, variant, a, shade, s)
    delta = []
    for w, n in zip(with_fin["rows"], without_fin["rows"]):
        delta.append(dict(year=w["year"], net=w["net"]-n["net"],
                          balance=w["balance"]-n["balance"],
                          discounted_balance=w["discounted_balance"]-n["discounted_balance"]))
    extra = s.discount+s.upgrade
    benefit = delta[1]["net"]
    return dict(with_sim=with_sim, without_sim=without_sim, with_fin=with_fin, without_fin=without_fin,
                with_investment=a.investment+s.upgrade, without_investment=a.investment-s.discount,
                delta=delta, extra_investment=extra, first_benefit=benefit,
                simple=extra/benefit if benefit > 0 else None,
                payback=sustained_payback(delta, "balance"),
                npv=with_fin["npv"]-without_fin["npv"])
