# AGENTS.md

This file contains essential information for agents working with this voice assistant project to avoid common mistakes and ramp up quickly.

## Project Overview

This is a single-file desktop AI assistant that combines speech recognition, natural language processing, and text-to-speech capabilities. It uses push-to-talk (Right Shift key) for input, Whisper for transcription, Claude API for responses, and ElevenLabs TTS for speech synthesis.

## Key Commands & Setup

### Environment Setup
- Virtual environment at `~/.venvs/desk-ai`
- Activate with: `source setupenv.sh` 
- Install dependencies: `pip install -r requirements.txt`

### Running the Assistant
```bash
source setupenv.sh && python assistant.py
```

### Audio Configuration
Run audio setup wizard first time:
```bash
python audio_setup.py
```

## Important Configuration

### API Keys Required
- `ANTHROPIC_API_KEY` for Claude
- `ELEVENLABS_API_KEY` for TTS
- `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` (optional) 

### Key Files
- `config.json.example` - Example configuration 
- `system_prompt.txt` - Custom system prompt
- `history.json` - Conversation history persistence

## Architecture Notes

### Tool Usage
The assistant supports three tool categories:
1. Web search (`web_search_20260209`) - handled inside the stream
2. Local tools (`read_file`, `write_file`, etc.) - restricted to `$HOME`
3. Spotify tools (`spotify_play`, `spotify_control`, etc.) - prefers dbus over Web API

### Audio Handling
- Uses `sounddevice` for audio input/output
- Whisper models automatically download on first run (~150MB for 'small')
- Voice activity detection (VAD) available as alternative to PTT mode
- Supports PulseAudio/PipeWire TTS output with sounddevice fallback

## Special Considerations

### Environment Requirements
- Python 3.8 or higher
- LM Studio running locally on port 1234 (for Claude API integration)
- Audio input/output devices configured properly

### Testing & Diagnostics
Use diagnostic scripts for troubleshooting:
```bash
python audio_setup.py      # Audio device configuration wizard
python test_pipeline.py    # Full STT check 
python spotify_auth.py     # Spotify OAuth setup
```

### Knowledge Base (RAG)
Local retrieval layer using Chroma + sentence-transformers. Enable with `kb_enabled: true` in config.
- Ingest via: `python ingest.py`
- Indexes PDFs and text files under `knowledge/` directory
- Stores embeddings in `kb_store/` (gitignored)

### File Structure
```
assistant.py              # Main application file
audio_setup.py           # Audio device configuration wizard
config.json.example       # Example configuration 
history.json              # Conversation history
system_prompt.txt         # Custom system prompt
requirements.txt          # Python dependencies
setupenv.sh               # Environment activation script
```

## Key Implementation Details

### Core Functions
- `chat_and_speak(messages, speak)` - Main processing loop with tool execution
- `_execute_tool()` - Dispatches tools by name 
- `_process_voice_audio()` - Handles audio input and whisper transcription
- `_tts_elevenlabs()` - Text-to-speech using ElevenLabs

### Configuration Options
- `ptt_enabled` (default: true) - Push-to-talk mode vs. always-listening VAD
- `tts_enabled` (default: false) - Spoken responses on/off 
- `web_search_enabled`, `local_tools_enabled`, `spotify_enabled` - Toggle tool groups
- `claude_model` - Default: "claude-opus-4-8"
- `llm_backend` - Can be "claude", "lmstudio", or "lmstudio_api" (default: "lmstudio_api")

### LM Studio Integration Notes

When using `llm_backend` set to "lmstudio_api", the assistant makes HTTP requests to LM Studio's `/api/v1/chat` endpoint. The API expects input items with proper type fields ('text' or 'image').

**Common Issues:**
- Invalid discriminator value error when sending messages with improperly formatted content blocks
- This typically occurs if image data isn't properly structured with required `type` and `data_url` fields

**Fixes to try:**
1. Ensure your LM Studio model supports the expected input format 
2. Verify that image content is correctly passed through `_content_to_images()` function
3. Check that all message items in API requests have proper 'text' or 'image' type fields

### Backend Support
The assistant supports multiple LLM backends:
1. **Claude API** (`llm_backend`: "claude") - Uses Anthropic's Claude models directly
2. **LM Studio SDK** (`llm_backend`: "lmstudio") - Uses the LM Studio Python client for local models
3. **LM Studio HTTP API** (`llm_backend`: "lmstudio_api") - Uses direct HTTP calls to LM Studio's /api/v1/chat endpoint

### Tool Categories
- Web search: server-side tool handled inside Claude stream
- Local tools: filesystem operations, command execution with $HOME restrictions  
- Spotify tools: music playback control via dbus (preferred) or Web API fallback
- Knowledge base: RAG functionality for local document retrieval

### Key Constants and Data Structures
- `_HALLUCINATIONS` - List of Whisper hallucinations to filter out
- `_SENTENCE_END` - Regex pattern for sentence boundaries in TTS output
- `LOCAL_TOOLS`, `SPOTIFY_TOOLS`, `KB_TOOLS` - Tool definitions available to Claude
- `AssistantConfig` class defines all configuration options with validation

### Threading and Concurrency
The assistant uses threading locks (`threading.Lock`) to serialize conversation turns, preventing interleaved audio/text/VAD inputs. The `state` dict contains shared mutable flags for TTS, PTT mode, and quit status.