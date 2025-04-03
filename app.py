# app.py
"""
Main application file for the Multi TTS Synthesizer GUI.

Uses Tkinter for the graphical interface and integrates multiple Text-to-Speech
engines (XTTSv2, Piper, Bark, ElevenLabs). Includes audio playback controls.
"""

# --- Standard Library Imports ---
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import logging
import time
import glob
import traceback
from typing import Optional, List, Tuple

# --- Third-Party Imports ---
import pygame         # For audio playback
import soundfile as sf # For reading audio file duration (WAV)
from dotenv import load_dotenv # For loading API keys from .env file

# --- Local Imports ---
# Import engine functions from the tts_engines package
try:
    from tts_engines import xtts_engine, piper_engine, bark_engine, elevenlabs_engine
except ImportError as e:
    # Provide a more detailed error message if imports fail
    print(f"ERROR: Could not import TTS engines. Error:\n{traceback.format_exc()}")
    print("Ensure the 'tts_engines' directory exists alongside app.py and")
    print("all required dependencies (TTS, piper-tts, transformers, elevenlabs, etc.) are installed.")
    exit(1) # Exit if engines can't be loaded

# --- Load Environment Variables ---
# Load variables from a .env file into os.environ BEFORE accessing them
load_dotenv()
# --------------------------------

# --- Basic Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [GUI] %(message)s'
)

# --- Default Paths and Constants ---
DEFAULT_OUTPUT_DIR = "audio_output"      # Directory for generated audio files
DEFAULT_SPEAKER_DIR = "speaker_samples"  # Directory for XTTS speaker WAV files
DEFAULT_PIPER_MODEL_DIR = "models/piper" # Default location for Piper models
# Default Bark voice presets (can be extended)
DEFAULT_BARK_VOICES = [
    "v2/en_speaker_0", "v2/en_speaker_1", "v2/en_speaker_2", "v2/en_speaker_3",
    "v2/en_speaker_4", "v2/en_speaker_5", "v2/en_speaker_6", "v2/en_speaker_7",
    "v2/en_speaker_8", "v2/en_speaker_9", "v2/de_speaker_1", "v2/es_speaker_1",
    "v2/fr_speaker_1", "v2/it_speaker_1", "v2/ja_speaker_1", "v2/ko_speaker_1",
    "v2/pl_speaker_1", "v2/pt_speaker_1", "v2/ru_speaker_1", "v2/tr_speaker_1",
    "v2/zh_speaker_1", "v2/nl_speaker_0", "v2/nl_speaker_1",
]
# Get ElevenLabs models list from the engine module
ELEVENLABS_MODELS = elevenlabs_engine.ELEVENLABS_MODELS


