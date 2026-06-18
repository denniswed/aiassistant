# Enhanced Debugging for "No Speech Detected"

## Changes Made to assistant.py

Added detailed logging throughout the audio pipeline to help diagnose issues:

### 1. Recording Start Logging
```python
logger.info(f"Starting audio recording - Device: {self.device}, Sample rate: {self.samplerate}, Channels: {self.channels}")
```
Shows exactly which device and settings are being used.

### 2. Recording Stop Logging
```python
logger.info(f"Stopping recording - Collected {len(self.frames)} frames")
logger.info(f"Audio captured - Length: {len(audio)} samples, RMS: {rms:.6f}, Max: {max_amp:.6f}")
```
Shows if audio was captured and the volume levels.

### 3. Transcription Logging
```python
logger.info(f"Audio stats - RMS: {rms:.6f}, Max amplitude: {max_amp:.6f}, Length: {len(audio_float32)} samples")
logger.info(f"Whisper detected language: {info.language} (probability: {info.language_probability:.2%})")
logger.info(f"Transcribed: {text}")
```
Shows audio quality and what Whisper detected.

### 4. Device Info at Startup
```python
logger.info(f"Using configured devices - Input: {config.input_device}, Output: {output}")
logger.info(f"Input device: {device_info['name']} (channels: {device_info['max_input_channels']})")
```
Confirms which device is actually being used.

## How to Use the Enhanced Logging

### 1. Run the assistant:
```bash
python assistant.py
```

### 2. Watch the log output in real-time:
```bash
tail -f assistant.log
```

### 3. Test recording and look for these log messages:

**When you press Right Shift:**
```
INFO - Starting audio recording - Device: 5, Sample rate: 16000, Channels: 1
```

**When you release Right Shift:**
```
INFO - Stopping recording - Collected 480 frames
INFO - Audio captured - Length: 80000 samples, RMS: 0.045000, Max: 0.234567
INFO - Audio stats - RMS: 0.045000, Max amplitude: 0.234567, Length: 80000 samples
INFO - Whisper detected language: en (probability: 99.50%)
INFO - Transcribed: testing one two three
```

## Diagnostic Checklist

### ✅ Audio is Being Captured (frames > 0)
```
INFO - Stopping recording - Collected 480 frames
```
**If you see 0 frames** → Device isn't capturing audio

### ✅ Audio Has Sufficient Level
```
INFO - Audio captured - RMS: 0.045000, Max: 0.234567
```
**Good values:**
- RMS: > 0.01
- Max: > 0.05

**Too quiet:**
- RMS: < 0.001
- Max: < 0.01

### ✅ Whisper Processes the Audio
```
INFO - Whisper detected language: en (probability: 99.50%)
```
**High probability (> 90%)** → Audio has speech
**Low probability (< 50%)** → Mostly noise

### ✅ Text is Extracted
```
INFO - Transcribed: testing one two three
```
**Empty or missing** → Whisper couldn't detect clear speech

## Common Patterns and Solutions

### Pattern 1: No Frames Captured
```
INFO - Starting audio recording - Device: 5...
INFO - Stopping recording - Collected 0 frames
WARNING - No audio frames captured
```

**Problem:** Audio stream isn't receiving data  
**Solutions:**
1. Wrong device number - verify with `python audio_setup.py`
2. Device permissions - check `groups` includes 'audio'
3. Device in use by another app

### Pattern 2: Audio Too Quiet
```
INFO - Audio captured - RMS: 0.000123, Max: 0.001234
WARNING - Audio level is extremely low
```

**Problem:** Microphone volume too low  
**Solutions:**
1. Increase mic volume: `pavucontrol` → Input Devices → 100%
2. Enable mic boost if available
3. Speak louder or closer to microphone

### Pattern 3: Whisper Returns Empty
```
INFO - Audio captured - RMS: 0.045000, Max: 0.234567
INFO - Whisper detected language: en (probability: 45.00%)
WARNING - Whisper returned empty transcription
```

**Problem:** Audio quality insufficient for speech recognition  
**Solutions:**
1. Reduce background noise
2. Speak more clearly
3. Try different Whisper model: `"whisper_model_size": "base"` or `"medium"`
4. Disable VAD (see below)

### Pattern 4: Wrong Device
```
INFO - Input device: Built-in Audio Analog Stereo (channels: 2)
```
But you want to use USB headset on device 5.

**Problem:** Config not reflecting correct device  
**Solution:** Edit config.json and restart

## Advanced Troubleshooting

### Disable VAD (Voice Activity Detection)

If Whisper is filtering out your speech as noise, modify the transcribe function:

```python
# In assistant.py, around line 460:
segments, info = whisper_model.transcribe(
    audio_float32, 
    language="en",
    vad_filter=False  # Add this line
)
```

### Save Audio for Analysis

Add this after line 568 to save every recording:

```python
# After: text = transcribe_ndarray(audio)
import time
filename = f"recording_{int(time.time())}.wav"
write_wav(filename, audio)
logger.info(f"Saved recording to {filename}")
```

Then you can:
1. Listen to the recordings: `aplay recording_*.wav`
2. Verify if speech is actually being captured
3. Check audio quality

### Test with Minimal Script

```python
import sounddevice as sd
import numpy as np

print("Recording 3 seconds from device 5...")
audio = sd.rec(48000, samplerate=16000, channels=1, device=5)
sd.wait()

rms = np.sqrt(np.mean(audio**2))
max_amp = np.max(np.abs(audio))

print(f"RMS: {rms:.6f}")
print(f"Max: {max_amp:.6f}")

if max_amp > 0.01:
    print("✓ Audio captured successfully")
else:
    print("✗ Audio level too low")
```

Save as `quick_test.py` and run: `python quick_test.py`

## Log File Analysis Commands

```bash
# Watch logs in real-time
tail -f assistant.log

# Search for errors
grep -i error assistant.log

# Check audio levels from all recordings
grep "Audio captured" assistant.log

# Check what was transcribed
grep "Transcribed:" assistant.log

# Check Whisper language detection
grep "Whisper detected" assistant.log
```

## Next Steps

1. **Run the assistant** with enhanced logging
2. **Try recording** and watch `tail -f assistant.log`
3. **Identify the pattern** from the sections above
4. **Apply the appropriate solution**
5. **Share the log output** if still having issues

The logs will now tell you exactly where the problem is! 🔍
