## Gebruik

1.  **Start de applicatie:**
    ```bash
    python app.py
    ```
    (Zorg ervoor dat je in de `MultiTTSApp` directory bent of pas de paden in de code aan).
2.  **Selecteer TTS Engine:** Kies "XTTSv2", "Piper", of "Bark" uit de dropdown.
3.  **Configureer Parameters:** De interface toont de relevante opties voor het gekozen model:
    *   **XTTSv2:** Geef optioneel het pad naar een speaker WAV-bestand op en selecteer de taal.
    *   **Piper:** Geef de paden naar de `.onnx` en `.json` bestanden van het model.
    *   **Bark:** Selecteer een `voice_preset` uit de lijst (bv. `v2/en_speaker_6`).
4.  **Voer Tekst In:** Plak of typ de tekst die je wilt omzetten in het grote tekstvak.
5.  **Kies Output Bestand:** Klik op "Bladeren..." om een locatie en bestandsnaam te kiezen voor het uitvoer WAV-bestand (standaard in `audio_output/output.wav`).
6.  **Start Synthese:** Klik op de "Start Synthese" knop. De statusbalk onderaan geeft de voortgang aan (laden model, synthetiseren, etc.). De knop wordt uitgeschakeld tijdens het proces.
7.  **Resultaat:** Na voltooiing verschijnt een berichtvenster met succes of falen. Het gegenereerde audiobestand staat op de opgegeven locatie.

## Aandachtspunten

*   **Prestaties:** Synthese, vooral met Bark en XTTSv2 (zeker op CPU), kan veel rekenkracht en tijd vergen. Een GPU met voldoende VRAM wordt sterk aanbevolen.
*   **Bark Kwaliteit/Stabiliteit:** Bark kan soms onverwachte geluiden, stiltes of hallucinaties produceren, vooral bij langere teksten of complexe zinnen. De kwaliteit van niet-Engelse stemmen kan variëren. Voor langere teksten is het aan te raden deze op te splitsen.
*   **XTTSv2 Chunking:** De huidige XTTS implementatie in `xtts_engine.py` synthetiseert de volledige ingevoerde tekst in één keer. Voor zeer lange teksten (zoals audioboeken) is het beter om de tekst op te splitsen in kleinere stukken (bv. per paragraaf) en deze apart te synthetiseren en eventueel achteraf samen te voegen (zoals in je originele XTTS script). Dit kan als toekomstige verbetering aan de GUI worden toegevoegd.
*   **Foutmeldingen:** Controleer de console/terminal output voor meer gedetailleerde logberichten en fouten als er iets misgaat.