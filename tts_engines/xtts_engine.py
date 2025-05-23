# tts_engines/xtts_engine.py
import torch
from TTS.api import TTS
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig
from TTS.config.shared_configs import BaseDatasetConfig
from TTS.tts.models.xtts import XttsArgs
import time
import os
import logging
from typing import Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global cache for loaded models
loaded_models: Dict[str, TTS] = {}
loaded_device = None

# Import configuration
try:
    from config.tts_models_config import get_enabled_models, get_models_by_category, MODEL_CATEGORIES

    CONFIG_AVAILABLE = True
    logging.info("TTS models configuration loaded successfully")
except ImportError:
    logging.warning("TTS models configuration not found, using fallback models")
    CONFIG_AVAILABLE = False

# Fallback models if config is not available
FALLBACK_MODELS = {
    "xtts_v2": {
        "name": "XTTSv2 (Multilingual)",
        "model_path": "tts_models/multilingual/multi-dataset/xtts_v2",
        "description": "Latest XTTS model with best quality and multilingual support",
        "languages": ["en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh-cn", "ja", "hu", "ko",
                      "hi"],
        "type": "xtts"
    },
    "tacotron2_ddc": {
        "name": "Tacotron2-DDC (English)",
        "model_path": "tts_models/en/ljspeech/tacotron2-DDC",
        "description": "High quality English model",
        "languages": ["en"],
        "type": "standard"
    }
}

# Default model
DEFAULT_MODEL = "xtts_v2"


def get_device():
    """Bepaalt of CUDA beschikbaar is."""
    return "cuda" if torch.cuda.is_available() else "cpu"


def get_available_models():
    """Return the available TTS models based on configuration."""
    if CONFIG_AVAILABLE:
        return get_enabled_models()
    else:
        return FALLBACK_MODELS


def get_models_by_type():
    """Return models grouped by type for UI organization."""
    if CONFIG_AVAILABLE:
        try:
            return get_models_by_category()
        except:
            pass  # Fall back to manual grouping

    # Manual grouping fallback
    models = get_available_models()
    models_by_type = {}
    for key, info in models.items():
        model_type = info.get("type", "other")
        if model_type not in models_by_type:
            models_by_type[model_type] = []
        models_by_type[model_type].append((key, info))
    return models_by_type


def get_model_categories():
    """Return model category information for UI."""
    if CONFIG_AVAILABLE:
        try:
            return MODEL_CATEGORIES
        except:
            pass

    # Fallback categories
    return {
        "xtts": {"display_name": "🎯 XTTS Models (Voice Cloning)", "priority": 1},
        "standard": {"display_name": "🔊 Standard Models", "priority": 2},
        "other": {"display_name": "📦 Other Models", "priority": 3}
    }


def get_model_languages(model_key: str) -> list:
    """Get supported languages for a specific model."""
    models = get_available_models()
    return models.get(model_key, {}).get("languages", [])


def load_xtts_model(model_key: str = DEFAULT_MODEL, force_reload: bool = False):
    """Laadt het TTS model (indien nog niet geladen) en verplaatst naar device."""
    global loaded_models, loaded_device
    device = get_device()

    # Check if this specific model is already loaded
    if model_key in loaded_models and loaded_device == device and not force_reload:
        logging.info(f"TTS model '{model_key}' al geladen op {device}.")
        return loaded_models[model_key]

    # Get available models and validate
    available_models = get_available_models()
    if model_key not in available_models:
        logging.warning(f"Unknown TTS model: {model_key}. Available models: {list(available_models.keys())}")
        # Try to fall back to default model
        if DEFAULT_MODEL in available_models and model_key != DEFAULT_MODEL:
            logging.info(f"Falling back to default model: {DEFAULT_MODEL}")
            return load_xtts_model(DEFAULT_MODEL, force_reload)
        else:
            raise ValueError(f"Unknown TTS model: {model_key}. Available models: {list(available_models.keys())}")

    model_info = available_models[model_key]
    model_path = model_info["model_path"]

    logging.info(f"TTS gebruikt device: {device}")
    if device == "cpu":
        logging.warning("CUDA niet beschikbaar, TTS synthese zal erg traag zijn!")

    logging.info(f"Laden TTS model: {model_info['name']} ({model_path})...")

    # Show download size if available
    if "download_size" in model_info:
        logging.info(f"Model download size: {model_info['download_size']}")

    try:
        # Gebruik safe_globals context voor PyTorch 2.6+ compatibiliteit
        with torch.serialization.safe_globals([XttsConfig, XttsAudioConfig, BaseDatasetConfig, XttsArgs]):
            logging.info("Downloading/loading model (this may take a while for first use)...")
            tts = TTS(model_path)  # Laadt initieel op CPU

        logging.info(f"Verplaatsen TTS model '{model_key}' naar device...")
        tts.to(device)

        # Cache the loaded model
        loaded_models[model_key] = tts
        loaded_device = device

        logging.info(f"TTS model '{model_key}' succesvol geladen en verplaatst naar {device}.")
        return tts
    except Exception as e:
        logging.error(f"FOUT bij laden/verplaatsen TTS model '{model_key}': {e}", exc_info=True)

        # Provide more helpful error messages
        if "404" in str(e) or "Not Found" in str(e):
            logging.error(f"Model '{model_path}' not found. Check if the model path is correct.")
        elif "OutOfMemoryError" in str(e) or "CUDA out of memory" in str(e):
            logging.error("GPU out of memory. Try using CPU or a smaller model.")
        else:
            logging.error(
                "Controleer modelnaam, dependencies, of probeer 'export TORCH_WEIGHTS_ONLY=0' (Linux/macOS) or 'set TORCH_WEIGHTS_ONLY=0' (Windows) als dit aanhoudt.")

        # Remove from cache if it was partially loaded
        if model_key in loaded_models:
            del loaded_models[model_key]

        raise  # Geef de fout door aan de oproeper


