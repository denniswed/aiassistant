# "No Speech Detected" Troubleshooting Guide

## Common Causes and Solutions

### 1. Audio Level Too Low

**Symptoms:**
- Max amplitude < 0.01 in tests
- Can barely hear playback

**Solutions:**

```bash
# Check current microphone level
pactl list sources | grep -A 10 "Name.*alsa"

# Increase microphone volume (ALSA)
alsamixer
# Press F4 to show capture devices
# Use arrow keys to increase "Capture" volume
# Press ESC when done

# Or use PulseAudio
pavucontrol
# Go to "Input Devices" tab
# Increase volume slider

# Or command line
pactl set-source-volume @DEFAULT_SOURCE@ 150%
```

**In config.json:**
- Audio level is hardware-controlled, not in config

### 2. Wrong Input Device

**Symptoms:**
- Device 7 exists but captures wrong source
- Captures system audio instead of microphone

**Solution:**

```bash
# List all input sources
pactl list sources short

# Set default source to your headset
pactl set-default-source <source-name>

# Example:
pactl set-default-source alsa_input.usb-Logitech_USB_Headset-00.mono-fallback
```

**In config.json:**
```json
{
  "input_device": null,  // Try null to use system default
  "output_device": null
}
```

Then test again with `python audio_setup.py`

### 3. Microphone Muted

**Check if muted:**

```bash
# Check mute status
pactl list sources | grep -i mute

# Unmute all sources
pactl set-source-mute @DEFAULT_SOURCE@ 0

# Or use alsamixer
alsamixer
# Press F4, look for "MM" (muted), press M to unmute
```

### 4. Permissions Issue

**Check audio group:**

```bash
# See if you're in audio group
groups

# Add yourself to audio group
sudo usermod -a -G audio $USER

# Then logout and login again
```

### 5. Whisper Model Issue

**If audio is captured but not transcribed:**

```bash
# Try a different model size
# Edit config.json:
```

```json
{
  "whisper_model_size": "base",  // Faster, might help
  // or
  "whisper_model_size": "medium" // More accurate
}
```

### 6. Speech Too Quiet or Unclear

**Best practices:**
- Speak clearly and at normal volume
- Get closer to microphone (6-12 inches)
- Reduce background noise
- Speak for at least 2-3 seconds
- Avoid very short utterances

### 7. VAD (Voice Activity Detection) Threshold

Whisper might be filtering out your speech as noise.

**Test without VAD:**

```python
# In assistant.py, modify transcribe_ndarray:
segments, info = whisper_model.transcribe(
    audio_float32, 
    language="en",
    vad_filter=False  # Disable VAD filtering
)
```

## Quick Diagnostic Commands

```bash
# 1. Test recording with system tools
arecord -d 5 -f cd test.wav
aplay test.wav

# 2. Check if device is working
pactl list sources | grep -A 15 "State: RUNNING"

# 3. Monitor live levels
pavucontrol
# Go to "Input Devices" tab and watch the level meter while speaking

# 4. Test with our diagnostic
python test_pipeline.py
```

## Typical Working Values

**Good audio capture:**
- RMS Volume: 0.02 - 0.2
- Max Amplitude: 0.1 - 0.8
- Should see clear waveform in test file

**Problem indicators:**
- RMS Volume: < 0.001 (too quiet)
- Max Amplitude: < 0.01 (definitely too quiet)
- Max Amplitude: > 0.95 (clipping, too loud)

## Step-by-Step Fix

1. **Run diagnostic:**
   ```bash
   python test_pipeline.py
   ```

2. **Check audio level in results**
   - If < 0.01: Increase microphone volume
   - If looks good: Check Whisper settings

3. **Adjust microphone:**
   ```bash
   pavucontrol
   # Input Devices → Increase volume to 80-100%
   ```

4. **Test again:**
   ```bash
   python test_pipeline.py
   ```

5. **Verify captured audio:**
   ```bash
   aplay test_diagnostic.wav
   # Can you hear your voice clearly?
   ```

6. **If still no speech detected:**
   - Try `"whisper_model_size": "base"` (faster, sometimes better)
   - Set `"input_device": null` (use system default)
   - Check system default: `pactl info | grep "Default Source"`

## Testing Checklist

- [ ] Audio level > 0.01 in diagnostic
- [ ] Can hear yourself in test_diagnostic.wav
- [ ] Microphone not muted (check pavucontrol)
- [ ] Correct input device selected
- [ ] Whisper model loads without errors
- [ ] Speaking clearly for 3+ seconds
- [ ] No excessive background noise

## Still Not Working?

Try the absolute minimum test:

```bash
# Record 5 seconds
arecord -d 5 -f S16_LE -r 16000 -c 1 minimal_test.wav

# Play it back
aplay minimal_test.wav

# If this doesn't work, it's a system audio issue, not the app
```
