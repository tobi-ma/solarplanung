# PV-Board · Dach und Fassade

Erstellt 08.11.2026. Lokales Streamlit-Board für vier Ertragsfälle und drei Eigenverbrauchsquoten. Keine Beauftragung oder Anbieterkommunikation.

## Start

`Start_PV_Board.command` im Finder doppelklicken. Beim ersten Start werden Streamlit und seine Abhängigkeiten in einer isolierten temporären Python-Umgebung installiert. Python 3.10+ und Internetzugang für diese Installation erforderlich. Danach läuft die Rechnung lokal. Das Terminalfenster offenlassen; mit Strg+C beenden. Adresse: http://127.0.0.1:8501. Nur auf diesem Computer erreichbar, nicht öffentlich bereitgestellt. Die temporäre Umgebung kann nach einem Neustart neu aufgebaut werden; der Quellcode bleibt in OneDrive.

Alternativ in einer eigenen Python-Umgebung:

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

## Deployment auf Streamlit Community Cloud

Dieser Ordner ist ein eigenständiges Git-Repository. Nur die App-Dateien werden versioniert; Hausunterlagen außerhalb des Ordners gehören nicht zum Repository. Rechenannahmen, Angebotssumme, Tarif und ungefährer Standort stehen allerdings im App-Code und in dieser Anleitung. Das Repository wurde lokal angelegt und noch nicht zu einem Hostingdienst hochgeladen.

1. Ein leeres GitHub-Repository anlegen (ohne automatisch erzeugte README).
2. Im lokalen App-Ordner das Remote verbinden und hochladen:

```sh
git remote add origin https://github.com/DEIN-KONTO/DEIN-REPOSITORY.git
git push -u origin main
```

3. Auf https://share.streamlit.io eine neue App erstellen. GitHub-Repository **tobi-ma/solarplanung**, Branch **main**, Einstieg **app.py**. Unter Advanced settings Python **3.14** auswählen (lokal mit **Python 3.14.3** geprüft). `requirements.txt` liegt direkt im Repository-Hauptverzeichnis. **Secrets-Feld leer lassen**: keine API-Schlüssel, Zugangsdaten oder externen Hausdateien erforderlich. Alle Wetterdaten sind im Repository enthalten. `.python-version` dokumentiert die lokale Zielversion; die Cloud-Version trotzdem im Deployment-Dialog auswählen.
4. Deploy starten. Der lokale macOS-Starter wird in der Cloud nicht benötigt. Einstellungen und hochgeladene JSON-Dateien liegen pro Sitzung im Arbeitsspeicher und müssen für dauerhafte Aufbewahrung exportiert werden.

[Offizielle Deployment-Anleitung](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)

## Bedienung des Boards

Auf der Startseite Heizart, Speichergröße (ohne / 7 / 14 / 21 kWh), Verschattung und Angebotspreise einstellen. Direkt darunter stehen Gesamtinvestition, jährlicher PV-Nettonutzen, Amortisation und Kapitalwert derselben Anlagenkonfiguration. ›Meine Rechnung‹ zeigt genau deren Jahreskurve und CSV-Jahresrechnung. Links stehen Tarife, Betrachtungszeitraum und weitere Finanzannahmen. Verbrauch, Wirkungsgrade und Batterieleistung liegen im aufklappbaren Bereich ›Weitere Annahmen‹ auf der Startseite.

Zusätzliche Tabs heißen ausdrücklich ›Einzelanalyse · Speicher‹, ›Einzelanalyse · Heizarten‹ und ›Einzelanalyse · feste Quote‹. Sie untersuchen Alternativen zur Hauptkonfiguration. Änderungen an frei vorgegebenen Quoten beeinflussen die Hauptrechnung nicht. Alle Hauptkennzahlen verwenden dagegen die stündliche Heizungs-/Speicherrechnung und ihren tatsächlichen Angebotspreis.

JSON-Download speichert die gesamte Konfiguration (Schema 4), einschließlich der gewählten Heizart, Speichergröße und Verschattung; ältere Exporte bleiben lesbar. Bei alten Dateien fehlen Heizart und Verschattung der Hauptauswahl: Nach Import prüfen, entsprechender Hinweis erscheint. Die Jahresrechnung und ihr Export sind dieselben Daten wie in der Hauptanzeige. Einstellungen sind ohne Export nur während der laufenden Sitzung verfügbar.

