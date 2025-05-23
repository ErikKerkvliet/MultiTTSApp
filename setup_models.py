#!/usr/bin/env python3
# setup_models.py
"""
Setup script for TTS models configuration.
Run this to configure which models you want to use.
"""

import os
import sys


def create_config_directory():
    """Create the config directory if it doesn't exist."""
    if not os.path.exists("config"):
        os.makedirs("config")
        print("✅ Created config directory")

    # Create __init__.py to make it a package
    init_file = "config/__init__.py"
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write("# TTS Configuration Package\n")
        print("✅ Created config/__init__.py")


def show_model_selection_menu():
    """Show interactive menu for model selection."""
    print("\n" + "=" * 60)
    print("🎙️  MULTI TTS SYNTHESIZER - MODEL SETUP")
    print("=" * 60)

    print("\nSelect which models you want to enable:")
    print("\n1. 📦 MINIMAL SETUP (~2GB download)")
    print("   • XTTSv2 (voice cloning)")
    print("   • Tacotron2-DDC (high quality English)")
    print("   • GlowTTS (fast English)")

    print("\n2. ⭐ RECOMMENDED SETUP (~3.5GB download)")
    print("   • XTTSv2 (voice cloning)")
    print("   • YourTTS (specialized voice cloning)")
    print("   • Tacotron2-DDC (high quality English)")
    print("   • GlowTTS (fast English)")
    print("   • Jenny (natural female voice)")

    print("\n3. 🚀 FULL SETUP (~6GB+ download)")
    print("   • All available high-quality models")
    print("   • Multiple voice options")
    print("   • Multi-speaker models")

    print("\n4. 🔧 CUSTOM SETUP")
    print("   • Choose individual models")

    print("\n5. ℹ️  SHOW ALL AVAILABLE MODELS")

    print("\n6. ❌ EXIT")

    while True:
        try:
            choice = input("\nEnter your choice (1-6): ").strip()
            if choice in ["1", "2", "3", "4", "5", "6"]:
                return choice
            else:
                print("❌ Invalid choice. Please enter 1-6.")
        except KeyboardInterrupt:
            print("\n\n👋 Setup cancelled.")
            sys.exit(0)


def show_all_models():
    """Show information about all available models."""
    print("\n" + "=" * 80)
    print("📋 ALL AVAILABLE TTS MODELS")
    print("=" * 80)

    # Import the configuration
    sys.path.insert(0, '.')
    try:
        from config.tts_models_config import TTS_MODELS_CONFIG, MODEL_CATEGORIES

        # Group models by category
        models_by_category = {}
        for model_key, model_config in TTS_MODELS_CONFIG.items():
            category = model_config.get("type", "other")
            if category not in models_by_category:
                models_by_category[category] = []
            models_by_category[category].append((model_key, model_config))

        # Display by category
        for category_key, category_info in MODEL_CATEGORIES.items():
            if category_key in models_by_category:
                print(f"\n{category_info['display_name']}")
                print("-" * len(category_info['display_name']))

                for model_key, model_config in models_by_category[category_key]:
                    status = "✅" if model_config.get("enabled", False) else "❌"
                    size = model_config.get("download_size", "Unknown size")
                    print(f"{status} {model_config['name']} ({size})")
                    print(f"     {model_config['description']}")
                    languages = ", ".join(model_config.get("languages", [])[:5])
                    if len(model_config.get("languages", [])) > 5:
                        languages += "..."
                    print(f"     Languages: {languages}")
                    print()

    except ImportError:
        print("❌ Configuration not found. Please run the setup first.")


