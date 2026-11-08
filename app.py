"""Run: python -m streamlit run app.py --server.address 127.0.0.1"""
from dataclasses import asdict
import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from model import Assumptions, calculate, validate
from heating_ui import HEAT_DEFAULTS, draw as draw_heating
from heating_model import Heating, validate_heating
from storage_model import Storage, SIZES, validate_storage
from storage_ui import STORAGE_DEFAULTS

st.set_page_config(page_title="PV · Dach & Fassade", page_icon="☀️", layout="wide")
DEFAULTS = dict(asdict(Assumptions()), shades=[0., 10., 20., 30.], shares=[40., 55., 70.], **HEAT_DEFAULTS, **STORAGE_DEFAULTS)
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)


def money(value):
    return f"{value:,.0f} €".replace(",", ".")


def duration(value, years):
    return f"{value:.1f} Jahre".replace(".", ",") if value is not None else f"nicht binnen {years} Jahren"


def load_settings():
    try:
        data = json.loads(st.session_state.settings_upload.getvalue())
        schema = data.get("schema")
        if schema not in (1, 2, 3):
            raise ValueError("Unbekanntes Einstellungsformat.")
        data = data["settings"]
        if schema == 1:
            data = dict(HEAT_DEFAULTS, **data)
        if schema in (1, 2):
            # Older free-form capacity migrates to the nearest supported class.
            size = min(SIZES, key=lambda k: abs(SIZES[k][0]-data["h_capacity"]))
            data = dict(STORAGE_DEFAULTS, **data, b_size=size)
            data["h_capacity"] = SIZES[size][0]
        if set(data) != set(DEFAULTS):
            raise ValueError("Unvollständige oder unbekannte Felder.")
        a = Assumptions(**{k: data[k] for k in asdict(Assumptions())})
        validate_storage(Storage(**{k: data[f"b_{k}"] for k in asdict(Storage())}), a)
        if not isinstance(data["h_battery"], bool) or not isinstance(data["h_central_cooling"], bool):
            raise ValueError("Batterie-/Kühlschalter müssen Wahrheitswerte sein.")
        if abs(data["h_capacity"]-SIZES[data["b_size"]][0]) > .00001:
            raise ValueError("Kapazität passt nicht zur gewählten Speicherklasse.")
        validate_heating(Heating(**{k: data[f"h_{k}"] for k in asdict(Heating())}))
        for k in ("household", "heat", "hot_water", "cooling"):
            if not 0 <= data[f"h_{k}"] <= (100000 if k in ("household", "heat") else 50000):
                raise ValueError("Wärme-/Verbrauchswert außerhalb des Eingabebereichs.")
        for k in ("split_jaz", "water_jaz", "dhw_jaz", "seer"):
            if not 1 <= data[f"h_{k}"] <= 10:
                raise ValueError("JAZ/SEER außerhalb des Eingabebereichs.")
        if data["h_capacity"] > 100 or max(data["h_charge_power"], data["h_discharge_power"]) > 50 or data["h_round_trip"] < 1:
            raise ValueError("Speicherwert außerhalb des Eingabebereichs.")
        if len(data["shades"]) != 4 or len(data["shares"]) != 3:
            raise ValueError("Vier Verluststufen und drei Eigenverbrauchsquoten erforderlich.")
        for shade in data["shades"]:
            for share in data["shares"]:
                validate(a, shade, share)
        # Validate against widget ranges before changing any state.
        for key in ("offer", "scaffold", "extras", "grant", "generation", "annual_cost", "replacement_cost"):
            if not 0 <= data[key] <= 1000000:
                raise ValueError(f"{key}: außerhalb des Eingabebereichs.")
        for key in ("power_price", "feed_price"):
            if not 0 <= data[key] <= 200:
                raise ValueError(f"{key}: außerhalb des Eingabebereichs.")
        for key in ("power_growth", "cost_growth"):
            if not -20 <= data[key] <= 20:
                raise ValueError(f"{key}: außerhalb des Eingabebereichs.")
        if not 0 <= data["discount"] <= 20 or not 1 <= data["replacement_year"] <= 50:
            raise ValueError("Abzinsung oder Ersatzjahr außerhalb des Eingabebereichs.")
        for key in ("years", "feed_years", "replacement_year"):
            if not isinstance(data[key], int):
                raise ValueError(f"{key}: Ganzzahl erforderlich.")
        st.session_state.update(data)
        for i, v in enumerate(data["shades"]):
            st.session_state[f"shade_{i}"] = float(v)
        for i, v in enumerate(data["shares"]):
            st.session_state[f"share_{i}"] = float(v)
        st.session_state.import_message = "Einstellungen geladen." + (" Ältere Speichergröße auf die nächste 7/14/21-kWh-Klasse übertragen." if schema < 3 else "")
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        st.session_state.import_message = f"Import abgelehnt: {exc}"