Belegt: Weiss-V2 16.090 € ohne Gerüst; Mainova-Nutzerauszug 30,60 ct/kWh brutto (Preisgarantiedauer offen). Grundpreis 164,62 €/Jahr wird nicht als PV-Ersparnis gerechnet. 2.000 € Gerüst, 150 €/Jahr Betrieb und 4.000 € Ersatz in Jahr 13 sind angenommene Werte.

Vergütung 7,70 ct/kWh für Überschusseinspeisung bis 10 kWp bei Inbetriebnahme 01.08.–31.12.2026 laut [Bundesnetzagentur](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/ErneuerbareEnergien/EEG_Foerderung/start.html), abgerufen 08.11.2026. Für spätere Inbetriebnahme keine bestätigte Zusage. Zeitraum ist im Board auf volle Modelljahre vereinfacht; nach Ablauf keine Vergütung. Pauschaler Erlösabschlag einstellbar. Negative Preisstunden und Einspeisebegrenzung nicht zeitaufgelöst berechnet.

Basis 7.060 kWh aus der PVGIS-Vorrechnung (gerundet aus 7.062): 5,58 kWp Südwest-Dach bei 38°, 2,79 kWp Südostfassade bei 90°, ungefähr Freudenberg 50,90/7,87. SARAH3 2005–2023, hinterlüftet, 14 % Systemverluste bereits enthalten, ohne Gelände-/Baum-/Gebäudeverschattung. [PVGIS-Parameter](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/api-non-interactive-service_en).

Eigenverbrauch ist der nutzbare Anteil der PV-Erzeugung nach Speicherverlusten, kein Autarkiegrad. Zusätzliche Speicherverluste standardmäßig 5 % der PV-Erzeugung. Eigenverbrauch + Verlust + Einspeisung = Erzeugung. Der Speicher ist nicht physikalisch simuliert; keine Ableitung der Quote aus Kapazität oder Jahresverbrauch.

Einfache Amortisation = Investition / Nettoüberschuss Jahr 1, ohne spätere Veränderungen. Jahresmodell berücksichtigt Degradation, Preisentwicklung und Ersatzkosten. Modell-Amortisation ist die letzte Nullüberschreitung, nach der der Jahressaldo bis zum Betrachtungsende positiv bleibt; Zwischenwerte linear interpoliert. Kapitalwert enthält Investition im Jahr 0 und Zahlungsüberschüsse am Jahresende, abgezinst. Kein Kredit, Steuerbonus, Restwert oder dynamisches Netzladen.

## Dateien

- `app.py`: Oberfläche, Diagramme und Exporte.
- `model.py`: unabhängiges Rechenmodell.
- `test_model.py`: Rechen- und Oberflächenprüfungen.
- `requirements.txt`: Streamlit-Version.
- `Start_PV_Board.command`: lokaler Starter.

Tests: `python -m unittest discover -s . -p 'test_*.py'` aus diesem Ordner (Streamlit-Umgebung).

## Heizungs- und Speichervergleich · Erweiterung 08.11.2026

Im Tab **Heizung & Speicher** werden drei Varianten bei allen vier Ertragsfällen verglichen: Splits plus kleine Wasser-WP, zentrale Luft-Wasser-WP sowie zentrale WP mit einzelnen Splits. Gleichbleibender Nutzwärmebedarf, aufgeteilt auf die Heizgeräte. Die Zentral-WP kühlt nur bei aktivierter entsprechender Option; sonst wird der Komfortunterschied angezeigt. Die Investitionsrechnung betrifft weiterhin ausschließlich PV einschließlich Batterie, nicht die noch unbekannten Heizungsinvestitionen.

Neue Startannahmen: Haushaltsstrom 3.500 kWh/Jahr, Raumwärme 16.000 kWh Wärme/Jahr, Warmwasser 2.500 kWh Wärme/Jahr, Kühlung 1.000 kWh Kälte/Jahr. JAZ Splits 3,5, Wasser-Raumheizung 3,2, Warmwasser 2,5; SEER Kühlung 4. Wärmeanteile FBH im Split-Konzept 25 %, Splits im Zentral-plus-Split-Konzept 20 %. Sämtliche Werte sind unbestätigte, veränderbare Szenarien. Gemeinsamer Stromzähler und Bezugspreis für alle Geräte angenommen.

