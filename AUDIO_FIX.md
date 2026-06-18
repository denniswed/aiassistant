# Audio Playback Sample Rate Fix

## Problem
The audio playback was failing with error:
```
Expression 'paInvalidSampleRate' failed in 'src/hostapi/alsa/pa_linux_alsa.c'
Error opening OutputStream: Invalid sample rate [PaErrorCode -9997]
```

## Root Cause
The issue occurs because:
1. We record audio at **16kHz** (16,000 Hz) - optimal for Whisper speech recognition
2. Many audio output devices have a default sample rate of **44.1kHz** or **48kHz**
3. The device doesn't support playback at 16kHz, causing the error

## Solution
The fix implements **automatic sample rate conversion**:

### 1. Detect Output Device Sample Rate
```python
device_info = sd.query_devices(playback_device)
output_sample_rate = int(device_info['default_samplerate'])
```

### 2. Resample Audio if Needed
If output sample rate differs from 16kHz, we resample the audio:

**Method A: High-Quality (scipy)**
```python
from scipy import signal
resampled = signal.resample(recording, num_output_samples)
```

**Method B: Fallback (numpy)**
```python
# Linear interpolation if scipy not available
x_old = np.linspace(0, 1, len(recording))
x_new = np.linspace(0, 1, num_output_samples)
playback_audio = np.interp(x_new, x_old, recording.flatten())
```

### 3. Play at Correct Rate
```python
sd.play(playback_audio, samplerate=output_sample_rate, device=playback_device)
```

## Installation

### Option 1: Install scipy (Recommended)
```bash
pip install scipy
```

Or use the install script:
```bash
chmod +x install_scipy.sh
./install_scipy.sh
```

### Option 2: Use Fallback
The script will automatically use numpy-based resampling if scipy isn't available.
Quality is slightly lower but works without additional dependencies.

## Updated Features

### New in audio_setup.py:
1. **Automatic sample rate detection** for output device
2. **High-quality resampling** using scipy (with numpy fallback)
3. **Playback device selection** - can test with same device or different one
4. **Better error reporting** with debug information

### Usage:
```bash
python audio_setup.py
```

The wizard will now:
1. List all devices
2. Let you select input device
3. Ask if you want to use same device for playback test
4. Automatically resample audio for playback
5. Play back at the correct sample rate

## Technical Details

### Common Sample Rates:
- **16 kHz** - Speech recognition (our recording rate)
- **44.1 kHz** - CD quality audio
- **48 kHz** - Professional audio/video
- **96 kHz** - High-resolution audio

### Resampling Quality:
- **scipy.signal.resample**: Uses FFT, high quality, preserves frequencies
- **numpy.interp**: Linear interpolation, lower quality but no extra dependencies

### Why 16 kHz for Recording?
- Optimal for speech recognition
- Whisper models are trained on 16 kHz audio
- Reduces file size and processing time
- Sufficient for voice (human speech is < 8 kHz)

## Testing

After the fix, you should see:
```
PLAYING BACK YOUR RECORDING...
======================================================================
Using playback sample rate: 48000 Hz
Resampling from 16000 Hz to 48000 Hz...

✓ Playback complete!
```

## Troubleshooting

### If playback still fails:
1. Check if output device supports its reported default sample rate
2. Try a different output device
3. Check audio system logs: `journalctl -xe | grep -i audio`

### If sound quality is poor:
1. Install scipy for better resampling: `pip install scipy`
2. Check microphone volume levels
3. Try a higher quality Whisper model

## Future Improvements
- [ ] Cache device sample rate information
- [ ] Support for multi-channel audio
- [ ] Real-time sample rate conversion option
- [ ] Audio format conversion (beyond just sample rate)
