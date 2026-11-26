# ==============================================================================
# CALYX FULL-STACK LOCAL LAUNCHER SCRIPT (Windows PowerShell)
# ==============================================================================
# Runs both Backend (API Gateway on Port 8000) and Frontend (Vite on Port 5173)
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting CALYX Autonomous AI Microservices Platform...   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Start Backend API Gateway in a new PowerShell window
Write-Host "[1/2] Launching Backend API Gateway on http://localhost:8000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'CALYX Backend API Gateway (Port 8000)' -ForegroundColor Green; python -m uvicorn services.calyx_gateway_service.main:app --host 0.0.0.0 --port 8000 --reload"

# Wait 2 seconds for backend to bind port
Start-Sleep -Seconds 2

# 2. Start Frontend Vite Development Server in the current window
Write-Host "[2/2] Launching Frontend UI on http://localhost:5173 ..." -ForegroundColor Green
Set-Location -Path "frontend"
npm run dev