Raumheizstrom wird anhand von Temperaturstunden unter 15 °C verteilt (Gewicht 18 °C minus Außentemperatur, mit zusätzlichem Kältefaktor), anschließend auf Nutzwärme/JAZ normiert. Kühlung verteilt sich auf warme Stunden über 22 °C zwischen 10 und 22 Uhr und wird auf Kältebedarf/SEER normiert. Haushaltsstrom folgt einfachen auswählbaren Tagesmustern; Warmwasserladung auf vier Mittags- oder Morgen-/Abendstunden. Keine Gebäudesimulation, keine Heizlastbestimmung, keine Messprofile und keine Vorhersage einer konkreten JAZ.

Batterie: anfangs leer, standardmäßig 6,9 kWh nutzbar, je 3,5 kW Lade-/Entladeleistung, 90 % Rundlaufwirkungsgrad als Annahme. Wirkungsgrad wird symmetrisch auf Laden/Entladen aufgeteilt. Direktverbrauch vor Laden, Entladung nur zur Lastdeckung, keine Netzladung. Die Energie am Jahresende bleibt gespeichert und wird nicht als Einspeisung oder Eigenverbrauch gezählt. Energieerhaltung: PV = Direktverbrauch + Batterieabgabe + Verluste + Einspeisung + Endinhalt. Keine Batteriealterung, Standbylast oder unterstündlichen Spitzen. Seit dem direkten Speichervergleich wird der Preis beim Ausschalten im Heizvergleich um den eingegebenen Minderpreis reduziert.

Im Heizungs-Langzeitmodell wird für jedes Jahr der degradierte PV-Ertrag erneut mit dem unveränderten Lastprofil und der Batterie simuliert. Kapazität und Leistung bleiben dabei konstant; Ersatzkosten sind weiterhin frei wählbare Zahlungsannahmen. Investition/Jahresnutzen/Kapitalwert betreffen PV gegenüber derselben Heizung ohne PV. Der Stromsaldo ist Netzbezug minus Einspeiseerlöse, ohne konstanten Grundpreis und ohne Heizungswartung. Einstellungen JSON Schema 2 enthalten beide Rechner; alte Schema-1-Dateien laden mit Startannahmen für den neuen Tab.

### Wetterdaten und Reproduzierbarkeit

`weather_2023.csv`: 8.760 stündliche Datensätze aus zwei öffentlichen PVGIS-5.3-Abfragen (abgerufen 08.11.2026). Zeitstempel UTC, PV-Mengen pro Stunde in kWh, Außentemperatur °C. Die Oberfläche nutzt Europe/Berlin einschließlich Sommerzeit. Wetterabfolge 2023; Monatsmengen beider Flächen werden jeweils auf die langjährigen Monatsmittel der Vorrechnung normiert. Anschließend Skalierung auf den gewählten Jahresertrag, standardmäßig 7.060 kWh. Das ergibt ein hybrides Planungsprofil, kein tatsächlich so beobachtetes Wetterjahr mit genau diesem Ertrag. Das Monatsprofil ist kein Ersatz für lokale Verschattungsnachweise.

API-Basis: `https://re.jrc.ec.europa.eu/api/v5_3/seriescalc`. Gemeinsame Parameter: `lat=50.90&lon=7.87&startyear=2023&endyear=2023&pvcalculation=1&loss=14&usehorizon=0&pvtechchoice=crystSi&mountingplace=free&raddatabase=PVGIS-SARAH3&outputformat=json`. Dach zusätzlich `peakpower=5.58&angle=38&aspect=45`, Fassade `peakpower=2.79&angle=90&aspect=-45`.

Nach Download beider JSON-Antworten kann `python prepare_weather.py ROOF.json WALL.json` die CSV reproduzieren. Im normalen App-Betrieb sind keine API-Zugriffe nötig. PVGIS-Systemverluste sind bereits im Ertrag enthalten; der pauschale Speicherverlust des alten Quotenmodells wird im Stundenmodell nicht zusätzlich angesetzt. Der Verschattungsabschlag wirkt pauschal und gleichmäßig auf alle Stunden.

[EU-PVGIS: Stundendaten und Einheiten](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-tools/hourly-radiation_en) · [API-Dokumentation](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/api-non-interactive-service_en).

Zusätzliche Dateien: `heating_model.py` (Simulation), `heating_ui.py` (Oberfläche und Erklärungen), `test_heating.py` (Energiebilanz und Rechenprüfung), `prepare_weather.py` (Datenaufbereitung), `weather_2023.csv` (öffentliche Wetterdaten, keine Haus-Messdaten).

## Direkter Speichervergleich · Erweiterung 08.11.2026