def apply_preset(preset_name):
    """Apply a model preset."""
    presets = {
        "minimal": ["xtts_v2", "tacotron2_ddc", "glow_tts"],
        "recommended": ["xtts_v2", "your_tts", "tacotron2_ddc", "glow_tts", "jenny"],
        "full": ["xtts_v2", "your_tts", "tacotron2_ddc", "glow_tts", "jenny", "vctk_vits", "speedy_speech"]
    }

    preset_models = presets.get(preset_name, [])

    config_content = f'''# config/tts_models_config.py
# AUTO-GENERATED CONFIGURATION - Edit manually if needed
# Preset: {preset_name.upper()}

TTS_MODELS_CONFIG = {{
    # === XTTS MODELS (Voice Cloning Capable) ===
    "xtts_v2": {{
        "enabled": {"true" if "xtts_v2" in preset_models else "false"},
        "name": "XTTSv2 (Multilingual)",
        "model_path": "tts_models/multilingual/multi-dataset/xtts_v2",
        "description": "Latest XTTS model with best quality and multilingual support",
        "languages": ["en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh-cn", "ja", "hu", "ko", "hi"],
        "type": "xtts",
        "download_size": "~1.8GB"
    }},

    "your_tts": {{
        "enabled": {"true" if "your_tts" in preset_models else "false"},
        "name": "YourTTS (Voice Cloning)",
        "model_path": "tts_models/multilingual/multi-dataset/your_tts",
        "description": "Specialized for voice cloning with fewer languages",
        "languages": ["en", "fr", "pt"],
        "type": "xtts",
        "download_size": "~1.2GB"
    }},

    # === STANDARD HIGH-QUALITY MODELS ===
    "tacotron2_ddc": {{
        "enabled": {"true" if "tacotron2_ddc" in preset_models else "false"},
        "name": "Tacotron2-DDC (English)",
        "model_path": "tts_models/en/ljspeech/tacotron2-DDC",
        "description": "High quality English model, excellent for clear speech",
        "languages": ["en"],
        "type": "standard",
        "download_size": "~200MB"
    }},

    "glow_tts": {{
        "enabled": {"true" if "glow_tts" in preset_models else "false"},
        "name": "GlowTTS (English)",
        "model_path": "tts_models/en/ljspeech/glow-tts",
        "description": "Fast and good quality English model",
        "languages": ["en"],
        "type": "standard",
        "download_size": "~100MB"
    }},

    "jenny": {{
        "enabled": {"true" if "jenny" in preset_models else "false"},
        "name": "Jenny (Natural Female)",
        "model_path": "tts_models/en/jenny/jenny",
        "description": "Natural sounding female voice with good prosody",
        "languages": ["en"],
        "type": "standard",
        "download_size": "~150MB"
    }},

    # === MULTI-SPEAKER MODELS ===
    "vctk_vits": {{
        "enabled": {"true" if "vctk_vits" in preset_models else "false"},
        "name": "VCTK-VITS (Multi-Speaker)",
        "model_path": "tts_models/en/vctk/vits",
        "description": "Multi-speaker English model with 100+ different voices",
        "languages": ["en"],
        "type": "multispeaker",
        "download_size": "~500MB"
    }},

    # === FAST MODELS ===
    "speedy_speech": {{
        "enabled": {"true" if "speedy_speech" in preset_models else "false"},
        "name": "SpeedySpeech (Ultra Fast)",
        "model_path": "tts_models/en/ljspeech/speedy-speech",
        "description": "Optimized for speed, good for real-time applications",
        "languages": ["en"],
        "type": "fast",
        "download_size": "~50MB"
    }}
}}

# Model Categories for UI Organization
MODEL_CATEGORIES = {{
    "xtts": {{
        "display_name": "🎯 XTTS Models (Voice Cloning)",
        "description": "Models that support voice cloning with speaker samples",
        "priority": 1
    }},
    "standard": {{
        "display_name": "🔊 Standard Models",
        "description": "High-quality single-speaker models",
        "priority": 2
    }},
    "multispeaker": {{
        "display_name": "👥 Multi-Speaker Models", 
        "description": "Models with multiple built-in voices",
        "priority": 3
    }},
    "fast": {{
        "display_name": "⚡ Fast Models",
        "description": "Optimized for speed over quality",
        "priority": 4
    }}
}}

def get_enabled_models():
    """Return only the models that are enabled in the configuration."""
    return {{key: config for key, config in TTS_MODELS_CONFIG.items() if config.get("enabled", False)}}

def get_models_by_category():
    """Return enabled models organized by category."""
    enabled_models = get_enabled_models()
    categorized = {{}}

    for model_key, model_config in enabled_models.items():
        category = model_config.get("type", "other")
        if category not in categorized:
            categorized[category] = []
        categorized[category].append((model_key, model_config))

    return categorized

def get_model_info(model_key):
    """Get information about a specific model."""
    return TTS_MODELS_CONFIG.get(model_key, {{}})

def is_model_enabled(model_key):
    """Check if a specific model is enabled."""
    return TTS_MODELS_CONFIG.get(model_key, {{}}).get("enabled", False)
'''

    # Write the configuration file
    with open("config/tts_models_config.py", "w") as f:
        f.write(config_content)

    print(f"✅ Applied {preset_name.upper()} preset configuration")

    # Show what was enabled
    enabled_models = [model for model in preset_models]
    print(f"📦 Enabled models: {', '.join(enabled_models)}")

    # Estimate download size
    sizes = {
        "xtts_v2": 1800,  # MB
        "your_tts": 1200,
        "tacotron2_ddc": 200,
        "glow_tts": 100,
        "jenny": 150,
        "vctk_vits": 500,
        "speedy_speech": 50
    }

    total_size = sum(sizes.get(model, 0) for model in enabled_models)
    print(f"📊 Estimated download size: ~{total_size / 1000:.1f}GB")


