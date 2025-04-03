# tts_engines/xtts_engine.py
import torch
from TTS.api import TTS
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig
from TTS.config.shared_configs import BaseDatasetConfig
from TTS.tts.models.xtts import XttsArgs
import time
import os
import logging # Gebruik logging voor betere feedback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Globale variabele om het model vast te houden (caching)
loaded_model = None
loaded_device = None

# --- Configuratie (kan later uit GUI komen) ---
MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"

def get_device():
    """Bepaalt of CUDA beschikbaar is."""
    return "cuda" if torch.cuda.is_available() else "cpu"

def load_xtts_model(force_reload=False):
    """Laadt het XTTS model (indien nog niet geladen) en verplaatst naar device."""
    global loaded_model, loaded_device
    device = get_device()

    if loaded_model is not None and loaded_device == device and not force_reload:
        logging.info(f"XTTS model al geladen op {device}.")
        return loaded_model

    logging.info(f"XTTS gebruikt device: {device}")
    if device == "cpu":
        logging.warning("CUDA niet beschikbaar, XTTS synthese zal erg traag zijn!")

    logging.info(f"Laden XTTS model: {MODEL_NAME}...")
    try:
        # Gebruik safe_globals context voor PyTorch 2.6+ compatibiliteit
        with torch.serialization.safe_globals([XttsConfig, XttsAudioConfig, BaseDatasetConfig, XttsArgs]):
            tts = TTS(MODEL_NAME) # Laadt initieel op CPU

        logging.info("Verplaatsen XTTS model naar device...")
        tts.to(device)
        loaded_model = tts
        loaded_device = device
        logging.info(f"XTTS model succesvol geladen en verplaatst naar {device}.")
        return loaded_model
    except Exception as e:
        logging.error(f"FOUT bij laden/verplaatsen XTTS model: {e}", exc_info=True)
        # Optioneel: probeer TORCH_WEIGHTS_ONLY=0 environment variabele
        logging.error("Controleer modelnaam, dependencies, of probeer 'export TORCH_WEIGHTS_ONLY=0' (Linux/macOS) or 'set TORCH_WEIGHTS_ONLY=0' (Windows) als dit aanhoudt.")
        loaded_model = None # Reset bij fout
        loaded_device = None
        raise  # Geef de fout door aan de oproeper

def synthesize_xtts(text, speaker_wav_path, language, output_path):
    """Synthetiseert de gegeven tekst met XTTSv2."""
    start_time = time.time()
    try:
        tts_model = load_xtts_model() # Zorg ervoor dat het model geladen is
        if tts_model is None:
            raise RuntimeError("XTTS model kon niet worden geladen.")

        # Valideer speaker_wav pad als het opgegeven is
        valid_speaker_wav = None
        if speaker_wav_path and os.path.exists(speaker_wav_path):
            valid_speaker_wav = speaker_wav_path
            logging.info(f"Gebruik speaker WAV: {speaker_wav_path}")
        elif speaker_wav_path:
            logging.warning(f"Speaker WAV bestand niet gevonden: {speaker_wav_path}. Gebruik standaard stem.")
        else:
            logging.info("Geen speaker WAV opgegeven, gebruik standaard stem.")

        logging.info(f"Start XTTS synthese voor output: {output_path}")
        # Opmerking: Deze functie splitst de tekst niet; dat moet eventueel
        # in de GUI of een aparte functie gebeuren voor lange teksten.
        tts_model.tts_to_file(
            text=text,
            speaker_wav=valid_speaker_wav,
            language=language,
            file_path=output_path,
            # split_sentences=True # Kan helpen bij stabiliteit, maar ook pauzes toevoegen
        )

        end_time = time.time()
        logging.info(f"XTTS synthese voltooid in {end_time - start_time:.2f} seconden.")
        return True, f"Audio succesvol opgeslagen in {output_path}"

    except Exception as e:
        logging.error(f"FOUT tijdens XTTS synthese: {e}", exc_info=True)
        return False, f"XTTS synthese mislukt: {e}"

# Voorbeeld van direct testen (optioneel)
if __name__ == '__main__':
    print("Testen XTTS Engine...")
    test_text = "Hallo wereld, dit is een test van het XTTSv2 model."
    test_output = "../audio_output/xtts_test.wav" # Pas pad aan indien nodig
    test_speaker_wav = "../speaker_samples/Ik.wav" # Pas pad aan indien nodig, of None

    os.makedirs("../audio_output", exist_ok=True) # Maak map als deze niet bestaat

    if test_speaker_wav and not os.path.exists(test_speaker_wav):
         print(f"WAARSCHUWING: Test speaker wav {test_speaker_wav} niet gevonden, gebruik standaard.")
         test_speaker_wav = None

    success, message = synthesize_xtts(test_text, test_speaker_wav, "nl", test_output)
    print(message)