Im Heizungs-Tab wird für die ausgewählte Heizvariante und Verschattung immer dieselbe PV-Anlage mit/ohne Batterie gegenübergestellt. Der Betriebsschalter steuert die übrigen Heizungsdiagramme; der Direktvergleich rechnet stets beide Seiten.

- Minderpreis ohne Batterie: einstellbarer vollständiger Preisunterschied gegenüber Rons ursprünglichem 7-kWh-Angebot. 3.650 € Startwert ist nur die bisherige Speicherposition, kein bestätigtes Alternativangebot.
- Klassen 7/14/21 kWh: nutzbar 6,9/13,8/20,7 kWh. Leistungspresets 3,5/7/10 kW. Hersteller nennt für die 21er-Batterie bis 10,5 kW; 10 kW ist unsere Systembegrenzungsannahme, kein Nachweis der tatsächlichen Leistung am angebotenen Wechselrichter. Lade-/Entladeleistung bleiben anpassbar. [Huawei-Datenblatt](https://solar.huawei.com/admin/asset/v1/pro/view/8da96b44831242eea1ddc3f4bf94a518.pdf).
- Aufpreise 14 und 21 kWh: separat einstellbar, jeweils gegenüber dem ursprünglichen 7-kWh-Angebot. Startwerte 0 € sind unbekannte Preise, kein Angebot; Warnhinweis bei Auswahl einer größeren Klasse ohne Preis.
- Investition mit Batterie = Basisinvestition + Klassen-Aufpreis. Ohne Batterie = Basisinvestition − Minderpreis. Mehrpreis Batterie = Minderpreis + Klassen-Aufpreis.
- Gemeinsame PV-Betriebs-/Ersatzkosten von links bleiben auf beiden Seiten gleich. Nur explizite zusätzliche jährliche Batterie- und Ersatzkosten belasten die Batterie zusätzlich; gleiche Kosten nicht doppelt eintragen.
- Gesamt-PV-Amortisation und Kapitalwert werden für beide Ausführungen berechnet. Zusätzlich wird die Differenz betrachtet: eigener Speicher-Kapitalwert, einfacher sowie modellierter Rückzahlungszeitpunkt und nominaler/abgezinster Mehrwert über die Jahre. Diese Differenz enthält entgangene Einspeiseerlöse, Speicherverluste und zusätzliche Batteriekosten.
- Einstellungen exportieren als Schema 3. Alte Schema-1/2-Dateien bleiben lesbar; freie alte Kapazitäten werden auf die nächstliegende 7/14/21-Klasse übertragen und im Importhinweis kenntlich gemacht.

Neue Dateien: `storage_model.py`, `storage_ui.py`, `test_storage.py`, `.python-version`. Tests prüfen auch Preisunterschiede, gemeinsame versus zusätzliche Ersatzkosten und Einstellungen der Speicherklassen.

### Vereinfachte Ergebnisansicht

Der Direktvergleich zeigt die wichtigsten Werte in einer kompakten Tabelle: Investition, Nettonutzen im ersten Jahr, modellierte Gesamt-Amortisation und Kapitalwert. Eine dritte Zeile **Differenz: mit minus ohne** macht Mehrpreis, jährlichen Vorteil und Kapitalwert-Vorteil unmittelbar nachvollziehbar. Die Kapitalwert-Subtraktion steht zusätzlich ausgeschrieben unter der Tabelle. **Amortisation · Speicher allein** wird separat aus den zusätzlichen Zahlungsüberschüssen berechnet; sie ist keine Differenz der Amortisationsdauern beider Gesamtanlagen. Strommengen und ausführliche Rechenwege sind aufklappbar. CSV enthält ebenfalls die drei Zeilen; für die Differenzzeile bleibt die Gesamt-Amortisation leer.

### Konfigurator als Startseite

Es gibt seit dieser Fortschreibung eine maßgebliche Hauptrechnung. Die früher auf der Startseite stehende 12er-Quotentabelle ist jetzt eine ausdrücklich vereinfachte Einzelanalyse. Deren Fehler oder unwirksame Quoten blockieren die Hauptrechnung nicht. Die Hauptkonfiguration steuert dieselben `Assumptions`-, `Heating`- und `Storage`-Parameter für Kennzahlen, Kurve, Jahresdaten und Export. Der Haupt-Kapitalwert entspricht damit immer dem letzten abgezinsten Saldo der exportierten Jahresrechnung. Die Heizungsanalyse verwendet dieselbe Auswahl für ihre Detailgrafiken und verändert nur in der gekennzeichneten Vergleichstabelle Heizarten und Verluststufen.
