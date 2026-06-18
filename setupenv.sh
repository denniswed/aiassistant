#!/bin/bash
# Activate the desk-ai virtual environment

# Note: This script should be sourced, not executed
# Usage: source setupenv.sh

if [ -d ~/.venvs/desk-ai ]; then
    source ~/.venvs/desk-ai/bin/activate
    echo "✓ Virtual environment activated: desk-ai"
    echo "Python: $(which python)"
    python --version
else
    echo "✗ Error: Virtual environment not found at ~/.venvs/desk-ai"
    echo "Create it with: python3 -m venv ~/.venvs/desk-ai"
    return 1
fi
