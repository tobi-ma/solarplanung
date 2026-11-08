"""One plant configuration drives the main calculation; sensitivity tabs are explicit."""
from dataclasses import asdict
import json
import altair as alt
import pandas as pd
import streamlit as st
from model import Assumptions, calculate, validate, parse_shading
from heating_model import Heating, VARIANTS, simulate, validate_heating
from heating_ui import HEAT_DEFAULTS, heating_settings, controls as heating_controls, draw as draw_heating
from storage_model import Storage, SIZES, validate_storage, priced_assumptions, storage_financial
from storage_ui import STORAGE_DEFAULTS, PRICE_NOTE, apply_size, apply_price_assumptions, settings as storage_settings, draw as draw_storage

st.set_page_config(page_title="PV · Meine Anlagenrechnung",page_icon="☀️",layout="wide")
DEFAULTS = dict(asdict(Assumptions()),shades=[0.,10.,20.,30.],shares=[40.,55.,70.],**HEAT_DEFAULTS,**STORAGE_DEFAULTS,
                plant_variant=VARIANTS[0],plant_storage=7,plant_shade=0.)
for k,v in DEFAULTS.items():
    st.session_state.setdefault(k,v)


def money(value):
    return f"{value:,.0f} €".replace(",",".")


def duration(value,years):
    return f"{value:.1f} Jahre".replace(".",",") if value is not None else f"nicht binnen {years} Jahren"


def change_storage():
    size = st.session_state.plant_storage
    st.session_state.h_battery = size != 0
    if size:
        st.session_state.b_size = size
        apply_size()


def load_settings():
    try:
        payload = json.loads(st.session_state.settings_upload.getvalue())
        schema,data = payload["schema"],payload["settings"]
        if schema not in (1,2,3,4):
            raise ValueError("Unbekanntes Einstellungsformat.")
        if schema == 1:
            data = dict(HEAT_DEFAULTS,**data)
        if schema <= 2:
            size = min(SIZES,key=lambda k:abs(SIZES[k][0]-data["h_capacity"]))
            data = {**STORAGE_DEFAULTS,**data,"b_size":size,"h_capacity":SIZES[size][0]}
        if schema < 4:
            data = dict(data,plant_variant=VARIANTS[0],plant_storage=data["b_size"] if data["h_battery"] else 0,plant_shade=0.)
        if set(data) != set(DEFAULTS):
            raise ValueError("Unvollständige oder unbekannte Felder.")
        if data["plant_variant"] not in VARIANTS or data["plant_storage"] not in (0,7,14,21):
            raise ValueError("Ungültige Anlagenkonfiguration.")
        if not isinstance(data["h_battery"],bool) or not isinstance(data["h_central_cooling"],bool):
            raise ValueError("Ungültiger Betriebs-/Kühlschalter.")
        if data["h_battery"] != (data["plant_storage"] != 0) or (data["plant_storage"] and data["plant_storage"] != data["b_size"]):
            raise ValueError("Widersprüchliche Speicherangaben.")
        a = Assumptions(**{k:data[k] for k in asdict(Assumptions())})
        h = Heating(**{k:data[f"h_{k}"] for k in asdict(Heating())})
        s = Storage(**{k:data[f"b_{k}"] for k in asdict(Storage())})
        validate(a,data["plant_shade"],0.)
        validate_heating(h)
        validate_storage(s,a)
        if abs(h.capacity-SIZES[s.size][0]) > .00001:
            raise ValueError("Kapazität und Speicherklasse passen nicht zusammen.")
        limits = {"household":100000,"heat":100000,"hot_water":50000,"cooling":50000,"capacity":100,"charge_power":50,"discharge_power":50}
        if any(not 0 <= data[f"h_{k}"] <= limit for k,limit in limits.items()):
            raise ValueError("Verbrauch oder Speicherwert außerhalb des Eingabebereichs.")
        if max(h.split_jaz,h.water_jaz,h.dhw_jaz,h.seer) > 10 or h.round_trip < 1:
            raise ValueError("JAZ/SEER oder Wirkungsgrad außerhalb des Eingabebereichs.")
        for k in ("offer","scaffold","extras","grant","generation","annual_cost","replacement_cost"):
            if not 0 <= data[k] <= 1000000:
                raise ValueError("Betrag außerhalb des Eingabebereichs.")
        if any(not 0 <= data[k] <= 200 for k in ("power_price","feed_price")):
            raise ValueError("Strompreis außerhalb des Eingabebereichs.")
        if any(not -20 <= data[k] <= 20 for k in ("power_growth","cost_growth")) or not 0 <= a.discount <= 20:
            raise ValueError("Änderungsrate außerhalb des Eingabebereichs.")
        if not 1 <= a.replacement_year <= 50 or any(not isinstance(data[k],int) for k in ("years","feed_years","replacement_year")):
            raise ValueError("Jahresangaben müssen passende Ganzzahlen sein.")
        if len(data["shades"]) != 4 or len(set(data["shades"])) != 4 or len(data["shares"]) != 3 or len(set(data["shares"])) != 3:
            raise ValueError("Einzelanalyse braucht vier verschiedene Verluststufen und drei verschiedene Quoten.")
        for shade in data["shades"]:
            for share in data["shares"]:
                validate(a,shade,share)
        st.session_state.update(data)
        st.session_state.plant_shade_input = f"{data['plant_shade']:g} %"
        for i,value in enumerate(data["shades"]):
            st.session_state[f"shade_{i}"] = float(value)
        for i,value in enumerate(data["shares"]):
            st.session_state[f"share_{i}"] = float(value)
        st.session_state.import_message = "Einstellungen geladen."+(" Alte Datei: Heizart und Ertragsverlust der Hauptrechnung bitte prüfen." if schema < 4 else "")
    except (ValueError,TypeError,KeyError,AttributeError) as exc:
        st.session_state.import_message = f"Import abgelehnt: {exc}"


