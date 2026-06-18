#!/usr/bin/env python3
"""
Complete audio pipeline test
Tests recording, saving, and transcription separately
"""

import sounddevice as sd
import numpy as np
import wave
import json
from pathlib import Path

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

input_device = config.get('input_device')
sample_rate = config.get('sample_rate', 16000)

print("=" * 70)
print("AUDIO PIPELINE DIAGNOSTIC")
print("=" * 70)
print(f"\nConfiguration:")
print(f"  Input device: {input_device}")
print(f"  Sample rate: {sample_rate} Hz")

# Show device info
if input_device is not None:
    device_info = sd.query_devices(input_device)
    print(f"  Device name: {device_info['name']}")
    print(f"  Input channels: {device_info['max_input_channels']}")
    print(f"  Device sample rate: {device_info['default_samplerate']} Hz")

print("\n" + "=" * 70)
print("TEST 1: RECORDING AUDIO")
print("=" * 70)
print("\nRecording 5 seconds of audio...")
print("SPEAK LOUDLY AND CLEARLY NOW!")
print("Say: 'Testing one two three four five'\n")

duration = 5

try:
    recording = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype='float32',
        device=input_device
    )
    sd.wait()
    
    print("✓ Recording complete")
    
    # Analyze audio
    rms = np.sqrt(np.mean(recording**2))
    max_amp = np.max(np.abs(recording))
    min_val = np.min(recording)
    max_val = np.max(recording)
    
    print(f"\nAudio Analysis:")
    print(f"  RMS Volume: {rms:.6f}")
    print(f"  Max Amplitude: {max_amp:.6f}")
    print(f"  Value Range: [{min_val:.6f}, {max_val:.6f}]")
    print(f"  Audio Length: {len(recording)} samples ({len(recording)/sample_rate:.2f} seconds)")
    
    if max_amp < 0.001:
        print("\n❌ PROBLEM: Audio level is EXTREMELY low!")
        print("   Possible causes:")
        print("   - Microphone is muted")
        print("   - Wrong input device selected")
        print("   - Microphone not working")
        print("   - Need to increase system volume")
    elif max_amp < 0.01:
        print("\n⚠ WARNING: Audio level is quite low")
        print("   You might want to increase microphone volume")
    else:
        print("\n✓ Audio level looks good")
    
    # Save to file
    filename = "test_diagnostic.wav"
    print(f"\n" + "=" * 70)
    print("TEST 2: SAVING AUDIO FILE")
    print("=" * 70)
    
    audio_int16 = np.clip(recording, -1, 1)
    audio_int16 = (audio_int16 * 32767.0).astype(np.int16)
    
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    
    print(f"✓ Saved to: {filename}")
    print(f"  You can play this file to verify audio was captured")
    print(f"  Command: aplay {filename}  (or open in audio player)")
    
    # Test transcription
    print(f"\n" + "=" * 70)
    print("TEST 3: TRANSCRIPTION")
    print("=" * 70)
    print("\nLoading Whisper model...")
    
    try:
        from faster_whisper import WhisperModel
        
        whisper_model = WhisperModel(
            config.get('whisper_model_size', 'small'),
            compute_type=config.get('whisper_compute_type', 'int8')
        )
        print("✓ Whisper model loaded")
        
        print("\nTranscribing audio...")
        segments, info = whisper_model.transcribe(recording, language="en")
        
        print(f"\nTranscription info:")
        print(f"  Language: {info.language}")
        print(f"  Language probability: {info.language_probability:.2%}")
        
        text_parts = []
        print(f"\nSegments:")
        for i, segment in enumerate(segments):
            print(f"  [{segment.start:.2f}s - {segment.end:.2f}s]: {segment.text}")
            text_parts.append(segment.text)
        
        full_text = "".join(text_parts).strip()
        
        print(f"\n" + "=" * 70)
        print("FINAL RESULT")
        print("=" * 70)
        
        if full_text:
            print(f"\n✓ Transcribed text: '{full_text}'")
        else:
            print("\n❌ NO TEXT DETECTED")
            print("\nPossible causes:")
            print("  1. Audio level too low (check Test 1 results above)")
            print("  2. Background noise only, no speech")
            print("  3. Speech not clear enough")
            print("  4. Wrong language (set to English)")
            
            if max_amp < 0.01:
                print("\n⚠ Your audio level was LOW - this is likely the problem!")
                print("   Solutions:")
                print("   - Increase microphone volume in system settings")
                print("   - Speak closer to the microphone")
                print("   - Check if microphone boost is available")
            
            print(f"\n💡 Listen to {filename} to verify what was recorded")
            print(f"   Command: aplay {filename}")
        
    except ImportError:
        print("❌ faster-whisper not installed")
        print("   Run: pip install faster-whisper")
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        import traceback
        traceback.print_exc()
    
except Exception as e:
    print(f"❌ Recording error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
print("\nNext steps:")
print("1. Check the audio analysis results above")
print(f"2. Play the test file: aplay test_diagnostic.wav")
print("3. If audio is too quiet, adjust microphone settings")
print("4. Try running the test again after adjustments")
print("\n")
