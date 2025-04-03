# tts_engines/bark_engine.py
import torch
import time
import os
from transformers import AutoProcessor, BarkModel
from scipy.io.wavfile import write as write_wav
import logging
import soundfile as sf # Gebruik soundfile voor mogelijk betere compatibiliteit
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Globale variabelen voor het model en processor (caching)
loaded_processor = None
loaded_model = None
loaded_device = None
# Standaard Bark model, kan later configureerbaar gemaakt worden
DEFAULT_BARK_MODEL_NAME = "suno/bark-small" # of "suno/bark" voor betere kwaliteit (langzamer)

def get_device():
    """Bepaalt of CUDA beschikbaar is."""
    if torch.cuda.is_available():
        return "cuda"
    # MPS (Apple Silicon) ondersteuning is experimenteel en kan problemen geven met Bark
    # elif torch.backends.mps.is_available():
    #     return "mps"
    else:
        return "cpu"

def load_bark_model(model_name=DEFAULT_BARK_MODEL_NAME, force_reload=False):
    """Laadt het Bark model en processor (indien nog niet geladen)."""
    global loaded_processor, loaded_model, loaded_device
    device = get_device()

    # Controleer of model al geladen is op het juiste device
    if loaded_model is not None and loaded_processor is not None and loaded_device == device and not force_reload:
        logging.info(f"Bark model '{model_name}' al geladen op {device}.")
        return loaded_processor, loaded_model

    logging.info(f"Bark gebruikt device: {device}")
    if device == "cpu":
        logging.warning("CUDA niet beschikbaar, Bark synthese zal EXTREEM traag zijn!")
    # elif device == "mps":
    #     logging.warning("Gebruik van MPS (Apple Silicon) met Bark is experimenteel.")

    logging.info(f"Laden Bark processor en model: {model_name}...")
    start_load_time = time.time()
    try:
        processor = AutoProcessor.from_pretrained(model_name)
        # Laad model en verplaats direct naar device
        # Gebruik torch_dtype=torch.float16 voor GPU's die half-precision ondersteunen
        model_kwargs = {}
        if device == "cuda":
            # Controleer of half precision wordt ondersteund
            try:
                 if torch.cuda.get_device_capability()[0] >= 7: # Volta or newer
                      model_kwargs['torch_dtype'] = torch.float16
                      logging.info("Gebruik float16 voor Bark model op compatibele GPU.")
                 else:
                      logging.info("GPU ondersteunt geen float16, gebruik float32.")
            except Exception as gpu_check_err:
                 logging.warning(f"Kon GPU capabilities niet controleren ({gpu_check_err}), gebruik float32.")

        model = BarkModel.from_pretrained(model_name, **model_kwargs).to(device)

        # Optioneel: Enable CPU offload als 'accelerate' geïnstalleerd is en je weinig VRAM hebt
        # try:
        #     from accelerate import cpu_offload
        #     cpu_offload(model, execution_device=device)
        #     logging.info("Accelerate CPU offload ingeschakeld voor Bark.")
        # except ImportError:
        #     pass # Accelerate niet geïnstalleerd

        loaded_processor = processor
        loaded_model = model
        loaded_device = device
        logging.info(f"Bark model geladen in {time.time() - start_load_time:.2f} seconden op {device}.")
        return loaded_processor, loaded_model
    except Exception as e:
        logging.error(f"FOUT bij laden Bark model {model_name}: {e}", exc_info=True)
        loaded_processor = None
        loaded_model = None
        loaded_device = None
        raise

def synthesize_bark(text, voice_preset, output_path, model_name=DEFAULT_BARK_MODEL_NAME):
    """Synthetiseert de gegeven tekst met Bark."""
    start_time = time.time()
    try:
        processor, model = load_bark_model(model_name)
        if not processor or not model:
            raise RuntimeError("Bark model kon niet geladen worden.")

        device = get_device() # Haal het device op waarop het model geladen is

        logging.info(f"Start Bark synthese met voice preset: {voice_preset}")
        logging.info(f"Input tekst (eerste 100 chars): {text[:100]}...")

        # Bereid inputs voor - voice_preset is hier de identifier zoals 'v2/en_speaker_6'
        inputs = processor(text, voice_preset=voice_preset, return_tensors="pt")

        # Verplaats inputs naar hetzelfde device als het model
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # Genereer audio
        with torch.no_grad(): # Belangrijk voor inference
            generation_output = model.generate(**inputs)

        # Haal audio array op (moet mogelijk naar CPU verplaatst worden)
        audio_array_raw = generation_output.cpu().numpy().squeeze() # Eerst ruwe data ophalen

        # --- FIX: CONVERTEER NAAR float32 ALS NODIG ---
        if audio_array_raw.dtype == np.float16:
            logging.info(f"Converteren Bark audio van {audio_array_raw.dtype} naar float32 voor opslag.")
            audio_array = audio_array_raw.astype(np.float32)
        else:
            # Als het al een ander type is (bv. float32 op CPU), gebruik het direct
            audio_array = audio_array_raw
        # --- EINDE FIX ---

        # Haal sample rate op uit model config
        sample_rate = model.generation_config.sample_rate

        # Log de uiteindelijke vorm en type voor de zekerheid
        logging.info(f"Bark synthese voltooid. Audio array shape: {audio_array.shape}, dtype: {audio_array.dtype}")

        # Opslaan als WAV met soundfile
        logging.info(f"Opslaan als WAV: {output_path} met sample rate {sample_rate}")
        sf.write(output_path, audio_array, sample_rate) # Gebruik de (mogelijk geconverteerde) array

        end_time = time.time()
        logging.info(f"Bark synthese en opslaan voltooid in {end_time - start_time:.2f} seconden.")
        return True, f"Audio succesvol opgeslagen in {output_path}"

    except Exception as e:
        # Als logging.error met exc_info=True een TypeError geeft,
        # formatteer de traceback handmatig.
        import traceback  # Importeer traceback hier (of bovenaan het bestand)
        error_details = f"FOUT tijdens Bark synthese: {e}\n{traceback.format_exc()}"
        logging.error(error_details)  # Log de geformatteerde string        return False, f"Bark synthese mislukt: {e}"

# Voorbeeld van direct testen (optioneel)
if __name__ == '__main__':
    print("Testen Bark Engine...")
    # Bark vereist soms langere context of specifieke prompts voor goede resultaten
    test_text = "Hello, my name is Suno. And, uh — and I like pizza. [laughs]"
    # test_text = "Hallo, mijn naam is Bark. Ik spreek ook een beetje Nederlands." # Probeer Nederlandse preset
    test_preset = "v2/en_speaker_6" # Populaire Engelse stem
    # test_preset = "v2/nl_speaker_1" # Experimentele Nederlandse stem (kwaliteit kan variëren)
    test_output = "../audio_output/bark_test.wav"

    os.makedirs("../audio_output", exist_ok=True)

    print(f"Gebruik preset: {test_preset}")
    success, message = synthesize_bark(test_text, test_preset, test_output)
    print(message)

    # Test met andere preset
    # test_preset_2 = "v2/en_speaker_9"
    # test_output_2 = "../audio_output/bark_test_2.wav"
    # print(f"\nTesten met preset: {test_preset_2}")
    # success, message = synthesize_bark(test_text, test_preset_2, test_output_2)
    # print(message)