# --- Main Application Class ---
class TTSApp(tk.Tk):
    """
    Main application class for the Multi TTS Synthesizer.

    Inherits from tk.Tk to create the main window.
    Manages the GUI layout, state, and interaction with TTS engines.
    """

    # --- Method Definitions First (for correct binding/command references) ---

    # --- UI Element Creation Functions (Parameter Frames) ---
    def _create_xtts_params(self, parent):
        """Creates the parameter frame specific to the XTTSv2 engine."""
        self.xtts_frame = ttk.LabelFrame(parent, text="XTTSv2 Parameters", padding="10")

        # Speaker WAV Selection
        ttk.Label(self.xtts_frame, text="Speaker WAV (optional):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(self.xtts_frame, textvariable=self.xtts_speaker_wav, width=40).grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(self.xtts_frame, text="Browse...", command=lambda: self.browse_file(self.xtts_speaker_wav, "Select Speaker WAV", [("WAV files", "*.wav")], DEFAULT_SPEAKER_DIR)).grid(row=0, column=2, padx=5, pady=5)

        # Language Selection
        ttk.Label(self.xtts_frame, text="Language:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        # Ensure these language codes are supported by your specific XTTS model version
        xtts_lang_options = ["nl", "en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "zh-cn", "ja", "ko"]
        lang_menu = ttk.Combobox(self.xtts_frame, textvariable=self.xtts_language, values=xtts_lang_options, state="readonly", width=5)
        lang_menu.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        lang_menu.set(self.xtts_language.get()) # Set initial value from the variable

        # Allow the entry field to expand horizontally
        self.xtts_frame.grid_columnconfigure(1, weight=1)

    def _create_piper_params(self, parent):
        """Creates the parameter frame specific to the Piper engine."""
        self.piper_frame = ttk.LabelFrame(parent, text="Piper Parameters", padding="10")

        # ONNX Model Path
        ttk.Label(self.piper_frame, text="Model (.onnx):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(self.piper_frame, textvariable=self.piper_onnx_path, width=40).grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(self.piper_frame, text="Browse...", command=lambda: self.browse_file(self.piper_onnx_path, "Select Piper ONNX Model", [("ONNX files", "*.onnx")], DEFAULT_PIPER_MODEL_DIR)).grid(row=0, column=2, padx=5, pady=5)

        # JSON Config Path
        ttk.Label(self.piper_frame, text="Config (.json):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(self.piper_frame, textvariable=self.piper_json_path, width=40).grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(self.piper_frame, text="Browse...", command=lambda: self.browse_file(self.piper_json_path, "Select Piper JSON Config", [("JSON files", "*.json")], DEFAULT_PIPER_MODEL_DIR)).grid(row=1, column=2, padx=5, pady=5)

        # Allow the entry fields to expand
        self.piper_frame.grid_columnconfigure(1, weight=1)

        # Set default paths for convenience if the files exist
        default_onnx = os.path.join(DEFAULT_PIPER_MODEL_DIR, "en_US-lessac-medium.onnx")
        default_json = os.path.join(DEFAULT_PIPER_MODEL_DIR, "en_US-lessac-medium.onnx.json")
        if os.path.exists(default_onnx): self.piper_onnx_path.set(default_onnx)
        if os.path.exists(default_json): self.piper_json_path.set(default_json)

    def _create_bark_params(self, parent):
        """Creates the parameter frame specific to the Bark engine."""
        self.bark_frame = ttk.LabelFrame(parent, text="Bark Parameters", padding="10")

        ttk.Label(self.bark_frame, text="Voice Preset:").pack(side=tk.LEFT, padx=5, pady=5)
        voice_menu = ttk.Combobox(self.bark_frame, textvariable=self.bark_voice_preset, values=DEFAULT_BARK_VOICES, state="readonly", width=25)
        voice_menu.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

        # Set a default voice preset safely
        if DEFAULT_BARK_VOICES:
            default_preset = "v2/en_speaker_6" # A common English preset
            self.bark_voice_preset.set(default_preset if default_preset in DEFAULT_BARK_VOICES else DEFAULT_BARK_VOICES[0])
        else:
            logging.warning("DEFAULT_BARK_VOICES list is empty! Cannot set default.")

    def _create_elevenlabs_params(self, parent):
        """Creates the parameter frame specific to the ElevenLabs engine."""
        self.elevenlabs_frame = ttk.LabelFrame(parent, text="ElevenLabs Parameters", padding="10")

        # --- Key Selection with aligned labels ---
        key_frame = ttk.Frame(self.elevenlabs_frame)
        key_frame.pack(fill=tk.X, pady=5)

        # Create a label frame with fixed width for alignment
        label_width = 15

        # Key Selection Row
        key_select_frame = ttk.Frame(key_frame)
        key_select_frame.pack(fill=tk.X, pady=(0, 5))
        key_label = ttk.Label(key_select_frame, text="Select Key (.env):", width=label_width, anchor=tk.W)
        key_label.pack(side=tk.LEFT)

        # Get key names from the dictionary populated in __init__
        key_names = list(self.elevenlabs_api_keys.keys())
        self.elevenlabs_key_selector = ttk.Combobox(
            key_select_frame,
            textvariable=self.selected_elevenlabs_key_name,
            values=key_names,
            state="readonly" if key_names else "disabled",  # Disable if no keys found
            width=20
        )
        self.elevenlabs_key_selector.pack(side=tk.LEFT, padx=(0, 5))
        # When a key is selected from the dropdown, call on_key_selected
        self.elevenlabs_key_selector.bind("<<ComboboxSelected>>", self.on_key_selected)
        # Set the first key as default display if available
        if key_names: self.selected_elevenlabs_key_name.set(key_names[0])

        # Add credits display button to the right of key selector
        self.check_credits_button = ttk.Button(
            key_select_frame,
            text="Check Credits",
            command=self.check_elevenlabs_credits,
            state=tk.DISABLED  # Initially disabled until a key is validated
        )
        self.check_credits_button.pack(side=tk.LEFT, padx=(0, 5))

        # Credits label to display remaining credits
        self.credits_label = ttk.Label(key_select_frame, text="Credits: -")
        self.credits_label.pack(side=tk.LEFT)

        # --- Manual Key Input Row ---
        key_manual_frame = ttk.Frame(key_frame)
        key_manual_frame.pack(fill=tk.X, pady=(0, 5))
        manual_label = ttk.Label(key_manual_frame, text="Or enter manually:", width=label_width, anchor=tk.W)
        manual_label.pack(side=tk.LEFT)

        self.elevenlabs_api_key_entry = ttk.Entry(
            key_manual_frame,
            textvariable=self.elevenlabs_api_key_manual_input,
            show="*",  # Hide the key entry
            width=30
        )
        self.elevenlabs_api_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(key_manual_frame, text="Use This", command=self.use_manual_key).pack(side=tk.LEFT)

        # --- Voice Selection Row ---
        voice_frame = ttk.Frame(self.elevenlabs_frame)
        voice_frame.pack(fill=tk.X, pady=5)
        voice_label = ttk.Label(voice_frame, text="Voice:", width=label_width, anchor=tk.W)
        voice_label.pack(side=tk.LEFT)

        self.elevenlabs_voice_dropdown = ttk.Combobox(
            voice_frame,
            textvariable=self.elevenlabs_voice_name,
            state="disabled",  # Initially disabled until voices are loaded
            width=38
        )
        self.elevenlabs_voice_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.refresh_voices_button = ttk.Button(
            voice_frame,
            text="Refresh",
            command=self.refresh_elevenlabs_voices_thread,
            state=tk.DISABLED  # Initially disabled until a key is validated
        )
        self.refresh_voices_button.pack(side=tk.LEFT)

        # --- Model Selection Row ---
        model_frame = ttk.Frame(self.elevenlabs_frame)
        model_frame.pack(fill=tk.X, pady=(0, 5))
        model_label = ttk.Label(model_frame, text="Model:", width=label_width, anchor=tk.W)
        model_label.pack(side=tk.LEFT)

        self.elevenlabs_model_dropdown = ttk.Combobox(
            model_frame,
            textvariable=self.elevenlabs_model_id,
            values=ELEVENLABS_MODELS,
            state="readonly"  # User must choose from the list
        )
        self.elevenlabs_model_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)
        # Set a default model if the list is not empty
        if ELEVENLABS_MODELS: self.elevenlabs_model_id.set(ELEVENLABS_MODELS[0])

    def check_elevenlabs_credits(self):
        """Fetches and displays the current credit status for the selected ElevenLabs API key."""
        if not self.current_elevenlabs_key:
            messagebox.showwarning("API Key Needed",
                                   "Please select or enter a valid ElevenLabs API key first.",
                                   parent=self)
            return

        self.update_status("Checking ElevenLabs credits...")
        # Disable button during check
        if hasattr(self, 'check_credits_button'):
            self.check_credits_button.config(state=tk.DISABLED)

        # Start a background thread to fetch credit information
        thread = threading.Thread(
            target=self._get_credits_worker,
            args=(self.current_elevenlabs_key,),
            daemon=True
        )
        thread.start()

    def _get_credits_worker(self, api_key):
        """Worker function (runs in thread) to fetch credit information using the provided key."""
        credits_result, error = None, None
        try:
            # Call the engine function with the validated API key
            credits_result = elevenlabs_engine.get_subscription_info(api_key)
        except Exception as e:
            error = e
            logging.error(f"Error in _get_credits_worker thread: {e}", exc_info=True)

        # Schedule the UI update back on the main thread
        self.after(0, self._update_elevenlabs_credits_display, credits_result, error)

    def _update_elevenlabs_credits_display(self, credits_result, error):
        """Updates the credits display in the main GUI thread."""
        # Re-enable check credits button
        if hasattr(self, 'check_credits_button'):
            new_state = tk.NORMAL if self.current_elevenlabs_key else tk.DISABLED
            self.check_credits_button.config(state=new_state)

        # Handle errors
        if error:
            self.update_status(f"Error fetching credits: {error}", clear_after=10)
            messagebox.showerror("Error Fetching Credits",
                                 f"Could not fetch ElevenLabs credits:\n{error}",
                                 parent=self)
            if hasattr(self, 'credits_label'):
                self.credits_label.config(text="Credits: Error")
            return

        # Process successful results
        if credits_result is not None:
            try:
                # Extract the character counts and limits
                character_count = credits_result.get('character_count', 'N/A')
                character_limit = credits_result.get('character_limit', 'N/A')

                # Format the credit information
                if isinstance(character_count, (int, float)) and isinstance(character_limit, (int, float)):
                    remaining = character_limit - character_count
                    percentage = (remaining / character_limit * 100) if character_limit > 0 else 0
                    credit_text = f"Credits: {remaining:,}/{character_limit:,} ({percentage:.1f}%)"
                else:
                    credit_text = f"Credits: {character_count}/{character_limit}"

                # Update the display
                if hasattr(self, 'credits_label'):
                    self.credits_label.config(text=credit_text)

                self.update_status("Credits information updated.", clear_after=5)
            except Exception as e:
                logging.error(f"Error processing credit information: {e}", exc_info=True)
                if hasattr(self, 'credits_label'):
                    self.credits_label.config(text="Credits: Parse Error")
        else:
            # Should ideally not happen if error is None
            self.update_status("Unknown state after fetching credits.", clear_after=10)
            if hasattr(self, 'credits_label'):
                self.credits_label.config(text="Credits: Unknown")

    def _set_active_elevenlabs_key(self, key_to_set: Optional[str]) -> bool:
        """Validates the given key using the engine and updates UI state."""
        self.update_status(f"Validating ElevenLabs API key...")
        validated_key = elevenlabs_engine.validate_api_key(key_to_set)

        if validated_key:
            self.current_elevenlabs_key = validated_key  # Store the validated key
            self.update_status("ElevenLabs API key validated successfully.", clear_after=5)

            # Enable the refresh voices button now that we have a valid key
            if hasattr(self, 'refresh_voices_button'):
                self.refresh_voices_button.config(state=tk.NORMAL)

            # Enable the check credits button now that we have a valid key
            if hasattr(self, 'check_credits_button'):
                self.check_credits_button.config(state=tk.NORMAL)

            # Automatically fetch voices after successful validation
            self.refresh_elevenlabs_voices_thread()

            # Automatically check credits after successful validation
            self.check_elevenlabs_credits()

            return True
        else:
            self.current_elevenlabs_key = None  # Clear the active key
            self.update_status("ElevenLabs API key validation failed.", clear_after=10)

            # Disable voice-related controls
            if hasattr(self, 'refresh_voices_button'):
                self.refresh_voices_button.config(state=tk.DISABLED)

            # Disable credits button
            if hasattr(self, 'check_credits_button'):
                self.check_credits_button.config(state=tk.DISABLED)

            if hasattr(self, 'credits_label'):
                self.credits_label.config(text="Credits: -")

            if hasattr(self, 'elevenlabs_voice_dropdown'):
                self.elevenlabs_voice_dropdown.config(state=tk.DISABLED, values=[])
                self.elevenlabs_voice_name.set("")

            self.elevenlabs_voices.clear()  # Clear internal voice mapping

            return False

    # --- Text Input Context Menu Methods ---
    def _create_text_context_menu(self):
        """Creates the right-click context menu for the text input field."""
        # Avoid creating multiple menus if called again
        if not hasattr(self, 'text_context_menu'):
            self.text_context_menu = tk.Menu(self, tearoff=0) # tearoff=0 removes the tear-off line
            self.text_context_menu.add_command(label="Undo (Ctrl+Z)", command=self._text_undo)
            self.text_context_menu.add_command(label="Redo (Ctrl+Y)", command=self._text_redo)
            self.text_context_menu.add_separator()
            self.text_context_menu.add_command(label="Cut", command=self._text_cut)
            self.text_context_menu.add_command(label="Copy", command=self._text_copy)
            self.text_context_menu.add_command(label="Paste", command=self._text_paste)
            self.text_context_menu.add_separator()
            self.text_context_menu.add_command(label="Select All (Ctrl+A)", command=self._text_select_all)

    def _show_text_context_menu(self, event):
        """Shows the text context menu at the mouse position and updates item states."""
        # Ensure necessary widgets exist
        if not hasattr(self, 'text_input') or not hasattr(self, 'text_context_menu'):
            return
        self.text_input.focus_set() # Ensure text widget has focus for clipboard ops

        # Update state for Undo/Redo (keep enabled, handle errors in commands)
        try: self.text_context_menu.entryconfig("Undo (Ctrl+Z)", state=tk.NORMAL)
        except tk.TclError: pass # Ignore errors if menu not fully ready
        try: self.text_context_menu.entryconfig("Redo (Ctrl+Y)", state=tk.NORMAL)
        except tk.TclError: pass

        # Update state for Cut/Copy based on text selection
        try:
            has_selection = bool(self.text_input.tag_ranges(tk.SEL))
            state = tk.NORMAL if has_selection else tk.DISABLED
            self.text_context_menu.entryconfig("Cut", state=state)
            self.text_context_menu.entryconfig("Copy", state=state)
        except tk.TclError: # Fallback if widget state is unusual
            self.text_context_menu.entryconfig("Cut", state=tk.DISABLED)
            self.text_context_menu.entryconfig("Copy", state=tk.DISABLED)

        # Update state for Paste based on clipboard content
        try:
            self.clipboard_get() # Raises TclError if clipboard is empty or non-text
            self.text_context_menu.entryconfig("Paste", state=tk.NORMAL)
        except tk.TclError:
            self.text_context_menu.entryconfig("Paste", state=tk.DISABLED)

        # Update state for Select All (always possible)
        try: self.text_context_menu.entryconfig("Select All (Ctrl+A)", state=tk.NORMAL)
        except tk.TclError: pass

        # Display the menu at the clicked coordinates
        self.text_context_menu.tk_popup(event.x_root, event.y_root)

    def _text_cut(self):
        """Performs the standard <<Cut>> virtual event."""
        if hasattr(self, 'text_input'):
            try: self.text_input.event_generate("<<Cut>>")
            except tk.TclError: pass # Ignore error if widget is destroyed
    def _text_copy(self):
        """Performs the standard <<Copy>> virtual event."""
        if hasattr(self, 'text_input'):
            try: self.text_input.event_generate("<<Copy>>")
            except tk.TclError: pass
    def _text_paste(self):
        """Performs the standard <<Paste>> virtual event."""
        if hasattr(self, 'text_input'):
            try: self.text_input.event_generate("<<Paste>>")
            except tk.TclError: pass
    def _text_select_all(self, event=None): # Accept event argument for key binding
        """Selects all text in the input field."""
        if hasattr(self, 'text_input'):
            try:
                self.text_input.tag_add(tk.SEL, "1.0", tk.END) # Add selection tag
                self.text_input.mark_set(tk.INSERT, "1.0")    # Move cursor to start
                self.text_input.see(tk.INSERT)             # Scroll to cursor
                return "break" # Prevent default binding behavior
            except tk.TclError: pass
    def _text_undo(self, event=None):
        """Performs the Undo action."""
        if hasattr(self, 'text_input'):
            try:
                self.text_input.edit_undo()
            except tk.TclError: logging.info("Undo stack is empty.") # Tkinter raises error if stack empty
            return "break" # Prevent default binding behavior
    def _text_redo(self, event=None):
        """Performs the Redo action."""
        if hasattr(self, 'text_input'):
            try:
                self.text_input.edit_redo()
            except tk.TclError: logging.info("Redo stack is empty.") # Tkinter raises error if stack empty
            return "break" # Prevent default binding behavior

    # --- General UI Helper Methods ---
    def update_parameter_ui(self, event=None):
        """Shows/hides the appropriate parameter frame based on model selection."""
        selected_model = self.model_choice.get()
        logging.info(f"Switching parameter view to: {selected_model}")

        # Hide all parameter frames first, checking if they exist
        if hasattr(self, 'xtts_frame'): self.xtts_frame.pack_forget()
        if hasattr(self, 'piper_frame'): self.piper_frame.pack_forget()
        if hasattr(self, 'bark_frame'): self.bark_frame.pack_forget()
        if hasattr(self, 'elevenlabs_frame'): self.elevenlabs_frame.pack_forget()

        # Show the frame corresponding to the selected model
        if selected_model == "XTTSv2" and hasattr(self, 'xtts_frame'): self.xtts_frame.pack(fill=tk.X)
        elif selected_model == "Piper" and hasattr(self, 'piper_frame'): self.piper_frame.pack(fill=tk.X)
        elif selected_model == "Bark" and hasattr(self, 'bark_frame'): self.bark_frame.pack(fill=tk.X)
        elif selected_model == "ElevenLabs" and hasattr(self, 'elevenlabs_frame'): self.elevenlabs_frame.pack(fill=tk.X)

        # Ensure the layout updates immediately
        self.update_idletasks()

    def browse_file(self, string_var: tk.StringVar, title: str, filetypes: list, initialdir: str):
        """Opens a file dialog and sets the selected path to a StringVar."""
        # Use user's home directory as fallback if initialdir doesn't exist
        if not os.path.isdir(initialdir): initialdir = os.path.expanduser("~")
        filename = filedialog.askopenfilename(title=title, filetypes=filetypes, initialdir=initialdir)
        if filename: # Only update if a file was selected
            string_var.set(filename)

    def browse_save_file(self):
        """Opens a save file dialog for the output WAV file."""
        current_path = self.output_file_path.get()
        initial_filename = os.path.basename(current_path) if current_path else "output.wav"
        initial_dir = os.path.dirname(current_path) or DEFAULT_OUTPUT_DIR
        if not os.path.isdir(initial_dir): initial_dir = DEFAULT_OUTPUT_DIR # Fallback

        filepath = filedialog.asksaveasfilename(
            title="Save Audio As",
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")],
            initialdir=initial_dir,
            initialfile=initial_filename
        )
        if filepath: # Only update if a path was chosen
            # Ensure the path ends with .wav for consistency
            if not filepath.lower().endswith(".wav"): filepath += ".wav"
            self.output_file_path.set(filepath)

    def update_status(self, message: str, clear_after: Optional[int] = None):
        """Updates the status bar text (thread-safe via self.after)."""
        def _update_in_main_thread():
            if hasattr(self, 'status_label'): # Check if label still exists
                self.status_label.config(text=message)
                if clear_after is not None:
                    # Schedule clearing the message after the specified delay
                    self.after(clear_after * 1000, lambda: self.status_label.config(text="Ready.") if hasattr(self, 'status_label') else None)
        # Schedule the update to run in the main Tkinter event loop
        self.after(0, _update_in_main_thread)

    def set_ui_state(self, state: str):
        """Enables/disables main UI elements during processing."""
        gui_state = tk.NORMAL if state == 'normal' else tk.DISABLED
        # Check existence before configuring widgets
        if hasattr(self, 'synthesize_button'): self.synthesize_button.config(state=gui_state)
        if hasattr(self, 'model_menu'): self.model_menu.config(state=gui_state)
        if hasattr(self, 'browse_output_button'): self.browse_output_button.config(state=gui_state)
        # Note: Playback controls have their own enable/disable logic

    # --- ElevenLabs Specific UI Methods ---
    def _set_active_elevenlabs_key(self, key_to_set: Optional[str]) -> bool:
        """Validates the given key using the engine and updates UI state."""
        self.update_status(f"Validating ElevenLabs API key...")
        validated_key = elevenlabs_engine.validate_api_key(key_to_set)

        if validated_key:
            self.current_elevenlabs_key = validated_key # Store the validated key
            self.update_status("ElevenLabs API key validated successfully.", clear_after=5)
            # Enable the refresh button now that we have a valid key
            if hasattr(self, 'refresh_voices_button'): self.refresh_voices_button.config(state=tk.NORMAL)
            # Automatically fetch voices after successful validation
            self.refresh_elevenlabs_voices_thread()
            return True
        else:
            self.current_elevenlabs_key = None # Clear the active key
            self.update_status("ElevenLabs API key validation failed.", clear_after=10)
            # Disable voice-related controls
            if hasattr(self, 'refresh_voices_button'): self.refresh_voices_button.config(state=tk.DISABLED)
            if hasattr(self, 'elevenlabs_voice_dropdown'):
                self.elevenlabs_voice_dropdown.config(state=tk.DISABLED, values=[]); self.elevenlabs_voice_name.set("")
            self.elevenlabs_voices.clear() # Clear internal voice mapping
            # Optionally, show a more prominent error message
            # messagebox.showerror("API Key Error", "The provided ElevenLabs API key failed validation.", parent=self)
            return False

    def on_key_selected(self, event=None):
        """Handles selection of an API key from the .env dropdown."""
        selected_name = self.selected_elevenlabs_key_name.get()
        if selected_name in self.elevenlabs_api_keys:
            selected_key = self.elevenlabs_api_keys[selected_name]
            logging.info(f"Selected key '{selected_name}' from dropdown.")
            # Clear the manual input field if a dropdown key is chosen
            if hasattr(self, 'elevenlabs_api_key_manual_input'): self.elevenlabs_api_key_manual_input.set("")
            # Validate and set this key as the active one
            self._set_active_elevenlabs_key(selected_key)
        else:
            logging.warning(f"Selected key name '{selected_name}' not found in loaded keys.")

    def use_manual_key(self):
        """Handles the 'Use This' button for the manually entered API key."""
        manual_key = self.elevenlabs_api_key_manual_input.get().strip()
        if manual_key:
            logging.info("Attempting to use manually entered API key.")
            # Clear the dropdown selection to indicate manual key usage
            if hasattr(self, 'selected_elevenlabs_key_name'): self.selected_elevenlabs_key_name.set("")
            # Validate and set this key as the active one
            self._set_active_elevenlabs_key(manual_key)
        else:
            messagebox.showwarning("No Key", "Please enter an API key manually first.", parent=self)

    def refresh_elevenlabs_voices_thread(self):
        """Starts fetching ElevenLabs voices in a background thread."""
        # Only proceed if there's a currently active (validated) key
        if not self.current_elevenlabs_key:
            messagebox.showwarning("API Key Needed", "Please select or enter a valid ElevenLabs API key first.", parent=self)
            return

        self.update_status("Fetching ElevenLabs voices...")
        # Disable button during refresh
        if hasattr(self, 'refresh_voices_button'): self.refresh_voices_button.config(state=tk.DISABLED)
        # Pass the active key to the worker thread
        thread = threading.Thread(target=self._get_voices_worker, args=(self.current_elevenlabs_key,), daemon=True)
        thread.start()

    def _get_voices_worker(self, api_key: str):
        """Worker function (runs in thread) to fetch voices using the provided key."""
        voices_result, error = None, None
        try:
            # Call the engine function with the validated API key
            voices_result = elevenlabs_engine.get_elevenlabs_voices(api_key)
        except Exception as e:
            error = e
            logging.error(f"Error in _get_voices_worker thread: {e}", exc_info=True)
        # Schedule the UI update back on the main thread
        self.after(0, self._update_elevenlabs_voice_list, voices_result, error)

    def _update_elevenlabs_voice_list(self, voices_result: Optional[List[Tuple[str, str]]], error: Optional[Exception]):
        """Updates the voice dropdown list in the main GUI thread."""
        # Re-enable refresh button only if a key is currently considered valid
        if hasattr(self, 'refresh_voices_button'):
            new_state = tk.NORMAL if self.current_elevenlabs_key else tk.DISABLED
            self.refresh_voices_button.config(state=new_state)

        # Handle errors first
        if error:
            self.update_status(f"Error fetching voices: {error}", clear_after=10)
            messagebox.showerror("Error Fetching Voices", f"Could not fetch ElevenLabs voices:\n{error}", parent=self)
            # Reset voice list UI elements
            if hasattr(self, 'elevenlabs_voice_dropdown'):
                 self.elevenlabs_voice_dropdown.config(state=tk.DISABLED, values=[])
                 self.elevenlabs_voice_name.set("")
            self.elevenlabs_voices.clear()
            return

        # Process successful results
        if voices_result is not None:
            self.elevenlabs_voices.clear() # Clear previous mapping
            voice_names = []
            for name, voice_id in voices_result:
                self.elevenlabs_voices[name] = voice_id # Store name -> ID map
                voice_names.append(name)

            if hasattr(self, 'elevenlabs_voice_dropdown'):
                self.elevenlabs_voice_dropdown.config(values=voice_names, state="readonly" if voice_names else "disabled")
                if voice_names:
                    # Try to maintain current selection, otherwise use default or first
                    default_voice = "Rachel" # A common voice
                    current_selection = self.elevenlabs_voice_name.get()
                    if current_selection and current_selection in self.elevenlabs_voices:
                        self.elevenlabs_voice_name.set(current_selection) # Keep current if valid
                    elif default_voice in self.elevenlabs_voices:
                        self.elevenlabs_voice_name.set(default_voice) # Use default
                    else:
                        self.elevenlabs_voice_name.set(voice_names[0]) # Use first available
                    self.update_status(f"{len(voice_names)} ElevenLabs voices loaded.", clear_after=5)
                else:
                    # No voices found
                    self.elevenlabs_voice_name.set("")
                    self.update_status("No ElevenLabs voices found.", clear_after=5)
        else:
            # Should ideally not happen if error is None, but good to handle
            self.update_status("Unknown state after fetching voices.", clear_after=10)

    # --- Audio List & Playback Methods (Mostly Unchanged) ---
    def load_existing_audio(self):
        """Loads existing WAV and MP3 files into the listbox."""
        if not hasattr(self, 'audio_listbox'): return
        self.audio_listbox.delete(0, tk.END); self.audio_files.clear()
        try:
            audio_exts = ('*.wav', '*.mp3'); all_audio_files = []
            for ext in audio_exts: all_audio_files.extend(glob.glob(os.path.join(DEFAULT_OUTPUT_DIR, ext)))
            all_audio_files.sort(key=os.path.getmtime, reverse=True) # Sort newest first
            for f_path in all_audio_files: f_name = os.path.basename(f_path); self.audio_files[f_name] = f_path; self.audio_listbox.insert(tk.END, f_name)
            logging.info(f"{len(self.audio_files)} existing audio files loaded.")
        except Exception as e: logging.error(f"Error loading existing audio: {e}")

    def add_audio_to_list(self, file_path: str):
        """Adds a newly generated file to the top of the listbox and selects it."""
        if not hasattr(self, 'audio_listbox'): return
        if os.path.exists(file_path):
            f_name = os.path.basename(file_path)
            if f_name not in self.audio_files: # Avoid duplicates
                self.audio_files[f_name] = file_path; self.audio_listbox.insert(0, f_name)
                logging.info(f"Audio file added to list: {f_name}")
                # Select the newly added item
                self.audio_listbox.selection_clear(0, tk.END); self.audio_listbox.selection_set(0); self.on_audio_select()

    def on_audio_select(self, event=None):
        """Handles selection changes in the audio listbox."""
        if not self.mixer_initialized or not hasattr(self, 'audio_listbox'): return
        selected_indices = self.audio_listbox.curselection()
        if not selected_indices: self.selected_audio_path = None; self.disable_playback_controls(); return # No selection
        selected_filename = self.audio_listbox.get(selected_indices[0])
        if selected_filename in self.audio_files:
            new_path = self.audio_files[selected_filename]
            if new_path != self.selected_audio_path: # Only update if path changed
                self.selected_audio_path = new_path; logging.info(f"Selected audio: {self.selected_audio_path}"); self.stop_audio()
                try: # Get duration (handle MP3 via pydub)
                    if self.selected_audio_path.lower().endswith(".mp3"):
                         from pydub import AudioSegment; sound = AudioSegment.from_mp3(self.selected_audio_path); self.audio_duration = len(sound) / 1000.0
                    else:
                        with sf.SoundFile(self.selected_audio_path) as f: self.audio_duration = f.frames / f.samplerate
                    logging.info(f"Duration: {self.audio_duration:.2f}s")
                    if hasattr(self, 'seek_slider'): self.seek_slider.config(to=self.audio_duration, state=tk.NORMAL)
                    self.update_time_label(); self.enable_playback_controls()
                except ImportError: logging.error("pydub not found, cannot determine MP3 duration."); messagebox.showerror("Playback Error", "pydub library not found.\nCannot load MP3 files correctly.", parent=self); self.selected_audio_path = None; self.disable_playback_controls()
                except Exception as e: logging.error(f"Error loading audio/getting duration: {e}", exc_info=True); messagebox.showerror("Playback Error", f"Error loading audio file:\n{e}", parent=self); self.selected_audio_path = None; self.disable_playback_controls()
        else: logging.warning(f"Selected filename '{selected_filename}' not found in dictionary."); self.selected_audio_path = None; self.disable_playback_controls()

    def disable_playback_controls(self):
        """Disables all playback buttons and the slider."""
        if hasattr(self, 'play_button'): self.play_button.config(state=tk.DISABLED)
        if hasattr(self, 'pause_button'): self.pause_button.config(state=tk.DISABLED)
        if hasattr(self, 'stop_button'): self.stop_button.config(state=tk.DISABLED)
        if hasattr(self, 'seek_slider'): self.seek_slider.config(state=tk.DISABLED, value=0)
        self.audio_duration = 0.0; self.update_time_label()

    def enable_playback_controls(self):
        """Enables Play button and slider if a valid file is selected."""
        if not self.mixer_initialized: return
        if hasattr(self, 'play_button') and hasattr(self, 'pause_button') and hasattr(self, 'stop_button') and hasattr(self, 'seek_slider'):
            if self.selected_audio_path: self.play_button.config(state=tk.NORMAL); self.pause_button.config(state=tk.DISABLED); self.stop_button.config(state=tk.DISABLED); self.seek_slider.config(state=tk.NORMAL)
            else: self.disable_playback_controls()

    def format_time(self, seconds: float) -> str:
        """Formats seconds into an MM:SS string."""
        minutes, seconds = divmod(int(max(0, seconds)), 60); return f"{minutes:02d}:{seconds:02d}"
    def update_time_label(self, current_time: float = 0.0):
        """Updates the time label with current/total duration."""
        if hasattr(self, 'time_label'): self.time_label.config(text=f"{self.format_time(current_time)} / {self.format_time(self.audio_duration)}")

    def play_audio(self):
        """Starts or resumes audio playback."""
        if not self.mixer_initialized or not self.selected_audio_path: return
        try:
            if not pygame.mixer.music.get_busy() and not self.is_paused: # Start new/stopped
                pygame.mixer.music.load(self.selected_audio_path); pygame.mixer.music.play(); self.is_paused = False; self.start_playback_update()
            elif self.is_paused: # Resume paused
                pygame.mixer.music.unpause(); self.is_paused = False; self.start_playback_update()
            # Update button states
            if hasattr(self, 'play_button'): self.play_button.config(state=tk.DISABLED)
            if hasattr(self, 'pause_button'): self.pause_button.config(state=tk.NORMAL)
            if hasattr(self, 'stop_button'): self.stop_button.config(state=tk.NORMAL)
        except Exception as e: logging.error(f"Error playing audio: {e}", exc_info=True); messagebox.showerror("Playback Error", f"Could not play audio:\n{e}"); self.stop_audio()

    def pause_audio(self):
        """Pauses currently playing audio."""
        if not self.mixer_initialized or not pygame.mixer.music.get_busy(): return
        pygame.mixer.music.pause(); self.is_paused = True; self.stop_playback_update()
        # Update button states
        if hasattr(self, 'play_button'): self.play_button.config(state=tk.NORMAL)
        if hasattr(self, 'pause_button'): self.pause_button.config(state=tk.DISABLED)
        if hasattr(self, 'stop_button'): self.stop_button.config(state=tk.NORMAL)

    def stop_audio(self):
        """Stops audio playback and resets related UI elements."""
        if not self.mixer_initialized: return
        if pygame.mixer.music.get_busy() or self.is_paused: # Only act if playing or paused
            pygame.mixer.music.stop(); pygame.mixer.music.unload(); self.is_paused = False; self.stop_playback_update()
            if hasattr(self, 'seek_slider'): self.seek_slider.set(0)
            self.update_time_label()
            # Reset controls based on whether a file is still selected
            if self.selected_audio_path: self.enable_playback_controls()
            else: self.disable_playback_controls()

    def start_playback_update(self):
        """Starts the periodic timer for updating the playback slider/time."""
        if hasattr(self, 'playback_update_id') and self.playback_update_id:
            try: self.after_cancel(self.playback_update_id)
            except ValueError: pass
        self.update_playback_slider() # Initiate the loop

    def stop_playback_update(self):
        """Stops the periodic playback update timer."""
        if hasattr(self, 'playback_update_id') and self.playback_update_id:
            try: self.after_cancel(self.playback_update_id)
            except ValueError: pass
            self.playback_update_id = None

    def update_playback_slider(self):
        """Callback function for the periodic timer to update playback UI."""
        if not self.mixer_initialized: return
        # Schedule the next update
        if not hasattr(self, 'playback_update_id'): self.playback_update_id = None
        self.playback_update_id = self.after(250, self.update_playback_slider) # ~4Hz update rate

        # Update only if playing, not paused, and user isn't dragging slider
        if pygame.mixer.music.get_busy() and not self.is_paused and not self.is_seeking:
            if hasattr(self, 'seek_slider'):
                try:
                    current_pos_ms = pygame.mixer.music.get_pos()
                    if current_pos_ms != -1: # -1 means not playing
                        current_pos_sec = max(0, min(current_pos_ms / 1000.0, self.audio_duration))
                        self.seek_slider.set(current_pos_sec); self.update_time_label(current_pos_sec)
                except pygame.error as e: logging.warning(f"Pygame error getting pos: {e}"); self.stop_audio_if_finished()
                except Exception as e: logging.error(f"Error updating slider: {e}"); self.stop_playback_update() # Stop loop on unexpected error
        elif not pygame.mixer.music.get_busy() and not self.is_paused:
            # Playback stopped naturally
            self.stop_audio_if_finished()

    def stop_audio_if_finished(self):
        """Checks if playback finished naturally and resets UI via stop_audio."""
        # Check if it *was* playing (play button disabled) and is not paused now
        if hasattr(self, 'play_button') and self.play_button['state'] == tk.DISABLED and not self.is_paused:
            # Double check it's truly not busy anymore
            if not pygame.mixer.music.get_busy():
                logging.info("Playback finished naturally.")
                self.after(100, self.stop_audio) # Call stop_audio after a short delay
                self.stop_playback_update() # Stop the update loop immediately

    def on_seek_press(self, event):
        """Flags that the user has started dragging the seek slider."""
        if hasattr(self, 'seek_slider') and self.seek_slider['state'] == tk.NORMAL: self.is_seeking = True
    def on_seek_release(self, event):
        """Seeks the audio when the user releases the seek slider."""
        if hasattr(self, 'seek_slider') and self.seek_slider['state'] == tk.NORMAL and self.is_seeking:
            self.is_seeking = False; self.seek_audio(self.seek_slider.get())
    def on_seek_slider_move(self, value):
        """Updates the time label while the user drags the slider."""
        self.update_time_label(float(value))

    def seek_audio(self, seconds: float):
        """Seeks audio playback to the specified time in seconds."""
        if not self.mixer_initialized or not self.selected_audio_path: return
        try:
            seek_time_sec = max(0, min(seconds, self.audio_duration)) # Clamp seek time
            # Using play(start=...) is often more reliable for seeking than set_pos
            pygame.mixer.music.play(start=seek_time_sec);
            logging.info(f"Seeked to {seek_time_sec:.2f}s")
            if self.is_paused: pygame.mixer.music.pause() # Re-pause if seeking while paused
            else:
                self.start_playback_update() # Ensure updates are running if playing
                # Update button states for playing
                if hasattr(self, 'play_button'): self.play_button.config(state=tk.DISABLED)
                if hasattr(self, 'pause_button'): self.pause_button.config(state=tk.NORMAL)
                if hasattr(self, 'stop_button'): self.stop_button.config(state=tk.NORMAL)
            # Update slider/label immediately
            if hasattr(self, 'seek_slider'): self.seek_slider.set(seek_time_sec)
            self.update_time_label(seek_time_sec)
        except pygame.error as e: logging.error(f"Pygame seek error: {e}", exc_info=True); messagebox.showerror("Playback Error", f"Seek error:\n{e}")
        except Exception as e: logging.error(f"Seek error: {e}", exc_info=True); messagebox.showerror("Playback Error", f"Unexpected seek error:\n{e}")

    # --- Synthesis Logic ---
    def start_synthesis_thread(self):
        """Validates inputs and parameters, then starts synthesis in a background thread."""
        if not hasattr(self, 'text_input'): messagebox.showerror("Error", "Text input field not initialized."); return
        text = self.text_input.get("1.0", tk.END).strip()
        output_path = self.output_file_path.get().strip()
        model_type = self.model_choice.get()

        # --- Input Validation ---
        if not text: messagebox.showerror("Input Error", "Please enter text to synthesize."); return
        if not output_path: messagebox.showerror("Input Error", "Please specify an output file."); return
        if not output_path.lower().endswith(".wav"): output_path += ".wav"; self.output_file_path.set(output_path) # Ensure .wav target
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            try: os.makedirs(output_dir); logging.info(f"Output directory created: {output_dir}");
            except OSError as e: messagebox.showerror("Error", f"Could not create output directory:\n{e}"); return
        if not model_type: messagebox.showerror("Input Error", "Please select a TTS model."); return

        # --- Collect Engine-Specific Parameters ---
        params = {'text': text, 'output_path': output_path}
        target_function = None
        try:
            if model_type == "XTTSv2":
                params['speaker_wav_path'] = self.xtts_speaker_wav.get().strip() or None
                params['language'] = self.xtts_language.get().strip()
                if not params['language']: raise ValueError("XTTSv2 language is required.")
                target_function = xtts_engine.synthesize_xtts
            elif model_type == "Piper":
                params['model_onnx_path'] = self.piper_onnx_path.get().strip()
                params['model_json_path'] = self.piper_json_path.get().strip()
                if not params['model_onnx_path'] or not params['model_json_path']: raise ValueError("Piper requires both .onnx and .json model files.")
                if not os.path.exists(params['model_onnx_path']): raise FileNotFoundError(f"Piper ONNX file not found: {params['model_onnx_path']}")
                if not os.path.exists(params['model_json_path']): raise FileNotFoundError(f"Piper JSON file not found: {params['model_json_path']}")
                target_function = piper_engine.synthesize_piper
            elif model_type == "Bark":
                params['voice_preset'] = self.bark_voice_preset.get().strip()
                if not params['voice_preset']: raise ValueError("Bark voice preset is required.")
                target_function = bark_engine.synthesize_bark
            elif model_type == "ElevenLabs":
                selected_voice_name = self.elevenlabs_voice_name.get()
                if not selected_voice_name: raise ValueError("Please select an ElevenLabs voice.")
                if selected_voice_name not in self.elevenlabs_voices: raise ValueError(f"Selected voice '{selected_voice_name}' not found in loaded voices.")
                params['voice_id'] = self.elevenlabs_voices[selected_voice_name]
                params['model_id'] = self.elevenlabs_model_id.get()
                if not params['model_id']: raise ValueError("Please select an ElevenLabs model.")
                # --- Pass the currently active validated key ---
                if not self.current_elevenlabs_key:
                     raise ValueError("ElevenLabs API key is not set or validated. Please select/enter a valid key.")
                params['api_key'] = self.current_elevenlabs_key # Add key to params for engine
                # ---
                target_function = elevenlabs_engine.synthesize_elevenlabs
            else:
                raise ValueError(f"Unknown model type selected: {model_type}")

        except (ValueError, FileNotFoundError) as e: messagebox.showerror("Parameter Error", str(e)); return
        except Exception as e: messagebox.showerror("Unexpected Error", f"Error preparing synthesis: {e}"); logging.error("Error preparing synthesis", exc_info=True); return

        # --- Start Background Thread for Synthesis ---
        self.set_ui_state('disabled') # Disable UI during processing
        self.update_status(f"Starting {model_type} synthesis...")
        synthesis_thread = threading.Thread(
            target=self.run_synthesis,
            args=(target_function, params, output_path), # Pass function, params, path
            daemon=True # Allow app to exit even if thread is running
        )
        synthesis_thread.start()

    def run_synthesis(self, synthesis_function, params: dict, generated_file_path: str):
        """Runs the synthesis function in the worker thread and handles UI updates."""
        success, message = False, "Synthesis started..."
        start_time = time.time()
        try:
            self.update_status(f"Synthesizing... ({self.model_choice.get()}) This may take a while.")
            # Log relevant params, avoid logging sensitive data like API keys directly
            log_params = {k: v for k, v in params.items() if k != 'api_key'}
            logging.info(f"Calling {synthesis_function.__name__} with params: {log_params}")

            # Call the appropriate engine function
            success, message = synthesis_function(**params)

        except Exception as e:
            success = False
            message = f"Unexpected error during synthesis: {e}"
            logging.error(f"Synthesis error in worker thread: {e}\n{traceback.format_exc()}")
        finally:
            # --- Update UI in Main Thread ---
            self.after(0, lambda: self.set_ui_state('normal')) # Re-enable UI elements

            duration = time.time() - start_time
            final_message = f"{message} (Duration: {duration:.2f} sec)"

            if success:
                # Determine the actual file path (might be .mp3 if conversion failed)
                final_path_to_add = generated_file_path
                if "as MP3!" in message and message.endswith(".mp3"):
                    final_path_to_add = message.split(" in ")[-1] # Extract .mp3 path

                self.update_status("Synthesis complete.", clear_after=10)
                # Add the generated file to the list (using main thread)
                self.after(0, self.add_audio_to_list, final_path_to_add)
                # Show success message box (using main thread)
                self.after(0, lambda: messagebox.showinfo("Success", final_message))
            else:
                self.update_status("Synthesis failed.", clear_after=10)
                # Show error message box (using main thread)
                self.after(0, lambda: messagebox.showerror("Error", final_message))

    # --- Application Closing ---
    def on_closing(self):
        """Handles the window closing event cleanly."""
        logging.info("Closing application...");
        self.stop_playback_update() # Stop any running timers
        if self.mixer_initialized:
            logging.info("Stopping pygame mixer...");
            try:
                pygame.mixer.music.stop(); pygame.mixer.quit(); pygame.quit()
                logging.info("Pygame closed successfully.")
            except Exception as e: logging.error(f"Error closing pygame: {e}")
        self.destroy() # Close the Tkinter window

    # --- Initialization Method ---
    def __init__(self):
        """Initializes the TTSApp class, sets up UI and variables."""
        super().__init__()
        self.title("Multi TTS Synthesizer")
        self.geometry("950x650") # Adjusted size

        # --- Initialize Pygame Mixer ---
        try:
            pygame.init(); pygame.mixer.init(); logging.info("Pygame mixer initialized.")
            self.mixer_initialized = True
        except Exception as e:
            logging.error(f"Could not initialize pygame mixer: {e}", exc_info=True)
            self.mixer_initialized = False # Continue without playback functionality

        # --- Ensure Output Directory Exists ---
        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)

        # --- Initialize Application State Variables ---
        self.model_choice = tk.StringVar(self)
        # XTTS
        self.xtts_speaker_wav = tk.StringVar(self); self.xtts_language = tk.StringVar(self, value="nl")
        # Piper
        self.piper_onnx_path = tk.StringVar(self); self.piper_json_path = tk.StringVar(self)
        # Bark
        self.bark_voice_preset = tk.StringVar(self)
        # ElevenLabs
        self.model_choice = tk.StringVar(self)
        # XTTS
        self.xtts_speaker_wav = tk.StringVar(self)
        self.xtts_language = tk.StringVar(self, value="nl")
        # Piper
        self.piper_onnx_path = tk.StringVar(self)
        self.piper_json_path = tk.StringVar(self)
        # Bark
        self.bark_voice_preset = tk.StringVar(self)
        # ElevenLabs
        self.elevenlabs_api_keys = {}  # Dict to store {Name: Key} from .env
        self.selected_elevenlabs_key_name = tk.StringVar(self)  # Name of key selected in dropdown
        self.elevenlabs_api_key_manual_input = tk.StringVar(self)  # Key entered manually
        self.current_elevenlabs_key = None  # The currently active *validated* key
        self.elevenlabs_voice_name = tk.StringVar(self)
        self.elevenlabs_model_id = tk.StringVar(self)
        self.elevenlabs_voices = {}  # {Name: ID} map
        # General / Playback
        self.output_file_path = tk.StringVar(self); self.audio_files = {}; self.selected_audio_path = None; self.audio_duration = 0.0; self.playback_update_id = None; self.is_paused = False; self.is_seeking = False

        # --- Read API Keys from .env ---
        key_prefix = "ELEVENLABS_API_KEY_"
        for key, value in os.environ.items():
            if key.startswith(key_prefix) and value:  # Check prefix and ensure value exists
                name = key.replace(key_prefix, "")
                if name:
                    self.elevenlabs_api_keys[name] = value  # Store if name part is not empty
                    logging.info(f"Found ElevenLabs API key: {name}")

        # --- Create UI Elements ---
        self._create_text_context_menu() # Create context menu early

        # Main Layout (Paned Window for resizing)
        self.paned_window = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Left Panel: Audio List and Playback Controls ---
        left_panel = ttk.Frame(self.paned_window, width=250)
        left_panel.pack(fill=tk.BOTH, expand=False) # Don't expand initially
        left_panel.columnconfigure(0, weight=1); left_panel.rowconfigure(0, weight=1) # Make content fill width/height
        self.paned_window.add(left_panel, minsize=200) # Add to pane window

        # Audio Files Listbox
        list_frame = ttk.LabelFrame(left_panel, text="Generated Audio", padding="5")
        list_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        list_frame.rowconfigure(0, weight=1); list_frame.columnconfigure(0, weight=1) # Listbox fills frame
        self.audio_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE)
        self.audio_listbox.grid(row=0, column=0, sticky="nsew")
        list_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.audio_listbox.yview)
        list_scrollbar.grid(row=0, column=1, sticky="ns"); self.audio_listbox.config(yscrollcommand=list_scrollbar.set)
        self.audio_listbox.bind('<<ListboxSelect>>', self.on_audio_select) # Handle selection

        # Playback Controls Frame
        controls_frame = ttk.LabelFrame(left_panel, text="Playback Controls", padding="5")
        controls_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        controls_frame.columnconfigure((0, 1, 2), weight=1) # Distribute space
        self.play_button = ttk.Button(controls_frame, text="▶ Play", command=self.play_audio, state=tk.DISABLED)
        self.play_button.grid(row=0, column=0, padx=2, pady=5, sticky="ew")
        self.pause_button = ttk.Button(controls_frame, text="❚❚ Pause", command=self.pause_audio, state=tk.DISABLED)
        self.pause_button.grid(row=0, column=1, padx=2, pady=5, sticky="ew")
        self.stop_button = ttk.Button(controls_frame, text="■ Stop", command=self.stop_audio, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=2, padx=2, pady=5, sticky="ew")
        self.time_label = ttk.Label(controls_frame, text="00:00 / 00:00") # Time display
        self.time_label.grid(row=1, column=0, columnspan=3, pady=(5, 0))
        self.seek_slider = ttk.Scale(controls_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.on_seek_slider_move, state=tk.DISABLED)
        self.seek_slider.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 5))
        self.seek_slider.bind("<ButtonPress-1>", self.on_seek_press); self.seek_slider.bind("<ButtonRelease-1>", self.on_seek_release) # Handle seeking

        # --- Right Panel: Configuration and Synthesis ---
        right_panel = ttk.Frame(self.paned_window)
        right_panel.pack(fill=tk.BOTH, expand=True)
        self.paned_window.add(right_panel) # Add to pane window

        # Model Selection Dropdown
        model_frame = ttk.LabelFrame(right_panel, text="TTS Engine Selection", padding="10")
        model_frame.pack(fill=tk.X, pady=5, padx=5)
        ttk.Label(model_frame, text="Choose Model:").pack(side=tk.LEFT, padx=5)
        model_options = ["XTTSv2", "Piper", "Bark", "ElevenLabs"] # Add EL to options
        self.model_menu = ttk.Combobox(model_frame, textvariable=self.model_choice, values=model_options, state="readonly")
        self.model_menu.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.model_menu.bind("<<ComboboxSelected>>", self.update_parameter_ui) # Update view on change
        self.model_menu.current(0) # Default to first model (XTTSv2)

        # Container for Engine-Specific Parameters
        self.param_frame_container = ttk.Frame(right_panel)
        self.param_frame_container.pack(fill=tk.X, pady=5, padx=5)
        # Create all parameter frames (they will be hidden/shown by update_parameter_ui)
        self._create_xtts_params(self.param_frame_container)
        self._create_piper_params(self.param_frame_container)
        self._create_bark_params(self.param_frame_container)
        self._create_elevenlabs_params(self.param_frame_container)

        # Text Input Area
        text_frame = ttk.LabelFrame(right_panel, text="Text to Synthesize", padding="10")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        self.text_input = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, height=10, undo=True) # Enable undo stack
        self.text_input.pack(fill=tk.BOTH, expand=True)
        self.text_input.insert(tk.END, "Enter your text here...")
        # Bind context menu and keyboard shortcuts
        self.text_input.bind("<Button-3>", self._show_text_context_menu) # Right-click
        self.text_input.bind("<Control-a>", self._text_select_all); self.text_input.bind("<Control-A>", self._text_select_all) # Select All
        self.text_input.bind("<Control-z>", self._text_undo); self.text_input.bind("<Control-Z>", self._text_undo)       # Undo
        self.text_input.bind("<Control-y>", self._text_redo); self.text_input.bind("<Control-Y>", self._text_redo)       # Redo

        # Output File Selection
        output_frame = ttk.LabelFrame(right_panel, text="Output File", padding="10")
        output_frame.pack(fill=tk.X, pady=5, padx=5)
        ttk.Label(output_frame, text="Save as:").pack(side=tk.LEFT, padx=5)
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_file_path, width=50)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.browse_output_button = ttk.Button(output_frame, text="Browse...", command=self.browse_save_file)
        self.browse_output_button.pack(side=tk.LEFT, padx=5)
        # Set default output path
        default_output_filename = os.path.join(DEFAULT_OUTPUT_DIR, "output.wav")
        self.output_file_path.set(default_output_filename)

        # Action Buttons and Status Bar
        action_frame = ttk.Frame(right_panel, padding="10")
        action_frame.pack(fill=tk.X, pady=5, padx=5)
        self.synthesize_button = ttk.Button(action_frame, text="Start Synthesis", command=self.start_synthesis_thread)
        self.synthesize_button.pack(side=tk.LEFT, padx=10)
        self.status_label = ttk.Label(action_frame, text="Ready.", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        # --- Final Initialization Steps ---
        self.update_parameter_ui() # Show the parameters for the default model

        # Attempt initial ElevenLabs setup using the first key found in .env (if any)
        if self.elevenlabs_api_keys:
             first_key_name = list(self.elevenlabs_api_keys.keys())[0]
             first_key = self.elevenlabs_api_keys[first_key_name]
             logging.info(f"Attempting initial EL setup with key '{first_key_name}' from .env")
             self._set_active_elevenlabs_key(first_key) # Validate and set as active
        else:
             logging.info("No EL keys found in .env. Manual input required for ElevenLabs.")
             self.current_elevenlabs_key = None # Ensure no key is active
             # Keep refresh button disabled if no key is active initially
             if hasattr(self, 'refresh_voices_button'): self.refresh_voices_button.config(state=tk.DISABLED)

        self.load_existing_audio() # Load previous audio files

        # Show warning and disable playback if mixer failed
        if not self.mixer_initialized:
            self.disable_playback_controls()
            messagebox.showwarning("Audio Error", "Could not initialize audio playback.\nPlayback functions are disabled.", parent=self)

        # Set window closing behavior
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

# --- Application Entry Point ---
if __name__ == "__main__":
    # Create and run the application
    app = TTSApp()
    app.mainloop()
