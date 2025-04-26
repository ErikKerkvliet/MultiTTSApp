# ui_engines/elevenlabs_ui.py
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
from typing import Optional, List, Tuple, Dict

# Import the engine functions ONLY NEEDED for validation/fetching within this UI module
# Keep the actual synthesis call within app.py's thread logic
try:
    from tts_engines import elevenlabs_engine
except ImportError:
    print("ERROR: Could not import elevenlabs_engine in elevenlabs_ui.py")
    # You might want a more robust way to handle this, maybe disable EL UI
    elevenlabs_engine = None # Avoid crashing if import fails

# --- Global variables within the module to hold widget references ---
# These are needed because callbacks are defined outside the create_ui function
# but need to access widgets created within it.
_refresh_voices_button = None
_voice_dropdown = None
_api_key_entry = None
_key_selector = None

# --- Helper Functions specific to ElevenLabs UI ---

def _set_active_elevenlabs_key(app_instance, key_to_set: Optional[str]) -> bool:
    """Validates the given key using the engine and updates UI state."""
    global _refresh_voices_button, _voice_dropdown
    if not elevenlabs_engine:
        app_instance.update_status("ElevenLabs engine module not loaded.", clear_after=10)
        return False

    app_instance.update_status(f"Validating ElevenLabs API key...")
    validated_key = elevenlabs_engine.validate_api_key(key_to_set)

    if validated_key:
        app_instance.current_elevenlabs_key = validated_key # Store the validated key in app instance
        app_instance.update_status("ElevenLabs API key validated successfully.", clear_after=5)
        # Enable the refresh button now that we have a valid key
        if _refresh_voices_button: _refresh_voices_button.config(state=tk.NORMAL)
        # Automatically fetch voices after successful validation
        refresh_elevenlabs_voices_thread(app_instance) # Pass app_instance
        return True
    else:
        app_instance.current_elevenlabs_key = None # Clear the active key in app instance
        app_instance.update_status("ElevenLabs API key validation failed.", clear_after=10)
        # Disable voice-related controls
        if _refresh_voices_button: _refresh_voices_button.config(state=tk.DISABLED)
        if _voice_dropdown:
            _voice_dropdown.config(state=tk.DISABLED, values=[])
            app_instance.elevenlabs_voice_name.set("") # Update the app's StringVar
        if hasattr(app_instance, 'elevenlabs_voices'):
            app_instance.elevenlabs_voices.clear() # Clear internal voice mapping in app instance
        # Optionally, show a more prominent error message
        # messagebox.showerror("API Key Error", "The provided ElevenLabs API key failed validation.", parent=app_instance)
        return False

def on_key_selected(event, app_instance, key_name_var, manual_key_var):
    """Handles selection of an API key from the .env dropdown."""
    global _api_key_entry
    selected_name = key_name_var.get()
    if selected_name in app_instance.elevenlabs_api_keys:
        selected_key = app_instance.elevenlabs_api_keys[selected_name]
        logging.info(f"[EL UI] Selected key '{selected_name}' from dropdown.")
        # Clear the manual input field if a dropdown key is chosen
        if _api_key_entry: manual_key_var.set("")
        # Validate and set this key as the active one
        _set_active_elevenlabs_key(app_instance, selected_key)
    else:
        logging.warning(f"[EL UI] Selected key name '{selected_name}' not found in loaded keys.")

def use_manual_key(app_instance, manual_key_var, key_name_var):
    """Handles the 'Use This' button for the manually entered API key."""
    global _key_selector
    manual_key = manual_key_var.get().strip()
    if manual_key:
        logging.info("[EL UI] Attempting to use manually entered API key.")
        # Clear the dropdown selection to indicate manual key usage
        if _key_selector: key_name_var.set("")
        # Validate and set this key as the active one
        _set_active_elevenlabs_key(app_instance, manual_key)
    else:
        messagebox.showwarning("No Key", "Please enter an API key manually first.", parent=app_instance)

