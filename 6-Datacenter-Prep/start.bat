@echo off
REM ACI Simulator starten (Windows). Weitere Optionen: start.bat --help
cd /d "%~dp0"
python -m dcprep %*
