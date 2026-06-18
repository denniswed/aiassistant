#!/bin/bash
# AI Assistant startup script
# Usage: ./setup.sh  (or  bash setup.sh)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load API keys
KEYS_FILE=~/assistant
if [ ! -f "$KEYS_FILE" ]; then
    echo "✗ API keys file not found: $KEYS_FILE"
    echo "  Create it and add your keys:"
    echo "    export ANTHROPIC_API_KEY=\"...\""
    echo "    export ELEVENLABS_API_KEY=\"...\""
    exit 1
fi
source "$KEYS_FILE"

# Validate keys are set and not placeholder values
if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "paste-your-anthropic-api-key-here" ]; then
    echo "✗ ANTHROPIC_API_KEY is not set in ~/assistant"
    exit 1
fi
if [ -z "$ELEVENLABS_API_KEY" ] || [ "$ELEVENLABS_API_KEY" = "paste-your-elevenlabs-api-key-here" ]; then
    echo "✗ ELEVENLABS_API_KEY is not set in ~/assistant"
    exit 1
fi

echo "✓ API keys loaded"

# Activate virtual environment
source "$SCRIPT_DIR/setupenv.sh"

# Spotify one-time auth (runs only if creds are set but token isn't cached yet)
cd "$SCRIPT_DIR"
SPOTIFY_CACHE="$SCRIPT_DIR/.spotify_token_cache"
if [ ! -f "$SPOTIFY_CACHE" ] && \
   [ -n "$SPOTIFY_CLIENT_ID" ] && \
   [ "$SPOTIFY_CLIENT_ID" != "paste-your-spotify-client-id-here" ]; then
    echo ""
    echo "Spotify credentials found but not yet authorized."
    echo "Starting one-time Spotify login…"
    if python spotify_auth.py; then
        echo "✓ Spotify ready"
    else
        echo "⚠ Spotify auth failed or was cancelled — Spotify commands won't work."
        echo "  Re-run setup.sh to try again."
    fi
    echo ""
fi

# Run from project directory so config.json is found
exec python assistant.py
