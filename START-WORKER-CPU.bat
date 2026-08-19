@echo off
cd /d "%~dp0"
title puzzle71-pool — worker CPU
if "%~1"=="" (
  echo Uzycie: START-WORKER-CPU.bat ADRES_BTC [URL] [nick]
  pause
  exit /b 1
)
set URL=%~2
if "%URL%"=="" set URL=http://127.0.0.1:8780
set NICK=%~3
if "%NICK%"=="" set NICK=miner
python worker.py %URL% %~1 cpu %NICK%
pause
