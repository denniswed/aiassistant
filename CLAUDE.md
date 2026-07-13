# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-file, push-to-talk (or always-listening) desktop voice assistant:

```
Right Shift / VAD → faster-whisper STT → Claude API (streaming, tool loop)
    → ElevenLabs TTS (sentence-by-sentence for low latency) → paplay
```

Everything lives in `assistant.py` (~1300 lines). The other Python files are one-off
utilities and diagnostics.

## Environment Setup

Virtual environment at `~/.venvs/desk-ai`.

```bash
source setupenv.sh                 # Activate the venv
pip install -r requirements.txt
```

**API keys are read from the environment**, not `config.json`:

| Env var | Used for |
|---|---|
| `ANTHROPIC_API_KEY` | Claude (`anthropic.Anthropic()`) |
| `ELEVENLABS_API_KEY` | TTS (`ElevenLabs()`) |
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | Spotify tools (optional) |

`setup.sh` sources these from `~/assistant` (a shell file of `export` lines);
`launch-assistant.sh` (the `.desktop` launcher) expects them already exported
(e.g. via `~/.config/environment.d/`).

## Running

```bash
./setup.sh                 # Recommended: loads keys from ~/assistant, activates venv,
                           # runs one-time Spotify auth if needed, then launches
# or, if keys are already exported:
source setupenv.sh && python assistant.py
```

Controls once running:
- **Hold Right Shift** to record; release to transcribe + respond (PTT mode).
- **Type + Enter** for text input (always available in parallel).
- Slash commands: `/tts [on|off]`, `/ptt [on|off]` (off ⇒ always-listening VAD), `/exitai`.
- `Ctrl+C` to quit.

## Diagnostics

```bash
python audio_setup.py      # Interactive wizard: select + test audio devices
python test_pipeline.py    # Records 5s, saves WAV, transcribes — full STT check
python spotify_auth.py     # One-time Spotify OAuth (writes .spotify_token_cache)
python compact_history.py  # Summarize old history.json exchanges into a memory block
```

> `check_lmstudio.py` and `check_env.sh` are **stale** — they reference the old
> LM Studio + Piper backend that no longer exists. Ignore them.

## Configuration

Copy `config.json.example` to `config.json`. Notable fields (see `AssistantConfig` for all):

| Field | Notes |
|---|---|
| `system_prompt_file` | Path to a prompt file; overrides the inline default (`system_prompt.txt`) |
| `claude_model` | e.g. `claude-opus-4-8` |
| `max_tokens` | On truncation the assistant **auto-continues** rather than stopping |
| `elevenlabs_voice_id` | **Required** — `__post_init__` raises if empty |
| `elevenlabs_model_id` | Default `eleven_turbo_v2` |
| `whisper_model_size` / `whisper_compute_type` | `int8` for CPU, `float16` for GPU |
| `input_device` / `output_device` | Integer index from `sd.query_devices()` |
| `web_search_enabled`, `local_tools_enabled`, `spotify_enabled` | Toggle each tool group |
| `ptt_enabled`, `tts_enabled` | Startup defaults for the runtime `state` dict |
| `vad_*` | Always-listening thresholds (auto-calibrated at runtime, see below) |

`AssistantConfig.from_json` silently drops unknown keys, so stale config files won't crash.

## Architecture (`assistant.py`)

**Global singletons at import time** — `config` (from `load_config()`), `claude_client`,
`el_client`, and `whisper_model` are all module-level globals initialized on import.
Functions reference `config` directly rather than taking it as a parameter.

**`chat_and_speak(messages, speak)` is the core.** It:
1. Assembles the tool list from three sources: server-side `web_search`, `LOCAL_TOOLS`
   (filesystem/shell), and `SPOTIFY_TOOLS`.
2. Streams the Claude response, printing + buffering text and flushing complete
   **sentences** to TTS as they arrive (`_SENTENCE_END` regex) so speech starts before
   the full reply is done.
3. Runs the **tool loop**: on `stop_reason == "tool_use"` it executes client-side tools
   via `_execute_tool`, appends `assistant` + `tool_result` turns, and re-streams. Loops
   until Claude returns plain text.
4. On `stop_reason == "max_tokens"` it **auto-continues** — feeds the partial turn back
   with a "resume where you left off" prompt.

`_blocks_to_params` converts SDK content-block objects back into plain dicts for the next
API call (needed because the tool loop re-sends prior assistant turns).

**Three input paths converge on `_process_input`:**
- **PTT** — `pynput` `on_press`/`on_release` on Right Shift drive a `Recorder`
  (background thread draining a `queue.Queue` from a `sounddevice.InputStream`).
- **VAD always-listening** — `_always_listening_loop` runs when PTT is off. It drains
  PipeWire's garbage startup frames, calibrates a noise floor, then does RMS-based
  start/stop detection with pre-roll, spawning `_process_voice_audio` per utterance.
