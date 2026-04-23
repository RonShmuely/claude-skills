@echo off
cd /d "%~dp0"
title Swarm Monitor
echo.
echo   [ swarm monitor ] live agent dashboard
echo   http://127.0.0.1:5173
echo.
start "" "http://127.0.0.1:5173"
python app.py
