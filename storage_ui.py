"""Direct with/without storage comparison and configurable incremental prices."""
from dataclasses import asdict
import altair as alt
import pandas as pd
import streamlit as st
from storage_model import Storage, SIZES, compare_storage

STORAGE_DEFAULTS = {f"b_{k}": v for k, v in asdict(Storage()).items()}


def settings():
    return Storage(**{k: st.session_state[f"b_{k}"] for k in asdict(Storage())})


def apply_size():
    capacity, power = SIZES[st.session_state.b_size]
    st.session_state.h_capacity = capacity
    st.session_state.h_charge_power = power
    st.session_state.h_discharge_power = power


def controls():
    st.selectbox("Speicherklasse · Huawei LUNA-S1", list(SIZES), key="b_size", on_change=apply_size,
                 format_func=lambda x: f"{x} kWh-Klasse · {SIZES[x][0]:g} kWh nutzbar")
    st.caption("7/14/21-kWh-Klassen entsprechen 6,9/13,8/20,7 kWh nutzbar. Beim Klassenwechsel werden Leistungsvorgaben auf 3,5/7/10 kW gesetzt; sie bleiben unten anpassbar. 21er-Batterie: bis 10,5 kW laut Datenblatt, hier auf 10 kW als Systemannahme begrenzt; die konkrete Wechselrichterfreigabe muss Ron bestätigen.")
    st.markdown("**Angebotspreise für den direkten Vergleich**")
    st.number_input("Tatsächlicher Minderpreis ohne Speicher gegenüber 7-kWh-Angebot · €", 0., 1000000., step=100., key="b_discount")
    st.caption("Startwert 3.650 € = bisherige Speicherposition, noch kein bestätigter Minderpreis. Hier den vollständigen Preisunterschied einschließlich entfallender Montage/Zubehör eintragen.")
    c1, c2 = st.columns(2)
    c1.number_input("Aufpreis 14-kWh-Klasse gegenüber 7-kWh-Angebot · €", 0., 1000000., step=100., key="b_upgrade14")
    c2.number_input("Aufpreis 21-kWh-Klasse gegenüber 7-kWh-Angebot · €", 0., 1000000., step=100., key="b_upgrade21")
    st.caption("Aufpreise sind vollständige Preisunterschiede, keine Preise je zusätzlichem Modul. 0 € bedeutet eine unbestätigte Annahme, kein kostenloses Angebot.")
    c1, c2, c3 = st.columns(3)
    c1.number_input("Zusätzliche Batteriekosten · €/Jahr", 0., 1000000., step=10., key="b_annual_extra")
    c2.number_input("Zusätzliche Batterie-Ersatzkosten · €", 0., 1000000., step=100., key="b_replacement_extra")
    c3.number_input("Batterie-Ersatz im Modelljahr", 1, 50, key="b_replacement_year")
    st.caption("Die allgemeine PV-Betriebs-/Ersatzreserve von links gilt für beide Anlagen. Nur die hier eingetragenen zusätzlichen Kosten belasten ausschließlich die Batterie. Eine bereits in der gemeinsamen Reserve enthaltene Batterieposition nicht nochmals eintragen.")


def draw(h, variant, a, shade, s, money, duration):
    st.subheader("Direktvergleich · mit und ohne Speicher")
    comp = compare_storage(h, variant, a, shade, s)
    if s.size > 7 and s.upgrade == 0:
        st.warning("Für die größere Speicherklasse fehlt ein bestätigter Aufpreis. Die Rechnung verwendet aktuell 0 € Aufpreis; die Wirtschaftlichkeit ist damit zu günstig, falls Ron einen Mehrpreis verlangt.")
    st.caption(f"Für {variant}, {shade:g} % Ertragsverlust, {s.size}-kWh-Klasse. Beide Anlagen erhalten identische PV-Erzeugung und Lasten. Der Vergleich wird immer für beide Betriebsweisen gerechnet, unabhängig vom Schalter ›Batterie verwenden‹.")
    table = []
    for label, prefix in [("Mit Speicher", "with"), ("Ohne Speicher", "without")]:
        sim, fin = comp[f"{prefix}_sim"], comp[f"{prefix}_fin"]
        t = sim["totals"]
        table.append({"Ausführung": label, "Investition €": comp[f"{prefix}_investment"],
            "Eigenverbrauch %": sim["own_pct"], "Autarkie %": sim["autonomy_pct"],
            "Netzbezug kWh": t["grid"], "Einspeisung kWh": t["export"],
            "PV-Nutzen Jahr 1 €": fin["rows"][1]["net"],
            "PV-Amortisation": duration(fin["payback"], a.years), "PV-Kapitalwert €": fin["npv"]})
    st.dataframe(pd.DataFrame(table).round(1), hide_index=True, width="stretch")
    st.caption("Investition mit Speicher = ursprüngliches Angebot plus Gerüst/Zusatzkosten minus Zuschuss plus Klassen-Aufpreis. Ohne Speicher wird vom ursprünglichen 7-kWh-Angebot der Minderpreis abgezogen. PV-Amortisation bewertet jeweils die ganze PV-Anlage.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Mehrinvestition nur Speicher", money(comp["extra_investment"]))
    c2.metric("Zusatznutzen Speicher · Jahr 1", money(comp["first_benefit"]))
    c3.metric(f"Speicher-Kapitalwert · {a.years} Jahre", money(comp["npv"]))
    st.markdown(f"**Speicher allein:** einfache Amortisation {duration(comp['simple'], a.years)}; Amortisation im Jahresmodell {duration(comp['payback'], a.years)}.")
    st.caption("Der Zusatznutzen ist die Differenz der jährlichen Nettoüberschüsse: weniger Netzbezug, aber auch weniger Einspeiseerlöse, Ladeverluste und zusätzliche Batteriekosten. Ein positiver Speicher-Kapitalwert bedeutet: Der zusätzliche Nutzen deckt Mehrpreis und gewählte Zusatzkosten einschließlich der eingestellten Abzinsung.")
    data = pd.DataFrame([{"Jahr": row["year"], "Saldo €": row[key], "Darstellung": title}
                         for row in comp["delta"] for key, title in
                         [("balance", "Nominal"), ("discounted_balance", "Abgezinst")]])
    chart = alt.Chart(data).mark_line(point=True).encode(x=alt.X("Jahr:Q", axis=alt.Axis(tickMinStep=1)),
        y="Saldo €:Q", color="Darstellung:N", strokeDash="Darstellung:N", tooltip=["Jahr", "Darstellung", alt.Tooltip("Saldo €:Q", format=".0f")])
    zero = alt.Chart(pd.DataFrame({"Saldo €": [0]})).mark_rule(color="gray").encode(y="Saldo €:Q")
    st.altair_chart((chart+zero).properties(height=260), width="stretch")
    st.caption("Die Linien zeigen ausschließlich den Mehrwert der Batterie gegenüber derselben PV-Anlage ohne Speicher. Start unter null = Mehrpreis. Über null = zurückverdient; ein späterer Knick entsteht durch eingetragene Batterie-Ersatzkosten. Die gemeinsame PV-Reserve fällt aus dieser Differenz heraus.")
    st.download_button("Speichervergleich · CSV", pd.DataFrame(table).to_csv(index=False, sep=";", decimal=","), "pv-speichervergleich.csv", "text/csv")
    return comp
