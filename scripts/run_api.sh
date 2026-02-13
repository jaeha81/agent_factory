#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "============================================"
echo "  JH Agent Factory - API Server Launcher"
echo "============================================"

if [ ! -d .venv ]; then
    echo "[1/4] Creating .venv ..."
    python3 -m venv .venv || python -m venv .venv
fi

echo "[2/4] Activating .venv ..."
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate

echo "[3/4] Installing dependencies ..."
python -m pip install -U pip -q
pip install -r requirements.txt -q

echo "[4/4] Starting API server ..."
echo ""
echo "  Swagger:  http://localhost:8000/docs"
echo "  Agents:   http://localhost:8000/api/agents"
echo "  Status:   http://localhost:8000/api/system/status"
echo "  Stop:     Ctrl+C"
echo ""

python api_server.py