def synthesize_xtts(text: str, speaker_wav_path: Optional[str], language: str, output_path: str,
                    model_key: str = DEFAULT_MODEL):
    """Synthetiseert de gegeven tekst met TTS models - ROBUST VERSION."""
    start_time = time.time()
    try:
        # Get available models and validate
        available_models = get_available_models()
        if model_key not in available_models:
            raise ValueError(f"Unknown TTS model: {model_key}")

        model_info = available_models[model_key]
        supported_languages = model_info["languages"]
        model_type = model_info.get("type", "xtts")

        if language not in supported_languages:
            logging.warning(
                f"Language '{language}' not officially supported by {model_info['name']}. Supported: {supported_languages}")
            # For non-XTTS models, fall back to English if available
            if model_type != "xtts" and "en" in supported_languages:
                logging.warning(f"Falling back to English for {model_info['name']}")
                language = "en"

        tts_model = load_xtts_model(model_key)
        if tts_model is None:
            raise RuntimeError(f"TTS model '{model_key}' kon niet worden geladen.")

        # Handle speaker_wav_path more robustly
        valid_speaker_wav = None
        use_speaker_cloning = False

        if speaker_wav_path and isinstance(speaker_wav_path, str) and speaker_wav_path.strip():
            speaker_path = speaker_wav_path.strip()
            if os.path.exists(speaker_path) and os.path.isfile(speaker_path):
                valid_speaker_wav = speaker_path
                use_speaker_cloning = True
                logging.info(f"Using speaker WAV: {valid_speaker_wav}")
            else:
                logging.warning(f"Speaker WAV file not found or invalid: {speaker_path}")

        if not use_speaker_cloning:
            logging.info("No valid speaker WAV provided, using default voice")

        logging.info(f"Starting TTS synthesis: Model='{model_info['name']}', Language={language}, Type={model_type}")
        logging.info(f"Voice cloning: {'Enabled' if use_speaker_cloning else 'Disabled'}")

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # ROBUST SYNTHESIS with multiple fallback methods
        synthesis_successful = False

        if model_type in ["xtts", "multilingual"] or "xtts" in model_key.lower():
            # XTTS models - try multiple approaches

            # Method 1: Standard XTTS with/without speaker
            if not synthesis_successful:
                try:
                    logging.info("Trying Method 1: Standard XTTS synthesis")
                    if use_speaker_cloning and valid_speaker_wav:
                        tts_model.tts_to_file(
                            text=text,
                            speaker_wav=valid_speaker_wav,
                            language=language,
                            file_path=output_path
                        )
                    else:
                        # Try without speaker_wav parameter at all
                        tts_model.tts_to_file(
                            text=text,
                            language=language,
                            file_path=output_path
                        )
                    synthesis_successful = True
                    logging.info("Method 1 successful")
                except Exception as e1:
                    logging.warning(f"Method 1 failed: {e1}")

            # Method 2: Use tts() method and save manually
            if not synthesis_successful:
                try:
                    logging.info("Trying Method 2: Direct tts() method")
                    if use_speaker_cloning and valid_speaker_wav:
                        wav = tts_model.tts(
                            text=text,
                            speaker_wav=valid_speaker_wav,
                            language=language
                        )
                    else:
                        wav = tts_model.tts(text=text, language=language)

                    # Save manually
                    import soundfile as sf
                    sf.write(output_path, wav, 22050)
                    synthesis_successful = True
                    logging.info("Method 2 successful")
                except Exception as e2:
                    logging.warning(f"Method 2 failed: {e2}")

            # Method 3: Force English if language is causing issues
            if not synthesis_successful and language != "en":
                try:
                    logging.info("Trying Method 3: Force English language")
                    if use_speaker_cloning and valid_speaker_wav:
                        wav = tts_model.tts(
                            text=text,
                            speaker_wav=valid_speaker_wav,
                            language="en"
                        )
                    else:
                        wav = tts_model.tts(text=text, language="en")

                    import soundfile as sf
                    sf.write(output_path, wav, 22050)
                    synthesis_successful = True
                    logging.info("Method 3 successful (using English)")
                except Exception as e3:
                    logging.warning(f"Method 3 failed: {e3}")

            # Method 4: Minimal parameters (last resort for XTTS)
            if not synthesis_successful:
                try:
                    logging.info("Trying Method 4: Minimal parameters")
                    wav = tts_model.tts(text=text)
                    import soundfile as sf
                    sf.write(output_path, wav, 22050)
                    synthesis_successful = True
                    logging.info("Method 4 successful (minimal parameters)")
                except Exception as e4:
                    logging.warning(f"Method 4 failed: {e4}")

        else:
            # Non-XTTS models (standard, multispeaker, etc.)
            try:
                if model_type == "multispeaker":
                    # Multi-speaker models
                    speaker_id = "p225"  # Default speaker
                    logging.info(f"Using multi-speaker model with speaker: {speaker_id}")
                    tts_model.tts_to_file(
                        text=text,
                        speaker=speaker_id,
                        file_path=output_path
                    )
                else:
                    # Standard single-speaker models
                    logging.info("Using standard single-speaker model")
                    tts_model.tts_to_file(
                        text=text,
                        file_path=output_path
                    )
                synthesis_successful = True
                logging.info("Non-XTTS synthesis successful")
            except Exception as e:
                logging.warning(f"Non-XTTS synthesis failed: {e}")
                # Try manual method for non-XTTS
                try:
                    wav = tts_model.tts(text=text)
                    import soundfile as sf
                    sf.write(output_path, wav, 22050)
                    synthesis_successful = True
                    logging.info("Non-XTTS manual method successful")
                except Exception as e2:
                    logging.error(f"All non-XTTS methods failed: {e2}")

        # Check if synthesis was successful
        if not synthesis_successful:
            raise RuntimeError("All synthesis methods failed - see previous error messages")

        # Verify output file
        if not os.path.exists(output_path):
            raise RuntimeError(f"Synthesis completed but output file not found: {output_path}")

        file_size = os.path.getsize(output_path)
        if file_size == 0:
            raise RuntimeError(f"Output file is empty: {output_path}")

        end_time = time.time()
        logging.info(f"TTS synthesis completed successfully in {end_time - start_time:.2f} seconds")
        logging.info(f"Output: {output_path} ({file_size} bytes)")

        return True, f"Audio successfully saved to {output_path} (Model: {model_info['name']}, Size: {file_size} bytes)"

    except Exception as e:
        logging.error(f"TTS synthesis failed: {e}")
        logging.error(f"Error type: {type(e).__name__}")
        import traceback
        logging.error(f"Full traceback:\n{traceback.format_exc()}")
        return False, f"TTS synthesis failed: {e}"