def refresh_elevenlabs_voices_thread(app_instance):
    """Starts fetching ElevenLabs voices in a background thread."""
    global _refresh_voices_button
    # Only proceed if there's a currently active (validated) key in the app instance
    if not app_instance.current_elevenlabs_key:
        messagebox.showwarning("API Key Needed", "Please select or enter a valid ElevenLabs API key first.", parent=app_instance)
        return
    if not elevenlabs_engine:
        app_instance.update_status("ElevenLabs engine module not loaded.", clear_after=10)
        return

    app_instance.update_status("Fetching ElevenLabs voices...")
    # Disable button during refresh
    if _refresh_voices_button: _refresh_voices_button.config(state=tk.DISABLED)
    # Pass the active key to the worker thread
    thread = threading.Thread(
        target=_get_voices_worker,
        args=(app_instance, app_instance.current_elevenlabs_key), # Pass app_instance and key
        daemon=True
    )
    thread.start()

def _get_voices_worker(app_instance, api_key: str):
    """Worker function (runs in thread) to fetch voices using the provided key."""
    voices_result, error = None, None
    if not elevenlabs_engine:
        error = Exception("ElevenLabs engine module not loaded.")
        # Schedule the UI update back on the main thread using app_instance.after
        app_instance.after(0, _update_elevenlabs_voice_list, app_instance, voices_result, error)
        return

    try:
        # Call the engine function with the validated API key
        voices_result = elevenlabs_engine.get_elevenlabs_voices(api_key)
    except Exception as e:
        error = e
        logging.error(f"[EL UI] Error in _get_voices_worker thread: {e}", exc_info=True)
    # Schedule the UI update back on the main thread using app_instance.after
    app_instance.after(0, _update_elevenlabs_voice_list, app_instance, voices_result, error)

def _update_elevenlabs_voice_list(app_instance, voices_result: Optional[List[Tuple[str, str]]], error: Optional[Exception]):
    """Updates the voice dropdown list in the main GUI thread."""
    global _refresh_voices_button, _voice_dropdown
    # Re-enable refresh button only if a key is currently considered valid
    if _refresh_voices_button:
        new_state = tk.NORMAL if app_instance.current_elevenlabs_key else tk.DISABLED
        _refresh_voices_button.config(state=new_state)

    # Handle errors first
    if error:
        app_instance.update_status(f"Error fetching voices: {error}", clear_after=10)
        messagebox.showerror("Error Fetching Voices", f"Could not fetch ElevenLabs voices:\n{error}", parent=app_instance)
        # Reset voice list UI elements
        if _voice_dropdown:
             _voice_dropdown.config(state=tk.DISABLED, values=[])
             app_instance.elevenlabs_voice_name.set("") # Update app's variable
        if hasattr(app_instance, 'elevenlabs_voices'):
             app_instance.elevenlabs_voices.clear() # Update app's voice map
        return

    # Process successful results
    if voices_result is not None and hasattr(app_instance, 'elevenlabs_voices'):
        app_instance.elevenlabs_voices.clear() # Clear previous mapping in app instance
        voice_names = []
        for name, voice_id in voices_result:
            app_instance.elevenlabs_voices[name] = voice_id # Store name -> ID map in app instance
            voice_names.append(name)

        if _voice_dropdown:
            _voice_dropdown.config(values=voice_names, state="readonly" if voice_names else "disabled")
            if voice_names:
                # Try to maintain current selection, otherwise use default or first
                default_voice = "Rachel" # A common voice
                current_selection = app_instance.elevenlabs_voice_name.get()
                if current_selection and current_selection in app_instance.elevenlabs_voices:
                    app_instance.elevenlabs_voice_name.set(current_selection) # Keep current if valid
                elif default_voice in app_instance.elevenlabs_voices:
                    app_instance.elevenlabs_voice_name.set(default_voice) # Use default
                else:
                    app_instance.elevenlabs_voice_name.set(voice_names[0]) # Use first available
                app_instance.update_status(f"{len(voice_names)} ElevenLabs voices loaded.", clear_after=5)
            else:
                # No voices found
                app_instance.elevenlabs_voice_name.set("")
                app_instance.update_status("No ElevenLabs voices found.", clear_after=5)
    else:
        # Should ideally not happen if error is None, but good to handle
        app_instance.update_status("Unknown state after fetching voices.", clear_after=10)


# --- Main UI Creation Function ---

