@echo off
echo ========================================
echo   Trading Optimization Web Server
echo ========================================
echo.
echo Directory: %cd%
echo Using Python: "C:\Users\aio\OneDrive\Desktop\DATA TRADINGVIEW\backtest\BTC\.venv_new\Scripts\python.exe"
echo.
echo PowerShell Execution Policy: FIXED (RemoteSigned)
echo Python Syntax Error: FIXED (duplicate function definitions)
echo Required packages: Flask, Pandas, Numpy - INSTALLED
echo.
echo Starting server at: http://localhost:5000
echo Access enhanced interface at: http://localhost:5000
echo Access classic interface at: http://localhost:5000/classic
echo Monitor progress at: http://localhost:5000/status
echo.
REM === Chạy phiên bản tối ưu tốc độ ===
echo Starting Python server...
"C:\Users\aio\OneDrive\Desktop\DATA TRADINGVIEW\backtest\BTC\.venv_new\Scripts\python.exe" "web_app.py"
if errorlevel 1 (
    echo.
    echo [ERROR] Python server did not start. Kiểm tra lại file web_app.py hoặc môi trường Python!
    echo [GỢI Ý] Chạy thử lệnh sau trong CMD để xem lỗi chi tiết:
    echo     "C:\Users\aio\OneDrive\Desktop\DATA TRADINGVIEW\backtest\BTC\.venv_new\Scripts\python.exe" web_app.py
)
echo Press Ctrl+C to stop the server
echo ========================================
echo.
pause
