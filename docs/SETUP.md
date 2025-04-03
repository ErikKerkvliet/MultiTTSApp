## Setup

1.  **Python:** Zorg ervoor dat je Python 3.8 of hoger hebt geïnstalleerd.
2.  **Dependencies:** Installeer de benodigde Python packages:
    ```bash
    pip install -r requirements.txt
    ```
3.  **CUDA (Optioneel, voor GPU):** Als je een NVIDIA GPU hebt en deze wilt gebruiken voor snellere synthese (vooral aanbevolen voor XTTSv2 en Bark), installeer dan PyTorch met CUDA support. Volg de instructies op [pytorch.org](https://pytorch.org/). Zorg er ook voor dat je de juiste NVIDIA drivers en CUDA Toolkit hebt geïnstalleerd.
4.  **Modellen:**
    *   **XTTSv2:** Wordt meestal automatisch gedownload door de `TTS` library bij het eerste gebruik en opgeslagen in een cache map (`~/.local/share/tts/` op Linux, vergelijkbaar op andere OS'en).
    *   **Piper:** Download de gewenste `.onnx` en `.onnx.json` modelbestanden (bv. van [Hugging Face - Piper Voices](https://huggingface.co/rhasspy/piper-voices/tree/main)). Plaats ze in de `models/piper/` map (of selecteer ze via de "Bladeren..." knop in de app).
    *   **Bark:** Wordt automatisch gedownload en gecached door de `transformers` library bij het eerste gebruik (meestal in `~/.cache/huggingface/hub/`).
5.  **Speaker Samples (Optioneel, voor XTTS):** Als je voice cloning met XTTSv2 wilt gebruiken, plaats dan een of meer schone WAV-audiobestanden (ongeveer 15-30 seconden spraak) in de `speaker_samples/` map. Selecteer het gewenste bestand in de app.
