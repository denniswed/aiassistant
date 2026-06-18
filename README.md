# AI Assistant

A voice-controlled desktop AI assistant that combines speech recognition, natural language processing, and text-to-speech capabilities. The assistant uses a push-to-talk interface (Right Shift key) to capture voice input, transcribes it using Whisper, processes it through a local LM Studio model, and responds with synthesized speech.

## Features

- **Voice Input**: Push-to-talk recording using the Right Shift key
- **Speech Recognition**: Powered by faster-whisper for accurate transcription
- **Local AI Processing**: Integrates with LM Studio for private, local AI responses
- **Text-to-Speech**: Uses Piper TTS for natural speech synthesis
- **Real-time Audio**: Handles audio recording and playback with minimal latency
- **Cross-platform**: Works on Linux, macOS, and Windows

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Voice Input   │    │   Transcription  │    │   AI Processing │
│   (Hotkey)      │───▶│   (Whisper)      │───▶│   (LM Studio)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐             │
│  Audio Output   │◀───│  Text-to-Speech  │◀────────────┘
│  (Speakers)     │    │     (Piper)      │
└─────────────────┘    └──────────────────┘
```

## Prerequisites

### System Requirements
- Python 3.8 or higher
- LM Studio running locally on port 1234
- Audio input/output devices
- ~2GB RAM for model loading

### Dependencies

Install the required Python packages:

```bash
pip install numpy sounddevice requests simpleaudio faster-whisper pynput
```

### External Dependencies

1. **LM Studio**: Download and install from [lmstudio.ai](https://lmstudio.ai)
2. **Piper TTS**: Install Piper binary and voice models

#### Piper Installation

```bash
# Create virtual environment (recommended)
python -m venv ~/.venvs/desk-ai
source ~/.venvs/desk-ai/bin/activate

# Install Piper (example for Linux)
pip install piper-tts

# Download voice models (example)
mkdir -p ~/piper-voices
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx \
     -O ~/piper-voices/en_US-amy-medium.onnx
```

## Configuration

### Environment Setup

The assistant uses a virtual environment located at `~/.venvs/desk-ai`. 

**Quick activation:**
```bash
source setupenv.sh
```

Or add this alias to your `~/.zshrc` or `~/.bashrc`:
```bash
alias setupenv='source ~/source/aiassistant/setupenv.sh'
```

Then simply run:
```bash
setupenv
```

### Basic Setup

1. **Create Virtual Environment** (if not already created):
   ```bash
   python3 -m venv ~/.venvs/desk-ai
   source ~/.venvs/desk-ai/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install lmstudio  # For LM Studio SDK support
   ```

3. **Configure the Application**:
   Create or edit `config.json`:
   ```json
   {
     "llm_backend": "lmstudio_sdk",
     "lmstudio_model": "",
     "piper_bin": "~/.venvs/desk-ai/bin/piper",
     "piper_voice": "~/piper-voices/en_US-amy-medium.onnx",
     "input_device": 5,
     "output_device": 5
   }
   ```

4. **Run Audio Setup** (first time):
   ```bash
   python audio_setup.py
   ```
   This will help you configure your microphone and speakers.

5. **Run the Assistant**:
   ```bash
   source setupenv.sh  # Activate environment
   python assistant.py
   ```

### LM Studio Backend Options

The assistant supports two LM Studio backends:

**SDK Mode (Recommended)**:
- No need to manually start LM Studio server
- Automatic model detection
- Better error handling

```json
{
  "llm_backend": "lmstudio_sdk",
  "lmstudio_model": ""  // Leave empty for auto-detection
}
```

**Important:** You must download a model in LM Studio first:
1. Open LM Studio application
2. Go to "Discover" or "Search"
3. Download a model (recommended: Llama 3.2, Phi-3, Mistral)
4. Load the model in LM Studio

Check your setup:
```bash
python check_lmstudio.py
```

**API Mode (Legacy)**:
- Requires LM Studio server running
- Manual model selection

```json
{
  "llm_backend": "lmstudio_api",
  "lmstudio_base_url": "http://localhost:1234/v1",
  "lmstudio_model": "your-model-name"
}
```

### Advanced Configuration

The application uses a JSON configuration file (`config.json`) for all settings. You can customize:

#### Configuration Options

Edit `config.json` to modify these settings:

```json
{
  "lmstudio_base_url": "http://localhost:1234/v1",
  "lmstudio_model": "openai/gpt-oss-20b",
  "system_prompt": "You are a helpful assistant...",
  "sample_rate": 16000,
  "channels": 1,
  "input_device": null,
  "output_device": null,
  "whisper_model_size": "small",
  "whisper_compute_type": "int8",
  "piper_bin": "~/.venvs/desk-ai/bin/piper",
  "piper_voice": "~/piper-voices/en_US-amy-medium.onnx",
  "hotkey": "shift_r",
  "temperature": 0.7,
  "timeout": 120
}
```

#### Audio Device Selection

**Easy Way - Use the Audio Setup Wizard:**

```bash
python audio_setup.py
```

This interactive wizard will:
- List all available audio devices
- Let you select your microphone/headset
- Test recording with playback verification
- Automatically configure your `config.json`

**Manual Way:**

```python
import sounddevice as sd
print(sd.query_devices())
```

Then edit `config.json` with the desired device indices:
```json
{
  "input_device": 5,
  "output_device": 5
}
```

#### Model Selection

- **Whisper Models**: Choose based on speed vs. accuracy trade-off:
  - `base`: Fastest, lower accuracy
  - `small`: Good balance (recommended)
  - `medium`: Higher accuracy, slower
  - `large`: Best accuracy, slowest

- **Compute Types**:
  - `int8`: CPU-optimized, lower memory
  - `float16`: GPU-optimized (requires CUDA)
  - `int8_float16`: Hybrid approach

## Usage

### Starting the Assistant

```bash
python assistant.py
```

### Basic Operation

1. **Start Recording**: Hold down the Right Shift key
2. **Speak**: Talk while holding the key
3. **Process**: Release the key to stop recording
4. **Response**: The assistant will transcribe, process, and speak the response

### Example Interaction

```
Assistant ready.
Hold [shift_r] to talk; release to transcribe & respond. Ctrl+C to quit.

