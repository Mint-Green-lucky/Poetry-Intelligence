@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title Poetry Agent - Do Not Close

set "PYTHON=%~dp0.venv\Scripts\python.exe"
set "LOG=%~dp0startup-error.log"

if exist "%PYTHON%" goto :check_environment

echo [1/3] Creating project virtual environment...
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -m venv "%~dp0.venv"
) else (
  where python >nul 2>nul
  if errorlevel 1 goto :missing_python
  python -m venv "%~dp0.venv"
)
if errorlevel 1 goto :missing_python

:check_environment
echo [2/3] Checking project dependencies...
"%PYTHON%" -c "import fastapi, uvicorn, langgraph"
if errorlevel 1 goto :install_dependencies
goto :start_server

:install_dependencies
echo Installing dependencies into .venv (network required only this time)...
"%PYTHON%" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 goto :dependency_error

:start_server
echo [3/3] Starting Poetry Agent...
echo URL: http://127.0.0.1:8000
echo Initial dataset loading may take 10-60 seconds.
echo Keep this window open. Press Ctrl+C to stop.
del /q "%LOG%" >nul 2>nul
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "$url='http://127.0.0.1:8000/api/health'; for($i=0;$i -lt 120;$i++){ try { $r=Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2; if($r.StatusCode -eq 200){ Start-Process 'http://127.0.0.1:8000'; exit } } catch {}; Start-Sleep -Seconds 1 }"
"%PYTHON%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 2>"%LOG%"
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo Server stopped with exit code %EXIT_CODE%.
if exist "%LOG%" type "%LOG%"
echo.
pause
exit /b %EXIT_CODE%

:missing_python
echo [ERROR] Python 3 was not found.
echo Install Python 3.11 or newer and enable "Add Python to PATH", then retry.
pause
exit /b 1

:dependency_error
echo [ERROR] Dependency installation failed.
pause
exit /b 1
