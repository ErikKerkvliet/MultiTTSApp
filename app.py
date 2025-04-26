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
from typing import Optional, List, Tuple, Dict

# --- Third-Party Imports ---
import pygame         # For audio playback
import soundfile as sf # For reading audio file duration (WAV)
from dotenv import load_dotenv # For loading API keys from .env file

# --- Local Imports ---
# Import engine *synthesis functions* from the tts_engines package
try:
    from tts_engines import xtts_engine, piper_engine, bark_engine, elevenlabs_engine
except ImportError as e:
    print(f"ERROR: Could not import TTS engines. Error:\n{traceback.format_exc()}")
    print("Ensure the 'tts_engines' directory exists alongside app.py and")
    print("all required dependencies (TTS, piper-tts, transformers, elevenlabs, etc.) are installed.")
    exit(1)

# Import *engine UI creation functions* from the ui_engines package
try:
    from ui_engines import xtts_ui, piper_ui, bark_ui, elevenlabs_ui
except ImportError as e:
    print(f"ERROR: Could not import UI engines. Error:\n{traceback.format_exc()}")
    print("Ensure the 'ui_engines' directory exists alongside app.py.")
    exit(1)
# --------------------------------

# --- Load Environment Variables ---
load_dotenv()
# --------------------------------

# --- Basic Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [GUI] %(message)s'
)

# --- Default Paths and Constants ---
DEFAULT_OUTPUT_DIR = "audio_output"
DEFAULT_SPEAKER_DIR = "speaker_samples"
DEFAULT_PIPER_MODEL_DIR = "models/piper"
DEFAULT_BARK_VOICES = [ # Keep this here as it's app-level config
    "v2/en_speaker_0", "v2/en_speaker_1", "v2/en_speaker_2", "v2/en_speaker_3",
    "v2/en_speaker_4", "v2/en_speaker_5", "v2/en_speaker_6", "v2/en_speaker_7",
    "v2/en_speaker_8", "v2/en_speaker_9", "v2/de_speaker_1", "v2/es_speaker_1",
    "v2/fr_speaker_1", "v2/it_speaker_1", "v2/ja_speaker_1", "v2/ko_speaker_1",
    "v2/pl_speaker_1", "v2/pt_speaker_1", "v2/ru_speaker_1", "v2/tr_speaker_1",
    "v2/zh_speaker_1", "v2/nl_speaker_0", "v2/nl_speaker_1",
]
# Get ElevenLabs models list from the engine module (still needed for dropdown)
ELEVENLABS_MODELS = elevenlabs_engine.ELEVENLABS_MODELS if elevenlabs_engine else []


