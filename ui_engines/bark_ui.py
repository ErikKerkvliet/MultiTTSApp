# ui_engines/bark_ui.py
import tkinter as tk
from tkinter import ttk
import logging

def create_bark_ui(parent, voice_preset_var, bark_voices_list):
    """
    Creates the parameter frame specific to the Bark engine.

    Args:
        parent: The parent widget (ttk.Frame) to place this UI in.
        voice_preset_var: tk.StringVar for the selected voice preset.
        bark_voices_list: List of available Bark voice presets.

    Returns:
        The created ttk.LabelFrame containing the Bark parameters.
    """
    bark_frame = ttk.LabelFrame(parent, text="Bark Parameters", padding="10")

    ttk.Label(bark_frame, text="Voice Preset:").pack(side=tk.LEFT, padx=5, pady=5)
    voice_menu = ttk.Combobox(bark_frame, textvariable=voice_preset_var, values=bark_voices_list, state="readonly", width=25)
    voice_menu.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

    # Set a default voice preset safely
    if bark_voices_list:
        default_preset = "v2/en_speaker_6" # A common English preset
        voice_preset_var.set(default_preset if default_preset in bark_voices_list else bark_voices_list[0])
    else:
        logging.warning("[Bark UI] BARK_VOICES list is empty! Cannot set default.")

    return bark_frame