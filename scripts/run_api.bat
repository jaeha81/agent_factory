@echo off
setlocal
cd /d %~dp0\..

echo ============================================
echo   JH Agent Factory - API Server Launcher
echo ============================================

if not exist .venv (
    echo [1/4] Creating .venv ...
    python -m venv .venv
)

echo [2/4] Activating .venv ...
call .venv\Scripts\activate

echo [3/4] Installing dependencies ...
python -m pip install -U pip >nul 2>&1
pip install -r requirements.txt >nul 2>&1

echo [4/4] Starting API server ...
echo.
echo   Swagger:  http://localhost:8000/docs
echo   Agents:   http://localhost:8000/api/agents
echo   Status:   http://localhost:8000/api/system/status
echo   Stop:     Ctrl+C
echo.

python api_server.py

endlocal