# --- Main Application Class ---
class TTSApp(tk.Tk):
    """
    Main application class for the Multi TTS Synthesizer.

    Inherits from tk.Tk to create the main window.
    Manages the GUI layout, state, and interaction with TTS engines.
    """

    # --- Method Definitions First (for correct binding/command references) ---

    # --- UI Element Creation Functions (REMOVED - Now in ui_engines) ---
    # _create_xtts_params REMOVED
    # _create_piper_params REMOVED
    # _create_bark_params REMOVED
    # _create_elevenlabs_params REMOVED

    # --- Text Input Context Menu Methods (UNCHANGED) ---
    def _create_text_context_menu(self):
        """Creates the right-click context menu for the text input field."""
        if not hasattr(self, 'text_context_menu'):
            self.text_context_menu = tk.Menu(self, tearoff=0)
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
        if not hasattr(self, 'text_input') or not hasattr(self, 'text_context_menu'): return
        self.text_input.focus_set()
        try: self.text_context_menu.entryconfig("Undo (Ctrl+Z)", state=tk.NORMAL)
        except tk.TclError: pass
        try: self.text_context_menu.entryconfig("Redo (Ctrl+Y)", state=tk.NORMAL)
        except tk.TclError: pass
        try:
            has_selection = bool(self.text_input.tag_ranges(tk.SEL)); state = tk.NORMAL if has_selection else tk.DISABLED
            self.text_context_menu.entryconfig("Cut", state=state); self.text_context_menu.entryconfig("Copy", state=state)
        except tk.TclError: self.text_context_menu.entryconfig("Cut", state=tk.DISABLED); self.text_context_menu.entryconfig("Copy", state=tk.DISABLED)
        try: self.clipboard_get(); self.text_context_menu.entryconfig("Paste", state=tk.NORMAL)
        except tk.TclError: self.text_context_menu.entryconfig("Paste", state=tk.DISABLED)
        try: self.text_context_menu.entryconfig("Select All (Ctrl+A)", state=tk.NORMAL)
        except tk.TclError: pass
        self.text_context_menu.tk_popup(event.x_root, event.y_root)

    def _text_cut(self):
        if hasattr(self, 'text_input'):
            try: self.text_input.event_generate("<<Cut>>")
            except tk.TclError: pass
    def _text_copy(self):
        if hasattr(self, 'text_input'):
            try: self.text_input.event_generate("<<Copy>>")
            except tk.TclError: pass
    def _text_paste(self):
        if hasattr(self, 'text_input'):
            try: self.text_input.event_generate("<<Paste>>")
            except tk.TclError: pass
    def _text_select_all(self, event=None):
        if hasattr(self, 'text_input'):
            try: self.text_input.tag_add(tk.SEL, "1.0", tk.END); self.text_input.mark_set(tk.INSERT, "1.0"); self.text_input.see(tk.INSERT); return "break"
            except tk.TclError: pass
    def _text_undo(self, event=None):
        if hasattr(self, 'text_input'):
            try: self.text_input.edit_undo()
            except tk.TclError: logging.info("Undo stack is empty."); return "break"
    def _text_redo(self, event=None):
        if hasattr(self, 'text_input'):
            try: self.text_input.edit_redo()
            except tk.TclError: logging.info("Redo stack is empty."); return "break"

    # --- General UI Helper Methods (UNCHANGED, except browse_file/save usage) ---
    def update_parameter_ui(self, event=None):
        """Shows/hides the appropriate parameter frame based on model selection."""
        selected_model = self.model_choice.get()
        logging.info(f"Switching parameter view to: {selected_model}")

        # Hide all parameter frames first, checking if they exist
        if hasattr(self, 'xtts_frame') and self.xtts_frame: self.xtts_frame.pack_forget()
        if hasattr(self, 'piper_frame') and self.piper_frame: self.piper_frame.pack_forget()
        if hasattr(self, 'bark_frame') and self.bark_frame: self.bark_frame.pack_forget()
        if hasattr(self, 'elevenlabs_frame') and self.elevenlabs_frame: self.elevenlabs_frame.pack_forget()

        # Show the frame corresponding to the selected model
        if selected_model == "XTTSv2" and hasattr(self, 'xtts_frame') and self.xtts_frame: self.xtts_frame.pack(fill=tk.X)
        elif selected_model == "Piper" and hasattr(self, 'piper_frame') and self.piper_frame: self.piper_frame.pack(fill=tk.X)
        elif selected_model == "Bark" and hasattr(self, 'bark_frame') and self.bark_frame: self.bark_frame.pack(fill=tk.X)
        elif selected_model == "ElevenLabs" and hasattr(self, 'elevenlabs_frame') and self.elevenlabs_frame: self.elevenlabs_frame.pack(fill=tk.X)

        self.update_idletasks()

    def browse_file(self, string_var: tk.StringVar, title: str, filetypes: list, initialdir: str):
        """Opens a file dialog and sets the selected path to a StringVar. (Called by UI modules)"""
        if not os.path.isdir(initialdir): initialdir = os.path.expanduser("~")
        filename = filedialog.askopenfilename(title=title, filetypes=filetypes, initialdir=initialdir)
        if filename: string_var.set(filename)

    def browse_save_file(self):
        """Opens a save file dialog for the output WAV file. (Called by app button)"""
        current_path = self.output_file_path.get()
        initial_filename = os.path.basename(current_path) if current_path else "output.wav"
        initial_dir = os.path.dirname(current_path) or DEFAULT_OUTPUT_DIR
        if not os.path.isdir(initial_dir): initial_dir = DEFAULT_OUTPUT_DIR
        filepath = filedialog.asksaveasfilename(title="Save Audio As", defaultextension=".wav", filetypes=[("WAV files", "*.wav"), ("All files", "*.*")], initialdir=initial_dir, initialfile=initial_filename)
        if filepath:
            if not filepath.lower().endswith(".wav"): filepath += ".wav"
            self.output_file_path.set(filepath)

    def update_status(self, message: str, clear_after: Optional[int] = None):
        """Updates the status bar text (thread-safe via self.after). (Called by UI modules and app logic)"""
        def _update_in_main_thread():
            if hasattr(self, 'status_label'):
                self.status_label.config(text=message)
                if clear_after is not None: self.after(clear_after * 1000, lambda: self.status_label.config(text="Ready.") if hasattr(self, 'status_label') else None)
        self.after(0, _update_in_main_thread)

    def set_ui_state(self, state: str):
        """Enables/disables main UI elements during processing."""
        gui_state = tk.NORMAL if state == 'normal' else tk.DISABLED
        if hasattr(self, 'synthesize_button'): self.synthesize_button.config(state=gui_state)
        if hasattr(self, 'model_menu'): self.model_menu.config(state=gui_state)
        if hasattr(self, 'browse_output_button'): self.browse_output_button.config(state=gui_state)
        # Playback controls have their own logic

    # --- ElevenLabs Specific UI Methods (REMOVED - Now in ui_engines/elevenlabs_ui.py) ---
    # _set_active_elevenlabs_key REMOVED
    # on_key_selected REMOVED
    # use_manual_key REMOVED
    # refresh_elevenlabs_voices_thread REMOVED
    # _get_voices_worker REMOVED
    # _update_elevenlabs_voice_list REMOVED

    # --- Audio List & Playback Methods (UNCHANGED) ---
    def load_existing_audio(self):
        if not hasattr(self, 'audio_listbox'): return
        self.audio_listbox.delete(0, tk.END); self.audio_files.clear()
        try:
            audio_exts = ('*.wav', '*.mp3'); all_audio_files = []
            for ext in audio_exts: all_audio_files.extend(glob.glob(os.path.join(DEFAULT_OUTPUT_DIR, ext)))
            all_audio_files.sort(key=os.path.getmtime, reverse=True)
            for f_path in all_audio_files: f_name = os.path.basename(f_path); self.audio_files[f_name] = f_path; self.audio_listbox.insert(tk.END, f_name)
            logging.info(f"{len(self.audio_files)} existing audio files loaded.")
        except Exception as e: logging.error(f"Error loading existing audio: {e}")

    def add_audio_to_list(self, file_path: str):
        if not hasattr(self, 'audio_listbox'): return
        if os.path.exists(file_path):
            f_name = os.path.basename(file_path)
            if f_name not in self.audio_files:
                self.audio_files[f_name] = file_path; self.audio_listbox.insert(0, f_name)
                logging.info(f"Audio file added to list: {f_name}")
                self.audio_listbox.selection_clear(0, tk.END); self.audio_listbox.selection_set(0); self.on_audio_select()

    def on_audio_select(self, event=None):
        if not self.mixer_initialized or not hasattr(self, 'audio_listbox'): return
        selected_indices = self.audio_listbox.curselection()
        if not selected_indices: self.selected_audio_path = None; self.disable_playback_controls(); return
        selected_filename = self.audio_listbox.get(selected_indices[0])
        if selected_filename in self.audio_files:
            new_path = self.audio_files[selected_filename]
            if new_path != self.selected_audio_path:
                self.selected_audio_path = new_path; logging.info(f"Selected audio: {self.selected_audio_path}"); self.stop_audio()
                try:
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
        if hasattr(self, 'play_button'): self.play_button.config(state=tk.DISABLED)
        if hasattr(self, 'pause_button'): self.pause_button.config(state=tk.DISABLED)
        if hasattr(self, 'stop_button'): self.stop_button.config(state=tk.DISABLED)
        if hasattr(self, 'seek_slider'): self.seek_slider.config(state=tk.DISABLED, value=0)
        self.audio_duration = 0.0; self.update_time_label()

    def enable_playback_controls(self):
        if not self.mixer_initialized: return
        if hasattr(self, 'play_button') and hasattr(self, 'pause_button') and hasattr(self, 'stop_button') and hasattr(self, 'seek_slider'):
            if self.selected_audio_path: self.play_button.config(state=tk.NORMAL); self.pause_button.config(state=tk.DISABLED); self.stop_button.config(state=tk.DISABLED); self.seek_slider.config(state=tk.NORMAL)
            else: self.disable_playback_controls()

    def format_time(self, seconds: float) -> str:
        minutes, seconds = divmod(int(max(0, seconds)), 60); return f"{minutes:02d}:{seconds:02d}"
    def update_time_label(self, current_time: float = 0.0):
        if hasattr(self, 'time_label'): self.time_label.config(text=f"{self.format_time(current_time)} / {self.format_time(self.audio_duration)}")

    def play_audio(self):
        if not self.mixer_initialized or not self.selected_audio_path: return
        try:
            if not pygame.mixer.music.get_busy() and not self.is_paused:
                pygame.mixer.music.load(self.selected_audio_path); pygame.mixer.music.play(); self.is_paused = False; self.start_playback_update()
            elif self.is_paused:
                pygame.mixer.music.unpause(); self.is_paused = False; self.start_playback_update()
            if hasattr(self, 'play_button'): self.play_button.config(state=tk.DISABLED)
            if hasattr(self, 'pause_button'): self.pause_button.config(state=tk.NORMAL)
            if hasattr(self, 'stop_button'): self.stop_button.config(state=tk.NORMAL)
        except Exception as e: logging.error(f"Error playing audio: {e}", exc_info=True); messagebox.showerror("Playback Error", f"Could not play audio:\n{e}"); self.stop_audio()

    def pause_audio(self):
        if not self.mixer_initialized or not pygame.mixer.music.get_busy(): return
        pygame.mixer.music.pause(); self.is_paused = True; self.stop_playback_update()
        if hasattr(self, 'play_button'): self.play_button.config(state=tk.NORMAL)
        if hasattr(self, 'pause_button'): self.pause_button.config(state=tk.DISABLED)
        if hasattr(self, 'stop_button'): self.stop_button.config(state=tk.NORMAL)

    def stop_audio(self):
        if not self.mixer_initialized: return
        if pygame.mixer.music.get_busy() or self.is_paused:
            pygame.mixer.music.stop(); pygame.mixer.music.unload(); self.is_paused = False; self.stop_playback_update()
            if hasattr(self, 'seek_slider'): self.seek_slider.set(0)
            self.update_time_label()
            if self.selected_audio_path: self.enable_playback_controls()
            else: self.disable_playback_controls()

    def start_playback_update(self):
        if hasattr(self, 'playback_update_id') and self.playback_update_id:
            try: self.after_cancel(self.playback_update_id)
            except ValueError: pass
        self.update_playback_slider()

    def stop_playback_update(self):
        if hasattr(self, 'playback_update_id') and self.playback_update_id:
            try: self.after_cancel(self.playback_update_id)
            except ValueError: pass
            self.playback_update_id = None

    def update_playback_slider(self):
        if not self.mixer_initialized: return
        if not hasattr(self, 'playback_update_id'): self.playback_update_id = None
        self.playback_update_id = self.after(250, self.update_playback_slider)
        if pygame.mixer.music.get_busy() and not self.is_paused and not self.is_seeking:
            if hasattr(self, 'seek_slider'):
                try:
                    current_pos_ms = pygame.mixer.music.get_pos()
                    if current_pos_ms != -1:
                        current_pos_sec = max(0, min(current_pos_ms / 1000.0, self.audio_duration))
                        self.seek_slider.set(current_pos_sec); self.update_time_label(current_pos_sec)
                except pygame.error as e: logging.warning(f"Pygame error getting pos: {e}"); self.stop_audio_if_finished()
                except Exception as e: logging.error(f"Error updating slider: {e}"); self.stop_playback_update()
        elif not pygame.mixer.music.get_busy() and not self.is_paused:
            self.stop_audio_if_finished()

    def stop_audio_if_finished(self):
        if hasattr(self, 'play_button') and self.play_button['state'] == tk.DISABLED and not self.is_paused:
            if not pygame.mixer.music.get_busy():
                logging.info("Playback finished naturally.")
                self.after(100, self.stop_audio)
                self.stop_playback_update()

    def on_seek_press(self, event):
        if hasattr(self, 'seek_slider') and self.seek_slider['state'] == tk.NORMAL: self.is_seeking = True
    def on_seek_release(self, event):
        if hasattr(self, 'seek_slider') and self.seek_slider['state'] == tk.NORMAL and self.is_seeking:
            self.is_seeking = False; self.seek_audio(self.seek_slider.get())
    def on_seek_slider_move(self, value):
        self.update_time_label(float(value))

    def seek_audio(self, seconds: float):
        if not self.mixer_initialized or not self.selected_audio_path: return
        try:
            seek_time_sec = max(0, min(seconds, self.audio_duration))
            pygame.mixer.music.play(start=seek_time_sec);
            logging.info(f"Seeked to {seek_time_sec:.2f}s")
            if self.is_paused: pygame.mixer.music.pause()
            else:
                self.start_playback_update()
                if hasattr(self, 'play_button'): self.play_button.config(state=tk.DISABLED)
                if hasattr(self, 'pause_button'): self.pause_button.config(state=tk.NORMAL)
                if hasattr(self, 'stop_button'): self.stop_button.config(state=tk.NORMAL)
            if hasattr(self, 'seek_slider'): self.seek_slider.set(seek_time_sec)
            self.update_time_label(seek_time_sec)
        except pygame.error as e: logging.error(f"Pygame seek error: {e}", exc_info=True); messagebox.showerror("Playback Error", f"Seek error:\n{e}")
        except Exception as e: logging.error(f"Seek error: {e}", exc_info=True); messagebox.showerror("Playback Error", f"Unexpected seek error:\n{e}")

    # --- Synthesis Logic (UNCHANGED, except for EL parameter gathering) ---
    def start_synthesis_thread(self):
        if not hasattr(self, 'text_input'): messagebox.showerror("Error", "Text input field not initialized."); return
        text = self.text_input.get("1.0", tk.END).strip()
        output_path = self.output_file_path.get().strip()
        model_type = self.model_choice.get()

        if not text: messagebox.showerror("Input Error", "Please enter text to synthesize."); return
        if not output_path: messagebox.showerror("Input Error", "Please specify an output file."); return
        if not output_path.lower().endswith(".wav"): output_path += ".wav"; self.output_file_path.set(output_path)
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            try: os.makedirs(output_dir); logging.info(f"Output directory created: {output_dir}");
            except OSError as e: messagebox.showerror("Error", f"Could not create output directory:\n{e}"); return
        if not model_type: messagebox.showerror("Input Error", "Please select a TTS model."); return

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
                selected_voice_name = self.elevenlabs_voice_name.get() # Get name from StringVar
                if not selected_voice_name: raise ValueError("Please select an ElevenLabs voice.")
                 # Look up ID in the app's voice map (populated by elevenlabs_ui)
                if selected_voice_name not in self.elevenlabs_voices: raise ValueError(f"Selected voice '{selected_voice_name}' not found or voices not loaded.")
                params['voice_id'] = self.elevenlabs_voices[selected_voice_name] # Use the map
                params['model_id'] = self.elevenlabs_model_id.get()
                if not params['model_id']: raise ValueError("Please select an ElevenLabs model.")
                # Pass the currently active validated key stored in the app instance
                if not self.current_elevenlabs_key: raise ValueError("ElevenLabs API key is not set or validated. Please select/enter a valid key via the UI.")
                params['api_key'] = self.current_elevenlabs_key
                target_function = elevenlabs_engine.synthesize_elevenlabs
            else:
                raise ValueError(f"Unknown model type selected: {model_type}")

        except (ValueError, FileNotFoundError) as e: messagebox.showerror("Parameter Error", str(e)); return
        except Exception as e: messagebox.showerror("Unexpected Error", f"Error preparing synthesis: {e}"); logging.error("Error preparing synthesis", exc_info=True); return

        self.set_ui_state('disabled')
        self.update_status(f"Starting {model_type} synthesis...")
        synthesis_thread = threading.Thread(target=self.run_synthesis, args=(target_function, params, output_path), daemon=True)
        synthesis_thread.start()

    def run_synthesis(self, synthesis_function, params: dict, generated_file_path: str):
        """Runs the synthesis function in the worker thread and handles UI updates."""
        success, message = False, "Synthesis started..."
        start_time = time.time()
        try:
            self.update_status(f"Synthesizing... ({self.model_choice.get()}) This may take a while.")
            log_params = {k: v for k, v in params.items() if k != 'api_key'} # Avoid logging key
            logging.info(f"Calling {synthesis_function.__name__} with params: {log_params}")
            success, message = synthesis_function(**params) # Call the engine
        except Exception as e:
            success = False; message = f"Unexpected error during synthesis: {e}"
            logging.error(f"Synthesis error in worker thread: {e}\n{traceback.format_exc()}")
        finally:
            self.after(0, lambda: self.set_ui_state('normal'))
            duration = time.time() - start_time
            final_message = f"{message} (Duration: {duration:.2f} sec)"
            if success:
                final_path_to_add = generated_file_path
                if "as MP3!" in message and message.endswith(".mp3"): final_path_to_add = message.split(" in ")[-1]
                self.update_status("Synthesis complete.", clear_after=10)
                self.after(0, self.add_audio_to_list, final_path_to_add)
                self.after(0, lambda: messagebox.showinfo("Success", final_message))
            else:
                self.update_status("Synthesis failed.", clear_after=10)
                self.after(0, lambda: messagebox.showerror("Error", final_message))

    # --- Application Closing (UNCHANGED) ---
    def on_closing(self):
        logging.info("Closing application..."); self.stop_playback_update()
        if self.mixer_initialized:
            logging.info("Stopping pygame mixer...");
            try: pygame.mixer.music.stop(); pygame.mixer.quit(); pygame.quit(); logging.info("Pygame closed successfully.")
            except Exception as e: logging.error(f"Error closing pygame: {e}")
        self.destroy()

    # --- Initialization Method (MODIFIED) ---
    def __init__(self):
        """Initializes the TTSApp class, sets up UI and variables."""
        super().__init__()
        self.title("Multi TTS Synthesizer")
        self.geometry("950x650")

        # --- Initialize Pygame Mixer ---
        try:
            pygame.init(); pygame.mixer.init(); logging.info("Pygame mixer initialized.")
            self.mixer_initialized = True
        except Exception as e:
            logging.error(f"Could not initialize pygame mixer: {e}", exc_info=True)
            self.mixer_initialized = False

        # --- Ensure Output Directory Exists ---
        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)

        # --- Initialize Application State Variables (Tkinter Vars) ---
        # These need to be owned by the main app instance so they persist
        # and can be accessed by synthesis logic. They are passed to UI modules.
        self.model_choice = tk.StringVar(self)
        # XTTS
        self.xtts_speaker_wav = tk.StringVar(self); self.xtts_language = tk.StringVar(self, value="nl")
        # Piper
        self.piper_onnx_path = tk.StringVar(self); self.piper_json_path = tk.StringVar(self)
        # Bark
        self.bark_voice_preset = tk.StringVar(self)
        # ElevenLabs (Variables for UI elements)
        self.selected_elevenlabs_key_name = tk.StringVar(self)
        self.elevenlabs_api_key_manual_input = tk.StringVar(self)
        self.elevenlabs_voice_name = tk.StringVar(self) # Name selected in dropdown
        self.elevenlabs_model_id = tk.StringVar(self)
        # ElevenLabs (Non-Tk variables managed by app/UI logic)
        self.elevenlabs_api_keys: Dict[str, str] = {} # {Name: Key} from .env
        self.current_elevenlabs_key: Optional[str] = None # The currently active *validated* key
        self.elevenlabs_voices: Dict[str, str] = {} # {Name: ID} map, populated by elevenlabs_ui
        # General / Playback
        self.output_file_path = tk.StringVar(self)
        self.audio_files: Dict[str, str] = {}
        self.selected_audio_path: Optional[str] = None
        self.audio_duration: float = 0.0
        self.playback_update_id: Optional[str] = None # Tkinter after ID
        self.is_paused: bool = False
        self.is_seeking: bool = False

        # --- Read API Keys from .env ---
        key_prefix = "ELEVENLABS_API_KEY_"
        for key, value in os.environ.items():
            if key.startswith(key_prefix) and value:
                name = key.replace(key_prefix, "")
                if name: self.elevenlabs_api_keys[name] = value
        logging.info(f"{len(self.elevenlabs_api_keys)} ElevenLabs keys found from .env: {list(self.elevenlabs_api_keys.keys())}")

        # --- Create UI Elements ---
        self._create_text_context_menu()

        # Main Layout
        self.paned_window = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Left Panel: Audio List and Playback Controls (UNCHANGED LAYOUT) ---
        left_panel = ttk.Frame(self.paned_window, width=250)
        left_panel.pack(fill=tk.BOTH, expand=False)
        left_panel.columnconfigure(0, weight=1); left_panel.rowconfigure(0, weight=1)
        self.paned_window.add(left_panel, minsize=200)
        # Audio Files Listbox
        list_frame = ttk.LabelFrame(left_panel, text="Generated Audio", padding="5")
        list_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        list_frame.rowconfigure(0, weight=1); list_frame.columnconfigure(0, weight=1)
        self.audio_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE)
        self.audio_listbox.grid(row=0, column=0, sticky="nsew")
        list_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.audio_listbox.yview)
        list_scrollbar.grid(row=0, column=1, sticky="ns"); self.audio_listbox.config(yscrollcommand=list_scrollbar.set)
        self.audio_listbox.bind('<<ListboxSelect>>', self.on_audio_select)
        # Playback Controls Frame
        controls_frame = ttk.LabelFrame(left_panel, text="Playback Controls", padding="5")
        controls_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        controls_frame.columnconfigure((0, 1, 2), weight=1)
        self.play_button = ttk.Button(controls_frame, text="▶ Play", command=self.play_audio, state=tk.DISABLED)
        self.play_button.grid(row=0, column=0, padx=2, pady=5, sticky="ew")
        self.pause_button = ttk.Button(controls_frame, text="❚❚ Pause", command=self.pause_audio, state=tk.DISABLED)
        self.pause_button.grid(row=0, column=1, padx=2, pady=5, sticky="ew")
        self.stop_button = ttk.Button(controls_frame, text="■ Stop", command=self.stop_audio, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=2, padx=2, pady=5, sticky="ew")
        self.time_label = ttk.Label(controls_frame, text="00:00 / 00:00")
        self.time_label.grid(row=1, column=0, columnspan=3, pady=(5, 0))
        self.seek_slider = ttk.Scale(controls_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.on_seek_slider_move, state=tk.DISABLED)
        self.seek_slider.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 5))
        self.seek_slider.bind("<ButtonPress-1>", self.on_seek_press); self.seek_slider.bind("<ButtonRelease-1>", self.on_seek_release)

        # --- Right Panel: Configuration and Synthesis (UNCHANGED LAYOUT) ---
        right_panel = ttk.Frame(self.paned_window)
        right_panel.pack(fill=tk.BOTH, expand=True)
        self.paned_window.add(right_panel)

        # Model Selection Dropdown
        model_frame = ttk.LabelFrame(right_panel, text="TTS Engine Selection", padding="10")
        model_frame.pack(fill=tk.X, pady=5, padx=5)
        ttk.Label(model_frame, text="Choose Model:").pack(side=tk.LEFT, padx=5)
        model_options = ["XTTSv2", "Piper", "Bark", "ElevenLabs"]
        self.model_menu = ttk.Combobox(model_frame, textvariable=self.model_choice, values=model_options, state="readonly")
        self.model_menu.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.model_menu.bind("<<ComboboxSelected>>", self.update_parameter_ui)
        self.model_menu.current(0) # Default to first model

        # Container for Engine-Specific Parameters
        self.param_frame_container = ttk.Frame(right_panel)
        self.param_frame_container.pack(fill=tk.X, pady=5, padx=5)

        # --- Create Engine Parameter Frames using UI Modules ---
        # Store the returned frames as instance variables
        self.xtts_frame = xtts_ui.create_xtts_ui(
            self.param_frame_container, self.xtts_speaker_wav, self.xtts_language,
            self.browse_file, DEFAULT_SPEAKER_DIR
        )
        self.piper_frame = piper_ui.create_piper_ui(
            self.param_frame_container, self.piper_onnx_path, self.piper_json_path,
            self.browse_file, DEFAULT_PIPER_MODEL_DIR
        )
        self.bark_frame = bark_ui.create_bark_ui(
            self.param_frame_container, self.bark_voice_preset, DEFAULT_BARK_VOICES
        )
        self.elevenlabs_frame = elevenlabs_ui.create_elevenlabs_ui(
            self.param_frame_container, self, # Pass app instance
            self.selected_elevenlabs_key_name, self.elevenlabs_api_key_manual_input,
            self.elevenlabs_voice_name, self.elevenlabs_model_id,
            self.elevenlabs_api_keys, ELEVENLABS_MODELS
        )
        # Hide all frames initially; update_parameter_ui will show the correct one
        self.xtts_frame.pack_forget()
        self.piper_frame.pack_forget()
        self.bark_frame.pack_forget()
        self.elevenlabs_frame.pack_forget()
        # -------------------------------------------------------

        # Text Input Area
        text_frame = ttk.LabelFrame(right_panel, text="Text to Synthesize", padding="10")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        self.text_input = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, height=10, undo=True)
        self.text_input.pack(fill=tk.BOTH, expand=True)
        self.text_input.insert(tk.END, "Enter your text here...")
        self.text_input.bind("<Button-3>", self._show_text_context_menu)
        self.text_input.bind("<Control-a>", self._text_select_all); self.text_input.bind("<Control-A>", self._text_select_all)
        self.text_input.bind("<Control-z>", self._text_undo); self.text_input.bind("<Control-Z>", self._text_undo)
        self.text_input.bind("<Control-y>", self._text_redo); self.text_input.bind("<Control-Y>", self._text_redo)

        # Output File Selection
        output_frame = ttk.LabelFrame(right_panel, text="Output File", padding="10")
        output_frame.pack(fill=tk.X, pady=5, padx=5)
        ttk.Label(output_frame, text="Save as:").pack(side=tk.LEFT, padx=5)
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_file_path, width=50)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.browse_output_button = ttk.Button(output_frame, text="Browse...", command=self.browse_save_file)
        self.browse_output_button.pack(side=tk.LEFT, padx=5)
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
        self.update_parameter_ui() # Show parameters for the default model

        # Initial ElevenLabs setup is now handled within elevenlabs_ui.create_elevenlabs_ui

        self.load_existing_audio() # Load previous audio files

        if not self.mixer_initialized:
            self.disable_playback_controls()
            messagebox.showwarning("Audio Error", "Could not initialize audio playback.\nPlayback functions are disabled.", parent=self)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

# --- Application Entry Point ---
if __name__ == "__main__":
    app = TTSApp()
    app.mainloop()