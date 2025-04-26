# ui_engines/piper_ui.py
import tkinter as tk
from tkinter import ttk
import os

def create_piper_ui(parent, onnx_path_var, json_path_var, browse_callback, default_model_dir):
    """
    Creates the parameter frame specific to the Piper engine.

    Args:
        parent: The parent widget (ttk.Frame) to place this UI in.
        onnx_path_var: tk.StringVar for the ONNX model path.
        json_path_var: tk.StringVar for the JSON config path.
        browse_callback: The function to call for the browse buttons.
        default_model_dir: Default directory for Piper models.

    Returns:
        The created ttk.LabelFrame containing the Piper parameters.
    """
    piper_frame = ttk.LabelFrame(parent, text="Piper Parameters", padding="10")

    # ONNX Model Path
    ttk.Label(piper_frame, text="Model (.onnx):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
    ttk.Entry(piper_frame, textvariable=onnx_path_var, width=40).grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
    ttk.Button(piper_frame, text="Browse...", command=lambda: browse_callback(onnx_path_var, "Select Piper ONNX Model", [("ONNX files", "*.onnx")], default_model_dir)).grid(row=0, column=2, padx=5, pady=5)

    # JSON Config Path
    ttk.Label(piper_frame, text="Config (.json):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
    ttk.Entry(piper_frame, textvariable=json_path_var, width=40).grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
    ttk.Button(piper_frame, text="Browse...", command=lambda: browse_callback(json_path_var, "Select Piper JSON Config", [("JSON files", "*.json")], default_model_dir)).grid(row=1, column=2, padx=5, pady=5)

    # Allow the entry fields to expand
    piper_frame.grid_columnconfigure(1, weight=1)

    # Set default paths for convenience if the files exist
    default_onnx = os.path.join(default_model_dir, "en_US-lessac-medium.onnx")
    default_json = os.path.join(default_model_dir, "en_US-lessac-medium.onnx.json")
    if os.path.exists(default_onnx): onnx_path_var.set(default_onnx)
    if os.path.exists(default_json): json_path_var.set(default_json)

    return piper_frame