def number(label, key, low=0., high=1000000., step=100., help=None):
    return st.number_input(label, min_value=low, max_value=high, step=step, key=key, help=help)


with st.sidebar:
    st.title("Annahmen")
    st.caption("Belegt: Angebot und Tarif. Alle übrigen Werte sind veränderbare Szenarien.")
    with st.expander("Investition · €", expanded=True):
        number("Angebot inkl. Speicher · belegt", "offer")
        number("Gerüst · Annahme", "scaffold")
        number("Weitere Zusatzkosten", "extras")
        number("Zuschuss / Investitionsminderung", "grant")
    with st.expander("Erzeugung & Eigenverbrauch", expanded=True):
        number("Jahresertrag ohne zusätzliche Verschattung · kWh", "generation", step=50.)
        for i in range(4):
            st.session_state.setdefault(f"shade_{i}", st.session_state.shades[i])
            number(f"Verluststufe {i + 1} · %", f"shade_{i}", 0., 100., 1.)
        for i in range(3):
            st.session_state.setdefault(f"share_{i}", st.session_state.shares[i])
            number(f"Eigenverbrauchsquote {i + 1} · %", f"share_{i}", 0., 100., 1.)
        number("Zusätzliche Speicherverluste · % der PV-Erzeugung", "storage_loss", 0., 100., 1.)
        st.caption("Eigenverbrauch = Strom, der tatsächlich im Haushalt ankommt. Rest nach Eigenverbrauch und Speicherverlusten = Einspeisung.")
        st.caption("Die drei Quoten und der pauschale Speicherverlust steuern nur den bisherigen Variantenvergleich. Im Tab ›Heizung & Speicher‹ entstehen diese Werte aus der Stundenrechnung.")
    with st.expander("Bezug & Einspeisung", expanded=True):
        number("Arbeitspreis brutto · ct/kWh · dokumentiert", "power_price", 0., 200., .1)
        number("Strompreisänderung · %/Jahr", "power_growth", -20., 20., .5)
        st.selectbox("Vergütungsgrundlage", ["2026-Referenz", "Spätere Inbetriebnahme – Annahme", "Eigene Annahme"], key="tariff_basis")
        number("Einspeisevergütung · ct/kWh", "feed_price", 0., 200., .1)
        st.number_input("Vergütungsdauer · volle Modelljahre", 0, 50, key="feed_years")
        number("Abschlag auf Einspeiseerlöse · %", "feed_discount", 0., 100., 1.,
               help="Pauschales Szenario, z. B. für zeitweise unvergütete Einspeisung. Kein berechneter Abregelungsverlust.")
    with st.expander("Betrieb, Alterung & Ersatz"):
        number("Laufende Kosten · €/Jahr", "annual_cost", step=10.)
        number("Kostensteigerung · %/Jahr", "cost_growth", -20., 20., .5)
        number("Ertragsrückgang · %/Jahr", "degradation", 0., 100., .1)
        st.selectbox("Ersatzkostenszenario", ["Mit Ersatzkosten", "Ohne Ersatzkosten"], key="replacement_mode")
        number("Ersatzkosten · € zum Ersatzzeitpunkt", "replacement_cost")
        st.number_input("Ersatz im Modelljahr", 1, 50, key="replacement_year")
    with st.expander("Zeitraum & Abzinsung"):
        st.number_input("Betrachtungszeitraum · Jahre", 1, 50, key="years")
        number("Abzinsung · %/Jahr", "discount", 0., 20., .5)
    st.file_uploader("Gespeicherte Einstellungen laden", type="json", key="settings_upload", on_change=load_settings)
    if "import_message" in st.session_state:
        st.caption(st.session_state.import_message)

