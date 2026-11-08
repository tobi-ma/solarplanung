"""Streamlit heating comparison, kept separate from the fixed-share calculator."""
from dataclasses import asdict
import json
import altair as alt
import pandas as pd
import streamlit as st
from heating_model import Heating, VARIANTS, simulate, financial
from storage_model import validate_storage, storage_financial
from storage_ui import controls as storage_controls, settings as storage_settings, draw as draw_storage

HEAT_DEFAULTS = {f"h_{k}": v for k, v in asdict(Heating()).items()}
MONTHS = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]


def heating_settings():
    return Heating(**{k: st.session_state[f"h_{k}"] for k in asdict(Heating())})


def controls(primary=False):
    with st.expander("Weitere Annahmen · Verbrauch, Heiztechnik und Batterie", expanded=False):
        left, right = st.columns(2)
        with left:
            st.number_input("Haushaltsstrom ohne Heizung/Kühlung · kWh/Jahr", 0., 100000., step=100., key="h_household")
            st.number_input("Nutzwärme Raumheizung · kWh Wärme/Jahr", 0., 100000., step=1000., key="h_heat")
            st.number_input("Nutzwärme Warmwasser · kWh Wärme/Jahr", 0., 50000., step=100., key="h_hot_water")
            st.number_input("Kühlbedarf · kWh Kälte/Jahr", 0., 50000., step=100., key="h_cooling")
            st.selectbox("Haushaltsprofil", ["Morgens und abends", "Tagsüber anwesend", "Gleichmäßig"], key="h_household_profile")
            st.selectbox("Warmwasserladung", ["Mittags", "Morgens und abends"], key="h_dhw_schedule")
            st.caption("Wärme/Kälte ist die ans Haus abgegebene Energie. Der Strombedarf ist kleiner: Wärme ÷ JAZ bzw. Kälte ÷ SEER. Warmwasserladung verteilt sich auf vier vorgegebene Stunden; kein detailliertes Trinkwasserspeichermodell.")
        with right:
            for key, label in [("split_jaz", "JAZ Split-Heizung"), ("water_jaz", "JAZ Luft-Wasser-Raumheizung"), ("dhw_jaz", "JAZ Warmwasser"), ("seer", "SEER Kühlung")]:
                st.number_input(label, 1., 10., step=.1, key=f"h_{key}")
            st.number_input("FBH-Anteil an Raumwärme · Split-Variante · %", 0., 100., step=5., key="h_water_fraction")
            st.number_input("Split-Heizanteil · Zentral-WP + Splits · %", 0., 100., step=5., key="h_hybrid_split_fraction")
            st.checkbox("Zentrale WP kann die angesetzte Kühlung liefern", key="h_central_cooling")
            st.caption("JAZ/SEER sind einstellbare Jahreswirkungsgrade. Der Raumwärmebedarf ist für alle Varianten gleich und wird auf die Geräte aufgeteilt. Effizienz ist keine bestätigte Geräteeigenschaft.")
        if not primary:
            st.checkbox("Batterie verwenden", key="h_battery")
        storage_controls(show_size=not primary, show_prices=not primary)
        c1, c2, c3, c4 = st.columns(4)
        c1.number_input("Nutzbare Kapazität · kWh", 0., 100., step=.1, key="h_capacity", disabled=True)
        c2.number_input("Ladeleistung · kW", 0., 50., step=.1, key="h_charge_power")
        c3.number_input("Entladeleistung · kW", 0., 50., step=.1, key="h_discharge_power")
        c4.number_input("Speicher-Rundlaufwirkungsgrad · %", 1., 100., step=1., key="h_round_trip")
        st.caption("Zuerst direkter PV-Verbrauch, dann Überschussladung, später Entladung bei Strombedarf. Keine Netzladung. Der pauschale Speicherverlust von links gilt nur im bisherigen Quotenmodell; hier ersetzen ihn die simulierten Lade-/Entladeverluste.")