def custom_model_setup():
    """Interactive custom model selection."""
    print("\n🔧 CUSTOM MODEL SETUP")
    print("=" * 40)

    models_info = {
        "xtts_v2": ("XTTSv2 (Multilingual Voice Cloning)", "~1.8GB", True),
        "your_tts": ("YourTTS (Specialized Voice Cloning)", "~1.2GB", False),
        "tacotron2_ddc": ("Tacotron2-DDC (High Quality English)", "~200MB", True),
        "glow_tts": ("GlowTTS (Fast English)", "~100MB", True),
        "jenny": ("Jenny (Natural Female Voice)", "~150MB", False),
        "vctk_vits": ("VCTK-VITS (Multi-Speaker)", "~500MB", False),
        "speedy_speech": ("SpeedySpeech (Ultra Fast)", "~50MB", False)
    }

    selected_models = []

    print("Select which models to enable (y/n for each):")
    print()

    for model_key, (name, size, recommended) in models_info.items():
        rec_text = " [RECOMMENDED]" if recommended else ""
        default = "y" if recommended else "n"

        while True:
            try:
                response = input(f"🎙️  {name} ({size}){rec_text} [{default}]: ").strip().lower()
                if not response:
                    response = default

                if response in ['y', 'yes', '1', 'true']:
                    selected_models.append(model_key)
                    print(f"   ✅ {name} - ENABLED")
                    break
                elif response in ['n', 'no', '0', 'false']:
                    print(f"   ❌ {name} - DISABLED")
                    break
                else:
                    print("   Please enter y/n")
            except KeyboardInterrupt:
                print("\n\n👋 Setup cancelled.")
                sys.exit(0)
        print()

    if not selected_models:
        print("⚠️  No models selected! Enabling minimal set...")
        selected_models = ["xtts_v2", "tacotron2_ddc"]

    # Create custom preset
    presets = {"custom": selected_models}
    apply_preset("custom")


def main():
    """Main setup function."""
    print("🎙️  Multi TTS Synthesizer - Model Setup")

    # Create config directory
    create_config_directory()

    while True:
        choice = show_model_selection_menu()

        if choice == "1":
            apply_preset("minimal")
            break
        elif choice == "2":
            apply_preset("recommended")
            break
        elif choice == "3":
            apply_preset("full")
            break
        elif choice == "4":
            custom_model_setup()
            break
        elif choice == "5":
            show_all_models()
            input("\nPress Enter to continue...")
        elif choice == "6":
            print("👋 Setup cancelled.")
            sys.exit(0)

    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETE!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Run your TTS application: python app.py")
    print("2. Models will be downloaded automatically on first use")
    print("3. To change models later, edit config/tts_models_config.py")
    print("   or run this setup script again")
    print()
    print("💡 Tips:")
    print("• First model download may take a while")
    print("• GPU is recommended for XTTS models")
    print("• Place speaker samples in speaker_samples/ for voice cloning")
    print()


if __name__ == "__main__":
    main()