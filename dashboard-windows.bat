@echo off
title LinkedIn Auto System Dashboard
echo Starting LinkedIn Auto System...
echo.

echo Starting Backend...
start "LinkedIn Backend" cmd /k "title LinkedIn Backend && python run_server.py"

echo Starting Frontend...
start "LinkedIn Frontend" cmd /k "title LinkedIn Frontend && cd linkedin-frontend && npm start"

echo.
echo Both services are starting!
echo Backend: http://127.0.0.1:5000
echo Frontend: http://localhost:3000
echo.
echo Press Enter to close both backend and frontend terminals gracefully...
pause >nul

echo Closing backend and frontend terminals gracefully...
echo Sending shutdown signals to backend and frontend processes...

REM Execute the PowerShell script for graceful shutdown
powershell -ExecutionPolicy Bypass -File "graceful_shutdown.ps1"

echo All done. You can close this window.
pause 