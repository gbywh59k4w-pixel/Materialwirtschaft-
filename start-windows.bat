@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo   Materialwirtschaft wird vorbereitet ...
echo ============================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYCMD=py"
) else (
    where python >nul 2>nul
    if !errorlevel!==0 (
        set "PYCMD=python"
    ) else (
        echo FEHLER: Python wurde nicht gefunden.
        echo.
        echo Bitte zuerst Python installieren: https://www.python.org/downloads/
        echo Wichtig: Beim Installer unten das Haekchen "Add python.exe to PATH" setzen.
        echo Danach diesen Ordner erneut oeffnen und start-windows.bat doppelklicken.
        echo.
        pause
        exit /b 1
    )
)

if not exist .venv (
    echo Erstelle virtuelle Umgebung ...
    !PYCMD! -m venv .venv
    if not exist .venv\Scripts\activate.bat (
        echo.
        echo FEHLER: Die virtuelle Umgebung konnte nicht erstellt werden.
        pause
        exit /b 1
    )
    call .venv\Scripts\activate.bat
    echo Installiere Abhaengigkeiten, das dauert beim ersten Mal 1-2 Minuten ...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo FEHLER bei der Installation. Bitte Internetverbindung pruefen und erneut versuchen.
        pause
        exit /b 1
    )
) else (
    call .venv\Scripts\activate.bat
)

echo.
echo ============================================
echo   Server wird gestartet ...
echo   Adresse im Browser: http://127.0.0.1:8000
echo   (oeffnet sich gleich automatisch)
echo.
echo   Dieses Fenster bitte GEOEFFNET lassen, solange
echo   Sie das Programm benutzen. Zum Beenden: Fenster
echo   schliessen oder STRG+C druecken.
echo ============================================
echo.

start "" cmd /c "timeout /t 3 >nul && start http://127.0.0.1:8000"
uvicorn app.main:app --host 127.0.0.1 --port 8000

echo.
echo Der Server wurde beendet.
pause
