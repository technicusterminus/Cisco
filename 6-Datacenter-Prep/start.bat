@echo off
REM Datacenter Prep starten (Windows). Weitere Optionen: start.bat --help
cd /d "%~dp0"
python -m dcprep %*
