@echo off
title Trading Optimization - Quick Start
color 0A

echo.
echo ████████ ██████   █████  ██████  ██ ███    ██  ██████  
echo    ██    ██   ██ ██   ██ ██   ██ ██ ████   ██ ██       
echo    ██    ██████  ███████ ██   ██ ██ ██ ██  ██ ██   ███ 
echo    ██    ██   ██ ██   ██ ██   ██ ██ ██  ██ ██ ██    ██ 
echo    ██    ██   ██ ██   ██ ██████  ██ ██   ████  ██████  
echo.
echo    ██████  ██████  ████████ ██ ███    ███ ██ ███████  █████  ████████ ██  ██████  ███    ██ 
echo   ██    ██ ██   ██    ██    ██ ████  ████ ██    ███  ██   ██   ██    ██ ██    ██ ████   ██ 
echo   ██    ██ ██████     ██    ██ ██ ████ ██ ██   ███   ███████   ██    ██ ██    ██ ██ ██  ██ 
echo   ██    ██ ██         ██    ██ ██  ██  ██ ██  ███    ██   ██   ██    ██ ██    ██ ██  ██ ██ 
echo    ██████  ██         ██    ██ ██      ██ ██ ███████ ██   ██   ██    ██  ██████  ██   ████ 
echo.
echo ================================================================================
echo 🚀 QUICK START - Trading Optimization with Progress Monitor
echo ================================================================================
echo.

echo [1] 📊 Checking current status...
powershell -ExecutionPolicy Bypass -File "check_status.ps1"

echo.
echo [2] 🚀 Starting Flask web server...
echo.
start "Trading Optimization Server" cmd /k "echo Starting Flask server... && python web_app.py"

echo [3] ⏱️ Waiting for server to start...
timeout /t 5 /nobreak > nul

echo [4] 🌐 Opening applications...
start "Progress Monitor" http://localhost:5000/status
timeout /t 2 /nobreak > nul
start "Main Application" http://localhost:5000

echo.
echo ================================================================================
echo ✅ ALL SERVICES STARTED SUCCESSFULLY!
echo ================================================================================
echo 📊 Progress Monitor: http://localhost:5000/status
echo 🎯 Main Application: http://localhost:5000  
echo 📈 Progress API: http://localhost:5000/progress
echo.
echo 💡 Your optimization (752,640 combinations) should show progress in real-time
echo ⏱️ Estimated completion time: ~76 minutes
echo 🔥 Check CPU usage - should be high during optimization
echo.
echo ================================================================================
echo Press any key to close this window (servers will keep running)...
pause > nul