st.title("PV · Dach & Fassade")
st.caption("Amortisation und Szenarien · Planungsstand 08.11.2026 · lokale Berechnung")
a = Assumptions(**{k: st.session_state[k] for k in asdict(Assumptions())})
shades = [st.session_state[f"shade_{i}"] for i in range(4)]
shares = [st.session_state[f"share_{i}"] for i in range(3)]
st.session_state.shades, st.session_state.shares = shades, shares
try:
    for shade in shades:
        for share in shares:
            validate(a, shade, share)
    if len(set(shades)) < 4 or len(set(shares)) < 3:
        raise ValueError("Bitte unterschiedliche Verluststufen und Eigenverbrauchsquoten eingeben.")
except ValueError as exc:
    st.error(str(exc))
    st.stop()

if a.tariff_basis == "2026-Referenz":
    st.info("7,70 ct/kWh sind für Überschusseinspeisung bis 10 kWp bei Inbetriebnahme 01.08.–31.12.2026 belegt. Der einstellbare Satz ist für 2027 nicht zugesichert.")
    if abs(a.feed_price - 7.7) > .00001:
        st.warning("Der eingestellte Vergütungssatz weicht von der belegten 2026-Referenz ab.")
else:
    st.warning("Vergütung ist hier eine eigene Zukunftsannahme. Satz und Laufzeit vor einer Investitionsentscheidung aktualisieren.")

metrics = {"Einfache Amortisation": "simple", "Amortisation im Jahresmodell": "payback",
           "Abgezinste Amortisation": "discounted_payback", "Kapitalwert": "npv", "Nettoüberschuss im ersten Jahr": "first_net"}
metric = st.selectbox("Kennzahl im Variantenvergleich", list(metrics), index=1)
st.caption({"Einfache Amortisation": "Investition geteilt durch den Nettoüberschuss des ersten Jahres. Spätere Alterung und Ersatzkosten bleiben in dieser Kennzahl unberücksichtigt.",
    "Amortisation im Jahresmodell": "Zeitpunkt der Kostendeckung mit jährlichem Ertragsrückgang und gewählten Ersatzkosten. Die Investition wird nicht verzinst.",
    "Abgezinste Amortisation": "Kostendeckung nach Berücksichtigung des Zeitwerts des Geldes: spätere Einsparungen zählen weniger als heutige.",
    "Kapitalwert": "Summe aller abgezinsten Überschüsse abzüglich Anfangsinvestition. Positiv: mehr als die eingestellte Verzinsungsanforderung; negativ: diese wird nicht erreicht.",
    "Nettoüberschuss im ersten Jahr": "Vermiedene Strombezugskosten plus Einspeiseerlöse minus laufende Kosten und gegebenenfalls Ersatzkosten in Jahr 1."}[metric])
results, export_rows, matrix = {}, [], []
for shade in shades:
    line = {"Ertragsverlust": f"{shade:g} % · {a.generation * (1-shade/100):,.0f} kWh".replace(",", ".")}
    for share in shares:
        r = calculate(a, shade, share)
        results[(shade, share)] = r
        key = metrics[metric]
        val = r["first"]["net"] if key == "first_net" else r[key]
        line[f"{share:g} % Eigenverbrauch"] = money(val) if key in ("npv", "first_net") else duration(val, a.years)
        export_rows.append(dict(Ertragsverlust_Prozent=shade, Eigenverbrauch_Prozent=share,
            Ertrag_kWh=r["first"]["generation"], Netto_Jahr1_EUR=r["first"]["net"],
            Einfache_Amortisation_Jahre=r["simple"], Amortisation_Modell_Jahre=r["payback"],
            Amortisation_abgezinst_Jahre=r["discounted_payback"], Kapitalwert_EUR=r["npv"]))
    matrix.append(line)
st.dataframe(pd.DataFrame(matrix), hide_index=True, width="stretch")
st.caption("Amortisation im Jahresmodell: ab diesem Zeitpunkt bleibt der kumulierte Saldo bis zum Ende des gewählten Zeitraums positiv. Jahresbruchteile sind linear interpoliert. Ersatzkosten können eine frühere Kostendeckung wieder aufheben.")

col1, col2 = st.columns(2)
shade = col1.selectbox("Detail · Ertragsverlust", shades, format_func=lambda v: f"{v:g} %")
share = col2.selectbox("Detail · Eigenverbrauch", shares, index=1, format_func=lambda v: f"{v:g} %")
r = results[(shade, share)]
c1, c2, c3 = st.columns(3)
c1.metric("Anfangsinvestition", money(a.investment))
c2.metric("Nettoüberschuss · Jahr 1", money(r["first"]["net"]))
c3.metric(f"Kapitalwert · {a.years} Jahre", money(r["npv"]))

