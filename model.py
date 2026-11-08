"""Transparent annual PV cash-flow model; no external dependencies or network calls."""
from dataclasses import asdict, dataclass
import math


@dataclass
class Assumptions:
    offer: float = 16090.0
    scaffold: float = 2000.0
    extras: float = 0.0
    grant: float = 0.0
    generation: float = 7060.0
    storage_loss: float = 5.0
    power_price: float = 30.60
    power_growth: float = 0.0
    tariff_basis: str = "2026-Referenz"
    feed_price: float = 7.70
    feed_years: int = 20
    feed_discount: float = 0.0
    annual_cost: float = 150.0
    cost_growth: float = 0.0
    degradation: float = 0.4
    replacement_mode: str = "Mit Ersatzkosten"
    replacement_cost: float = 4000.0
    replacement_year: int = 13
    years: int = 20
    discount: float = 3.0

    @property
    def investment(self):
        return self.offer + self.scaffold + self.extras - self.grant


def validate(a, shading, own):
    for key, value in asdict(a).items():
        if isinstance(value, (int, float)) and not math.isfinite(value):
            raise ValueError(f"{key}: nur endliche Zahlen erlaubt.")
    nonnegative = (a.offer, a.scaffold, a.extras, a.grant, a.generation,
                   a.power_price, a.feed_price, a.annual_cost, a.replacement_cost)
    if min(nonnegative) < 0 or a.investment <= 0:
        raise ValueError("Kosten und Erträge müssen nichtnegativ, die Nettoinvestition positiv sein.")
    for value in (a.storage_loss, a.feed_discount, a.degradation, shading, own):
        if not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError("Anteile müssen zwischen 0 und 100 % liegen.")
    if own + a.storage_loss > 100 + 1e-9:
        raise ValueError("Eigenverbrauch und Speicherverluste dürfen zusammen höchstens 100 % betragen.")
    if not 1 <= a.years <= 50 or not 0 <= a.feed_years <= 50:
        raise ValueError("Zeitraum: 1–50 Jahre; Vergütungsdauer: 0–50 Jahre.")
    if a.replacement_year < 1 or any(v <= -100 for v in (a.discount, a.power_growth, a.cost_growth)):
        raise ValueError("Ungültiges Ersatzjahr oder Änderungsrate.")
    if a.tariff_basis not in ("2026-Referenz", "Spätere Inbetriebnahme – Annahme", "Eigene Annahme"):
        raise ValueError("Unbekannte Vergütungsgrundlage.")
    if a.replacement_mode not in ("Mit Ersatzkosten", "Ohne Ersatzkosten"):
        raise ValueError("Unbekanntes Ersatzkostenszenario.")


def sustained_payback(rows, key):
    """First crossing after which year-end balance never becomes negative again.

    Fractional interpolation is an orientation within the crossing year only.
    """
    negative = [i for i, row in enumerate(rows) if row[key] < 0]
    last = max(negative, default=-1)
    if last >= len(rows) - 1:
        return None
    if last < 0:
        return 0.0
    before, after = rows[last][key], rows[last + 1][key]
    return rows[last]["year"] + (-before) / (after - before)


def calculate(a, shading, own):
    validate(a, shading, own)
    balance = discounted = -a.investment
    rows = [dict(year=0, generation=0., own=0., losses=0., export=0.,
                 avoided=0., feed=0., operating=0., replacement=0., net=-a.investment,
                 discounted_net=-a.investment, balance=balance, discounted_balance=discounted)]
    for year in range(1, a.years + 1):
        generation = a.generation * (1 - shading / 100) * (1 - a.degradation / 100) ** (year - 1)
        used = generation * own / 100
        losses = generation * a.storage_loss / 100
        export = max(0., generation - used - losses)
        avoided = used * a.power_price / 100 * (1 + a.power_growth / 100) ** (year - 1)
        feed = export * a.feed_price / 100 * (1 - a.feed_discount / 100) if year <= a.feed_years else 0.
        operating = a.annual_cost * (1 + a.cost_growth / 100) ** (year - 1)
        replacement = a.replacement_cost if a.replacement_mode == "Mit Ersatzkosten" and year == a.replacement_year else 0.
        net = avoided + feed - operating - replacement
        discounted_net = net / (1 + a.discount / 100) ** year
        balance += net
        discounted += discounted_net
        rows.append(dict(year=year, generation=generation, own=used, losses=losses,
                         export=export, avoided=avoided, feed=feed, operating=operating,
                         replacement=replacement, net=net, discounted_net=discounted_net,
                         balance=balance, discounted_balance=discounted))
    first = rows[1]
    return dict(rows=rows, first=first,
                simple=a.investment / first["net"] if first["net"] > 0 else None,
                payback=sustained_payback(rows, "balance"),
                discounted_payback=sustained_payback(rows, "discounted_balance"),
                npv=discounted, final_balance=balance)
