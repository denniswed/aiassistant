# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

The project uses a virtual environment at `~/.venvs/desk-ai`.

```bash
source setupenv.sh        # Activate the virtual environment
pip install -r requirements.txt
pip install lmstudio      # LM Studio Python SDK
```

## Running the Assistant

```bash
source setupenv.sh
python assistant.py
```

Hold Right Shift to record, release to transcribe and get a response. `Ctrl+C` to quit.

## Diagnostic / Setup Commands

```bash
python audio_setup.py      # Interactive wizard to select and test audio devices
python test_pipeline.py    # Full pipeline diagnostic: records 5s, saves WAV, transcribes
python check_lmstudio.py   # Verify LM Studio connection and model availability
./check_env.sh             # Check system dependencies
```

## Configuration

Copy `config.json.example` to `config.json` before first run. Key fields:

| Field | Description |
|---|---|
| `llm_backend` | `"lmstudio_sdk"` (recommended) or `"lmstudio_api"` |
| `lmstudio_model` | Leave empty for auto-detection in SDK mode |
| `whisper_model_size` | `base`/`small`/`medium`/`large` — speed vs. accuracy |
| `whisper_compute_type` | `int8` (CPU), `float16` (GPU/CUDA), `int8_float16` |
| `input_device` / `output_device` | Integer device index from `sd.query_devices()` |
| `piper_bin` | Path to Piper binary (default: `~/.venvs/desk-ai/bin/piper`) |
| `piper_voice` | Path to `.onnx` voice model file |

## Architecture

The pipeline is linear and single-file (`assistant.py`):

```
Right Shift (pynput) → Recorder (sounddevice) → transcribe_ndarray (faster-whisper)
    → chat_lmstudio (LM Studio SDK or HTTP API) → tts_piper (Piper subprocess) → play_wav
```

**`AssistantConfig` dataclass** — loaded from `config.json` at module import time into the global `config`. All functions reference this global directly rather than accepting config as a parameter.

**`Recorder` class** — uses a `sounddevice.InputStream` with a background thread (`_collect_loop`) pulling from a `queue.Queue`. `stop()` joins the thread and concatenates frames into a single numpy array.

**LM Studio backends** — `chat_lmstudio()` dispatches to `_chat_lmstudio_sdk()` or `_chat_lmstudio_api()` based on `config.llm_backend`. SDK mode auto-detects loaded models; API mode requires LM Studio server running on port 1234. SDK falls back to API if the `lmstudio` package is unavailable.

**TTS** — `tts_piper()` pipes text to the Piper binary via `subprocess.Popen`, writes a temp WAV, then calls `play_wav()` via `simpleaudio`. TTS is skipped gracefully if the voice model file is missing.

**Conversation state** — maintained as a plain list of OpenAI-format message dicts in `main()`, prepended with the system prompt. No persistence between runs.

## External Dependencies

- **LM Studio app** must be running with a model loaded (SDK mode can auto-detect; API mode requires the local server started manually)
- **Piper binary + voice model** — installed separately; default voice: `en_US-amy-medium.onnx`
- **faster-whisper** — downloads Whisper model weights on first run (~150MB for `small`)
