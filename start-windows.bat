@echo off
setlocal
cd /d "%~dp0"

if not exist .venv (
    echo Erstelle virtuelle Umgebung und installiere Abhaengigkeiten - das dauert beim ersten Start ein bis zwei Minuten ...
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo FEHLER: Python wurde nicht gefunden. Bitte Python 3 von https://www.python.org/downloads/ installieren
        echo und beim Setup das Haekchen "Add python.exe to PATH" setzen. Danach dieses Skript erneut starten.
        pause
        exit /b 1
    )
    call .venv\Scripts\activate.bat
    pip install --quiet -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

echo.
echo Starte Materialwirtschaft ... Browser oeffnet sich gleich automatisch.
echo Zum Beenden dieses Fenster einfach schliessen oder STRG+C druecken.
echo.

start "" cmd /c "timeout /t 2 >nul && start http://127.0.0.1:8000"
uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
