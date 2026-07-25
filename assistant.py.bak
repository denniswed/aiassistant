"""
AI Voice Assistant — Claude API + ElevenLabs TTS

Push-to-talk (Right Shift) → faster-whisper STT → Claude API (streaming)
→ ElevenLabs TTS sentence-by-sentence for low-latency spoken responses.
"""

import collections
import json
import logging
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import urllib.request
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import anthropic
import numpy as np
import sounddevice as sd
from elevenlabs import ElevenLabs
from faster_whisper import WhisperModel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('assistant.log')
    ]
)
logger = logging.getLogger(__name__)


# -----------------------------
# Configuration
# -----------------------------
@dataclass
class AssistantConfig:
    system_prompt: str = (
        "You are a concise, helpful desktop AI assistant. "
        "When asked to perform risky actions, explain first and ask before proceeding. "
        "IMPORTANT: When the user asks you to play, pause, skip, or control music, "
        "you MUST call the appropriate Spotify tool every single time — even if a previous "
        "attempt returned an error. Never describe an action as done without actually calling the tool."
    )
    sample_rate: int = 16000
    channels: int = 1
    input_device: Optional[int] = None
    output_device: Optional[int] = None
    whisper_model_size: str = "small"
    whisper_compute_type: str = "int8"
    hotkey: str = "shift_r"
    temperature: float = 0.7
    max_tokens: int = 1000
    claude_model: str = "claude-opus-4-8"
    elevenlabs_voice_id: str = ""
    elevenlabs_model_id: str = "eleven_turbo_v2"
    tts_enabled: bool = True
    ptt_enabled: bool = True
    vad_start_threshold: float = 0.02   # RMS to trigger speech start
    vad_stop_threshold: float = 0.008   # RMS to trigger speech end
    vad_start_frames: int = 2           # consecutive loud frames to start (×100ms)
    vad_stop_frames: int = 15           # consecutive quiet frames to stop (×100ms = 1.5s)
    debug: bool = False
    web_search_enabled: bool = True
    web_search_max_uses: int = 5
    local_tools_enabled: bool = True
    spotify_enabled: bool = True
    system_prompt_file: str = ""

    def __post_init__(self) -> None:
        if self.system_prompt_file:
            prompt_path = Path(self.system_prompt_file).expanduser()
            if not prompt_path.exists():
                raise FileNotFoundError(f"system_prompt_file not found: {prompt_path}")
            self.system_prompt = prompt_path.read_text().strip()
        if self.sample_rate <= 0:
            raise ValueError(f"Invalid sample_rate: {self.sample_rate}")
        if self.channels not in [1, 2]:
            raise ValueError(f"Invalid channels: {self.channels}")
        if self.whisper_model_size not in ["base", "small", "medium", "large"]:
            raise ValueError(f"Invalid whisper_model_size: {self.whisper_model_size}")
        if self.whisper_compute_type not in ["int8", "float16", "int8_float16"]:
            raise ValueError(f"Invalid whisper_compute_type: {self.whisper_compute_type}")
        if not 0 <= self.temperature <= 2:
            raise ValueError(f"Temperature must be between 0 and 2: {self.temperature}")
        if not self.elevenlabs_voice_id:
            raise ValueError("elevenlabs_voice_id must be set in config.json")

    @classmethod
    def from_json(cls, config_path: str) -> 'AssistantConfig':
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_file, 'r') as f:
            data = json.load(f)
        # Drop unknown keys so old config files don't break the dataclass
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


def load_config() -> AssistantConfig:
    config_path = "config.json"
    if os.path.exists(config_path):
        try:
            return AssistantConfig.from_json(config_path)
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            raise
    return AssistantConfig()


config = load_config()

HISTORY_FILE = Path(__file__).parent / "history.json"


def load_history() -> List[Dict[str, str]]:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load history: {e}")
    return []


def save_history(messages: List[Dict[str, str]]) -> None:
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(messages, f, indent=2)
    except Exception as e:
        logger.error(f"Could not save history: {e}")


# -----------------------------
# API clients (keys from env)
# -----------------------------
claude_client = anthropic.Anthropic()   # ANTHROPIC_API_KEY
el_client = ElevenLabs()               # ELEVENLABS_API_KEY


# -----------------------------
# faster-whisper model
# -----------------------------
logger.info("Loading faster-whisper model… (once at startup)")
try:
    whisper_model = WhisperModel(
        config.whisper_model_size,
        compute_type=config.whisper_compute_type
    )
    logger.info(f"Loaded Whisper model: {config.whisper_model_size}")
except Exception as e:
    logger.error(f"Failed to load Whisper model: {e}")
    raise


# -----------------------------
# Push-to-talk hotkey
# -----------------------------
try:
    from pynput import keyboard
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pynput"])
    from pynput import keyboard