tab1, tab2, tab3, tab_heat, tab4 = st.tabs(["Zahlungsverlauf", "Solarstrom & Nutzen", "Strompreis-Sensitivität", "Heizung & Speicher", "Modell & Quellen"])
with tab1:
    discounted = st.radio("Darstellung", ["Nominal", "Abgezinst"], horizontal=True) == "Abgezinst"
    balance_key = "discounted_balance" if discounted else "balance"
    series = []
    for s in shades:
        for row in results[(s, share)]["rows"]:
            series.append({"Jahr": row["year"], "Saldo (€)": row[balance_key], "Ertragsverlust": f"{s:g} %"})
    data = pd.DataFrame(series)
    chart = alt.Chart(data).mark_line(point=True).encode(
        x=alt.X("Jahr:Q", axis=alt.Axis(tickMinStep=1)), y=alt.Y("Saldo (€):Q"),
        color="Ertragsverlust:N", strokeDash="Ertragsverlust:N", tooltip=list(data.columns))
    zero = alt.Chart(pd.DataFrame({"Null": [0]})).mark_rule(color="gray").encode(y="Null:Q")
    st.altair_chart((chart + zero).properties(height=360), width="stretch")
    st.caption(f"Alle vier Ertragsfälle bei {share:g} % Eigenverbrauch. Abzinsung: {a.discount:g} %. Ersatzkosten werden am Ende des eingestellten Jahres verbucht.")
    st.caption(f"Die Null-Linie bedeutet: Die anfängliche PV-Investition ist zurückverdient. Der Knick in Jahr {a.replacement_year} entsteht bei aktiviertem Ersatzkostenszenario durch die angenommenen {money(a.replacement_cost)}. Das ist eine Annahme und kein vorhergesagter Defekt.")
with tab2:
    first = r["first"]
    energy = pd.DataFrame([{"Jahr": "Jahr 1", "Verwendung": name, "kWh": first[key]} for name, key in
                          [("Eigenverbrauch", "own"), ("Speicherverluste", "losses"), ("Einspeisung", "export")]])
    st.altair_chart(alt.Chart(energy).mark_bar().encode(x="kWh:Q", y="Jahr:N", color="Verwendung:N",
                     tooltip=["Verwendung", alt.Tooltip("kWh:Q", format=".0f")]).properties(height=150), width="stretch")
    st.dataframe(pd.DataFrame({"Bestandteil · Jahr 1": ["PV-Erzeugung (kWh)", "Nutzbarer Eigenverbrauch (kWh)", "Speicherverluste (kWh)", "Einspeisung (kWh)", "Vermiedene Bezugskosten (€)", "Einspeiseerlöse (€)", "Betriebskosten (€)", "Ersatzkosten (€)", "Nettoüberschuss (€)"],
        "Wert": [first[k] for k in ("generation", "own", "losses", "export", "avoided", "feed", "operating", "replacement", "net")]}).round(2), hide_index=True)
    st.caption("Eigenverbrauch und Speicherverluste sind feste Jahresanteile als Sensitivität. Keine automatische Speicheroptimierung, keine Lastprofil- oder Autarkieprognose.")
with tab3:
    method = st.radio("Sensitivität · Kennzahl", ["Einfache Amortisation", "Amortisation im Jahresmodell"], horizontal=True)
    price_rows = []
    for price in range(20, 46):
        other = Assumptions(**dict(asdict(a), power_price=float(price)))
        for s in shades:
            result = calculate(other, s, share)
            price_rows.append({"Strompreis (ct/kWh)": price, "Amortisation (Jahre)": result["simple" if method == "Einfache Amortisation" else "payback"], "Ertragsverlust": f"{s:g} %"})
    df = pd.DataFrame(price_rows)
    st.altair_chart(alt.Chart(df).mark_line(point=True).encode(x="Strompreis (ct/kWh):Q", y="Amortisation (Jahre):Q", color="Ertragsverlust:N", strokeDash="Ertragsverlust:N", tooltip=list(df.columns)).properties(height=330), width="stretch")
    st.caption("Fehlende Punkte: keine Amortisation innerhalb des Modellzeitraums bzw. kein positiver Jahresüberschuss. Preisänderung pro Jahr bleibt wie links eingestellt.")
