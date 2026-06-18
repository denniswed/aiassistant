#!/usr/bin/env python3
"""
Audio Device Setup Helper

This script helps you identify and configure the correct audio input device
for the AI Assistant.
"""

import sounddevice as sd
import json
from pathlib import Path


def list_audio_devices():
    """List all available audio devices with their indices."""
    print("=" * 70)
    print("AVAILABLE AUDIO DEVICES")
    print("=" * 70)
    
    devices = sd.query_devices()
    
    for i, device in enumerate(devices):
        device_type = []
        if device['max_input_channels'] > 0:
            device_type.append("INPUT")
        if device['max_output_channels'] > 0:
            device_type.append("OUTPUT")
        
        type_str = "/".join(device_type) if device_type else "NO I/O"
        default_marker = ""
        
        try:
            default_in = sd.default.device[0]
            default_out = sd.default.device[1]
            
            if i == default_in and i == default_out:
                default_marker = " [DEFAULT IN/OUT]"
            elif i == default_in:
                default_marker = " [DEFAULT INPUT]"
            elif i == default_out:
                default_marker = " [DEFAULT OUTPUT]"
        except:
            pass
        
        # Add emoji indicators
        emoji = ""
        if "INPUT" in device_type and "OUTPUT" in device_type:
            emoji = "🎧"  # Headset/full duplex device
        elif "INPUT" in device_type:
            emoji = "🎤"  # Microphone only
        elif "OUTPUT" in device_type:
            emoji = "🔊"  # Speaker only
        
        print(f"\n{emoji} Device {i}: {device['name']}{default_marker}")
        print(f"  Type: {type_str}")
        if device['max_input_channels'] > 0:
            print(f"  Input Channels: {device['max_input_channels']}")
        if device['max_output_channels'] > 0:
            print(f"  Output Channels: {device['max_output_channels']}")
        print(f"  Sample Rate: {device['default_samplerate']} Hz")
    
    print("\n" + "=" * 70)
    print("Legend: 🎧=Headset  🎤=Mic only  🔊=Speaker only")
    print("=" * 70)


def test_recording(device_index=None, duration=3, play_back=True, output_device=None):
    """Test recording from a specific device."""
    import numpy as np
    import time
    import wave
    
    # Try to import scipy for better resampling
    try:
        from scipy import signal
        has_scipy = True
    except ImportError:
        has_scipy = False
        print("Note: scipy not available, using basic resampling")
    
    print(f"\nTesting recording for {duration} seconds...")
    if device_index is not None:
        print(f"Using device index: {device_index}")
    else:
        print("Using default device")
    
    print("Speak into your microphone NOW...")
    print("(Say something like: 'Testing, one, two, three')")
    
    try:
        recording = sd.rec(
            int(duration * 16000),
            samplerate=16000,
            channels=1,
            dtype='float32',
            device=device_index
        )
        sd.wait()
        
        # Calculate volume (RMS)
        rms = np.sqrt(np.mean(recording**2))
        max_amplitude = np.max(np.abs(recording))
        
        print(f"\n✓ Recording successful!")
        print(f"  RMS Volume: {rms:.6f}")
        print(f"  Max Amplitude: {max_amplitude:.6f}")
        
        if max_amplitude < 0.001:
            print("\n⚠ WARNING: Very low audio level detected!")
            print("  - Check if your microphone is muted")
            print("  - Check microphone volume in system settings")
            print("  - Try a different device index")
        elif max_amplitude < 0.01:
            print("\n⚠ Audio level is low but detectable")
            print("  - Consider increasing microphone volume")
        else:
            print("\n✓ Audio level looks good!")
        
        # Play back the recording
        if play_back and max_amplitude > 0.0001:
            print("\n" + "=" * 70)
            print("PLAYING BACK YOUR RECORDING...")
            print("=" * 70)
            print("Listen to verify your microphone is working correctly.\n")
            
            time.sleep(0.5)  # Short pause before playback
            
            try:
                # Get the output device's default sample rate
                playback_device = output_device if output_device is not None else None
                
                # Validate playback device
                if playback_device is not None:
                    device_info = sd.query_devices(playback_device)
                    
                    # Check if device actually supports output
                    if device_info['max_output_channels'] == 0:
                        print(f"⚠ Warning: Device {playback_device} has no output channels!")
                        print("  Falling back to default output device")
                        playback_device = None
                        # Get default output device
                        device_info = sd.query_devices(kind='output')
                    
                    output_sample_rate = int(device_info['default_samplerate'])
                else:
                    # Get default output device
                    device_info = sd.query_devices(kind='output')
                    output_sample_rate = int(device_info['default_samplerate'])
                    playback_device = device_info['index'] if 'index' in device_info else None
                
                print(f"Playback device: {device_info['name']}")
                print(f"Using playback sample rate: {output_sample_rate} Hz")
                
                # Resample if needed
                if output_sample_rate != 16000:
                    print(f"Resampling from 16000 Hz to {output_sample_rate} Hz...")
                    
                    if has_scipy:
                        # Use scipy for high-quality resampling
                        num_output_samples = int(len(recording) * output_sample_rate / 16000)
                        resampled = signal.resample(recording, num_output_samples)
                        playback_audio = resampled
                    else:
                        # Use numpy for basic linear interpolation
                        x_old = np.linspace(0, 1, len(recording))
                        x_new = np.linspace(0, 1, int(len(recording) * output_sample_rate / 16000))
                        playback_audio = np.interp(x_new, x_old, recording.flatten()).reshape(-1, 1)
                    
                    playback_rate = output_sample_rate
                else:
                    playback_audio = recording
                    playback_rate = 16000
                
                sd.play(playback_audio, samplerate=playback_rate, device=playback_device)
                sd.wait()
                print("\n✓ Playback complete!")
                
                # Offer to save the recording
                save_choice = input("\nSave this recording to a file? (y/n): ").strip().lower()
                if save_choice == 'y':
                    filename = f"test_recording_{int(time.time())}.wav"
                    # Convert float32 to int16
                    audio_int16 = np.clip(recording, -1, 1)
                    audio_int16 = (audio_int16 * 32767.0).astype(np.int16)
                    
                    with wave.open(filename, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)  # 16-bit
                        wf.setframerate(16000)
                        wf.writeframes(audio_int16.tobytes())
                    
                    print(f"✓ Recording saved to: {filename}")
                    
            except Exception as e:
                print(f"\n⚠ Playback failed: {e}")
                print("  (Recording still worked, just couldn't play it back)")
                import traceback
                print("\nDebug info:")
                traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"\n✗ Recording failed: {e}")
        return False


