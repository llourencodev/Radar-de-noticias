@echo off
chcp 65001 >nul
title Radar Inteligente de Noticias
cd /d "%~dp0"

where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")

if not exist ".venv\Scripts\python.exe" (
  echo Preparando o ambiente pela primeira vez. Isso leva cerca de 1 minuto...
  %PY% -m venv .venv || (echo. & echo Python nao encontrado. Instale em https://www.python.org/downloads/ e marque "Add python.exe to PATH". & pause & exit /b 1)
  ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || (echo. & echo Falha ao instalar dependencias. Verifique a internet e tente novamente. & pause & exit /b 1)
)

if not exist ".env" copy ".env.example" ".env" >nul

".venv\Scripts\python.exe" run.py %*
pause
