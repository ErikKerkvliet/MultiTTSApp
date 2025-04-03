# tts_engines/elevenlabs_engine.py
"""
Handles interaction with the ElevenLabs Text-to-Speech API.

Provides functions to validate API keys, fetch voices, get subscription info,
and synthesize text using the ElevenLabs service.
Requires 'elevenlabs' and 'httpx'. Conversion optionally uses 'pydub'.
"""

import os
import time
import logging
from typing import Optional, List, Tuple, Dict, Any

# Official ElevenLabs client library
from elevenlabs.client import ElevenLabs
from elevenlabs import Voice, save
import httpx  # For detailed HTTP error handling

# --- Basic Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__) # Logger specific to this module

# --- Constants ---
# Common ElevenLabs model IDs. Check ElevenLabs docs for the latest.
ELEVENLABS_MODELS: List[str] = [
    "eleven_multilingual_v2",  # Recommended default, supports multiple languages
    "eleven_multilingual_v1",
    "eleven_monolingual_v1",   # Primarily for English
    # "eleven_turbo_v2"      # Lower latency option if needed
]

# --- API Interaction Functions ---

def validate_api_key(api_key_to_validate: Optional[str]) -> Optional[str]:
    """
    Validates the provided API key by making a light API call (fetching models).

    Args:
        api_key_to_validate: The ElevenLabs API key string to validate.

    Returns:
        The validated API key string if successful, None otherwise.
    """
    if not api_key_to_validate:
        logger.warning("No API key provided for validation.")
        return None

    logger.info("Validating ElevenLabs API key...")
    try:
        # Create a temporary client with the provided key for validation purposes
        client = ElevenLabs(api_key=api_key_to_validate)
        # Perform a lightweight API call to check if the key is valid
        client.models.get_all()
        logger.info("ElevenLabs API key validated successfully.")
        return api_key_to_validate  # Return the key if validation succeeded
    except httpx.HTTPStatusError as http_err:
        # Specifically catch HTTP errors (like 401 Unauthorized)
        logger.error(
            f"API key validation failed: HTTP Status {http_err.response.status_code}. Check the key."
        )
        return None
    except Exception as e:
        # Catch other potential errors during client creation or API call
        logger.error(f"API key validation failed: {e}", exc_info=False) # Log less verbosely
        return None

def get_elevenlabs_voices(api_key: Optional[str]) -> List[Tuple[str, str]]:
    """
    Fetches the list of available voices using the provided API key.

    Args:
        api_key: The validated ElevenLabs API key.

    Returns:
        A list of tuples, where each tuple contains (voice_name, voice_id).

    Raises:
        ValueError: If the API key is missing.
        RuntimeError: If fetching voices fails for other reasons.
    """
    if not api_key:
        logger.error("Cannot fetch voices: API key not provided.")
        raise ValueError("API key is required to fetch ElevenLabs voices.")

    logger.info("Fetching ElevenLabs voices...")
    try:
        # Create the client using the provided (presumably validated) API key
        client = ElevenLabs(api_key=api_key)
        voice_list = client.voices.get_all().voices

        # Format the response into a more usable list of (name, id) tuples
        # Sort alphabetically by voice name for easier display
        formatted_voices: List[Tuple[str, str]] = sorted(
            [(v.name, v.voice_id) for v in voice_list if v.name and v.voice_id], # Ensure name and id exist
            key=lambda item: item[0] # Sort by name (item[0])
        )
        logger.info(f"{len(formatted_voices)} ElevenLabs voices successfully fetched.")
        return formatted_voices
    except httpx.HTTPStatusError as http_err:
        logger.error(
            f"HTTP Error fetching ElevenLabs voices ({http_err.response.status_code}): {http_err.response.text}",
            exc_info=True
        )
        raise RuntimeError(f"Could not fetch ElevenLabs voices due to HTTP error: {http_err.response.status_code}")
    except Exception as e:
        logger.error(f"Error fetching ElevenLabs voices: {e}", exc_info=True)
        raise RuntimeError(f"Could not fetch ElevenLabs voices: {e}")


def get_subscription_info(api_key: Optional[str]) -> Dict[str, Any]:
    """
    Fetches user subscription information (including character counts).

    Args:
        api_key: The validated ElevenLabs API key.

    Returns:
        A dictionary containing subscription details. Check ElevenLabs API docs
        for the exact structure of the 'Subscription' object. Returns an empty
        dictionary if the call fails.

    Raises:
        ValueError: If the API key is missing.
        RuntimeError: If fetching subscription info fails.
    """
    if not api_key:
        logger.error("Cannot get subscription info: API key not provided.")
        raise ValueError("API key is required to get subscription info.")

    logger.info("Fetching ElevenLabs subscription info...")
    try:
        client = ElevenLabs(api_key=api_key)
        # Fix: Use 'user' (singular) instead of 'users' (plural)
        sub_info_obj = client.user.get_subscription()

        # Instead of trying to get all attributes automatically,
        # directly extract just the specific attributes we need
        # This avoids issues with special attributes like '__signature__'
        info_dict = {
            'character_count': getattr(sub_info_obj, 'character_count', 0),
            'character_limit': getattr(sub_info_obj, 'character_limit', 0),
            'tier': getattr(sub_info_obj, 'tier', 'unknown'),
            'status': getattr(sub_info_obj, 'status', 'unknown')
        }

        logger.info("ElevenLabs subscription info successfully fetched.")
        return info_dict

    except httpx.HTTPStatusError as http_err:
        logger.error(f"HTTP Error fetching subscription info ({http_err.response.status_code})")
        raise RuntimeError(f"Could not fetch subscription info due to HTTP error: {http_err.response.status_code}")
    except Exception as e:
        logger.error(f"Error fetching subscription info: {e}")
        raise RuntimeError(f"Could not fetch subscription info: {e}")

