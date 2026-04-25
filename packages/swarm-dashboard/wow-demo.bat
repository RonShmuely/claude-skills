@echo off
setlocal EnableDelayedExpansion
title Swarm Wow Demo

echo.
echo.
echo    [swarm-orchestrator] wow demo launcher
echo    ======================================
echo.
echo    Opening the live dashboard in your browser...
echo.

REM Start the Flask server in a new window if it isn't already running
netstat -ano ^| findstr ":5173" ^| findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo    Starting Flask backend on port 5173...
    start "Swarm Monitor" cmd /c "cd /d %~dp0 && python app.py"
    timeout /t 3 /nobreak >nul
) else (
    echo    Flask backend already running on port 5173.
)

REM Open the dashboard
start "" "http://127.0.0.1:5173"

echo.
echo    Dashboard opened. Now:
echo.
echo    1. Make sure Claude Code is running in a terminal
echo    2. Switch to the Claude Code window
echo    3. Paste this trigger phrase:
echo.
echo         fire the wow demo
echo.
echo    Watch the dashboard. Five cards will light up in parallel.
echo    After they finish, a sixth (reviewer) card will appear.
echo    Synthesis lands in chat when the reviewer completes.
echo.
echo    Total wall time: ~4-5 min. Estimated cost: ~$0.80.
echo.
pause
