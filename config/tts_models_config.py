# config/tts_models_config.py
# AUTO-GENERATED CONFIGURATION - Edit manually if needed
# Preset: FULL

TTS_MODELS_CONFIG = {
    # === XTTS MODELS (Voice Cloning Capable) ===
    "xtts_v2": {
        "enabled": True,
        "name": "XTTSv2 (Multilingual)",
        "model_path": "tts_models/multilingual/multi-dataset/xtts_v2",
        "description": "Latest XTTS model with best quality and multilingual support",
        "languages": ["en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh-cn", "ja", "hu", "ko", "hi"],
        "type": "xtts",
        "download_size": "~1.8GB"
    },

    "your_tts": {
        "enabled": True,
        "name": "YourTTS (Voice Cloning)",
        "model_path": "tts_models/multilingual/multi-dataset/your_tts",
        "description": "Specialized for voice cloning with fewer languages",
        "languages": ["en", "fr", "pt"],
        "type": "xtts",
        "download_size": "~1.2GB"
    },

    # === STANDARD HIGH-QUALITY MODELS ===
    "tacotron2_ddc": {
        "enabled": True,
        "name": "Tacotron2-DDC (English)",
        "model_path": "tts_models/en/ljspeech/tacotron2-DDC",
        "description": "High quality English model, excellent for clear speech",
        "languages": ["en"],
        "type": "standard",
        "download_size": "~200MB"
    },

    "glow_tts": {
        "enabled": True,
        "name": "GlowTTS (English)",
        "model_path": "tts_models/en/ljspeech/glow-tts",
        "description": "Fast and good quality English model",
        "languages": ["en"],
        "type": "standard",
        "download_size": "~100MB"
    },

    "jenny": {
        "enabled": True,
        "name": "Jenny (Natural Female)",
        "model_path": "tts_models/en/jenny/jenny",
        "description": "Natural sounding female voice with good prosody",
        "languages": ["en"],
        "type": "standard",
        "download_size": "~150MB"
    },

    # === MULTI-SPEAKER MODELS ===
    "vctk_vits": {
        "enabled": True,
        "name": "VCTK-VITS (Multi-Speaker)",
        "model_path": "tts_models/en/vctk/vits",
        "description": "Multi-speaker English model with 100+ different voices",
        "languages": ["en"],
        "type": "multispeaker",
        "download_size": "~500MB"
    },

    # === FAST MODELS ===
    "speedy_speech": {
        "enabled": True,
        "name": "SpeedySpeech (Ultra Fast)",
        "model_path": "tts_models/en/ljspeech/speedy-speech",
        "description": "Optimized for speed, good for real-time applications",
        "languages": ["en"],
        "type": "fast",
        "download_size": "~50MB"
    }
}

# Model Categories for UI Organization
MODEL_CATEGORIES = {
    "xtts": {
        "display_name": "🎯 XTTS Models (Voice Cloning)",
        "description": "Models that support voice cloning with speaker samples",
        "priority": 1
    },
    "standard": {
        "display_name": "🔊 Standard Models",
        "description": "High-quality single-speaker models",
        "priority": 2
    },
    "multispeaker": {
        "display_name": "👥 Multi-Speaker Models", 
        "description": "Models with multiple built-in voices",
        "priority": 3
    },
    "fast": {
        "display_name": "⚡ Fast Models",
        "description": "Optimized for speed over quality",
        "priority": 4
    }
}

def get_enabled_models():
    """Return only the models that are enabled in the configuration."""
    return {key: config for key, config in TTS_MODELS_CONFIG.items() if config.get("enabled", False)}

def get_models_by_category():
    """Return enabled models organized by category."""
    enabled_models = get_enabled_models()
    categorized = {}

    for model_key, model_config in enabled_models.items():
        category = model_config.get("type", "other")
        if category not in categorized:
            categorized[category] = []
        categorized[category].append((model_key, model_config))

    return categorized

def get_model_info(model_key):
    """Get information about a specific model."""
    return TTS_MODELS_CONFIG.get(model_key, {})

def is_model_enabled(model_key):
    """Check if a specific model is enabled."""
    return TTS_MODELS_CONFIG.get(model_key, {}).get("enabled", False)