def _parse_elevenlabs_error_details(response: httpx.Response) -> str:
    """Attempts to extract a user-friendly error message from an ElevenLabs error response."""
    try:
        details_json = response.json().get('detail', response.text)
        if isinstance(details_json, list) and details_json:
            error_info = details_json[0]
            msg = error_info.get('msg', response.text)
            loc = error_info.get('loc', [])
            if loc: return f"{msg} (Field: {' -> '.join(map(str, loc))})"
            return msg
        elif isinstance(details_json, dict):
            return details_json.get('message', response.text)
        else: return response.text
    except Exception: return response.text # Fallback on JSON parsing error

def synthesize_elevenlabs(
    api_key: Optional[str],
    text: str,
    voice_id: str,
    model_id: str,
    output_path: str
) -> Tuple[bool, str]:
    """
    Synthesizes text using ElevenLabs with the provided API key.

    Saves as MP3 and attempts conversion to WAV.

    Args:
        api_key: The validated ElevenLabs API key.
        text: The text to synthesize.
        voice_id: The ID of the voice to use.
        model_id: The ID of the model to use.
        output_path: The desired *WAV* output file path.

    Returns:
        A tuple (success: bool, message: str). Message contains the final output path.
    """
    start_time = time.time()
    # --- Input Validation ---
    if not api_key: return False, "API key is required for ElevenLabs synthesis."
    if not voice_id: return False, "No ElevenLabs voice ID selected."
    if not model_id: return False, "No ElevenLabs model ID selected."
    if not text or not text.strip(): return False, "No text entered for synthesis."

    logger.info(f"Starting ElevenLabs synthesis: Voice={voice_id}, Model={model_id}")
    logger.info(f"Target output path (WAV): {output_path}")

    try:
        # --- Ensure Output Directory Exists ---
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir); logger.info(f"Output directory created: {output_dir}")

        # --- API Call ---
        client = ElevenLabs(api_key=api_key)
        audio_data = client.generate(text=text, voice=Voice(voice_id=voice_id), model=model_id)

        # --- Save as MP3 ---
        output_path_mp3 = output_path.replace(".wav", ".mp3")
        if output_path_mp3 == output_path: output_path_mp3 += ".mp3"
        save(audio=audio_data, filename=output_path_mp3)
        synthesis_duration = time.time() - start_time
        logger.info(f"ElevenLabs synthesis API call completed in {synthesis_duration:.2f}s.")
        logger.warning(f"Audio initially saved as MP3: {output_path_mp3}")

        # --- Attempt Conversion to WAV ---
        try:
            from pydub import AudioSegment
            logger.info(f"Attempting to convert MP3 to WAV: {output_path}")
            sound = AudioSegment.from_mp3(output_path_mp3)
            sound.export(output_path, format="wav"); logger.info(f"Successfully converted to WAV: {output_path}")
            # Optionally remove MP3: # try: os.remove(output_path_mp3)...
            return True, f"Audio successfully synthesized and saved as WAV in {output_path}"
        except ImportError:
            logger.warning("pydub not found. Cannot convert MP3->WAV. File saved as MP3.")
            return True, f"Audio successfully saved (as MP3!) in {output_path_mp3}"
        except Exception as conv_err:
            logger.error(f"Error converting MP3->WAV: {conv_err}", exc_info=True)
            return True, f"Audio successfully saved (as MP3!) in {output_path_mp3}. Conversion to WAV failed."

    except httpx.HTTPStatusError as http_err:
        # --- Handle HTTP errors ---
        status_code = http_err.response.status_code
        error_details = _parse_elevenlabs_error_details(http_err.response)
        user_message = f"HTTP Error ({status_code})"
        if status_code == 401: user_message = "Authentication Error (401): Check API Key."
        elif status_code == 402: user_message = "Quota Error (402): Character limit likely reached."
        elif status_code == 422: user_message = f"Validation Error (422): {error_details}"
        else: user_message = f"{user_message}: {error_details}"
        logger.error(f"ElevenLabs API Error: {user_message}")
        return False, f"ElevenLabs Error: {user_message}"
    except Exception as e:
        # --- Catch-all for other errors ---
        logger.error(f"Unexpected error during ElevenLabs synthesis: {e}", exc_info=True)
        return False, f"ElevenLabs synthesis failed: {e}"

# --- Example Test Block (If needed) ---
# ... (Can be added here, ensuring to call validate_api_key first
#      and pass the validated key to other functions) ...