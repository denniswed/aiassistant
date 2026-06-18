#!/usr/bin/env python3
"""
Check LM Studio setup and list available models.
"""

import sys
import json

def check_lmstudio_sdk():
    """Check if LM Studio SDK is installed and working."""
    print("=== Checking LM Studio SDK ===")
    print()
    
    try:
        from lmstudio import LMStudio
        print("✓ LM Studio SDK is installed")
        return True
    except ImportError:
        print("✗ LM Studio SDK not installed")
        print()
        print("Install with:")
        print("  pip install lmstudio")
        return False


def check_lmstudio_connection():
    """Try to connect to LM Studio and list models."""
    print()
    print("=== Checking LM Studio Connection ===")
    print()
    
    try:
        from lmstudio import LMStudio
        
        print("Connecting to LM Studio...")
        client = LMStudio()
        
        # Try to list models
        try:
            models = client.list_models()
            
            if models:
                print(f"✓ Connected! Found {len(models)} model(s):")
                print()
                for i, model in enumerate(models, 1):
                    print(f"  {i}. {model}")
                print()
                return True, models
            else:
                print("⚠ Connected, but no models loaded")
                print()
                print("You need to download a model in LM Studio first:")
                print("  1. Open LM Studio")
                print("  2. Go to 'Discover' or 'Search'")
                print("  3. Download a model (recommended: Llama 3.2, Phi-3, or similar)")
                print("  4. Load the model (click the model in 'My Models')")
                print()
                return False, []
                
        except Exception as e:
            print(f"✗ Error listing models: {e}")
            print()
            print("Make sure LM Studio is running and has a model loaded")
            return False, []
            
    except ImportError:
        print("✗ LM Studio SDK not installed")
        return False, []
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Make sure LM Studio application is running")
        print("  2. Load a model in LM Studio")
        print("  3. Check that LM Studio is using default port")
        return False, []


def check_config():
    """Check current config.json settings."""
    print()
    print("=== Current Configuration ===")
    print()
    
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        llm_backend = config.get('llm_backend', 'not set')
        model = config.get('lmstudio_model', 'not set')
        
        print(f"LLM Backend: {llm_backend}")
        print(f"Model: {model if model else '(auto-detect)'}")
        print()
        
        if llm_backend == "lmstudio_sdk":
            print("✓ Using SDK mode (recommended)")
        elif llm_backend == "lmstudio_api":
            print("⚠ Using API mode (requires manual server start)")
        else:
            print("✗ Invalid backend setting")
            
        return config
        
    except FileNotFoundError:
        print("✗ config.json not found")
        print("Run: python audio_setup.py")
        return None
    except json.JSONDecodeError:
        print("✗ config.json is invalid JSON")
        return None


def update_config_with_model(model_name):
    """Update config.json with selected model."""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        config['lmstudio_model'] = model_name
        
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✓ Updated config.json with model: {model_name}")
        return True
    except Exception as e:
        print(f"✗ Failed to update config: {e}")
        return False


def main():
    """Main check routine."""
    print("LM Studio Setup Checker")
    print("=" * 50)
    print()
    
    # Check SDK installation
    if not check_lmstudio_sdk():
        sys.exit(1)
    
    # Check connection and models
    connected, models = check_lmstudio_connection()
    
    # Check config
    config = check_config()
    
    # Offer to update config if models found
    if connected and models and config:
        current_model = config.get('lmstudio_model', '')
        
        if not current_model or current_model not in models:
            print()
            print("Would you like to set a model in config.json?")
            print()
            for i, model in enumerate(models, 1):
                print(f"  {i}. {model}")
            print(f"  0. Skip (auto-detect)")
            print()
            
            try:
                choice = input("Select model number [0]: ").strip()
                if choice and choice != "0":
                    idx = int(choice) - 1
                    if 0 <= idx < len(models):
                        update_config_with_model(models[idx])
            except (ValueError, KeyboardInterrupt):
                print("\nSkipped")
    
    print()
    print("=" * 50)
    
    if connected:
        print("✓ LM Studio is ready!")
        print()
        print("You can now run:")
        print("  python assistant.py")
    else:
        print("✗ Setup incomplete")
        print()
        print("Next steps:")
        print("  1. Open LM Studio")
        print("  2. Download and load a model")
        print("  3. Run this script again")


if __name__ == "__main__":
    main()