def update_config(input_device=None, output_device=None):
    """Update config.json with device settings."""
    config_path = Path("config.json")
    
    if not config_path.exists():
        config_example = Path("config.json.example")
        if config_example.exists():
            print(f"Creating config.json from example...")
            with open(config_example, 'r') as f:
                config = json.load(f)
        else:
            print("Error: config.json.example not found")
            return False
    else:
        with open(config_path, 'r') as f:
            config = json.load(f)
    
    if input_device is not None:
        config['input_device'] = input_device
        print(f"✓ Set input_device to {input_device}")
    
    if output_device is not None:
        config['output_device'] = output_device
        print(f"✓ Set output_device to {output_device}")
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✓ Configuration saved to {config_path}")
    return True


def main():
    """Main setup wizard."""
    print("\n" + "=" * 70)
    print("AI ASSISTANT - AUDIO SETUP WIZARD")
    print("=" * 70)
    
    # List devices
    list_audio_devices()
    
    # Get input device
    print("\n" + "=" * 70)
    print("SELECT INPUT DEVICE (Microphone/Headset)")
    print("=" * 70)
    print("\nLook for devices marked with 🎤 (mic) or 🎧 (headset) in the list above.")
    print("For headsets, choose the device that shows INPUT or INPUT/OUTPUT.")
    print("\nEnter the device number, or press Enter to use default.")
    
    input_choice = input("\nInput device number: ").strip()
    
    if input_choice == "":
        input_device = None
        print("Using default input device")
    else:
        try:
            input_device = int(input_choice)
            device_info = sd.query_devices(input_device)
            if device_info['max_input_channels'] == 0:
                print(f"⚠ Warning: Device {input_device} has no input channels!")
            else:
                print(f"Selected: {device_info['name']}")
        except (ValueError, IndexError) as e:
            print(f"Invalid device number: {e}")
            return
    
    # Test recording
    print("\n" + "=" * 70)
    print("TESTING AUDIO INPUT")
    print("=" * 70)
    
    test_choice = input("\nTest recording with playback? (y/n): ").strip().lower()
    if test_choice == 'y':
        # Check if input device can also do output
        test_output_device = None
        
        if input_device is not None:
            device_info = sd.query_devices(input_device)
            has_output = device_info['max_output_channels'] > 0
            
            if has_output:
                # Device supports both input and output (like a USB headset)
                use_same = input(f"\nYour device '{device_info['name']}' supports output.\nUse it for playback? (y/n, default=y): ").strip().lower()
                if use_same == '' or use_same == 'y':
                    test_output_device = input_device
                    print(f"✓ Will use device {input_device} for playback")
                else:
                    print("✓ Will use default output device for playback")
            else:
                print(f"\nNote: Your device '{device_info['name']}' is input-only.")
                print("✓ Will use default output device for playback")
        else:
            print("\n✓ Will use default output device for playback")
        
        while True:
            # Get custom duration
            duration_input = input("\nRecording duration in seconds (default 3): ").strip()
            if duration_input == "":
                duration = 3
            else:
                try:
                    duration = int(duration_input)
                    if duration < 1 or duration > 10:
                        print("Duration must be between 1 and 10 seconds")
                        continue
                except ValueError:
                    print("Invalid duration, using 3 seconds")
                    duration = 3
            
            test_recording(input_device, duration=duration, play_back=True, output_device=test_output_device)
            
            # Ask what to do next
            print("\nOptions:")
            print("  r - Record and test again")
            print("  d - Try a different device")
            print("  c - Continue with this device")
            
            choice = input("\nYour choice (r/d/c): ").strip().lower()
            
            if choice == 'd':
                return main()  # Restart wizard
            elif choice == 'r':
                continue  # Test again with same device
            else:
                break  # Continue to output device selection
    
    # Get output device
    print("\n" + "=" * 70)
    print("SELECT OUTPUT DEVICE (Speakers/Headset)")
    print("=" * 70)
    print("\nEnter the device number for audio output, or press Enter for default.")
    
    output_choice = input("\nOutput device number: ").strip()
    
    if output_choice == "":
        output_device = None
        print("Using default output device")
    else:
        try:
            output_device = int(output_choice)
            device_info = sd.query_devices(output_device)
            if device_info['max_output_channels'] == 0:
                print(f"⚠ Warning: Device {output_device} has no output channels!")
            else:
                print(f"Selected: {device_info['name']}")
        except (ValueError, IndexError) as e:
            print(f"Invalid device number: {e}")
            return
    
    # Update config
    print("\n" + "=" * 70)
    print("SAVING CONFIGURATION")
    print("=" * 70)
    
    update_config(input_device, output_device)
    
    print("\n" + "=" * 70)
    print("SETUP COMPLETE!")
    print("=" * 70)
    print("\nYou can now run: python assistant.py")
    print("\nIf you need to change devices later, run this script again:")
    print("  python audio_setup.py")
    print("\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
