@echo off
setlocal
set "ROOT=%~dp0.."
if not exist "%ROOT%\.env" copy "%ROOT%\.env.example" "%ROOT%\.env" >nul
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
echo Starting KOHA-CIL services in separate windows...
start "KOHA-CIL Backend" /D "%ROOT%\backend" "%PYTHON%" -m uvicorn main:app --reload --port 8000
start "KOHA-CIL Gateway" /D "%ROOT%\security" cmd /k "npm install && npm run dev"
start "KOHA-CIL Frontend" /D "%ROOT%\frontend" cmd /k "npm install && npm run dev"
echo Open http://localhost:5173 after the services are ready.