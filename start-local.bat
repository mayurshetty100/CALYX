@echo off
title CALYX Full-Stack Launcher
echo ==========================================================
echo   Starting CALYX Platform (Backend + Frontend)
echo ==========================================================

echo [1/2] Launching Backend on http://localhost:8000 ...
start "CALYX Backend (Port 8000)" powershell -NoExit -Command "python -m uvicorn services.calyx_gateway_service.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 2 /nobreak >nul

echo [2/2] Launching Frontend on http://localhost:5173 ...
cd frontend
npm run dev