def number(label,key,low=0.,high=1000000.,step=100.,help=None):
    return st.number_input(label,min_value=low,max_value=high,step=step,key=key,help=help)


st.title("Meine PV-Anlage konfigurieren")
st.caption("Oben konfigurieren → direkt darunter Amortisation und Kapitalwert ablesen. Alle Ergebnisse der Hauptrechnung gehören zu dieser einen Auswahl.")
c1,c2,c3 = st.columns([2,1,1])
variant = c1.selectbox("Heizart",VARIANTS,key="plant_variant")
c2.selectbox("Speichergröße",[0,7,14,21],key="plant_storage",on_change=change_storage,
             format_func=lambda n:"Ohne Speicher" if n == 0 else f"{n} kWh-Klasse")
st.session_state.setdefault("plant_shade_input",f"{st.session_state.plant_shade:g} %")
shade_input = c3.selectbox("Ertragsverlust durch Verschattung · %",["0 %","10 %","20 %","30 %"],
                          key="plant_shade_input",accept_new_options=True,
                          help="Vorgabe auswählen oder eigenen Wert eintippen (z. B. 12,5) und mit Enter bestätigen. Erlaubt: 0 bis 100 %.")
c3.caption("0 / 10 / 20 / 30 % wählen oder eigenen Wert eintippen + Enter.")
with st.expander("Angebot und Anlagengröße einstellen",expanded=True):
    c1,c2,c3 = st.columns(3)
    with c1:
        number("Basisangebot mit 7-kWh-Speicher · €","offer")
        number("Gerüst · €","scaffold")
    with c2:
        number("Minderpreis ohne Speicher · €","b_discount")
        number("Jahresertrag vor Verschattung · kWh","generation",step=50.)
    with c3:
        number("Aufpreis 14 kWh · Preisannahme · €","b_upgrade14")
        number("Aufpreis 21 kWh · Preisannahme · €","b_upgrade21")
    st.caption(PRICE_NOTE)
    st.button("Recherchierte Aufpreisannahmen übernehmen",on_click=apply_price_assumptions,
              help="Setzt nur die beiden Aufpreise auf 2.500 / 5.000 €. Praktisch bei früher gespeicherten Einstellungen mit 0 €.")
    st.caption("Der gewählte Speicher bestimmt den Gesamtpreis: Basis + Aufpreis bzw. Basis − Minderpreis. Preise und Herleitung siehe ›Modell & Quellen‹. Der Jahresertrag bestimmt die PV-Erzeugung; Dachwinkel werden hier nicht neu simuliert.")

