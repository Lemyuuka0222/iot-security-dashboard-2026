@echo off
title IoT Security Dashboard
cd /d "%~dp0"

echo ============================================
echo   IoT Security Dashboard - INICIO RAPIDO
echo ============================================
echo.

echo [1/3] Iniciando Backend...
start "Backend" cmd /c "python -m uvicorn main:app --host 0.0.0.0 --port 8000"
cd backend
timeout /t 3 /nobreak >nul

echo [2/3] Iniciando generador de datos de prueba...
start "Mock Data" cmd /c "python mock_data.py"
timeout /t 2 /nobreak >nul

echo [3/3] Abriendo Dashboard local...
start "" http://localhost:8000/docs

echo.
echo Backend: http://localhost:8000
echo Dashboard: http://localhost:8000/docs
echo Datos falsos: mock_data.py corriendo
echo.
echo Presiona cualquier tecla para abrir el dashboard de GitHub Pages
pause >nul
start "" https://lemyuuka0222.github.io/iot-security-dashboard-2026/
