#!/usr/bin/env bash
set -euo pipefail
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
echo "ACOS installed. Run: source .venv/bin/activate && uvicorn acos.main:app --reload"
