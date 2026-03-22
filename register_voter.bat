@echo off
setlocal
echo =============================================
echo    Smart Voting - Voter Registration
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
echo [INFO] Starting registration script...
python mock_register.py
pause
