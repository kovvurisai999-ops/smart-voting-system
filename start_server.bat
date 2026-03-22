@echo off
setlocal
echo =============================================
echo    Smart Voting - Start Server
echo =============================================
cd /d "%~dp0"

if not exist venv (
    echo [ERROR] Virtual environment 'venv' not found!
    echo Please ensure you have installed the requirements in a 'venv' folder.
    pause
    exit /b
)

echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat
echo [INFO] Starting Flask server...
start "Smart Voting - Web Server" venv\Scripts\python.exe app.py
echo [INFO] Starting Local Discovery Service (mDNS)...
start "Smart Voting - Discovery" venv\Scripts\python.exe broadcast_service.py
echo =============================================
echo All services started! 
echo Access locally via: http://smart-voting.local:5000
echo =============================================
pause