# -----------------------------
# Audio recording
# -----------------------------
class Recorder:
    def __init__(self) -> None:
        self.samplerate = config.sample_rate
        self.channels = config.channels
        self.device = config.input_device
        self.q: queue.Queue = queue.Queue()
        self.stream: Optional[sd.InputStream] = None
        self.frames: List[np.ndarray] = []
        self._collect_thread: Optional[threading.Thread] = None

    def _callback(self, indata: np.ndarray, frames: int, time_info: Any,
                  status: sd.CallbackFlags) -> None:
        if status:
            logger.warning(f"Audio callback status: {status}")
        self.q.put(indata.copy())

    def start(self) -> None:
        self.frames = []
        self.stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype="float32",
            device=self.device,
            callback=self._callback,
            blocksize=0
        )
        self.stream.start()
        self._collect_thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._collect_thread.start()

    def _collect_loop(self) -> None:
        while True:
            try:
                data = self.q.get(timeout=0.2)
                self.frames.append(data)
            except queue.Empty:
                if self.stream is None:
                    break
            except Exception:
                break

    def stop(self) -> Optional[np.ndarray]:
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            finally:
                self.stream = None
        if self._collect_thread and self._collect_thread.is_alive():
            self._collect_thread.join(timeout=0.5)
        if not self.frames:
            return None
        audio = np.concatenate(self.frames, axis=0)
        logger.info(f"Audio captured: {len(audio)} samples, "
                    f"RMS={np.sqrt(np.mean(audio**2)):.6f}")
        return audio


# -----------------------------
# Transcription
# -----------------------------
def transcribe_ndarray(audio: np.ndarray) -> str:
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    audio = audio.flatten()

    duration = len(audio) / 16000.0
    logger.info(f"Transcribing {duration:.2f}s of audio")

    if np.max(np.abs(audio)) < 0.001:
        logger.warning("Audio level extremely low — check microphone")

    segments, info = whisper_model.transcribe(audio, language="en")
    logger.info(f"Detected language: {info.language} ({info.language_probability:.0%})")

    parts = []
    for seg in segments:
        logger.info(f"  [{seg.start:.2f}s–{seg.end:.2f}s] {seg.text}")
        parts.append(seg.text)

    return "".join(parts).strip()