def clear_model_cache():
    """Clear all loaded models from memory."""
    global loaded_models
    for model_key in list(loaded_models.keys()):
        del loaded_models[model_key]
    loaded_models.clear()
    logging.info("TTS model cache cleared.")


def get_model_info_summary():
    """Get a summary of available models for logging/debugging."""
    models = get_available_models()
    summary = []
    for key, info in models.items():
        languages_str = ", ".join(info.get("languages", [])[:3])
        if len(info.get("languages", [])) > 3:
            languages_str += "..."
        summary.append(f"{key}: {info.get('name', 'Unknown')} ({languages_str})")
    return summary


# Voorbeeld van direct testen (optioneel)
if __name__ == '__main__':
    print("Testen TTS Engine met configuratie...")

    # Print configuration status
    print(f"Configuration available: {CONFIG_AVAILABLE}")

    # Print available models
    models = get_available_models()
    print(f"\nBeschikbare TTS modellen ({len(models)}):")
    for summary in get_model_info_summary():
        print(f"  • {summary}")

    # Print models by category
    print(f"\nModellen per categorie:")
    categories = get_model_categories()
    models_by_type = get_models_by_type()

    for category_key in sorted(categories.keys(), key=lambda x: categories[x].get("priority", 99)):
        if category_key in models_by_type:
            category_info = categories[category_key]
            print(f"\n{category_info['display_name']}:")
            for model_key, model_info in models_by_type[category_key]:
                print(f"  • {model_info['name']}")

    # Test synthesis if models are available
    if models:
        test_text = "Hello world, this is a test of the TTS configuration system."
        test_output = "../audio_output/tts_config_test.wav"
        os.makedirs("../audio_output", exist_ok=True)

        print(f"\nTesten met model: {DEFAULT_MODEL}")
        try:
            success, message = synthesize_xtts(test_text, None, "en", test_output, DEFAULT_MODEL)
            print(f"Result: {message}")
        except Exception as e:
            print(f"Test failed: {e}")
    else:
        print("\nNo models available for testing.")