@echo off
title RAVINALA - Launch
color 0A

echo.
echo  ==========================================
echo   RAVINALA - Starting all services...
echo  ==========================================
echo.

REM Start FastAPI backend
echo  [1/2] Starting Backend (port 8000)...
start "RAVINALA Backend" cmd /k "cd /d C:\Users\Matthias\Project\montecarlo\backend && ..\\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

REM Wait 3 seconds for backend to initialize
timeout /t 3 /nobreak > nul

REM Start Vite frontend
echo  [2/2] Starting Frontend (port 5173)...
start "RAVINALA Frontend" cmd /k "cd /d C:\Users\Matthias\Project\ravinala-web && npm run dev"

REM Wait for frontend to start then open browser
timeout /t 4 /nobreak > nul
echo.
echo  Opening browser...
start http://localhost:5173/agents/monitor

echo.
echo  ==========================================
echo   Both services are running!
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8000
echo   API Docs : http://localhost:8000/docs
echo  ==========================================
echo.
pause
