# Materialwirtschaft – Draht-Lager

Webbasierte Materialwirtschaft für einen Drahtverarbeiter mit ca. 160
Artikeln (Kombinationen aus Durchmesser und Legierung), QR-Code-Etiketten
und einer Scan-Station, an der Mitarbeiter Materialbedarf direkt am
Computer austragen können.

## Kernfunktionen

- **Artikelstamm**: ~160 Drahtartikel (z.B. `DR-4.90-C4C` = 4,90 mm,
  Legierung C4C), jeweils mit Bestand, Mindestbestand und Lagerplatz.
  Jeder Artikel hat einen eigenen QR-Code (druckbares Etikett) und kann
  über Suche/Filter (Legierung, Volltext, Unterbestand) gefunden werden.
- **Aufträge**: Ein Auftrag hat eine Auftragsnummer (z.B. `A-000001`),
  einen Ziel-Artikel und einen Bedarf in kg (z.B. 500 kg von 4,9 mm
  C4C-Draht). Jeder Auftrag hat einen eigenen QR-Code und einen
  druckbaren "Laufzettel".
- **Scan-Station** (`/scan`): Mitarbeiter scannen entweder
  - den **Auftrags-Code** vom Laufzettel → System zeigt Artikel, Bedarf
    und Restmenge, Mitarbeiter bestätigt die Menge → Bestand wird
    automatisch ausgebucht und der Auftrag als erledigt markiert
    (oder bei Teilmengen als "in Arbeit"), oder
  - den **Artikel-Code** direkt am Regal/Coil → System zeigt aktuellen
    Bestand, Mitarbeiter trägt die entnommene Menge ein → Bestand wird
    ohne Auftragsbezug ausgebucht.

  Das Scan-Feld funktioniert mit **USB-/Bluetooth-Scannern** (Tastatur-
  Emulation, Eingabefeld ist automatisch fokussiert, Enter löst die Suche
  aus) und alternativ mit der **Gerätekamera** (Button "Kamera-Scanner
  starten", nutzt die Bibliothek html5-qrcode).
- **Manuelle Buchung direkt am Artikel**: Wareneingang, Ausbuchen und
  Bestandskorrektur (Inventur) sind auch ohne Scan über die
  Artikeldetailseite möglich.
- **Bewegungshistorie**: Lückenlose Nachverfolgung aller Zu- und Abgänge
  mit Zeitstempel, Mitarbeiter, Quelle (Scan/manuell) und Bezug zum
  Auftrag.
- **Dashboard**: Übersicht offene Aufträge, Artikel unter Mindestbestand,
  letzte Bewegungen.

## Technischer Aufbau

- **Backend**: Python / FastAPI, SQLAlchemy, SQLite (Datei
  `materialwirtschaft.db`, wird beim ersten Start automatisch angelegt
  und mit Beispieldaten befüllt).
- **Oberfläche**: serverseitig gerenderte HTML-Seiten (Jinja2) mit
  Bootstrap 5, auf Deutsch, ohne Build-Schritt.
- **QR-Codes**: werden serverseitig aus der Artikel- bzw. Auftragsnummer
  erzeugt (`python-qrcode`) und als PNG ausgeliefert
  (`/materialien/{id}/qr.png`, `/auftraege/{id}/qr.png`).
- **Kamera-Scan**: `html5-qrcode` (per CDN eingebunden) für Tablets/
  Smartphones/Notebooks mit Kamera an der Werkbank.

## Schnellstart zum Testen auf dem eigenen Desktop

Zum Ausprobieren reicht es, die App auf dem eigenen Rechner zu starten –
ganz ohne Netzwerk-Konfiguration, nur für Sie selbst sichtbar.

1. **Code herunterladen**: Diesen Branch (`claude/draht-materialwirtschaft-system-sdbcia`)
   als ZIP von GitHub herunterladen und entpacken, oder per `git clone`
   auschecken.
2. **Python installieren**, falls noch nicht vorhanden: von
   [python.org/downloads](https://www.python.org/downloads/) (bei Windows
   beim Setup unbedingt "Add python.exe to PATH" ankreuzen).
3. **Starter-Skript doppelklicken** – je nach Betriebssystem:
   - Windows: `start-windows.bat`
   - Mac: `start-mac.command` (beim allerersten Öffnen ggf. mit
     Rechtsklick → "Öffnen" bestätigen, da macOS unbekannte Skripte erst
     freigeben lässt)
   - Linux: `start-linux.sh` (einmalig ausführbar machen:
     `chmod +x start-linux.sh`)

   Das Skript richtet beim ersten Mal automatisch eine Python-Umgebung
   ein und installiert alles Nötige (dauert ca. 1–2 Minuten), startet
   danach den Server und öffnet automatisch den Browser auf
   `http://127.0.0.1:8000`. Bei jedem weiteren Start geht es sofort los.
   Zum Beenden einfach das Terminal-/Konsolenfenster schließen.

   Da alles nur lokal auf `127.0.0.1` (dem eigenen Rechner) läuft,
   funktioniert hier auch der **Kamera-QR-Scanner ohne Zusatzaufwand**
   (Browser behandeln `localhost` als sicheren Ursprung) – ideal, um den
   kompletten Scan-Workflow am eigenen Rechner mit der Webcam zu testen,
   bevor später ggf. weitere Geräte (iPad, Scan-Station) im
   Firmennetzwerk eingerichtet werden.

Alternativ manuell im Terminal:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Danach im Browser `http://localhost:8000` öffnen. Beim ersten Start wird
die Datenbank automatisch angelegt und mit ca. 160 Beispiel-Drahtartikeln,
5 Beispiel-Mitarbeitern und ein paar Beispielaufträgen befüllt (u.a.
`A-000001`: 500 kg Bedarf an 4,90 mm C4C-Draht).

Die Datenbankdatei `materialwirtschaft.db` liegt im Projektverzeichnis
und wird nicht versioniert (`.gitignore`). Zum Zurücksetzen auf die
Beispieldaten einfach diese Datei löschen und die App neu starten.

**Für den späteren Mehrbenutzer-Betrieb** (mehrere Rechner/Tablets im
Firmennetzwerk, z.B. eine feste Scan-Station am iPad) muss der Server
stattdessen mit `--host 0.0.0.0` auf einem dauerhaft laufenden Rechner
gestartet werden. Das ist ein separater, kleiner Zusatzschritt – siehe
dazu die eigene iPad-Anleitung.

## Typischer Arbeitsablauf

1. **Auftrag anlegen** (Büro/Planung): `/auftraege/neu` → Artikel wählen
   (z.B. `DR-4.90-C4C`), Bedarf eingeben (z.B. `500` kg) → Auftrag wird
   angelegt, Laufzettel mit QR-Code kann ausgedruckt werden
   (`/auftraege/{id}/laufzettel`).
2. **Mitarbeiter fertigt am Arbeitsplatz** und geht mit dem Laufzettel
   zur Scan-Station (`/scan`).
3. **Scannen**: Der Auftrags-Code wird gescannt (Kamera oder
   USB-Scanner) → System zeigt Bedarf/Restmenge → Mitarbeiter wählt
   sich aus der Liste aus und bestätigt → 500 kg werden automatisch vom
   Bestand des Artikels abgebucht, der Auftrag wird als "erledigt"
   markiert.
4. Alternativ kann derselbe Vorgang auch **ohne Scan direkt am
   Computer** über die Auftragsdetailseite (`/auftraege/{id}`) oder über
   die Artikeldetailseite (`/materialien/{id}`) ausgeführt werden.

## Artikel-Nummernschema

`DR-<Durchmesser in mm, 2 Nachkommastellen>-<Legierungscode>`, z.B.
`DR-4.90-C4C`. Dieser Code ist gleichzeitig der Inhalt des QR-Codes auf
dem Artikeletikett.

## Erweiterungsideen (nicht umgesetzt)

- Benutzeranmeldung/Rechteverwaltung statt freier Mitarbeiterauswahl
- Mehrsprachigkeit
- Export der Bewegungen als CSV/Excel
- Anbindung an ERP-System