- **Keyboard** — `_keyboard_input_loop` reads stdin lines; handles slash commands.

A shared `threading.Lock` serializes turns so voice/text/VAD inputs don't interleave.
A shared `state` dict (`tts`, `ptt`, `quit` Event) is mutated by slash commands.

**Whisper hallucination filter** — `_process_voice_audio` drops sub-0.5s / low-RMS clips
and known Whisper filler phrases (`_HALLUCINATIONS`, e.g. "thanks for watching").

**Tools** (`_execute_tool` dispatches by name):
- *Local* (`LOCAL_TOOLS`): `read_file`, `write_file`, `list_directory`, `download_file`
  are all **restricted to `$HOME`** (`_in_home` check). `run_command` is **unrestricted**
  shell execution (only a 120s timeout + output truncation) — powerful and dangerous.
- *Spotify* (`SPOTIFY_TOOLS`): `spotify_play`, `spotify_control`, `spotify_now_playing`,
  `spotify_queue`. **Prefers local dbus/MPRIS2** (`_dbus_spotify`) over the Web API — the
  Web API reports a "ghost device" and returns a lying `200 OK` when the desktop app is
  idle, so dbus is the reliable path; Web API is the fallback for remote/volume/search.
- *Web search*: server-side (`web_search_20260209`), handled inside the stream.
- `_TOOL_ANNOUNCEMENTS` maps each tool to a short spoken phrase played when it starts.

**TTS** — `_tts_elevenlabs` strips markdown (`_clean_for_tts`) then requests
`pcm_22050`; `_play_audio_bytes` writes a temp WAV and plays via `paplay`, falling back
to `sounddevice` if `paplay` is unavailable.

**Conversation persistence** — the message list is loaded from / saved to `history.json`
(`load_history`/`save_history`) every turn, so conversations resume across runs. Use
`compact_history.py` to summarize old exchanges into a `[MEMORY —` block and keep the
file lean. The startup greeting is a one-off Claude call **not** added to history.

## Knowledge base (local RAG)

A fully local retrieval layer lets Claude answer from the user's own library of
books and papers. Nothing leaves the machine except the passages Claude ends up
citing (which go to the Claude API like any other context).

**Files:**
- `rag.py` — standalone core. Deliberately does **not** import `assistant.py`, so
  ingesting never loads Whisper/Claude/ElevenLabs. Lazy-loads the embedding model and
  Chroma client on first use.
- `ingest.py` — CLI to (re)index documents.

**Stack:** `sentence-transformers` (`BAAI/bge-base-en-v1.5`, local, ~440MB, CPU) →
Chroma persistent store (`kb_store/`, cosine space). bge wants a query instruction
prefix on queries only — handled in `rag._embed(is_query=...)`.

**Ingest** (`rag.ingest_path`): recurses a folder, extracts text (PDFs **page-by-page**
via `pypdf` for exact page attribution; `.txt/.md` whole), token-aware chunks
(`kb_chunk_tokens`≈400 to stay under bge's 512 limit, with overlap), embeds, and stores
each chunk with metadata (`title`, `source`, `page`, `file_hash`). **Incremental**: files
are hashed, so re-running skips unchanged files and re-indexes changed ones. Extensible —
drop new papers into `kb_dir` and re-run.

```bash
python ingest.py                          # index everything under kb_dir (config), incremental
python ingest.py --path ~/papers          # index a specific folder/file
python ingest.py --reset                  # wipe kb_store and rebuild
python ingest.py --stats                  # list indexed sources + chunk counts
python ingest.py --query "backreaction"   # test a retrieval without launching the assistant
```

**Retrieval** is exposed to Claude as the **`search_knowledge_base` tool** (in `KB_TOOLS`,
gated by `config.kb_enabled`), not always-on injection — so ordinary turns ("skip this
song") don't drag in book chunks. `_tool_search_knowledge_base` returns the top-k passages
**each with its source (title, page, filename)** so Claude can cite the primary source.
`config.kb_top_k` controls how many passages come back.

`kb_store/` and `knowledge/` are gitignored (vector index + potentially large/copyrighted
source docs).

## External Dependencies

- **ElevenLabs** and **Anthropic** accounts / API keys (required).
- **faster-whisper** downloads model weights on first run (~150MB for `small`).
- **Spotify** (optional): Premium account + a registered app; run `spotify_auth.py` once
  to cache a token. Playback control needs the desktop app running (dbus/MPRIS2).
- **`paplay`** (PulseAudio/PipeWire) for TTS output, with a `sounddevice` fallback.
- **RAG** (optional): `sentence-transformers` (+PyTorch), `chromadb`, `pypdf`. First
  ingest downloads the bge model (~440MB). Disable with `kb_enabled: false` if unused.
