@echo off
cd /d "%~dp0"
title puzzle71-pool — serwer
python --version >nul 2>&1 || (echo Potrzebny Python 3 & pause & exit /b 1)
echo Serwer puli: http://127.0.0.1:8780/
echo.
python server.py --host 0.0.0.0 --port 8780
pause
