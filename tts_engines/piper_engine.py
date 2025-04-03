# tts_engines/piper_engine.py
import time
import os
import wave
from piper.voice import PiperVoice
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Globale cache voor geladen Piper stemmen
loaded_voices = {} # key = onnx_path, value = voice object

def load_piper_model(onnx_path, json_path, force_reload=False):
    """Laadt een Piper stem model (indien nog niet geladen)."""
    global loaded_voices

    if not onnx_path or not json_path:
        raise ValueError("Zowel ONNX als JSON paden zijn vereist voor Piper.")

    cache_key = onnx_path # Gebruik onnx pad als unieke identifier

    if cache_key in loaded_voices and not force_reload:
        logging.info(f"Piper model {onnx_path} al geladen.")
        return loaded_voices[cache_key]

    if not os.path.exists(onnx_path):
        raise FileNotFoundError(f"Piper model ONNX bestand niet gevonden: {onnx_path}")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Piper model JSON bestand niet gevonden: {json_path}")

    logging.info(f"Laden Piper model: {onnx_path}")
    start_load_time = time.time()
    try:
        voice = PiperVoice.load(onnx_path, config_path=json_path)
        logging.info(f"Piper model geladen in {time.time() - start_load_time:.2f} seconden.")

        # Verifieer nodige config eigenschappen
        if not hasattr(voice, 'config') or not hasattr(voice.config, 'sample_rate'):
            raise AttributeError("voice.config of voice.config.sample_rate ontbreekt!")

        loaded_voices[cache_key] = voice
        return voice
    except Exception as e:
        logging.error(f"FOUT bij laden Piper model {onnx_path}: {e}", exc_info=True)
        if cache_key in loaded_voices:
            del loaded_voices[cache_key] # Verwijder uit cache bij fout
        raise

def synthesize_piper(text, model_onnx_path, model_json_path, output_path):
    """Synthetiseert de gegeven tekst met Piper."""
    start_time = time.time()
    wav_file = None # Initialiseer buiten try block

    try:
        # Laad (of haal uit cache) het Piper model
        voice = load_piper_model(model_onnx_path, model_json_path)
        if not voice:
             raise RuntimeError("Piper model kon niet geladen worden.")

        # Haal parameters uit het geladen model config
        sample_rate = voice.config.sample_rate
        sample_width = getattr(voice.config, 'sample_width', 2) # Default 2 (16-bit)
        num_channels = getattr(voice.config, 'num_channels', 1) # Default 1 (mono)

        logging.info(f"Start Piper synthese voor output: {output_path}")
        logging.info(f"Piper WAV params: Rate={sample_rate}, Width={sample_width}, Channels={num_channels}")

        # Open WAV bestand om te schrijven
        wav_file = wave.open(output_path, "wb")
        wav_file.setnchannels(num_channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)

        # Synthetiseer direct naar het WAV bestand object
        voice.synthesize(text, wav_file=wav_file)

        end_time = time.time()
        logging.info(f"Piper synthese voltooid in {end_time - start_time:.2f} seconden.")
        return True, f"Audio succesvol opgeslagen in {output_path}"

    except Exception as e:
        logging.error(f"FOUT tijdens Piper synthese: {e}", exc_info=True)
        return False, f"Piper synthese mislukt: {e}"
    finally:
        # Zorg ervoor dat het WAV bestand altijd gesloten wordt
        if wav_file:
            wav_file.close()
            logging.info(f"WAV bestand gesloten: {output_path}")


# Voorbeeld van direct testen (optioneel)
if __name__ == '__main__':
    print("Testen Piper Engine...")
    test_text = "Hello world, this is a test from the Piper model."
    test_onnx = "../models/piper/en_US-lessac-medium.onnx" # Pas pad aan
    test_json = "../models/piper/en_US-lessac-medium.onnx.json" # Pas pad aan
    test_output = "../audio_output/piper_test.wav"

    # Maak mappen indien nodig
    os.makedirs("../models/piper", exist_ok=True)
    os.makedirs("../audio_output", exist_ok=True)

    # Basis controle of de test model bestanden bestaan
    if not os.path.exists(test_onnx) or not os.path.exists(test_json):
         print(f"WAARSCHUWING: Piper testmodel bestanden niet gevonden op {test_onnx} / {test_json}. Synthese zal falen.")
         print("Download een Piper model (bv. van https://huggingface.co/rhasspy/piper-voices/tree/main) en plaats het in models/piper/")
    else:
        success, message = synthesize_piper(test_text, test_onnx, test_json, test_output)
        print(message)