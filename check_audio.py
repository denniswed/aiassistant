#!/usr/bin/env python3
"""
Quick audio device diagnostic tool
Shows current config and system defaults
"""

import sounddevice as sd
import json
from pathlib import Path

print("=" * 70)
print("AUDIO DEVICE DIAGNOSTIC")
print("=" * 70)

# Load config
config_path = Path("config.json")
if config_path.exists():
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print("\n📄 YOUR CURRENT CONFIG:")
    print(f"  input_device: {config.get('input_device')}")
    print(f"  output_device: {config.get('output_device')}")
else:
    print("\n⚠ No config.json found")
    config = {}

# Show system defaults
print("\n🔧 SYSTEM DEFAULT DEVICES:")
try:
    default_in, default_out = sd.default.device
    print(f"  Default input: {default_in}")
    print(f"  Default output: {default_out}")
except Exception as e:
    print(f"  Error: {e}")

# Show configured devices details
print("\n" + "=" * 70)
print("CONFIGURED DEVICE DETAILS")
print("=" * 70)

input_dev = config.get('input_device')
output_dev = config.get('output_device')

if input_dev is not None:
    try:
        device_info = sd.query_devices(input_dev)
        print(f"\n🎤 INPUT DEVICE #{input_dev}:")
        print(f"  Name: {device_info['name']}")
        print(f"  Input channels: {device_info['max_input_channels']}")
        print(f"  Output channels: {device_info['max_output_channels']}")
        print(f"  Sample rate: {device_info['default_samplerate']} Hz")
        
        if device_info['max_input_channels'] == 0:
            print("  ⚠ WARNING: This device has NO input channels!")
    except Exception as e:
        print(f"\n❌ INPUT DEVICE #{input_dev}: Error - {e}")
else:
    print(f"\n🎤 INPUT DEVICE: Using system default (#{default_in})")
    try:
        device_info = sd.query_devices(default_in)
        print(f"  Name: {device_info['name']}")
    except:
        pass

if output_dev is not None:
    try:
        device_info = sd.query_devices(output_dev)
        print(f"\n🔊 OUTPUT DEVICE #{output_dev}:")
        print(f"  Name: {device_info['name']}")
        print(f"  Input channels: {device_info['max_input_channels']}")
        print(f"  Output channels: {device_info['max_output_channels']}")
        print(f"  Sample rate: {device_info['default_samplerate']} Hz")
        
        if device_info['max_output_channels'] == 0:
            print("  ⚠ WARNING: This device has NO output channels!")
            print("  ⚠ Sound will NOT work - set to null for default")
    except Exception as e:
        print(f"\n❌ OUTPUT DEVICE #{output_dev}: Error - {e}")
else:
    print(f"\n🔊 OUTPUT DEVICE: Using system default (#{default_out})")
    try:
        device_info = sd.query_devices(default_out)
        print(f"  Name: {device_info['name']}")
    except:
        pass

# Check if they're the same device
if input_dev is not None and output_dev is not None and input_dev == output_dev:
    print("\n" + "=" * 70)
    print("⚠ NOTICE: Input and output are set to the SAME device!")
    print("=" * 70)
    try:
        device_info = sd.query_devices(input_dev)
        if device_info['max_output_channels'] > 0:
            print("✓ This is OK - device supports both input and output (headset)")
        else:
            print("❌ PROBLEM: This device is INPUT ONLY (microphone)")
            print("   Sound output will NOT work!")
            print("\nRECOMMENDED FIX:")
            print("  Set output_device to null in config.json:")
            print('  "output_device": null')
    except:
        pass

# Show default device details
print("\n" + "=" * 70)
print("SYSTEM DEFAULT OUTPUT DEVICE")
print("=" * 70)
try:
    default_out_info = sd.query_devices(kind='output')
    print(f"\nDevice #{default_out_info.get('index', 'unknown')}: {default_out_info['name']}")
    print(f"  Channels: {default_out_info['max_output_channels']}")
    print(f"  Sample rate: {default_out_info['default_samplerate']} Hz")
    print("\nThis is what will be used if output_device is set to null")
except Exception as e:
    print(f"Error: {e}")

# Recommendations
print("\n" + "=" * 70)
print("RECOMMENDATIONS")
print("=" * 70)

if output_dev is not None:
    try:
        device_info = sd.query_devices(output_dev)
        if device_info['max_output_channels'] == 0:
            print("\n❌ Your output device has no output channels!")
            print("\n✅ TO FIX: Edit config.json and change:")
            print('   "output_device": 7')
            print("   to:")
            print('   "output_device": null')
            print("\n   This will use your system default speakers/headphones")
        elif input_dev == output_dev and device_info['max_output_channels'] > 0:
            print("\n✓ Configuration looks OK - using headset for both input and output")
        else:
            print("\n✓ Configuration looks OK")
    except:
        print("\n⚠ Could not verify output device")
else:
    print("\n✓ Using system default output - this is usually correct")

print("\n" + "=" * 70)