def draw(a, shades, money, duration, selection=None, show_controls=True, include_storage=True):
    st.subheader("Heizvarianten und Stromverbrauch")
    st.caption("PV-Zeitverlauf und Temperatur aus PVGIS 2023, monatlich auf die bisherige Ertragsabschätzung normiert. Verbrauch und Effizienz sind veränderbare Annahmen.")
    if show_controls:
        controls()
    h = heating_settings()
    s = storage_settings()
    try:
        validate_storage(s, a)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    if not h.central_cooling and h.cooling:
        st.warning("Die Zentral-WP ohne Splits liefert aktuell keine Kühlung. Ihr niedrigerer Stromverbrauch bedeutet daher teilweise weniger Komfort. Für einen Vergleich bei gleicher Kühlleistung die Kühlfähigkeit aktivieren oder den Kühlbedarf auf 0 setzen.")
    st.caption("Alle unbekannten Verbrauchswerte sind Startannahmen. Im Heizvergleich berücksichtigt ›Batterie verwenden‹ jetzt auch den eingestellten Minderpreis bzw. Klassen-Aufpreis und die Batterie-Zusatzkosten. Der ursprüngliche Quotenvergleich oben bleibt separat.")
    records, simulations = [], {}
    with st.spinner("Stündliche Energiebilanzen und Jahresmodelle berechnen …"):
        for shade in shades:
            for variant in VARIANTS:
                sim = simulate(h, variant, a.generation, shade)
                simulations[(shade, variant)] = sim
                t = sim["totals"]
                fin = storage_financial(h, variant, a, shade, s)
                grid_cost = t["grid"]*a.power_price/100
                feed = t["export"]*a.feed_price/100*(1-a.feed_discount/100) if a.feed_years else 0.
                records.append({"Variante": variant, "Verlust %": shade, "Verbrauch kWh": t["load"],
                    "Netzbezug kWh": t["grid"], "Einspeisung kWh": t["export"],
                    "Eigenverbrauch %": sim["own_pct"], "Autarkie %": sim["autonomy_pct"],
                    "Stromsaldo €/Jahr": grid_cost-feed,
                    "PV-Nutzen netto €/Jahr": fin["rows"][1]["net"],
                    "PV-Amortisation": duration(fin["payback"], a.years), "PV-Kapitalwert €": fin["npv"]})
    st.subheader("Vier Ertragsfälle × drei Heizvarianten")
    st.dataframe(pd.DataFrame(records).round(1), hide_index=True, width="stretch")
    st.caption("Stromsaldo = Kosten des verbleibenden Netzbezugs minus Einspeiseerlöse, ohne unveränderten Grundpreis und Heizungswartung. PV-Nutzen = Vorteil gegenüber derselben Heizung ohne PV, abzüglich PV-Betriebskosten. Ein höherer Strombedarf kann den PV-Nutzen steigern und trotzdem höhere Gesamtkosten verursachen.")
    st.caption("PV-Amortisation/Kapitalwert verwenden die PV-Anfangsinvestition von links, korrigiert um Minderpreis ohne Speicher bzw. Aufpreis der gewählten Klasse. Heizungsinvestitionen fehlen weiterhin. Pro Jahr wird die Stundenbilanz mit sinkendem PV-Ertrag neu gerechnet; Batteriekapazität bleibt konstant.")
    if selection is None:
        c1, c2 = st.columns(2)
        shade = c1.selectbox("Heizvergleich · Ertragsverlust", shades, format_func=lambda v: f"{v:g} %", key="heat_detail_shade")
        variant = c2.selectbox("Heizvergleich · Detailvariante", VARIANTS, key="heat_detail_variant")
    else:
        shade, variant = selection
    if include_storage:
        draw_storage(h, variant, a, shade, s, money, duration)
    st.markdown("**Weitere Betriebsdetails · aktuell gewählter Batterie-Schalter**")
    sim = simulate(h, variant, a.generation, shade, detail=True)
    t = sim["totals"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Eigenverbrauch der PV", f"{sim['own_pct']:.1f} %")
    c2.metric("Solar gedeckter Verbrauch", f"{sim['autonomy_pct']:.1f} %")
    c3.metric("Verbleibender Netzbezug", f"{t['grid']:,.0f} kWh".replace(",", "."))
    st.caption("Eigenverbrauch: Anteil des PV-Stroms, der direkt oder aus der Batterie im Haus ankommt. Autarkie: Anteil eures gesamten Strombedarfs, der dadurch gedeckt wird. Im Winter kann der erste Wert hoch und der zweite gleichzeitig niedrig sein.")
    monthly = []
    for row in sim["monthly"]:
        used = row["direct"]+row["discharge"]
        monthly.append({"Monat": MONTHS[row["month"]-1], "PV kWh": row["pv"], "Verbrauch kWh": row["load"],
            "Eigenverbrauch %": 100*used/row["pv"] if row["pv"] else 0.,
            "Autarkie %": 100*used/row["load"] if row["load"] else 0., **row})
    months = pd.DataFrame(monthly)
    st.markdown("**Monatliche Erzeugung und Strombedarf**")
    load_chart = months.melt(id_vars="Monat", value_vars=["PV kWh", "Verbrauch kWh"], var_name="Reihe", value_name="kWh")
    st.altair_chart(alt.Chart(load_chart).mark_bar().encode(x=alt.X("Monat:N", sort=MONTHS), y="kWh:Q", xOffset="Reihe:N", color="Reihe:N", tooltip=["Monat", "Reihe", alt.Tooltip("kWh:Q", format=".0f")]).properties(height=260), width="stretch")
    st.caption("Die Balken zeigen Monatssummen zur Orientierung. Nur die stündliche Rechnung entscheidet, wie viel davon zeitgleich nutzbar ist. Sommerüberschüsse können nicht mit Winterbedarf verrechnet werden.")
    quote_chart = months.melt(id_vars="Monat", value_vars=["Eigenverbrauch %", "Autarkie %"], var_name="Quote", value_name="Prozent")
    st.altair_chart(alt.Chart(quote_chart).mark_line(point=True).encode(x=alt.X("Monat:N", sort=MONTHS), y=alt.Y("Prozent:Q", scale=alt.Scale(domain=[0,100])), color="Quote:N", strokeDash="Quote:N", tooltip=["Monat", "Quote", alt.Tooltip("Prozent:Q", format=".1f")]).properties(height=240), width="stretch")
    st.caption("Diese Quoten entstehen aus den Last- und Speicherannahmen. 100 % Eigenverbrauch bedeutet nicht, dass die PV den gesamten Heizstrom liefert.")
    st.markdown("**Eine Beispielwoche im Stundenverlauf**")
    season = st.selectbox("Beispielwoche", ["Winter · Januar", "Sommer · Juli"], key="heat_week")
    selected_month = 1 if season.startswith("Winter") else 7
    week = [row for row in sim["hourly"] if int(row["time"][5:7]) == selected_month and 8 <= int(row["time"][8:10]) <= 14]
    week_df = pd.DataFrame(week).rename(columns={"time": "Zeit", "pv": "PV", "load": "Bedarf", "grid": "Netzbezug", "soc": "Speicherinhalt"})
    wd = week_df.melt(id_vars="Zeit", value_vars=["PV", "Bedarf", "Netzbezug"], var_name="Reihe", value_name="kWh je Stunde")
    st.altair_chart(alt.Chart(wd).mark_line().encode(x="Zeit:T", y="kWh je Stunde:Q", color="Reihe:N", tooltip=["Zeit:T", "Reihe", alt.Tooltip("kWh je Stunde:Q", format=".2f")]).properties(height=250), width="stretch")
    st.caption("Wetterverlauf einer Woche aus 2023, normiert auf den langjährigen Monatsertrag. Die Lastkurve ist modelliert. Stundenmittel glätten kurze Leistungsspitzen und können den Eigenverbrauch überschätzen.")
    st.caption(f"Der Speicher startet leer und endet mit {sim['end_soc']:.2f} kWh. Lade- und Entladeverluste: {t['loss']:.0f} kWh/Jahr. Standby-Verbrauch, Batteriealterung und Netzladung sind nicht modelliert. Eine größere Batterie wird nicht automatisch als wirtschaftlicher bewertet.")
    with st.expander("Monatliche Strommengen und Rechenweg"):
        labels = {"household": "Haushalt kWh", "heat": "Heizung kWh", "dhw": "Warmwasser kWh", "cool": "Kühlung kWh", "direct": "Direktverbrauch kWh", "discharge": "Aus Batterie kWh", "loss": "Speicherverlust kWh", "grid": "Netzbezug kWh", "export": "Einspeisung kWh"}
        st.dataframe(months[["Monat", "PV kWh", "Verbrauch kWh", *labels, "Eigenverbrauch %", "Autarkie %"]].rename(columns=labels).round(1), hide_index=True)
        st.markdown("Heizstrom = aufgeteilte Raumwärme ÷ jeweilige JAZ. Wärme-/Kältestunden werden aus Außentemperatur und Tageszeiten verteilt; die Jahressummen bleiben auf eure Eingaben normiert. Haushaltsprofile sind einfache Tagesmuster. Alle Geräte hängen im Modell am gemeinsamen PV-Zähler und haben denselben Bezugspreis.")
        st.markdown("[PVGIS-Stundendaten](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-tools/hourly-radiation_en) · Referenzjahr 2023, SARAH3, Freudenberg näherungsweise 50,90° N / 7,87° E. Ohne lokale Verschattung; Abschlag wirkt gleichmäßig auf alle Stunden. Das ersetzt keine Baum-/Gebäudesimulation.")
    st.download_button("Heizvergleich · CSV", pd.DataFrame(records).to_csv(index=False, sep=";", decimal=","), "pv-heizvergleich.csv", "text/csv")
    st.download_button("Stundenbilanz · CSV", pd.DataFrame(sim["hourly"]).to_csv(index=False, sep=";", decimal=","), "pv-stundenbilanz.csv", "text/csv")
