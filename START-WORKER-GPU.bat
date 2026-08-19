@echo off
cd /d "%~dp0"
title puzzle71-pool — worker GPU
if "%~1"=="" (
  echo Uzycie: START-WORKER-GPU.bat ADRES_BTC [URL] [nick]
  echo Przyklad: START-WORKER-GPU.bat bc1q... http://127.0.0.1:8780 Kuba
  pause
  exit /b 1
)
set URL=%~2
if "%URL%"=="" set URL=http://127.0.0.1:8780
set NICK=%~3
if "%NICK%"=="" set NICK=miner
python worker.py %URL% %~1 gpu %NICK%
pause
