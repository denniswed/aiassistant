# Quick Start Guide

Get up and running with AI Assistant in 5 minutes!

## Prerequisites

- Python 3.8+
- A microphone and speakers
- ~2GB disk space for models

## Installation

### 1. Clone and Setup

```bash
git clone https://github.com/denniswed/aiassistant.git
cd aiassistant

# Create virtual environment
python3 -m venv ~/.venvs/desk-ai

# Activate environment
source ~/.venvs/desk-ai/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install lmstudio  # For LM Studio SDK
```

**Pro Tip:** Add this alias to your `~/.zshrc` or `~/.bashrc`:
```bash
alias setupenv='source ~/source/aiassistant/setupenv.sh'
```

Then you can activate the environment anytime with just:
```bash
setupenv
```

### 2. Configure Audio Devices

Run the audio setup wizard:
```bash
source setupenv.sh  # or 'setupenv' if you added the alias
python audio_setup.py
```

This interactive tool will:
- List all audio devices
- Test your microphone
- Configure speakers
- Save settings to `config.json`

### 3. Install Piper TTS (Optional)

For text-to-speech output:
```bash
pip install piper-tts

# Download voice model
mkdir -p ~/piper-voices
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx \
     -O ~/piper-voices/en_US-amy-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json \
     -O ~/piper-voices/en_US-amy-medium.onnx.json
```

### 4. Setup LM Studio

**Download a model:**
1. Download LM Studio from [lmstudio.ai](https://lmstudio.ai)
2. Open LM Studio
3. Go to "Discover" or "Search"
4. Download a model (recommendations):
   - **Llama 3.2** (3B or 8B) - Fast, efficient
   - **Phi-3** (3.8B) - Great for desktop
   - **Mistral** (7B) - Good balance
5. Click on the model to load it

**Verify setup:**
```bash
python check_lmstudio.py
```

This will check if LM Studio is accessible and list available models.

### 5. Run the Assistant

```bash
source setupenv.sh  # Activate environment (or 'setupenv')
python assistant.py
```

**First run:** The assistant will automatically load the Whisper model (one-time download).

## Usage

1. **Press and hold Right Shift** - Start recording
2. **Speak your question** - Audio is captured
3. **Release Right Shift** - Processing begins
4. **Get your answer** - Text and voice response

Example:
```
🎙️  Recording... (hold Right Shift)
⏹️  Stopped. Transcribing...
🗣️  You: What's the weather like today?
🤖 Assistant: I don't have access to real-time weather...
```

## Configuration Options

Edit `config.json` to customize:

```json
{
  "llm_backend": "lmstudio_sdk",        // or "lmstudio_api"
  "lmstudio_model": "",                 // Auto-detect or specify model
  "whisper_model_size": "small",        // base, small, medium, large
  "input_device": 5,                    // Your microphone
  "output_device": 5,                   // Your speakers
  "temperature": 0.7,                   // LLM creativity (0-2)
  "hotkey": "shift_r"                   // Push-to-talk key
}
```

## LM Studio Modes

### SDK Mode (Default - Recommended)
```json
{"llm_backend": "lmstudio_sdk"}
```
- ✅ No need to manually start LM Studio
- ✅ Auto-detects loaded models
- ✅ Better error messages

### API Mode (Alternative)
```json
{
  "llm_backend": "lmstudio_api",
  "lmstudio_base_url": "http://localhost:1234/v1"
}
```
- Requires manually starting LM Studio server
- Must specify model name

## Troubleshooting

**No speech detected:**
```bash
python audio_setup.py  # Re-configure audio
```

**Microphone too quiet:**
- Use system audio settings (e.g., `pavucontrol` on Linux)
- Increase input volume to 80-100%

**LM Studio connection error:**
- Ensure LM Studio has a model loaded
- For API mode: Start the local server in LM Studio

**Import errors:**
```bash
source setupenv.sh
pip install -r requirements.txt
```

## Usage

1. **Hold Right Shift** - Start recording
2. **Speak** - While holding the key
3. **Release** - Stop recording and get response

## Quick Troubleshooting

### "Cannot connect to LM Studio"
- Check LM Studio is running
- Verify port in config.json (default: 1234)

### "Piper binary not found"
- Update `piper_bin` path in config.json
- Ensure Piper is installed correctly

### "No audio captured"
- Check microphone permissions
- Test microphone in system settings
- Set `input_device` in config.json if needed

### Check logs
```bash
tail -f assistant.log
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [CONTRIBUTING.md](CONTRIBUTING.md) to contribute
- Review [CHANGELOG.md](CHANGELOG.md) for latest updates

## Common Configuration Examples

### Use GPU for Whisper
```json
{
  "whisper_compute_type": "float16"
}
```

### Change Hotkey (if Right Shift doesn't work)
```json
{
  "hotkey": "ctrl_r"
}
```

### Faster Response (Lower Quality)
```json
{
  "whisper_model_size": "base",
  "temperature": 0.5
}
```

### Better Quality (Slower)
```json
{
  "whisper_model_size": "medium",
  "temperature": 0.9
}
```

## Need Help?

- Check [README.md](README.md) for comprehensive docs
- Review logs in `assistant.log`
- Open an issue on GitHub

Happy voice chatting! 🎙️🤖
