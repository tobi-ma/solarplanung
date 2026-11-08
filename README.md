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

3. Auf https://share.streamlit.io eine neue App erstellen. GitHub-Repository auswählen, Branch **main**, Einstieg **app.py**. Python **3.14** verwenden, soweit angeboten (lokal damit geprüft); andernfalls zuerst die gewünschte Python-Version mit den festgelegten Abhängigkeiten prüfen. `requirements.txt` liegt direkt im Repository-Hauptverzeichnis. Keine Secrets oder externen Hausdateien nötig.
4. Deploy starten. Der lokale macOS-Starter wird in der Cloud nicht benötigt. Einstellungen und hochgeladene JSON-Dateien liegen pro Sitzung im Arbeitsspeicher und müssen für dauerhafte Aufbewahrung exportiert werden.

[Offizielle Deployment-Anleitung](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)

## Bedienung des Boards

Links Annahmen ändern. Rechts zwölf Varianten vergleichen, Detailfall wählen, nominale/abgezinste Salden, Stromverwendung und Strompreis-Sensitivität ansehen. JSON-Download speichert Einstellungen; JSON-Upload lädt sie. CSV-Dateien exportieren die Varianten und die gewählte Jahresrechnung. Einstellungen sind ohne Export nur während der laufenden Sitzung verfügbar.

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
