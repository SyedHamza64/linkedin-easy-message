@echo off
title LinkedIn Auto System - One-Click Launch
color 0A
echo.
echo ========================================
echo  LinkedIn Auto System - Setup & Launch
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH!
    echo Please install Node.js from nodejs.org
    pause
    exit /b 1
)

echo [1/5] Checking Python virtual environment...
if not exist "venv\" (
    echo [INFO] Virtual environment not found. Creating...
    python -m venv venv
    echo [SUCCESS] Virtual environment created!
) else (
    echo [SUCCESS] Virtual environment already exists.
)

echo.
echo [2/5] Checking Python dependencies...
if not exist "venv\Lib\site-packages\flask\" (
    echo [INFO] Installing Python dependencies...
    call venv\Scripts\activate.bat
    pip install --upgrade pip
    pip install -r requirements.txt
    echo [SUCCESS] Python dependencies installed!
) else (
    echo [SUCCESS] Python dependencies already installed.
)

echo.
echo [3/5] Checking Frontend dependencies...
if not exist "linkedin-frontend\node_modules\" (
    echo [INFO] Installing Frontend dependencies...
    cd linkedin-frontend
    call npm install
    cd ..
    echo [SUCCESS] Frontend dependencies installed!
) else (
    echo [SUCCESS] Frontend dependencies already installed.
)

echo.
echo [4/5] Starting Backend Server...
start "LinkedIn Backend" cmd /c "title LinkedIn Backend && cd /d %~dp0 && call venv\Scripts\activate.bat && python api_server.py"
timeout /t 2 >nul

echo.
echo [5/5] Starting Frontend Server...
start "LinkedIn Frontend" cmd /c "title LinkedIn Frontend && cd /d %~dp0linkedin-frontend && npm start"

echo.
echo ========================================
echo  SETUP COMPLETE!
echo ========================================
echo.
echo Backend:  http://127.0.0.1:5000
echo Frontend: http://localhost:3000
echo.
echo Both services are running in separate windows.
echo.
echo Press ENTER to shutdown both services...
pause >nul

echo.
echo ========================================
echo  Shutting down services...
echo ========================================
echo.

REM Stop Backend (port 5000)
echo [1/3] Stopping Backend...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a /T 2>nul
)

REM Stop Frontend (port 3000 and all node processes)
echo [2/3] Stopping Frontend...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a /T 2>nul
)
taskkill /F /IM node.exe /T 2>nul

REM Close all CMD windows with "LinkedIn" in title
echo [3/3] Closing terminal windows...
powershell -Command "Get-Process | Where-Object {$_.MainWindowTitle -like '*LinkedIn*'} | Stop-Process -Force" 2>nul

echo.
echo ========================================
echo  All services stopped!
echo ========================================
echo.
timeout /t 2 >nul
exit 