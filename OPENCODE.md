# Opencode Configuration

This file provides configuration for opencode to understand and work with this voice assistant project.

## Project Overview

A single-file, push-to-talk (or always-listening) desktop voice assistant that:
- Uses Right Shift / VAD for input
- Processes speech with faster-whisper STT 
- Generates responses using Claude API (streaming, tool loop)
- Outputs speech via ElevenLabs TTS (sentence-by-sentence for low latency) to paplay

## Key Files

- `assistant.py` (~1300 lines) - Main application logic
- `setupenv.sh` - Environment setup script
- `requirements.txt` - Python dependencies
- `config.json.example` - Configuration template
- `system_prompt.txt` - System prompt for Claude

## Core Components

### Architecture
- Global singletons at import time: config, claude_client, el_client, whisper_model
- chat_and_speak() is the core function handling streaming responses and tool loops
- Three input paths: PTT (Right Shift), VAD (always-listening), Keyboard input
- Conversation persistence with history.json

### Tools
- Local tools: read_file, write_file, list_directory, download_file, run_command
- Spotify tools: spotify_play, spotify_control, spotify_now_playing, spotify_queue
- Web search: server-side web_search_20260209 tool
- Knowledge base: search_knowledge_base tool for local RAG

### Dependencies
- Anthropic API key (ANTHROPIC_API_KEY)
- ElevenLabs API key (ELEVENLABS_API_KEY) 
- Spotify client credentials (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
- faster-whisper model (~150MB for 'small' model)
- sentence-transformers (BAAI/bge-base-en-v1.5) for RAG (~440MB)
- Chroma persistent store for knowledge base