# -----------------------------
# ElevenLabs TTS
# -----------------------------
def _clean_for_tts(text: str) -> str:
    """Strip markdown formatting so it isn't read aloud literally."""
    # Code blocks — keep the content, drop the fences
    text = re.sub(r'```[^\n]*\n?(.*?)```', r'\1', text, flags=re.DOTALL)
    # Inline code — keep content, drop backticks
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Links — keep display text, drop URL
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Images — drop entirely
    text = re.sub(r'!\[[^\]]*\]\([^\)]+\)', '', text)
    # Bold+italic, bold, italic (handle *** before ** before *)
    text = re.sub(r'\*{3}(.+?)\*{3}', r'\1', text)
    text = re.sub(r'\*{2}(.+?)\*{2}', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # Underscores (same order)
    text = re.sub(r'_{3}(.+?)_{3}', r'\1', text)
    text = re.sub(r'_{2}(.+?)_{2}', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    # Headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Blockquotes
    text = re.sub(r'^\s*>\s?', '', text, flags=re.MULTILINE)
    # Horizontal rules
    text = re.sub(r'^\s*[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # Bullet points
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    # Numbered list markers
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    # Collapse newlines and extra spaces
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def _play_audio_bytes(audio_bytes: bytes) -> None:
    """Play raw int16 PCM (22050 Hz, mono) through PulseAudio/PipeWire or ALSA fallback."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = Path(tmp.name)
    try:
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            wf.writeframes(audio_bytes)
        tmp.close()
        result = subprocess.run(
            ["paplay", tmp.name],
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode().strip())
    except (FileNotFoundError, RuntimeError):
        # paplay not found or failed — fall back to sounddevice
        tmp.close()
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        sd.play(audio_array, samplerate=22050, device=config.output_device)
        sd.wait()
    finally:
        tmp_path.unlink(missing_ok=True)


def _tts_elevenlabs(text: str) -> None:
    text = _clean_for_tts(text)
    if not text:
        return
    try:
        audio_chunks = el_client.text_to_speech.convert(
            voice_id=config.elevenlabs_voice_id,
            text=text,
            model_id=config.elevenlabs_model_id,
            output_format="pcm_22050",
        )
        _play_audio_bytes(b"".join(audio_chunks))
    except Exception as e:
        logger.error(f"ElevenLabs TTS error: {e}")


# Sentence boundary: punctuation followed by whitespace or end-of-string
_SENTENCE_END = re.compile(r'[.!?](?:\s|$)')


# -----------------------------
# Local filesystem tools
# -----------------------------
HOME = Path.home()
_MAX_READ_BYTES = 500_000   # ~500KB — keeps tokens sane
_MAX_OUTPUT_CHARS = 10_000  # truncate command output sent to Claude


def _resolve_path(path: str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = HOME / p
    return p.resolve()


def _in_home(p: Path) -> bool:
    try:
        p.relative_to(HOME)
        return True
    except ValueError:
        return False


def _tool_read_file(path: str) -> str:
    p = _resolve_path(path)
    if not _in_home(p):
        return f"Error: {p} is outside the home directory."
    if not p.exists():
        return f"Error: file not found: {p}"
    if not p.is_file():
        return f"Error: not a file: {p}"
    size = p.stat().st_size
    if size > _MAX_READ_BYTES:
        return (f"Error: file is {size:,} bytes — too large to read whole. "
                f"Use run_command with head, tail, or grep instead.")
    return p.read_text(errors="replace")


def _tool_write_file(path: str, content: str) -> str:
    p = _resolve_path(path)
    if not _in_home(p):
        return f"Error: {p} is outside the home directory."
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"Wrote {len(content):,} characters to {p}"


def _tool_list_directory(path: str) -> str:
    p = _resolve_path(path)
    if not _in_home(p):
        return f"Error: {p} is outside the home directory."
    if not p.exists():
        return f"Error: path not found: {p}"
    if not p.is_dir():
        return f"Error: not a directory: {p}"
    lines = []
    for entry in sorted(p.iterdir()):
        if entry.is_dir():
            lines.append(f"dir   {entry.name}/")
        else:
            lines.append(f"file  {entry.name}  ({entry.stat().st_size:,} bytes)")
    return "\n".join(lines) if lines else "(empty)"


def _tool_run_command(command: str, timeout: int = 30) -> str:
    timeout = min(timeout, 120)
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        out = result.stdout
        if result.stderr:
            out += ("\n" if out else "") + f"STDERR:\n{result.stderr}"
        if result.returncode != 0:
            out = f"Exit code: {result.returncode}\n" + out
        out = out or "(no output)"
        if len(out) > _MAX_OUTPUT_CHARS:
            out = out[:_MAX_OUTPUT_CHARS] + f"\n…[truncated at {_MAX_OUTPUT_CHARS} chars]"
        return out
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout}s"


def _tool_download_file(url: str, destination: str) -> str:
    p = _resolve_path(destination)
    if not _in_home(p):
        return f"Error: {p} is outside the home directory."
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(url, p)
        return f"Downloaded to {p} ({p.stat().st_size:,} bytes)"
    except Exception as e:
        return f"Error downloading {url}: {e}"


def _execute_tool(name: str, inputs: dict) -> str:
    try:
        if name == "read_file":
            return _tool_read_file(inputs["path"])
        if name == "write_file":
            return _tool_write_file(inputs["path"], inputs["content"])
        if name == "list_directory":
            return _tool_list_directory(inputs["path"])
        if name == "run_command":
            return _tool_run_command(inputs["command"], inputs.get("timeout", 30))
        if name == "download_file":
            return _tool_download_file(inputs["url"], inputs["destination"])
        if name == "spotify_play":
            return _tool_spotify_play(inputs["query"])
        if name == "spotify_control":
            return _tool_spotify_control(inputs["action"], inputs.get("value"))
        if name == "spotify_now_playing":
            return _tool_spotify_now_playing()
        if name == "spotify_queue":
            return _tool_spotify_queue(inputs["query"])
        return f"Unknown tool: {name}"
    except Exception as e:
        return f"Error in {name}: {e}"


LOCAL_TOOLS = [
    {
        "name": "read_file",
        "description": "Read a file's contents. Home directory only.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path (~ expands to home)."}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write or overwrite a file. Creates missing parent directories. Home directory only.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Destination file path."},
                "content": {"type": "string", "description": "Content to write."}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "list_directory",
        "description": "List files and subdirectories at a path. Home directory only.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path."}
            },
            "required": ["path"]
        }
    },
    {
        "name": "run_command",
        "description": (
            "Execute a shell command and return stdout/stderr. "
            "Use for diagnostics, git, package management, compiling, system info, etc. "
            "No restriction on what commands can run."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to run."},
                "timeout": {"type": "integer", "description": "Timeout seconds (max 120, default 30)."}
            },
            "required": ["command"]
        }
    },
    {
        "name": "download_file",
        "description": "Download a file from a URL and save it locally. Home directory only.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to download."},
                "destination": {"type": "string", "description": "Local path to save the file."}
            },
            "required": ["url", "destination"]
        }
    }
]

_TOOL_ANNOUNCEMENTS = {
    "read_file":           "Let me read that file.",
    "write_file":          "Writing the file now.",
    "list_directory":      "Let me check that directory.",
    "run_command":         "Running that command.",
    "download_file":       "Downloading that file.",
    "spotify_play":        "Let me put something on.",
    "spotify_control":     "",   # instant — no need to announce
    "spotify_now_playing": "",
    "spotify_queue":       "Adding that to the queue.",
}


# -----------------------------
# Spotify tools
# -----------------------------
_sp = None  # lazy-initialized spotipy client


def _get_spotify():
    global _sp
    if _sp is not None:
        return _sp

    cache_path = Path(__file__).parent / ".spotify_token_cache"
    if not cache_path.exists():
        raise RuntimeError(
            "Spotify not authorized yet. Run: python spotify_auth.py"
        )

    import spotipy
    from spotipy.oauth2 import SpotifyOAuth

    _sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.environ.get("SPOTIFY_CLIENT_ID", ""),
        client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET", ""),
        redirect_uri="http://127.0.0.1:9090",
        scope=(
            "user-modify-playback-state "
            "user-read-playback-state "
            "user-read-currently-playing"
        ),
        cache_path=str(cache_path),
        open_browser=False,  # never prompt during a voice session
    ))
    return _sp


_SPOTIFY_MPRIS_DEST = "org.mpris.MediaPlayer2.spotify"
_SPOTIFY_MPRIS_PATH = "/org/mpris/MediaPlayer2"


def _dbus_spotify(method: str, *args: str) -> bool:
    """Send an MPRIS2 Player method call to the running Spotify app via dbus-send."""
    try:
        result = subprocess.run(
            [
                "dbus-send", "--session", "--print-reply",
                f"--dest={_SPOTIFY_MPRIS_DEST}",
                _SPOTIFY_MPRIS_PATH,
                f"org.mpris.MediaPlayer2.Player.{method}",
            ] + list(args),
            capture_output=True, timeout=4,
        )
        ok = result.returncode == 0
        logger.info(f"dbus Spotify.{method}: {'ok' if ok else 'failed'} {result.stderr.decode().strip()}")
        return ok
    except Exception as e:
        logger.info(f"dbus Spotify.{method}: exception {e}")
        return False


def _spotify_local_running() -> bool:
    """Return True if the Spotify desktop app is reachable via dbus/MPRIS2."""
    dbus_addr = os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")
    logger.info(f"DBUS_SESSION_BUS_ADDRESS={dbus_addr!r}")
    try:
        result = subprocess.run(
            [
                "dbus-send", "--session", "--print-reply",
                f"--dest={_SPOTIFY_MPRIS_DEST}",
                _SPOTIFY_MPRIS_PATH,
                "org.freedesktop.DBus.Properties.Get",
                "string:org.mpris.MediaPlayer2.Player",
                "string:PlaybackStatus",
            ],
            capture_output=True, timeout=2,
        )
        logger.info(f"dbus probe: rc={result.returncode} stdout={result.stdout[:80]} stderr={result.stderr[:80]}")
        return result.returncode == 0
    except Exception as e:
        logger.info(f"dbus probe exception: {e}")
        return False


def _get_spotify_device_id() -> Optional[str]:
    """Return the active Spotify device ID, logging all visible devices."""
    sp = _get_spotify()
    devices = sp.devices().get("devices", [])
    if devices:
        for d in devices:
            logger.info(f"Spotify device: {d['name']!r} id={d['id']} active={d['is_active']} type={d['type']}")
    else:
        logger.info("Spotify API reports no devices")
    for d in devices:
        if d.get("is_active"):
            return d["id"]
    return devices[0]["id"] if devices else None


def _tool_spotify_play(query: str) -> str:
    sp = _get_spotify()
    results = sp.search(q=query, type="track,playlist,artist", limit=1)
    tracks = results.get("tracks", {}).get("items", [])
    playlists = results.get("playlists", {}).get("items", [])
    artists = results.get("artists", {}).get("items", [])

    uri: Optional[str] = None
    label: str = ""
    is_track: bool = False

    if tracks:
        t = tracks[0]
        uri = t["uri"]
        label = f"Playing '{t['name']}' by {', '.join(a['name'] for a in t['artists'])}"
        is_track = True
    elif playlists:
        p = playlists[0]
        uri = p["uri"]
        label = f"Playing playlist '{p['name']}'"
    elif artists:
        a = artists[0]
        uri = a["uri"]
        label = f"Playing {a['name']}"
    else:
        return f"Nothing found for '{query}'"

    # Prefer local dbus (bypasses ghost-device problem — the API's 200 OK is a lie)
    if _spotify_local_running():
        logger.info(f"Using dbus to open URI: {uri}")
        if _dbus_spotify("OpenUri", f"string:{uri}"):
            _dbus_spotify("Play")  # ensure playback starts if Spotify was paused
            return label
        logger.warning("dbus OpenUri failed despite Spotify being local — trying Web API")

    # Web API fallback (for remote/non-Linux scenarios)
    device_id = _get_spotify_device_id()
    if device_id:
        try:
            if is_track:
                sp.start_playback(device_id=device_id, uris=[uri])
            else:
                sp.start_playback(device_id=device_id, context_uri=uri)
            return label
        except Exception as e:
            logger.error(f"Web API playback failed: {e}")

    return f"Couldn't reach Spotify. Make sure the desktop app is open."


def _tool_spotify_control(action: str, value: Optional[int] = None) -> str:
    sp = _get_spotify()

    # Volume must go through Web API
    if action == "volume" and value is not None:
        device_id = _get_spotify_device_id()
        sp.volume(max(0, min(100, value)), device_id=device_id)
        return f"Volume set to {value}%"

    _mpris_method = {"pause": "Pause", "resume": "Play", "skip": "Next", "previous": "Previous"}
    if action not in _mpris_method:
        return f"Unknown action: {action}"

    label = {"pause": "Paused", "resume": "Resumed", "skip": "Skipped", "previous": "Going back"}[action]

    # Prefer dbus (same ghost-device reason as play)
    if _spotify_local_running():
        if _dbus_spotify(_mpris_method[action]):
            return label

    # Web API fallback
    device_id = _get_spotify_device_id()
    _api = {
        "pause": sp.pause_playback,
        "resume": sp.start_playback,
        "skip": sp.next_track,
        "previous": sp.previous_track,
    }
    try:
        _api[action](device_id=device_id)
        return label
    except Exception as e:
        return f"Couldn't reach Spotify for action: {action} ({e})"


def _tool_spotify_now_playing() -> str:
    sp = _get_spotify()
    current = sp.current_playback()
    if current and current.get("is_playing"):
        item = current.get("item")
        if item:
            artists = ", ".join(a["name"] for a in item["artists"])
            return f"'{item['name']}' by {artists} — {item['album']['name']}"
        return "Something is playing but couldn't get track info"

    # Web API sees nothing — query the local Spotify app via dbus
    try:
        status_result = subprocess.run(
            [
                "dbus-send", "--session", "--print-reply",
                f"--dest={_SPOTIFY_MPRIS_DEST}",
                _SPOTIFY_MPRIS_PATH,
                "org.freedesktop.DBus.Properties.Get",
                "string:org.mpris.MediaPlayer2.Player",
                "string:PlaybackStatus",
            ],
            capture_output=True, text=True, timeout=3,
        )
        meta_result = subprocess.run(
            [
                "dbus-send", "--session", "--print-reply",
                f"--dest={_SPOTIFY_MPRIS_DEST}",
                _SPOTIFY_MPRIS_PATH,
                "org.freedesktop.DBus.Properties.Get",
                "string:org.mpris.MediaPlayer2.Player",
                "string:Metadata",
            ],
            capture_output=True, text=True, timeout=3,
        )
        status_match = re.search(r'string "(\w+)"', status_result.stdout)
        status = status_match.group(1) if status_match else "Unknown"

        title_match = re.search(r'xesam:title[^\n]*\n\s*variant\s+string "([^"]+)"', meta_result.stdout)
        artist_match = re.search(r'xesam:artist[^\n]*\n.*?string "([^"]+)"', meta_result.stdout, re.DOTALL)
        title = title_match.group(1) if title_match else "Unknown"
        artist = artist_match.group(1) if artist_match else "Unknown"

        return f"Spotify is {status}: '{title}' by {artist} (app is idle — not visible to Spotify API)"
    except Exception:
        pass

    return "Nothing is currently playing"


def _tool_spotify_queue(query: str) -> str:
    sp = _get_spotify()
    device_id = _get_spotify_device_id()
    results = sp.search(q=query, type="track", limit=1)
    tracks = results.get("tracks", {}).get("items", [])
    if not tracks:
        return f"No track found for '{query}'"
    t = tracks[0]
    sp.add_to_queue(t["uri"], device_id=device_id)
    return f"Queued '{t['name']}' by {', '.join(a['name'] for a in t['artists'])}"


SPOTIFY_TOOLS = [
    {
        "name": "spotify_play",
        "description": "Search Spotify and play a track, artist, or playlist. Requires Spotify Premium.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to play — song, artist, playlist name, genre, mood, etc."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "spotify_control",
        "description": "Control Spotify playback: pause, resume, skip to next, go to previous, or set volume.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["pause", "resume", "skip", "previous", "volume"],
                    "description": "Action to perform."
                },
                "value": {
                    "type": "integer",
                    "description": "Volume level 0–100 (only for 'volume' action)."
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "spotify_now_playing",
        "description": "Get the currently playing track on Spotify.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "spotify_queue",
        "description": "Add a track to the Spotify queue without interrupting what's playing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Track to queue."}
            },
            "required": ["query"]
        }
    }
]


def _blocks_to_params(content_blocks: list) -> list:
    """Convert SDK content block objects to plain dicts for the next API call."""
    result = []
    for block in content_blocks:
        btype = getattr(block, "type", "")
        if btype == "text":
            result.append({"type": "text", "text": block.text})
        elif btype == "tool_use":
            result.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
        # server_tool_use / web_search_tool_result are handled server-side;
        # passing them back verbatim keeps the conversation coherent.
        elif btype == "server_tool_use":
            result.append({
                "type": "server_tool_use",
                "id": block.id,
                "name": block.name,
                "input": getattr(block, "input", {}),
            })
    return result


# -----------------------------
# Claude streaming + tool loop + sentence TTS
# -----------------------------
def chat_and_speak(messages: List[Dict[str, str]], speak: bool = True) -> str:
    """Stream Claude, handle tool calls, speak each sentence as it arrives."""
    full_response = ""

    # Build tool list
    tools: list = []
    if config.web_search_enabled:
        tools.append({
            "type": "web_search_20260209",
            "name": "web_search",
            "max_uses": config.web_search_max_uses,
        })
    if config.local_tools_enabled:
        tools.extend(LOCAL_TOOLS)
    if config.spotify_enabled:
        tools.extend(SPOTIFY_TOOLS)

    working_messages = list(messages)
    logger.info(f"Tools offered: {[t.get('name', t.get('type')) for t in tools]}")

    while True:
        sentence_buffer = ""
        search_announced = False

        stream_kwargs: dict = dict(
            model=config.claude_model,
            max_tokens=config.max_tokens,
            system=config.system_prompt,
            messages=working_messages,
        )
        if tools:
            stream_kwargs["tools"] = tools

        with claude_client.messages.stream(**stream_kwargs) as stream:
            for event in stream:
                btype = ""
                if event.type == "content_block_start":
                    btype = getattr(event.content_block, "type", "")

                # Web search (server-side) — announce and wait
                if (event.type == "content_block_start" and
                        btype == "server_tool_use" and
                        getattr(event.content_block, "name", "") == "web_search"):
                    if not search_announced:
                        search_announced = True
                        print("\n[searching…] ", end="", flush=True)
                        if speak:
                            _tts_elevenlabs("Let me look that up.")

                # Local tool call starting — announce what we're doing
                elif event.type == "content_block_start" and btype == "tool_use":
                    name = getattr(event.content_block, "name", "tool")
                    announcement = _TOOL_ANNOUNCEMENTS.get(name, f"Using {name}.")
                    print(f"\n[{name}…] ", end="", flush=True)
                    if speak and announcement:
                        _tts_elevenlabs(announcement)

                # Text chunk — speak sentence by sentence
                elif (event.type == "content_block_delta" and
                      getattr(event.delta, "type", "") == "text_delta"):
                    chunk = event.delta.text
                    print(chunk, end="", flush=True)
                    sentence_buffer += chunk
                    full_response += chunk

                    while True:
                        match = _SENTENCE_END.search(sentence_buffer)
                        if not match:
                            break
                        to_speak = sentence_buffer[:match.end()].strip()
                        sentence_buffer = sentence_buffer[match.end():]
                        if speak:
                            _tts_elevenlabs(to_speak)

            final_msg = stream.get_final_message()

        logger.info(f"Claude stop_reason={final_msg.stop_reason!r} "
                    f"content_types={[getattr(b,'type','?') for b in final_msg.content]}")

        # Speak any trailing text after stream closes
        if speak and sentence_buffer.strip():
            _tts_elevenlabs(sentence_buffer.strip())
        print()

        # Done — no client-side tool calls pending
        if final_msg.stop_reason != "tool_use":
            logger.info("No tool use — Claude responded with text only")
            break

        # Execute client-side tool calls and loop
        tool_results = []
        for block in final_msg.content:
            if getattr(block, "type", "") != "tool_use":
                continue
            logger.info(f"Tool call: {block.name}({block.input})")
            result = _execute_tool(block.name, block.input)
            logger.info(f"Tool result ({block.name}): {result[:300]}")
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

        working_messages.append({
            "role": "assistant",
            "content": _blocks_to_params(final_msg.content),
        })
        working_messages.append({
            "role": "user",
            "content": tool_results,
        })

    return full_response


# -----------------------------
# Shared voice audio processing
# -----------------------------
_HALLUCINATIONS = {
    "thanks for watching", "thank you for watching",
    "please subscribe", "like and subscribe",
    "you", "thank you", "thanks", "bye", "bye bye",
    "subtitles by", "translated by",
}


def _process_voice_audio(audio: np.ndarray, messages: List[Dict[str, str]],
                         lock: threading.Lock, state: dict) -> None:
    """Validate and dispatch a voice recording — shared by PTT and VAD paths."""
    duration = len(audio) / config.sample_rate
    rms = float(np.sqrt(np.mean(audio ** 2)))
    if duration < 0.5:
        return
    if rms < 0.02:
        return
    try:
        text = transcribe_ndarray(audio)
    except Exception as e:
        print(f"Transcription error: {e}")
        return
    if not text:
        return
    if text.strip().lower().rstrip(".!?,") in _HALLUCINATIONS:
        logger.info(f"Whisper hallucination filtered: {text!r} (rms={rms:.4f})")
        return
    _process_input(text, messages, lock, speak=state["tts"])


def _always_listening_loop(messages: List[Dict[str, str]],
                            lock: threading.Lock, state: dict) -> None:
    """VAD-based continuous listening — runs when PTT is disabled."""
    import time
    FRAME_SAMPLES = int(config.sample_rate * 0.1)   # 100 ms frames
    PRE_ROLL = 4

    print("Calibrating ambient noise… (be quiet for 1 second)")

    with sd.InputStream(
        samplerate=config.sample_rate,
        channels=config.channels,
        dtype="float32",
        device=config.input_device,
        blocksize=FRAME_SAMPLES,
    ) as stream:
        # Actively drain PipeWire garbage frames — wait until signal stabilizes
        # (PipeWire emits frames with RMS ~1.0 for ~1 second on stream open)
        stable_streak = 0
        for _ in range(50):  # max 5 second drain timeout
            data, _ = stream.read(FRAME_SAMPLES)
            rms = float(np.sqrt(np.mean(data ** 2)))
            if np.isfinite(rms) and rms < 0.3:
                stable_streak += 1
                if stable_streak >= 5:
                    break
            else:
                stable_streak = 0

        # Measure noise floor over 2 seconds of stable signal
        noise_samples = []
        for _ in range(20):
            data, _ = stream.read(FRAME_SAMPLES)
            rms = float(np.sqrt(np.mean(data ** 2)))
            if np.isfinite(rms) and rms < 1.0:
                noise_samples.append(rms)

        noise_floor = float(np.mean(noise_samples)) if noise_samples else 0.02
        # 2× above noise floor; cap at 0.15 so music during calibration doesn't make
        # the threshold unreachable; honour any explicit override in config
        start_thresh = max(noise_floor * 2.0, config.vad_start_threshold)
        start_thresh = min(start_thresh, 0.15)
        stop_thresh  = max(noise_floor * 1.2, config.vad_stop_threshold)
        logger.info(f"VAD noise_floor={noise_floor:.4f} start={start_thresh:.4f} stop={stop_thresh:.4f}")
        if config.debug:
            print(f"Noise floor={noise_floor:.4f}  start>{start_thresh:.4f}  stop<{stop_thresh:.4f}")
        print("Always-listening mode active. Speak anytime.")

        pre_roll: collections.deque = collections.deque(maxlen=PRE_ROLL)
        accumulated: List[np.ndarray] = []
        speech_frames = 0
        silence_frames = 0
        recording = False
        frame_count = 0

        while not state["ptt"]:
            data, _ = stream.read(FRAME_SAMPLES)
            rms = float(np.sqrt(np.mean(data ** 2)))
            if not np.isfinite(rms):
                continue

            frame_count += 1
            if config.debug and frame_count % 10 == 0:
                bar = "█" * min(int(rms / max(start_thresh, 0.001) * 20), 30)
                status = "REC" if recording else "   "
                print(f"\r[VAD {status}] {rms:.4f}  {bar:<30}", end="", flush=True)

            if not recording:
                pre_roll.append(data.copy())
                if rms > start_thresh:
                    speech_frames += 1
                    if speech_frames >= config.vad_start_frames:
                        recording = True
                        speech_frames = 0
                        silence_frames = 0
                        accumulated = [d.copy() for d in pre_roll]
                        print(f"\n[recording… RMS={rms:.4f}]", flush=True)
                else:
                    speech_frames = max(0, speech_frames - 1)
            else:
                accumulated.append(data.copy())
                if rms < stop_thresh:
                    silence_frames += 1
                    if silence_frames >= config.vad_stop_frames:
                        recording = False
                        silence_frames = 0
                        audio = np.concatenate(accumulated)
                        accumulated = []
                        print()
                        threading.Thread(
                            target=_process_voice_audio,
                            args=(audio, messages, lock, state),
                            daemon=True,
                        ).start()
                else:
                    silence_frames = 0

    print("Always-listening mode stopped.")


def _process_input(text: str, messages: List[Dict[str, str]],
                   lock: threading.Lock, speak: bool = True) -> None:
    """Handle one user turn — shared by voice and keyboard paths."""
    with lock:
        print(f"\nYou: {text}")
        messages.append({"role": "user", "content": text})
        print("Assistant: ", end="", flush=True)
        try:
            reply = chat_and_speak(messages, speak=speak)
        except Exception as e:
            logger.error(f"Claude error: {e}")
            reply = "I ran into an error contacting Claude."
            print(reply)
            if speak:
                _tts_elevenlabs(reply)
        messages.append({"role": "assistant", "content": reply})
        save_history(messages)


def _start_always_listening(messages: List[Dict[str, str]],
                            lock: threading.Lock, state: dict) -> None:
    threading.Thread(
        target=_always_listening_loop, args=(messages, lock, state), daemon=True
    ).start()


def _keyboard_input_loop(messages: List[Dict[str, str]], lock: threading.Lock,
                         state: dict) -> None:
    """Read lines from stdin and process them as text input."""
    while True:
        try:
            text = input()
        except EOFError:
            break
        text = text.strip()
        if not text:
            continue
        if text.lower() in ("/exitai", "/exit", "/quit"):
            print("Goodbye.")
            state["quit"].set()
            break
        if text.lower() in ("/tts", "/tts toggle"):
            state["tts"] = not state["tts"]
            print(f"TTS {'enabled' if state['tts'] else 'disabled'}.")
            continue
        if text.lower() == "/tts on":
            state["tts"] = True
            print("TTS enabled.")
            continue
        if text.lower() == "/tts off":
            state["tts"] = False
            print("TTS disabled.")
            continue
        if text.lower() in ("/ptt", "/ptt toggle"):
            state["ptt"] = not state["ptt"]
            if state["ptt"]:
                print("Push-to-talk enabled. Hold Right Shift to speak.")
            else:
                print("Push-to-talk disabled.")
                _start_always_listening(messages, lock, state)
            continue
        if text.lower() == "/ptt on":
            state["ptt"] = True
            print("Push-to-talk enabled. Hold Right Shift to speak.")
            continue
        if text.lower() == "/ptt off":
            state["ptt"] = False
            print("Push-to-talk disabled.")
            _start_always_listening(messages, lock, state)
            continue
        _process_input(text, messages, lock, speak=state["tts"])


def main() -> None:
    try:
        if config.input_device is not None or config.output_device is not None:
            sd.default.device = (config.input_device, config.output_device)
            logger.info(f"Audio devices — input: {config.input_device}, output: {config.output_device}")

        messages: List[Dict[str, str]] = load_history()
        rec = Recorder()
        lock = threading.Lock()
        state = {"tts": config.tts_enabled, "ptt": config.ptt_enabled,
                 "quit": threading.Event()}

        if messages:
            print(f"Resuming — {len(messages) // 2} previous exchanges loaded.")
        else:
            print("Assistant ready.")
        print(f"Hold [{config.hotkey}] to talk; release to transcribe & respond.")
        print("Or just type and press Enter.")
        print("Commands: /tts  /ptt  /exitai\n")

        # Keyboard text input thread
        kb_thread = threading.Thread(
            target=_keyboard_input_loop, args=(messages, lock, state), daemon=True
        )
        kb_thread.start()

        # Startup greeting — one-off Claude call, not added to conversation history
        def _greet() -> None:
            with lock:
                greeting_msgs = [{"role": "user", "content": "Greet me briefly — one or two sentences max."}]
                chat_and_speak(greeting_msgs, speak=state["tts"])
        threading.Thread(target=_greet, daemon=True).start()

        # Start always-listening if PTT is disabled at launch
        if not state["ptt"]:
            _start_always_listening(messages, lock, state)

        recording_flag = {"active": False}

        def on_press(key: keyboard.Key) -> None:
            try:
                if (key == keyboard.Key.shift_r and not recording_flag["active"]
                        and state["ptt"]):
                    recording_flag["active"] = True
                    print("\nRecording… (hold Right Shift)")
                    rec.start()
            except AttributeError:
                pass
            except Exception as e:
                logger.error(f"on_press error: {e}")

        def on_release(key: keyboard.Key) -> None:
            try:
                if key == keyboard.Key.shift_r and recording_flag["active"] and state["ptt"]:
                    recording_flag["active"] = False
                    print("Stopped. Transcribing…")
                    audio = rec.stop()

                    if audio is None or len(audio) == 0:
                        print("No audio captured.")
                        return

                    _process_voice_audio(audio, messages, lock, state)
            except AttributeError:
                pass
            except Exception as e:
                logger.error(f"on_release error: {e}")

        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            try:
                state["quit"].wait()
            except KeyboardInterrupt:
                print("\nExiting…")
            finally:
                save_history(messages)
                listener.stop()

    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
