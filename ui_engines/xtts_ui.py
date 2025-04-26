# ui_engines/xtts_ui.py
import tkinter as tk
from tkinter import ttk
import os

def create_xtts_ui(parent, speaker_wav_var, language_var, browse_callback, default_speaker_dir):
    """
    Creates the parameter frame specific to the XTTSv2 engine.

    Args:
        parent: The parent widget (ttk.Frame) to place this UI in.
        speaker_wav_var: tk.StringVar for the speaker WAV path.
        language_var: tk.StringVar for the selected language.
        browse_callback: The function to call for the browse button.
        default_speaker_dir: Default directory for speaker WAVs.

    Returns:
        The created ttk.LabelFrame containing the XTTS parameters.
    """
    xtts_frame = ttk.LabelFrame(parent, text="XTTSv2 Parameters", padding="10")

    # Speaker WAV Selection
    ttk.Label(xtts_frame, text="Speaker WAV (optional):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
    ttk.Entry(xtts_frame, textvariable=speaker_wav_var, width=40).grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
    ttk.Button(xtts_frame, text="Browse...", command=lambda: browse_callback(speaker_wav_var, "Select Speaker WAV", [("WAV files", "*.wav")], default_speaker_dir)).grid(row=0, column=2, padx=5, pady=5)

    # Language Selection
    ttk.Label(xtts_frame, text="Language:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
    # Ensure these language codes are supported by your specific XTTS model version
    xtts_lang_options = ["nl", "en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "zh-cn", "ja", "ko"]
    lang_menu = ttk.Combobox(xtts_frame, textvariable=language_var, values=xtts_lang_options, state="readonly", width=5)
    lang_menu.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
    lang_menu.set(language_var.get()) # Set initial value from the variable

    # Allow the entry field to expand horizontally
    xtts_frame.grid_columnconfigure(1, weight=1)

    return xtts_frame