with tab4:
    st.markdown("""**Berechnungsgrundlage**

    - 8,37 kWp: Dach 5,58 kWp / 38° / Südwest; Fassade 2,79 kWp / 90° / Südost.
    - PVGIS 5.3 / SARAH3, 2005–2023, ungefähr 50,90° N / 7,87° E. 14 % Systemverluste bereits im Ertrag enthalten. Zusätzliche Speicherverluste werden erst hier abgezogen.
    - Ausgangswert 7.060 kWh gerundet aus 7.062 kWh; Gelände, Bäume und Gebäude noch nicht simuliert. Winkel sind dokumentierte Eingaben der Vorrechnung, keine Live-PVGIS-Steuerung.
    - Im Quotenmodell: Eigenverbrauch = Erzeugung × Quote. Einspeisung = Erzeugung − Eigenverbrauch − Speicherverluste. Der Tab Heizung & Speicher rechnet stattdessen stündliche Lasten und Batterieflüsse.
    - Jahresnutzen = vermiedene Bezugskosten + vergütete Einspeisung − Betriebskosten − Ersatzkosten.
    - Kapitalwert = negative Anfangsinvestition + Summe der abgezinsten jährlichen Zahlungsüberschüsse.
    - Vergütung für volle Modelljahre; nach Ablauf 0 €. Inbetriebnahme-Restjahr und eventuelle Verlängerung nicht modelliert. Abschlag auf Einspeiseerlöse ist eine Annahme; 60-%-Begrenzung und negative Preisstunden sind nicht stundengenau simuliert.
    - Mainova: 30,60 ct/kWh brutto aus Nutzerauszug 27.10.2026. Preisgarantiedauer offen. Der Grundpreis 164,62 €/Jahr bleibt bestehen und wird nicht als PV-Ersparnis gezählt.
    - Keine Finanzierung, Steuererstattung, dynamisches Netzladen oder Restwert. Ersatzkosten sind ein Szenario, keine Lebensdauerzusage. Alle Eurobeträge nominal; Strom-/Kostensteigerung und Diskontsatz konsistent wählen.

    **Quellen (geprüft 08.11.2026)**

    [Bundesnetzagentur · Fördersätze](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/ErneuerbareEnergien/EEG_Foerderung/start.html) ·
    [EU-PVGIS · Rechenparameter](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/api-non-interactive-service_en)

    Lokal: Mainova_Vertragsstand_und_WP_Optionen_2026-10-27.md und Weiss-Angebot 2026-09-441-V2. Die veröffentlichte Vergütung betrifft Inbetriebnahme 01.08.–31.12.2026. Für spätere Inbetriebnahme Satz und Rechtslage neu prüfen.
    """)

with tab_heat:
    draw_heating(a, shades, money, duration)

with st.expander("Jahresrechnung · ausgewählte Kombination"):
    annual = pd.DataFrame(r["rows"]).rename(columns={"year": "Jahr", "generation": "PV_kWh", "own": "Eigenverbrauch_kWh", "losses": "Speicherverlust_kWh", "export": "Einspeisung_kWh", "avoided": "Bezug_gespart_EUR", "feed": "Verguetung_EUR", "operating": "Betrieb_EUR", "replacement": "Ersatz_EUR", "net": "Netto_EUR", "discounted_net": "Netto_abgezinst_EUR", "balance": "Saldo_EUR", "discounted_balance": "Saldo_abgezinst_EUR"})
    st.dataframe(annual.round(2), hide_index=True)
settings = dict(asdict(a), shades=shades, shares=shares, **{k: st.session_state[k] for k in HEAT_DEFAULTS}, **{k: st.session_state[k] for k in STORAGE_DEFAULTS})
left, middle, right = st.columns(3)
left.download_button("Einstellungen · JSON", json.dumps({"schema": 3, "settings": settings}, ensure_ascii=False, indent=2), "pv-einstellungen.json", "application/json")
middle.download_button("12 Varianten · CSV", pd.DataFrame(export_rows).to_csv(index=False, sep=";", decimal=","), "pv-varianten.csv", "text/csv")
right.download_button("Jahresrechnung · CSV", annual.to_csv(index=False, sep=";", decimal=","), "pv-jahresrechnung.csv", "text/csv")
