#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Erstelle virtuelle Umgebung und installiere Abhängigkeiten - das dauert beim ersten Start ein bis zwei Minuten ..."
    if ! command -v python3 >/dev/null 2>&1; then
        echo ""
        echo "FEHLER: Python 3 wurde nicht gefunden. Bitte Python 3 installieren (z.B. 'sudo apt install python3 python3-venv')."
        exit 1
    fi
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --quiet -r requirements.txt
else
    source .venv/bin/activate
fi

echo ""
echo "Starte Materialwirtschaft ... Browser öffnet sich gleich automatisch."
echo "Zum Beenden dieses Fenster schließen oder Strg+C drücken."
echo ""

( sleep 2 && xdg-open "http://127.0.0.1:8000" >/dev/null 2>&1 ) &
uvicorn app.main:app --host 127.0.0.1 --port 8000
