@echo off
title Emergency Flask Server
color 0C

echo.
echo ███████ ███    ███ ███████ ██████   ██████  ███████ ███    ██  ██████ ██    ██ 
echo ██      ████  ████ ██      ██   ██ ██       ██      ████   ██ ██       ██  ██  
echo █████   ██ ████ ██ █████   ██████  ██   ███ █████   ██ ██  ██ ██        ████   
echo ██      ██  ██  ██ ██      ██   ██ ██    ██ ██      ██  ██ ██ ██         ██    
echo ███████ ██      ██ ███████ ██   ██  ██████  ███████ ██   ████  ██████    ██    
echo.
echo ████████ ██████   █████  ██████  ██ ███    ██  ██████                        
echo    ██    ██   ██ ██   ██ ██   ██ ██ ████   ██ ██                             
echo    ██    ██████  ███████ ██   ██ ██ ██ ██  ██ ██   ███                       
echo    ██    ██   ██ ██   ██ ██   ██ ██ ██  ██ ██ ██    ██                       
echo    ██    ██   ██ ██   ██ ██████  ██ ██   ████  ██████                        
echo.
echo ================================================================================
echo 🚨 EMERGENCY FLASK SERVER - CONNECTION TROUBLESHOOTER
echo ================================================================================
echo.

echo [STEP 1] 📍 Navigating to project directory...
cd /d "C:\Users\aio\OneDrive\Desktop\DATA TRADINGVIEW\backtest\BTC"
echo ✅ Current directory: %CD%
echo.

echo [STEP 2] 🔍 Checking Python availability...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Trying python3...
    python3 --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ Python not available in PATH
        echo 💡 Please install Python or add it to PATH
        echo 🔗 Download: https://python.org/downloads
        pause
        exit /b 1
    ) else (
        echo ✅ Using python3
        set PYTHON_CMD=python3
    )
) else (
    echo ✅ Using python
    set PYTHON_CMD=python
)
echo.

echo [STEP 3] 🧪 Testing basic Python functionality...
%PYTHON_CMD% -c "print('✅ Python is working!')"
if errorlevel 1 (
    echo ❌ Python execution failed
    pause
    exit /b 1
)
echo.

echo [STEP 4] 📦 Checking Flask installation...
%PYTHON_CMD% -c "import flask; print('✅ Flask version:', flask.__version__)" 2>nul
if errorlevel 1 (
    echo ⚠️ Flask not installed. Installing Flask...
    %PYTHON_CMD% -m pip install flask
    if errorlevel 1 (
        echo ❌ Failed to install Flask
        echo 💡 Try manually: pip install flask
        pause
        exit /b 1
    )
) else (
    echo ✅ Flask is available
)
echo.

echo [STEP 5] 🚀 Starting Emergency Flask Server...
echo ================================================================================
echo 🌐 Server will start on: http://localhost:5000
echo 🔄 Press Ctrl+C to stop the server
echo 💡 If this works, the connection issue is resolved!
echo ================================================================================
echo.

%PYTHON_CMD% emergency_server.py

echo.
echo ================================================================================
echo 🛑 Server stopped
echo 💡 If the server started successfully, you can now run the main application
echo 🎯 Try running: python web_app.py
echo ================================================================================
pause
