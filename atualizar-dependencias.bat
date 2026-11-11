@echo off
cd /d "%~dp0"
echo Atualizando dependencias...
".venv\Scripts\python.exe" -m pip install -r requirements.txt --upgrade
pause
