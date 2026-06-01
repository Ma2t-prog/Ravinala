@echo off
title RAVINALA - Launcher

echo Nettoyage des anciens processus...
powershell -Command "Get-Process -Name 'streamlit','python','python3*' -ErrorAction SilentlyContinue | Stop-Process -Force" >nul 2>&1
timeout /t 2 /nobreak >nul

echo Demarrage de Ravinala...
cd /d "%~dp0"
start "" http://localhost:8501
.venv\Scripts\streamlit run src/app.py --server.port 8501 --server.headless false
