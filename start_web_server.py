#!/usr/bin/env python3
"""
Start script for the Multi TTS Web Application.
This script sets up necessary directories and starts the web server.
"""

import os
import sys
import subprocess
import webbrowser
import time
import platform

# Configure the default directories
DIRECTORIES = [
    "audio_output",
    "web_uploads",
    "speaker_samples",
    "models/piper"
]

# Default host and port
DEFAULT_HOST = "0.0.0.0"  # Listen on all interfaces
DEFAULT_PORT = 5000


def create_directories():
    """Create the necessary directories if they don't exist."""
    print("Setting up directories...")
    for directory in DIRECTORIES:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")


def get_local_ip():
    """Get the local IP address to display to the user."""
    import socket
    try:
        # Create a socket and connect to an external server
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "localhost"


def open_browser(host, port):
    """Open the default web browser to the application URL."""
    # If host is 0.0.0.0, use localhost for browser
    browser_host = "localhost" if host == "0.0.0.0" else host
    url = f"http://{browser_host}:{port}"

    print(f"\nOpening web browser to {url}")
    webbrowser.open(url)


def start_server():
    """Start the web application server."""
    # Create the required directories
    create_directories()

    # Check if web_app.py exists
    if not os.path.exists("web_app.py"):
        print("Error: web_app.py not found in the current directory.")
        print("Please run this script from the Multi TTS Web Application directory.")
        sys.exit(1)

    # Get the local IP address for display
    local_ip = get_local_ip()

    print("\n===== Multi TTS Web Application =====")
    print(f"Starting server on http://{DEFAULT_HOST}:{DEFAULT_PORT}")
    print(f"Access locally via: http://localhost:{DEFAULT_PORT}")
    print(f"Access from other computers via: http://{local_ip}:{DEFAULT_PORT}")

    # Open browser with a small delay to allow server startup
    if platform.system() != "Linux":  # Skip on Linux as it often causes issues
        timer = threading.Timer(2.0, open_browser, args=("localhost", DEFAULT_PORT))
        timer.daemon = True
        timer.start()

    # Start the Flask application
    try:
        # Use sys.executable to ensure the same Python interpreter is used
        subprocess.run([sys.executable, "web_app.py"])
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
    except Exception as e:
        print(f"\nError starting server: {e}")


if __name__ == "__main__":
    import threading  # Import here to avoid issues if the script fails early

    try:
        start_server()
    except KeyboardInterrupt:
        print("\nExiting...")