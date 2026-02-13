#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
python -m venv .venv || true
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
python api_server.py
