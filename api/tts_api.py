# tts_api.py
"""
API wrapper for the Multi TTS Synthesizer application.

This module provides a programmatic interface to the TTS engines,
allowing external applications to use the synthesizer functionality
without the GUI.
"""

import os
import logging
import time
from typing import Dict, Any, Optional, Tuple, List

# Import the TTS engines
from tts_engines import xtts_engine, piper_engine, bark_engine, elevenlabs_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [API] %(message)s'
)
logger = logging.getLogger('tts_api')


class MultiTTSAPI:
    """
    API class for the Multi TTS Synthesizer.

    Provides methods to access and use all supported TTS engines
    (XTTSv2, Piper, Bark, ElevenLabs) without the GUI interface.
    """

    # Default directories
    DEFAULT_OUTPUT_DIR = "../audio_output"
    DEFAULT_SPEAKER_DIR = "speaker_samples"
    DEFAULT_PIPER_MODEL_DIR = "models/piper"

    def __init__(self):
        """Initialize the API and ensure output directories exist."""
        # Ensure output directory exists
        os.makedirs(self.DEFAULT_OUTPUT_DIR, exist_ok=True)
        logger.info("MultiTTS API initialized")

        # Cache for ElevenLabs voices
        self._elevenlabs_voices = {}
        # Current validated ElevenLabs API key
        self._current_elevenlabs_key = None

    # --- XTTSv2 Methods ---

    def synthesize_xtts(self,
                        text: str,
                        output_path: str,
                        language: str = "en",
                        speaker_wav_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Synthesize text using XTTSv2.

        Args:
            text: The text to synthesize
            output_path: Path to save the output WAV file
            language: Language code (e.g., "en", "nl", "fr")
            speaker_wav_path: Path to an optional speaker reference WAV

        Returns:
            A tuple (success: bool, message: str)
        """
        logger.info(f"XTTSv2 synthesis requested: language={language}, speaker={speaker_wav_path or 'default'}")
        self._ensure_output_dir_exists(output_path)

        try:
            return xtts_engine.synthesize_xtts(
                text=text,
                speaker_wav_path=speaker_wav_path,
                language=language,
                output_path=output_path
            )
        except Exception as e:
            logger.error(f"XTTSv2 synthesis failed: {e}")
            return False, f"XTTSv2 synthesis failed: {e}"

    # --- Piper Methods ---

    def synthesize_piper(self,
                         text: str,
                         output_path: str,
                         model_onnx_path: str,
                         model_json_path: str) -> Tuple[bool, str]:
        """
        Synthesize text using Piper.

        Args:
            text: The text to synthesize
            output_path: Path to save the output WAV file
            model_onnx_path: Path to Piper's ONNX model file
            model_json_path: Path to Piper's JSON config file

        Returns:
            A tuple (success: bool, message: str)
        """
        logger.info(f"Piper synthesis requested: model={os.path.basename(model_onnx_path)}")
        self._ensure_output_dir_exists(output_path)

        # Verify model files exist
        if not os.path.exists(model_onnx_path):
            return False, f"Piper ONNX model not found: {model_onnx_path}"
        if not os.path.exists(model_json_path):
            return False, f"Piper JSON config not found: {model_json_path}"

        try:
            return piper_engine.synthesize_piper(
                text=text,
                model_onnx_path=model_onnx_path,
                model_json_path=model_json_path,
                output_path=output_path
            )
        except Exception as e:
            logger.error(f"Piper synthesis failed: {e}")
            return False, f"Piper synthesis failed: {e}"

    # --- Bark Methods ---

    def synthesize_bark(self,
                        text: str,
                        output_path: str,
                        voice_preset: str,
                        model_name: str = "suno/bark-small") -> Tuple[bool, str]:
        """
        Synthesize text using Bark.

        Args:
            text: The text to synthesize
            output_path: Path to save the output WAV file
            voice_preset: Voice preset ID (e.g., "v2/en_speaker_6")
            model_name: Bark model name/path

        Returns:
            A tuple (success: bool, message: str)
        """
        logger.info(f"Bark synthesis requested: voice={voice_preset}, model={model_name}")
        self._ensure_output_dir_exists(output_path)

        try:
            return bark_engine.synthesize_bark(
                text=text,
                voice_preset=voice_preset,
                output_path=output_path,
                model_name=model_name
            )
        except Exception as e:
            logger.error(f"Bark synthesis failed: {e}")
            return False, f"Bark synthesis failed: {e}"

    # --- ElevenLabs Methods ---

    def validate_elevenlabs_key(self, api_key: str) -> bool:
        """
        Validate an ElevenLabs API key.

        Args:
            api_key: The API key to validate

        Returns:
            True if valid, False otherwise
        """
        logger.info("Validating ElevenLabs API key")
        validated_key = elevenlabs_engine.validate_api_key(api_key)

        if validated_key:
            self._current_elevenlabs_key = validated_key
            return True
        else:
            return False

    def get_elevenlabs_voices(self, api_key: Optional[str] = None) -> List[Tuple[str, str]]:
        """
        Get available ElevenLabs voices.

        Args:
            api_key: Optional API key (uses cached key if None)

        Returns:
            List of (voice_name, voice_id) tuples

        Raises:
            ValueError: If no API key is provided or cached
        """
        key_to_use = api_key or self._current_elevenlabs_key

        if not key_to_use:
            raise ValueError("No ElevenLabs API key provided or cached")

        logger.info("Fetching ElevenLabs voices")
        voices = elevenlabs_engine.get_elevenlabs_voices(key_to_use)

        # Cache the results for quick lookup
        self._elevenlabs_voices = {name: voice_id for name, voice_id in voices}
        return voices

    def get_elevenlabs_voice_id(self, voice_name: str) -> Optional[str]:
        """
        Get the voice ID for a given voice name.

        Args:
            voice_name: The name of the voice

        Returns:
            The voice ID or None if not found
        """
        return self._elevenlabs_voices.get(voice_name)

    def get_elevenlabs_subscription_info(self, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Get ElevenLabs subscription information.

        Args:
            api_key: Optional API key (uses cached key if None)

        Returns:
            Dictionary with subscription information

        Raises:
            ValueError: If no API key is provided or cached
        """
        key_to_use = api_key or self._current_elevenlabs_key

        if not key_to_use:
            raise ValueError("No ElevenLabs API key provided or cached")

        logger.info("Fetching ElevenLabs subscription info")
        return elevenlabs_engine.get_subscription_info(key_to_use)

    def synthesize_elevenlabs(self,
                              text: str,
                              output_path: str,
                              voice_id: str,
                              model_id: str = "eleven_multilingual_v2",
                              api_key: Optional[str] = None) -> Tuple[bool, str]:
        """
        Synthesize text using ElevenLabs.

        Args:
            text: The text to synthesize
            output_path: Path to save the output WAV file
            voice_id: ID of the voice to use
            model_id: ID of the model to use
            api_key: Optional API key (uses cached key if None)

        Returns:
            A tuple (success: bool, message: str)

        Raises:
            ValueError: If no API key is provided or cached
        """
        key_to_use = api_key or self._current_elevenlabs_key

        if not key_to_use:
            raise ValueError("No ElevenLabs API key provided or cached")

        logger.info(f"ElevenLabs synthesis requested: voice={voice_id}, model={model_id}")
        self._ensure_output_dir_exists(output_path)

        try:
            return elevenlabs_engine.synthesize_elevenlabs(
                text=text,
                voice_id=voice_id,
                model_id=model_id,
                output_path=output_path,
                api_key=key_to_use
            )
        except Exception as e:
            logger.error(f"ElevenLabs synthesis failed: {e}")
            return False, f"ElevenLabs synthesis failed: {e}"

    # --- Utility Methods ---

    def _ensure_output_dir_exists(self, output_path: str) -> None:
        """Ensure the output directory for a file exists."""
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Created output directory: {output_dir}")

    @property
    def available_models(self) -> Dict[str, str]:
        """Return information about available models."""
        return {
            "XTTSv2": "tts_models/multilingual/multi-dataset/xtts_v2",
            "Piper": f"Check {self.DEFAULT_PIPER_MODEL_DIR} directory for available models",
            "Bark": "suno/bark-small or suno/bark",
            "ElevenLabs": ", ".join(elevenlabs_engine.ELEVENLABS_MODELS)
        }

    @property
    def default_bark_voices(self) -> List[str]:
        """Return a list of default Bark voice presets."""
        return [
            "v2/en_speaker_0", "v2/en_speaker_1", "v2/en_speaker_2", "v2/en_speaker_3",
            "v2/en_speaker_4", "v2/en_speaker_5", "v2/en_speaker_6", "v2/en_speaker_7",
            "v2/en_speaker_8", "v2/en_speaker_9", "v2/de_speaker_1", "v2/es_speaker_1",
            "v2/fr_speaker_1", "v2/it_speaker_1", "v2/ja_speaker_1", "v2/ko_speaker_1",
            "v2/pl_speaker_1", "v2/pt_speaker_1", "v2/ru_speaker_1", "v2/tr_speaker_1",
            "v2/zh_speaker_1", "v2/nl_speaker_0", "v2/nl_speaker_1"
        ]


# --- Example Usage ---
if __name__ == "__main__":
    # Example of how to use the API
    api = MultiTTSAPI()

    # Example: XTTSv2
    text = "This is a test of the TTS API."
    output_path = "audio_output/api_test_xtts.wav"

    success, message = api.synthesize_xtts(
        text=text,
        output_path=output_path,
        language="en"
    )

    print(f"XTTSv2 Result: {message}")

    # Example: Get available models info
    print("\nAvailable Models:")
    for model, info in api.available_models.items():
        print(f"- {model}: {info}")