with st.sidebar:
    st.title("Tarife & Rechenannahmen")
    number("Arbeitspreis brutto · ct/kWh","power_price",0.,200.,.1)
    number("Einspeisevergütung · ct/kWh","feed_price",0.,200.,.1)
    st.number_input("Betrachtungszeitraum · Jahre",1,50,key="years")
    number("Abzinsung · %/Jahr","discount",0.,20.,.5)
    with st.expander("Weitere Kosten und Preisentwicklung"):
        number("Weitere Zusatzkosten · €","extras")
        number("Zuschuss / Investitionsminderung · €","grant")
        number("Laufende PV-Kosten · €/Jahr","annual_cost",step=10.)
        number("Strompreisänderung · %/Jahr","power_growth",-20.,20.,.5)
        number("Kostensteigerung · %/Jahr","cost_growth",-20.,20.,.5)
        number("Ertragsrückgang · %/Jahr","degradation",0.,100.,.1)
        st.selectbox("Gemeinsame PV-Ersatzreserve",["Mit Ersatzkosten","Ohne Ersatzkosten"],key="replacement_mode")
        number("Gemeinsame Ersatzkosten · €","replacement_cost")
        st.number_input("Gemeinsamer Ersatz im Modelljahr",1,50,key="replacement_year")
    with st.expander("Vergütungsgrundlage"):
        st.selectbox("Grundlage",["2026-Referenz","Spätere Inbetriebnahme – Annahme","Eigene Annahme"],key="tariff_basis")
        st.number_input("Vergütungsdauer · volle Modelljahre",0,50,key="feed_years")
        number("Abschlag auf Einspeiseerlöse · %","feed_discount",0.,100.,1.)
        st.caption("7,70 ct/kWh sind für Inbetriebnahme 01.08.–31.12.2026 bis 10 kWp belegt. Für spätere Inbetriebnahme Satz prüfen; keine Zukunftszusage.")
    st.file_uploader("Einstellungen laden",type="json",key="settings_upload",on_change=load_settings)
    if "import_message" in st.session_state:
        st.caption(st.session_state.import_message)

heating_controls(primary=True)
a = Assumptions(**{k:st.session_state[k] for k in asdict(Assumptions())})
h,s = heating_settings(),storage_settings()
try:
    shade = parse_shading(shade_input)
    st.session_state.plant_shade = shade
    validate(a,shade,0.)
    validate_heating(h)
    validate_storage(s,a)
except ValueError as exc:
    st.error(str(exc))
    st.stop()
fin = storage_financial(h,variant,a,shade,s)
sim = simulate(h,variant,a.generation,shade)
investment = priced_assumptions(a,s,h.battery).investment
st.subheader("Ergebnis deiner Anlage")
storage_label = f"{s.size}-kWh-Speicher ({h.capacity:g} kWh nutzbar)" if h.battery else "ohne Speicher"
st.caption(f"{variant} · {storage_label} · {shade:g} % Ertragsverlust · {a.generation*(1-shade/100):,.0f} kWh PV/Jahr".replace(",","."))
c1,c2,c3,c4 = st.columns(4)
c1.metric("Gesamtinvestition PV",money(investment))
c2.metric("PV-Nettonutzen · Jahr 1",money(fin["rows"][1]["net"]))
c3.metric("Amortisation deiner Anlage",duration(fin["payback"],a.years))
c4.metric(f"Kapitalwert deiner Anlage · {a.years} Jahre",money(fin["npv"]))
st.caption(f"Amortisation: Wann die gewählte PV-Anlage einschließlich der eingestellten Kosten zurückverdient ist, ohne Abzinsung. Kapitalwert: Überschuss nach {a.years} Jahren mit {a.discount:g} % Abzinsung; positiv = Verzinsungsziel erreicht. Heizungsanschaffungskosten sind mangels vollständiger Angebote nicht enthalten.")
if h.battery and s.size > 7 and s.upgrade == 0:
    st.warning("Der größere Speicher wird aktuell mit 0 € Aufpreis gerechnet. Bitte den tatsächlichen Aufpreis oben eintragen.")
