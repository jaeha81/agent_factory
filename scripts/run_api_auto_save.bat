@echo off
setlocal enabledelayedexpansion
cd /d %~dp0\..

echo ============================================
echo   JH Agent Factory - Run + AutoSave
echo ============================================
echo.

:: Start the API server (blocks until Ctrl+C)
echo [RUN] API server start...
call scripts\run_api.bat

echo.
echo [STOP] Server stopped. Now autosave and push...
echo.

:: Prompt for commit message
set "MSG="
set /p MSG="Commit message (Enter=auto): "

:: If empty, generate auto message with timestamp
if "!MSG!"=="" (
    for /f "tokens=*" %%a in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm\""') do set "TS=%%a"
    set "MSG=AutoSave: !TS!"
)

:: Save and push
call scripts\save_and_push.bat "!MSG!"

echo.
echo [DONE] Saved and pushed.
pause
exit /b 0
