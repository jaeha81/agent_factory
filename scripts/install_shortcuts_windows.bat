@echo off
setlocal
cd /d %~dp0\..

echo ============================================
echo   JH Agent Factory - Install Desktop Shortcuts
echo ============================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\install_shortcuts_windows.ps1"

echo.
if errorlevel 1 (
    echo [FAIL] Shortcut installation failed.
) else (
    echo [OK] Shortcuts installed on your Desktop.
)
echo.
pause
exit /b 0
