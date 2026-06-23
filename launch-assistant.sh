#!/bin/bash
# Launch the AI assistant in its virtual environment.
# Run directly (not sourced) — used by the .desktop launcher.

set -euo pipefail

VENV=~/.venvs/desk-ai
ASSISTANT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$VENV" ]; then
    echo "Error: virtual environment not found at $VENV"
    echo "Run: python3 -m venv $VENV && pip install -r $ASSISTANT_DIR/requirements.txt"
    read -r -p "Press Enter to close…"
    exit 1
fi

source "$VENV/bin/activate"
cd "$ASSISTANT_DIR"
exec python assistant.py