if variant == VARIANTS[1] and h.cooling and not h.central_cooling:
    st.warning("Diese Zentral-WP-Variante liefert aktuell keine Kühlung. Für gleichen Komfort die Kühlfähigkeit unter ›Weitere Annahmen‹ aktivieren.")
main,storage_tab,heat_tab,quota_tab,sources = st.tabs(["Meine Rechnung","Einzelanalyse · Speicher","Einzelanalyse · Heizarten","Einzelanalyse · feste Quote","Modell & Quellen"])
with main:
    display = st.radio("Zahlungsverlauf deiner Anlage",["Nominal","Abgezinst"],horizontal=True)
    key = "balance" if display == "Nominal" else "discounted_balance"
    curve = pd.DataFrame({"Jahr":[r["year"] for r in fin["rows"]],"Saldo €":[r[key] for r in fin["rows"]]})
    chart = alt.Chart(curve).mark_line(point=True).encode(x=alt.X("Jahr:Q",axis=alt.Axis(tickMinStep=1)),y="Saldo €:Q",tooltip=["Jahr",alt.Tooltip("Saldo €:Q",format=".0f")])
    zero = alt.Chart(pd.DataFrame({"Saldo €":[0]})).mark_rule(color="gray").encode(y="Saldo €:Q")
    st.altair_chart((chart+zero).properties(height=300),width="stretch")
    st.caption("Diese Kurve gehört exakt zur Auswahl oben. Null = Investition zurückverdient. Ein Knick entsteht durch eingestellte Ersatzkosten; diese sind Annahmen, keine vorhergesagten Defekte.")
    c1,c2,c3 = st.columns(3)
    c1.metric("Eigenverbrauch der PV",f"{sim['own_pct']:.1f} %")
    c2.metric("Solar gedeckter Verbrauch",f"{sim['autonomy_pct']:.1f} %")
    c3.metric("Netzbezug · Jahr 1",f"{sim['totals']['grid']:,.0f} kWh".replace(",","."))
    st.caption("Eigenverbrauch = Anteil des PV-Stroms, der im Haus ankommt. Solar gedeckter Verbrauch = Anteil eures gesamten Strombedarfs, den die PV abdeckt. Beide Werte entstehen aus derselben Stundenrechnung.")
    annual = pd.DataFrame(fin["rows"])
    with st.expander("Jahresrechnung deiner Anlage"):
        st.dataframe(annual.round(2),hide_index=True,width="stretch")
    st.download_button("Meine Jahresrechnung · CSV",annual.to_csv(index=False,sep=";",decimal=","),"pv-jahresrechnung.csv","text/csv")
with storage_tab:
    st.caption("Einzelanalyse: Hier wird ausschließlich die Batterie verändert. Heizart, PV-Ertrag, Tarife und Lasten bleiben wie in deiner Konfiguration. Die Hauptrechnung oben wird dadurch nicht umgestellt.")
    draw_storage(h,variant,a,shade,s,money,duration)
with heat_tab:
    st.caption("Einzelanalyse: Vergleicht drei Heizarten und vier Ertragsfälle auf Basis deiner übrigen Konfiguration. Einzelne Zeilen sind Alternativen zur Hauptrechnung, keine zusätzlichen Einsparungen.")
    draw_heating(a,[0.,10.,20.,30.],money,duration,selection=(shade,variant),show_controls=False,include_storage=False)
with quota_tab:
    st.caption("Einzelanalyse mit frei vorgegebener Eigenverbrauchsquote. Diese vereinfachte Sensitivität verwendet keine Heizungs-/Batteriesimulation und verändert die Hauptrechnung nicht.")
    with st.expander("Annahmen nur für diese Einzelanalyse"):
        for i in range(4):
            st.session_state.setdefault(f"shade_{i}",st.session_state.shades[i])
            number(f"Ertragsverlust {i+1} · %",f"shade_{i}",0.,100.,1.)
        for i in range(3):
            st.session_state.setdefault(f"share_{i}",st.session_state.shares[i])
            number(f"Eigenverbrauchsquote {i+1} · %",f"share_{i}",0.,100.,1.)
        number("Pauschaler Speicherverlust · %","storage_loss",0.,100.,1.)
    shades = [st.session_state[f"shade_{i}"] for i in range(4)]
    shares = [st.session_state[f"share_{i}"] for i in range(3)]
    st.session_state.shades,st.session_state.shares = shades,shares
    records = []
    try:
        for qshade in shades:
            for share in shares:
                result = calculate(a,qshade,share)
                records.append({"Ertragsverlust %":qshade,"Eigenverbrauch %":share,"Amortisation":duration(result["payback"],a.years),"Kapitalwert €":result["npv"]})
        st.dataframe(pd.DataFrame(records).round(1),hide_index=True,width="stretch")
    except ValueError as exc:
        st.error(f"Nur Einzelanalyse: {exc}")
    st.caption("Rechnet mit dem Basisangebot inklusive 7-kWh-Speicher, ohne Klassen-Aufpreis/Minderpreis. Keine Aussage über die aktuell gewählte Anlagenkonfiguration.")