🎙️  Recording… (hold Right Shift)
⏹️  Stopped. Transcribing…
🗣️  You: What's the weather like today?
🤖 Assistant: I don't have access to current weather data, but I can help you find weather information through various weather services or apps.
```

### Stopping the Assistant

Press `Ctrl+C` to exit the application.

## API Reference

### Core Classes

#### `Recorder`

Handles audio recording with configurable parameters.

```python
recorder = Recorder(samplerate=16000, channels=1, device=None)
recorder.start()  # Begin recording
audio_data = recorder.stop()  # Stop and retrieve audio
```

**Methods:**
- `start()`: Initialize audio stream and begin recording
- `stop()`: Stop recording and return numpy array of audio data
- `_callback()`: Internal callback for audio stream
- `_collect_loop()`: Background thread for collecting audio frames

#### Key Functions

##### `transcribe_ndarray(audio_float32)`
Transcribes audio data using faster-whisper.
- **Input**: NumPy array of float32 audio data
- **Returns**: String containing transcribed text

##### `chat_lmstudio(messages)`
Sends conversation to LM Studio for processing.
- **Input**: List of message dictionaries (OpenAI format)
- **Returns**: String response from the AI model

##### `tts_piper(text)`
Converts text to speech using Piper TTS.
- **Input**: String text to synthesize
- **Output**: Plays audio through default output device

##### `write_wav(path, audio_float32, samplerate)`
Saves audio data to WAV file.
- **Input**: File path, audio array, sample rate
- **Output**: WAV file written to disk

##### `play_wav(path, device)`
Plays WAV file through specified audio device.
- **Input**: File path and optional device index
- **Output**: Audio playback

## File Structure

```
aiassistant/
├── assistant.py              # Main application file
├── audio_setup.py           # Interactive audio device configuration wizard
├── config.json.example       # Example configuration file
├── config.json              # User configuration (create from example)
├── README.md                # This documentation
├── CHANGELOG.md             # Version history and changes
├── CONTRIBUTING.md          # Contribution guidelines
├── BEST_PRACTICES.md        # Code quality improvements summary
├── QUICKSTART.md            # 5-minute setup guide
├── LICENSE                  # MIT License
├── requirements.txt         # Python dependencies
├── .gitignore              # Git ignore patterns
└── assistant.log           # Application logs (auto-generated)
```

## Troubleshooting

### Common Issues

#### "No module named 'pynput'"
The application will automatically install pynput if missing, but you can install manually:
```bash
pip install pynput
```

#### Audio Device Errors

**Not picking up audio from headset:**
```bash
# Run the audio setup wizard
python audio_setup.py

# Follow the prompts to:
# 1. List all audio devices
# 2. Select your headset
# 3. Test recording with playback
# 4. Verify you can hear yourself
```

**Check available devices manually:**
```python
import sounddevice as sd
print(sd.query_devices())
```

**Edit config.json with correct device:**
```json
{
  "input_device": 5,  // Your headset's device number
  "output_device": 5
}
```

#### LM Studio Connection Issues
1. Ensure LM Studio is running
2. Verify the correct port (default: 1234)
3. Check the model name matches your loaded model

#### Piper TTS Errors
1. Verify Piper binary path is correct
2. Ensure voice model file exists
3. Check file permissions

#### Performance Issues
1. Use smaller Whisper model (`base` instead of `small`)
2. Adjust `WHISPER_COMPUTE_TYPE` for your hardware
3. Close unnecessary applications

### Debug Mode

For debugging, you can enable verbose output by modifying the code to include print statements or adding a logging system.

## Security Considerations

- The application executes external binaries (Piper)
- Network communication with LM Studio (localhost only by default)
- Temporary file creation for audio processing
- Keyboard input monitoring for hotkey detection

## Performance Optimization

### Memory Usage
- Whisper models are loaded once at startup
- Audio data is processed in chunks
- Temporary files are cleaned up automatically

### Latency Optimization
- Use smaller Whisper models for faster transcription
- Optimize audio buffer sizes
- Consider GPU acceleration for Whisper if available

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Code Style
- Follow PEP 8 conventions
- Add type hints for new functions
- Include docstrings for public methods
- Handle errors gracefully

## Future Enhancements

- [ ] Configuration file support (YAML/JSON)
- [ ] Multiple hotkey support
- [ ] Voice activity detection (VAD)
- [ ] Conversation history persistence
- [ ] Plugin system for extending functionality
- [ ] GUI interface option
- [ ] Multiple language support
- [ ] Streaming response support
- [ ] Voice cloning integration
- [ ] Cloud service integration options

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [faster-whisper](https://github.com/guillaumekln/faster-whisper) for speech recognition
- [Piper](https://github.com/rhasspy/piper) for text-to-speech synthesis
- [LM Studio](https://lmstudio.ai) for local AI model hosting
- [pynput](https://github.com/moses-palmer/pynput) for keyboard input handling
