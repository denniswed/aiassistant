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

for var in ANTHROPIC_API_KEY ELEVENLABS_API_KEY; do
    if [ -z "${!var:-}" ]; then
        echo "Error: $var is not set."
        echo "Add it to ~/.config/environment.d/ai-assistant.conf and log out/in."
        read -r -p "Press Enter to close…"
        exit 1
    fi
done

source "$VENV/bin/activate"
cd "$ASSISTANT_DIR"
exec python assistant.py
