#!/bin/bash
# Check virtual environment setup

echo "=== Checking desk-ai Virtual Environment ==="
echo ""

# Check if directory exists
if [ -d ~/.venvs/desk-ai ]; then
    echo "✓ Directory exists: ~/.venvs/desk-ai"
    
    # Check for pyvenv.cfg (standard venv)
    if [ -f ~/.venvs/desk-ai/pyvenv.cfg ]; then
        echo "✓ Standard Python venv detected"
        echo ""
        echo "Configuration:"
        cat ~/.venvs/desk-ai/pyvenv.cfg
    fi
    
    # Check for Python executable
    if [ -f ~/.venvs/desk-ai/bin/python ]; then
        echo ""
        echo "✓ Python executable found"
        ~/.venvs/desk-ai/bin/python --version
    else
        echo "✗ No Python executable found"
    fi
    
    # Check for piper
    if [ -f ~/.venvs/desk-ai/bin/piper ]; then
        echo "✓ Piper TTS installed"
    else
        echo "✗ Piper TTS not found"
    fi
    
else
    echo "✗ Directory not found: ~/.venvs/desk-ai"
    echo ""
    echo "You need to create the virtual environment first."
fi

echo ""
echo "=== Checking uv installation ==="
if command -v uv &> /dev/null; then
    echo "✓ uv is installed"
    uv --version
else
    echo "✗ uv is not installed"
fi

echo ""
echo "=== Current Python ==="
which python
python --version
