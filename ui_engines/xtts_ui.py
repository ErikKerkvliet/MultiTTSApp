# ui_engines/xtts_ui.py - ENHANCED VERSION
import tkinter as tk
from tkinter import ttk
import os
import logging

# Import the engine to get available models
try:
    from tts_engines import xtts_engine

    XTTS_ENGINE_AVAILABLE = True
except ImportError:
    XTTS_ENGINE_AVAILABLE = False
    logging.warning("XTTS engine not available for UI model list")
    xtts_engine = None


def create_xtts_ui(parent, speaker_wav_var, language_var, browse_callback, default_speaker_dir, model_var=None):
    """
    Creates the parameter frame specific to the XTTSv2 engine with expanded model support.

    Args:
        parent: The parent widget (ttk.Frame) to place this UI in.
        speaker_wav_var: tk.StringVar for the speaker WAV path.
        language_var: tk.StringVar for the selected language.
        browse_callback: The function to call for the browse button.
        default_speaker_dir: Default directory for speaker WAVs.
        model_var: tk.StringVar for the selected model (optional).

    Returns:
        The created ttk.LabelFrame containing the XTTS parameters.
    """
    xtts_frame = ttk.LabelFrame(parent, text="TTS Engine Parameters", padding="10")

    current_row = 0

    # Model Selection with Categories
    if model_var is not None and hasattr(model_var, 'set') and XTTS_ENGINE_AVAILABLE:
        ttk.Label(xtts_frame, text="Model:").grid(row=current_row, column=0, padx=5, pady=5, sticky=tk.W)

        try:
            # Get models organized by type
            models_by_type = xtts_engine.get_models_by_type()
            all_models = xtts_engine.get_available_models()

            # Create a list with category separators
            model_options = []
            model_mapping = {}

            # Define display order for categories
            category_order = ["xtts", "standard", "multilingual", "multispeaker", "fast", "other"]
            category_names = {
                "xtts": "🎯 XTTS Models (Voice Cloning)",
                "standard": "🔊 Standard Models",
                "multilingual": "🌍 Multilingual Models",
                "multispeaker": "👥 Multi-Speaker Models",
                "fast": "⚡ Fast Models",
                "other": "📦 Other Models"
            }

            for category in category_order:
                if category in models_by_type:
                    # Add category header (disabled option)
                    category_header = f"──── {category_names.get(category, category.upper())} ────"
                    model_options.append(category_header)

                    # Add models in this category
                    for model_key, model_info in models_by_type[category]:
                        display_name = f"   {model_info['name']}"
                        model_options.append(display_name)
                        model_mapping[display_name] = model_key

            if model_options:
                # Create custom combobox that handles categories
                model_combo = ttk.Combobox(
                    xtts_frame,
                    textvariable=model_var,
                    values=model_options,
                    state="readonly",
                    width=40
                )
                model_combo.grid(row=current_row, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)

                # Custom validation to prevent selecting category headers
                def validate_selection(event=None):
                    selected = model_combo.get()
                    if selected.startswith("────") or not selected.strip():
                        # Reset to previous valid selection or default
                        default_key = "xtts_v2" if "xtts_v2" in all_models else list(all_models.keys())[0]
                        default_display = next(
                            (display for display, key in model_mapping.items() if key == default_key), None)
                        if default_display:
                            model_var.set(default_display)
                        return False
                    return True

                model_combo.bind("<<ComboboxSelected>>", lambda e: [validate_selection(), update_model_info()])

                # Store mappings and references
                model_combo._key_mapping = model_mapping
                model_combo._all_models = all_models

                # Set default selection
                default_key = "xtts_v2" if "xtts_v2" in all_models else list(all_models.keys())[0]
                default_display = next((display for display, key in model_mapping.items() if key == default_key), None)
                if default_display:
                    model_var.set(default_display)

                # Create info display
                info_frame = ttk.Frame(xtts_frame)
                info_frame.grid(row=current_row + 1, column=1, columnspan=2, padx=5, pady=(0, 5), sticky=tk.EW)

                model_info_label = ttk.Label(info_frame, text="", foreground="gray", font=("TkDefaultFont", 8))
                model_info_label.pack(fill=tk.X)

                def update_model_info(event=None):
                    selected_display = model_combo.get()
                    selected_key = model_mapping.get(selected_display)
                    if selected_key and selected_key in all_models:
                        model_info = all_models[selected_key]
                        info_text = f"{model_info['description']}\nLanguages: {', '.join(model_info['languages'][:6])}{'...' if len(model_info['languages']) > 6 else ''}"
                        model_info_label.config(text=info_text)
                        # Update language options
                        update_language_options(selected_key)
                    else:
                        model_info_label.config(text="")

                # Store references
                xtts_frame._model_combo = model_combo
                xtts_frame._model_info_label = model_info_label
                xtts_frame._all_models = all_models
                xtts_frame._model_mapping = model_mapping

                current_row += 1  # Skip the info row

            else:
                # Fallback if no models available
                ttk.Label(xtts_frame, text="Default TTS Model", foreground="gray").grid(row=current_row, column=1,
                                                                                        padx=5, pady=5, sticky=tk.W)
                model_var.set("XTTSv2 (Multilingual)")

        except Exception as e:
            logging.error(f"Error setting up TTS model selection: {e}")
            # Fallback UI
            ttk.Label(xtts_frame, text="Default TTS Model", foreground="gray").grid(row=current_row, column=1, padx=5,
                                                                                    pady=5, sticky=tk.W)
            if hasattr(model_var, 'set'):
                model_var.set("XTTSv2 (Multilingual)")

        current_row += 1

    # Language Selection
    current_row += 1
    ttk.Label(xtts_frame, text="Language:").grid(row=current_row, column=0, padx=5, pady=5, sticky=tk.W)

    # Create language combobox
    language_combo = ttk.Combobox(xtts_frame, textvariable=language_var, state="readonly", width=25)
    language_combo.grid(row=current_row, column=1, padx=5, pady=5, sticky=tk.EW)

    # Store reference for updates
    xtts_frame._language_combo = language_combo

    def update_language_options(model_key):
        """Update language options based on selected model."""
        try:
            if XTTS_ENGINE_AVAILABLE and xtts_engine:
                languages = xtts_engine.get_model_languages(model_key)
                if languages:
                    # Create language display with codes and names
                    language_options = []
                    language_names = {
                        "en": "English", "es": "Spanish", "fr": "French", "de": "German",
                        "it": "Italian", "pt": "Portuguese", "pl": "Polish", "tr": "Turkish",
                        "ru": "Russian", "nl": "Dutch", "cs": "Czech", "ar": "Arabic",
                        "zh-cn": "Chinese", "ja": "Japanese", "hu": "Hungarian",
                        "ko": "Korean", "hi": "Hindi"
                    }

                    for lang_code in languages:
                        lang_name = language_names.get(lang_code, lang_code.upper())
                        language_options.append(f"{lang_name} ({lang_code})")

                    language_combo.config(values=language_options)

                    # Set default language (Dutch if available, English second choice, otherwise first)
                    if "nl" in languages:
                        default_lang = "Dutch (nl)"
                    elif "en" in languages:
                        default_lang = "English (en)"
                    else:
                        default_lang = language_options[0]
                    language_var.set(default_lang)
                else:
                    # Fallback if no languages found
                    fallback_languages = ["English (en)", "Dutch (nl)", "Spanish (es)", "French (fr)"]
                    language_combo.config(values=fallback_languages)
                    language_var.set("English (en)")
            else:
                # Fallback if engine not available
                fallback_languages = ["English (en)", "Dutch (nl)", "Spanish (es)", "French (fr)", "German (de)",
                                      "Italian (it)"]
                language_combo.config(values=fallback_languages)
                language_var.set("English (en)")
        except Exception as e:
            logging.error(f"Error updating language options: {e}")
            # Final fallback
            fallback_languages = ["English (en)", "Dutch (nl)", "Spanish (es)", "French (fr)"]
            language_combo.config(values=fallback_languages)
            language_var.set("English (en)")

    # Store the update function
    xtts_frame._update_language_options = update_language_options

    # Initialize language options
    try:
        if hasattr(xtts_frame, '_model_mapping') and model_var:
            # Get initial model
            initial_display = model_var.get()
            initial_key = xtts_frame._model_mapping.get(initial_display, "xtts_v2")
            update_language_options(initial_key)
        else:
            update_language_options("xtts_v2")
    except Exception as e:
        logging.error(f"Error during initial language setup: {e}")
        update_language_options("xtts_v2")

    current_row += 1

    # Speaker WAV Selection
    ttk.Label(xtts_frame, text="Speaker WAV (optional):").grid(row=current_row, column=0, padx=5, pady=5, sticky=tk.W)
    ttk.Entry(xtts_frame, textvariable=speaker_wav_var, width=40).grid(row=current_row, column=1, padx=5, pady=5,
                                                                       sticky=tk.EW)
    ttk.Button(xtts_frame, text="Browse...",
               command=lambda: browse_callback(speaker_wav_var, "Select Speaker WAV", [("WAV files", "*.wav")],
                                               default_speaker_dir)).grid(row=current_row, column=2, padx=5, pady=5)

    # Model capability hint
    current_row += 1
    capability_label = ttk.Label(xtts_frame, text="", foreground="blue", font=("TkDefaultFont", 8))
    capability_label.grid(row=current_row, column=1, columnspan=2, padx=5, pady=(0, 5), sticky=tk.W)
    xtts_frame._capability_label = capability_label

    def update_capability_hint():
        """Update the capability hint based on selected model."""
        try:
            if hasattr(xtts_frame, '_model_mapping') and model_var:
                selected_display = model_var.get()
                selected_key = xtts_frame._model_mapping.get(selected_display)
                if selected_key and hasattr(xtts_frame, '_all_models'):
                    model_info = xtts_frame._all_models[selected_key]
                    model_type = model_info.get("type", "")

                    if model_type == "xtts":
                        capability_label.config(text="💡 This model supports voice cloning with speaker WAV files")
                    elif model_type == "multispeaker":
                        capability_label.config(text="💡 This model has multiple built-in speakers")
                    elif model_type == "fast":
                        capability_label.config(text="⚡ This model is optimized for speed")
                    else:
                        capability_label.config(text="")
        except:
            capability_label.config(text="")

    # Bind capability update to model selection
    if hasattr(xtts_frame, '_model_combo'):
        original_update = xtts_frame._model_combo.bind("<<ComboboxSelected>>")

        def combined_update(event=None):
            if callable(original_update):
                original_update(event)
            update_capability_hint()

        xtts_frame._model_combo.bind("<<ComboboxSelected>>", combined_update)

    # Initial capability update
    update_capability_hint()

    # Allow the entry field to expand horizontally
    xtts_frame.grid_columnconfigure(1, weight=1)

    return xtts_frame


def get_selected_model_key(model_var, xtts_frame=None):
    """Helper function to get the actual model key from the display name."""
    if not model_var or not hasattr(model_var, 'get'):
        return "xtts_v2"

    try:
        selected_display = model_var.get()

        # Try to get mapping from the frame
        if xtts_frame and hasattr(xtts_frame, '_model_mapping'):
            return xtts_frame._model_mapping.get(selected_display, "xtts_v2")

        # Fallback: try engine directly
        if XTTS_ENGINE_AVAILABLE and xtts_engine:
            available_models = xtts_engine.get_available_models()
            for key, info in available_models.items():
                if info['name'] in selected_display:
                    return key

        return "xtts_v2"
    except Exception as e:
        logging.error(f"Error getting selected model key: {e}")
        return "xtts_v2"


def get_selected_language_code(language_var):
    """Helper function to extract language code from the display string."""
    try:
        if not language_var or not hasattr(language_var, 'get'):
            return "en"

        language_display = language_var.get()
        if "(" in language_display and ")" in language_display:
            start = language_display.rfind("(") + 1
            end = language_display.rfind(")")
            return language_display[start:end]

        return "en"
    except Exception as e:
        logging.error(f"Error getting selected language code: {e}")
        return "en"