def create_elevenlabs_ui(parent, app_instance, key_name_var, manual_key_var, voice_name_var, model_id_var, api_keys_dict, elevenlabs_models_list):
    """
    Creates the parameter frame specific to the ElevenLabs engine.

    Args:
        parent: The parent widget (ttk.Frame) to place this UI in.
        app_instance: The main TTSApp instance (needed for callbacks, status updates, etc.).
        key_name_var: tk.StringVar for the selected key name from .env.
        manual_key_var: tk.StringVar for the manually entered API key.
        voice_name_var: tk.StringVar for the selected voice name.
        model_id_var: tk.StringVar for the selected model ID.
        api_keys_dict: Dictionary of {name: key} loaded from .env.
        elevenlabs_models_list: List of available ElevenLabs model IDs.

    Returns:
        The created ttk.LabelFrame containing the ElevenLabs parameters.
    """
    global _refresh_voices_button, _voice_dropdown, _api_key_entry, _key_selector

    elevenlabs_frame = ttk.LabelFrame(parent, text="ElevenLabs Parameters", padding="10")

    # --- Key Selection ---
    key_select_frame = ttk.Frame(elevenlabs_frame)
    key_select_frame.pack(fill=tk.X, pady=5)
    ttk.Label(key_select_frame, text="Select Key (.env):").pack(side=tk.LEFT, padx=(0, 5))
    key_names = list(api_keys_dict.keys())
    _key_selector = ttk.Combobox(
        key_select_frame,
        textvariable=key_name_var,
        values=key_names,
        state="readonly" if key_names else "disabled",
        width=20
    )
    _key_selector.pack(side=tk.LEFT, padx=(0, 10))
    # When a key is selected, call on_key_selected (pass necessary args)
    _key_selector.bind("<<ComboboxSelected>>", lambda e: on_key_selected(e, app_instance, key_name_var, manual_key_var))
    # Set the first key as default display if available
    if key_names: key_name_var.set(key_names[0])

    # --- Manual Key Input ---
    key_manual_frame = ttk.Frame(elevenlabs_frame)
    key_manual_frame.pack(fill=tk.X, pady=(0, 5))
    ttk.Label(key_manual_frame, text="Or enter manually:").pack(side=tk.LEFT, padx=(0, 5))
    _api_key_entry = ttk.Entry(
        key_manual_frame,
        textvariable=manual_key_var,
        show="*",
        width=30
    )
    _api_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    ttk.Button(key_manual_frame, text="Use This", command=lambda: use_manual_key(app_instance, manual_key_var, key_name_var)).pack(side=tk.LEFT, padx=(5, 0))

    # --- Voice Selection ---
    voice_frame = ttk.Frame(elevenlabs_frame)
    voice_frame.pack(fill=tk.X, pady=5)
    ttk.Label(voice_frame, text="Voice:").pack(side=tk.LEFT, padx=(0, 5))
    _voice_dropdown = ttk.Combobox(
        voice_frame,
        textvariable=voice_name_var, # Use the variable from app_instance
        state="disabled",
        width=38
    )
    _voice_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)
    _refresh_voices_button = ttk.Button(
        voice_frame,
        text="Refresh",
        command=lambda: refresh_elevenlabs_voices_thread(app_instance), # Pass app_instance
        state=tk.DISABLED # Initially disabled
    )
    _refresh_voices_button.pack(side=tk.LEFT, padx=(5, 0))

    # --- Model Selection ---
    model_frame = ttk.Frame(elevenlabs_frame)
    model_frame.pack(fill=tk.X, pady=(0, 5))
    ttk.Label(model_frame, text="Model:").pack(side=tk.LEFT, padx=(0, 5))
    model_dropdown = ttk.Combobox( # No need for global ref if not modified by callbacks
        model_frame,
        textvariable=model_id_var,
        values=elevenlabs_models_list,
        state="readonly"
    )
    model_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)
    # Set a default model if the list is not empty
    if elevenlabs_models_list: model_id_var.set(elevenlabs_models_list[0])

    # --- Initial Setup Attempt ---
    # Try to validate the first key from .env if available on creation
    if key_names:
        first_key_name = key_names[0]
        first_key = api_keys_dict[first_key_name]
        logging.info(f"[EL UI] Attempting initial setup with key '{first_key_name}'")
        # Use app_instance.after to ensure this runs after the main loop starts
        # and doesn't block UI creation. Schedule the validation.
        app_instance.after(100, lambda: _set_active_elevenlabs_key(app_instance, first_key))
    else:
        logging.info("[EL UI] No EL keys found in .env. Manual input required.")
        app_instance.current_elevenlabs_key = None # Ensure no key active in app

    return elevenlabs_frame