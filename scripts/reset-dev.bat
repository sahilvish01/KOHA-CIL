@echo off
cd /d "%~dp0.."

echo ============================================================
echo   KOHA-CIL Prototype -- Resetting Data to Fresh Default State
echo ============================================================
echo.

echo [Step 1] Cleaning SQLite Database...
if exist "data\koha_cil.db" del /f /q "data\koha_cil.db"

echo.
echo [Step 2] Clearing Uploads, Quarantine, Cache and Chroma Vector Store...
if exist "data\uploads" del /f /q /s "data\uploads\*.*" >nul 2>&1
if exist "data\quarantine" del /f /q /s "data\quarantine\*.*" >nul 2>&1
if exist "data\cache" del /f /q /s "data\cache\*.*" >nul 2>&1
if exist "data\chroma" rmdir /s /q "data\chroma" >nul 2>&1

echo.
echo ============================================================
echo   SUCCESS: Prototype data reset complete!
echo   Run 'scripts\start-dev.bat' to launch clean server with seed data.
echo ============================================================
echo.
pause