with sources:
    st.markdown("""**Speicher-Aufpreise · unverbindliche Annahmen, Recherche 08.11.2026.**

    Für 14 kWh ist gegenüber Rons 7-kWh-Speicher ein zusätzliches Huawei LUNA2000-7-E1-Modul angesetzt, für 21 kWh zwei. Das bereits angebotene Steuermodul und der Sockel werden weiterverwendet; [Huawei beschreibt 1/2/3 Batteriemodule je Steuermodul](https://solar.huawei.com/ae-en/products/LUNA2000-7-14-21-S1/specs/).

    Beobachtete Einzelmodulpreise: [SolarOutlet 2.029,70 € plus 99 € Versand](https://solaroutlet.de/products/huawei-luna2000-7-e1-batteriespeicher-6-9-kwh), [mg-solar 2.060,80 € plus Versand](https://www.mg-solar-shop.de/huawei-luna2000-7-e1-batteriemodul-6-9-kwh-fuer-luna2000-s1-batteriespeicher), jeweils mit ausgewiesenen 0 % MwSt. wie im Basisangebot, ohne Montage. Preise können sich ändern.

    **Rechenannahmen:** rund 2.100 € Material + 400 € pauschaler Zuschlag für Versand, Einbau/Inbetriebnahme und Anbieteraufschlag je zusätzlichem Modul = **2.500 € für 14 kWh bzw. 5.000 € für 21 kWh insgesamt gegenüber 7 kWh**. Der Zuschlag ist geschätzt, kein recherchierter Handwerkerpreis. Ron muss Aufpreis, Lieferumfang und Eignung der vorhandenen Komponenten bestätigen. Diese Werte gehen bereits in die Hauptrechnung ein; eigene Eingaben und ältere JSON-Dateien behalten ihre eingetragenen Preise.
    """)
    st.markdown("""**Eine Konfiguration, eine Hauptrechnung.** Investition, Amortisation, Kapitalwert, Jahreskurve und Export verwenden dieselbe Heizart, Speichergröße und Verschattung. Einzelanalysen variieren ausdrücklich benannte Annahmen.

    PVGIS-Wetterfolge 2023 mit 8.760 Stunden, normiert auf die Monatsmittel der bisherigen Ertragsabschätzung (7.060 kWh/Jahr als Startwert). Dach 5,58 kWp, 38° Südwest; Fassade 2,79 kWp, 90° Südost. Keine lokale Baum-/Gebäudeverschattung; der eingestellte Abschlag wirkt pauschal. Verbrauch und Effizienz sind Modellannahmen, keine Messung des Hauses.

    Keine Finanzierung, Heizungsinvestition, dynamische Netzladung oder Restwert. Batterie ohne Alterung/Standbyverbrauch, Stundenmittel ohne kurze Leistungsspitzen. 30,60 ct/kWh aus Mainova-Auszug, Preisgarantiedauer offen. Grundpreis wird nicht als Ersparnis gerechnet. 7,70 ct/kWh sind die belegte 2026-Referenz, keine Zusage für spätere Inbetriebnahme.

    [EU-PVGIS](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/api-non-interactive-service_en) · [Bundesnetzagentur](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/ErneuerbareEnergien/EEG_Foerderung/start.html)
    """)
settings = {k:st.session_state[k] for k in DEFAULTS}
st.download_button("Gesamte Konfiguration speichern · JSON",json.dumps({"schema":4,"settings":settings},ensure_ascii=False,indent=2),"pv-einstellungen.json","application/json")
