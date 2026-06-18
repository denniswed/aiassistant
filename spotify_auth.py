#!/usr/bin/env python3
"""
One-time Spotify OAuth setup.

Run this once before starting the assistant:
    source ~/source/aiassistant/setupenv.sh
    python spotify_auth.py

After completion, the assistant handles Spotify without any auth prompts.
"""

import os
import sys
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Load keys from ~/assistant so the user doesn't have to export manually
assistant_file = Path.home() / "assistant"
if assistant_file.exists():
    for line in assistant_file.read_text().splitlines():
        line = line.strip()
        if line.startswith("export "):
            key, _, value = line[7:].partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

CLIENT_ID     = os.environ.get("SPOTIFY_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
REDIRECT_URI  = "http://127.0.0.1:9090"
SCOPE         = (
    "user-modify-playback-state "
    "user-read-playback-state "
    "user-read-currently-playing"
)
CACHE_PATH = Path(__file__).parent / ".spotify_token_cache"

if not CLIENT_ID or CLIENT_ID == "paste-your-spotify-client-id-here":
    print("✗ SPOTIFY_CLIENT_ID is not set in ~/assistant")
    sys.exit(1)
if not CLIENT_SECRET or CLIENT_SECRET == "paste-your-spotify-client-secret-here":
    print("✗ SPOTIFY_CLIENT_SECRET is not set in ~/assistant")
    sys.exit(1)

try:
    from spotipy.oauth2 import SpotifyOAuth
except ImportError:
    print("✗ spotipy not installed. Run: pip install spotipy")
    sys.exit(1)


class _CallbackHandler(BaseHTTPRequestHandler):
    auth_code: str | None = None
    error: str | None = None

    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _CallbackHandler.auth_code = params.get("code", [None])[0]
        _CallbackHandler.error = params.get("error", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        if _CallbackHandler.auth_code:
            self.wfile.write(
                b"<h2>Authorization complete!</h2><p>You can close this tab.</p>"
            )
        else:
            self.wfile.write(
                b"<h2>Authorization failed.</h2><p>Check the terminal for details.</p>"
            )

    def log_message(self, *args):
        pass  # keep output clean


oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path=str(CACHE_PATH),
    open_browser=False,
)

auth_url = oauth.get_authorize_url()

# Start server BEFORE opening browser so the port is ready when Spotify redirects back
server = HTTPServer(("127.0.0.1", 9090), _CallbackHandler)
server.timeout = 120  # give up after 2 minutes

print("\nOpening Spotify authorization in your browser…")
webbrowser.open(auth_url)
print("Waiting for callback on http://127.0.0.1:9090 … (Ctrl+C to cancel)")

server.handle_request()

if _CallbackHandler.auth_code is None and _CallbackHandler.error is None:
    print("\n✗ Timed out waiting for authorization. Run spotify_auth.py again to retry.")
    sys.exit(1)

if _CallbackHandler.error:
    print(f"\n✗ Spotify authorization denied: {_CallbackHandler.error}")
    sys.exit(1)

if not _CallbackHandler.auth_code:
    print("\n✗ No authorization code received — did the browser redirect correctly?")
    sys.exit(1)

oauth.get_access_token(_CallbackHandler.auth_code, as_dict=False)
print(f"\n✓ Spotify authorized! Token cached at {CACHE_PATH.name}")
print("Start the assistant normally — Spotify will work without any further prompts.")
