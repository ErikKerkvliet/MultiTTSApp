# web_app.py
"""
Web application version of the Multi TTS Synthesizer.

This script creates a Flask web application that provides the same
functionality as the original Tkinter app, but accessible through a web browser.
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
import os
import uuid
import threading
import logging
import time
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Import the TTS engines
try:
    from tts_engines import xtts_engine, piper_engine, bark_engine, elevenlabs_engine
except ImportError as e:
    print(f"ERROR: Could not import TTS engines. Error: {e}")
    print("Ensure the 'tts_engines' directory exists and all required dependencies are installed.")
    exit(1)

# Import the API (for reusing existing functionality)
from api.tts_api import MultiTTSAPI

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [WEB-APP] %(message)s',
    handlers=[
        logging.FileHandler("web_tts_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('web_app')

# Initialize the API
tts_api = MultiTTSAPI()

# Create Flask app
app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = 'web_uploads'
app.config['OUTPUT_FOLDER'] = 'audio_output'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', uuid.uuid4().hex)

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Track synthesis jobs
synthesis_jobs = {}


# Utility functions
def get_audio_files():
    """Get list of generated audio files with their metadata."""
    audio_files = []
    for filename in os.listdir(app.config['OUTPUT_FOLDER']):
        if filename.endswith(('.wav', '.mp3')):
            filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
            created_time = os.path.getctime(filepath)
            # Get file size in MB
            file_size = os.path.getsize(filepath) / (1024 * 1024)

            audio_files.append({
                'filename': filename,
                'path': filepath,
                'created': created_time,
                'size_mb': round(file_size, 2)
            })

    # Sort by creation time (newest first)
    audio_files.sort(key=lambda x: x['created'], reverse=True)
    return audio_files


def get_piper_models():
    """Get list of available Piper models with enhanced logging."""
    models = []
    # Ensure tts_api and its default path are correctly defined/accessible
    # If tts_api isn't defined here, you might need to access the path differently
    # For example, directly use the string:
    # piper_dir = "models/piper"
    try:
        piper_dir = tts_api.DEFAULT_PIPER_MODEL_DIR # Check if tts_api is available here
    except NameError:
        logger.warning("tts_api not defined in get_piper_models scope, using default path string.")
        piper_dir = "models/piper" # Fallback path

    logger.info(f"Attempting to scan Piper model directory: {os.path.abspath(piper_dir)}") # Log absolute path

    if os.path.exists(piper_dir) and os.path.isdir(piper_dir):
        try:
            found_files = os.listdir(piper_dir)
            logger.info(f"Files found in {piper_dir}: {found_files}")

            onnx_files = {}
            json_files = {}

            for filename in found_files:
                 # Use os.path.join for robustness
                full_path = os.path.join(piper_dir, filename)
                if filename.endswith('.onnx') and os.path.isfile(full_path):
                    base_name = filename[:-5] # Remove .onnx
                    onnx_files[base_name] = full_path
                    logger.debug(f"Found potential ONNX: {filename} (Base: {base_name})")
                elif filename.endswith('.onnx.json') and os.path.isfile(full_path):
                     base_name = filename[:-10] # Remove .onnx.json
                     json_files[base_name] = full_path
                     logger.debug(f"Found potential JSON: {filename} (Base: {base_name})")

            # Match ONNX and JSON files by base name
            valid_model_names = set(onnx_files.keys()) & set(json_files.keys())
            logger.info(f"Found {len(valid_model_names)} matching ONNX/JSON pairs.")

            for name in sorted(list(valid_model_names)): # Sort for consistent order
                models.append({
                    'name': name, # e.g., en_US-lessac-medium
                    'onnx_path': onnx_files[name],
                    'json_path': json_files[name]
                })
                logger.info(f"Added valid Piper model: {name}")

        except OSError as e:
            logger.error(f"Error accessing directory {piper_dir}: {e}", exc_info=True)
        except Exception as e:
             logger.error(f"Unexpected error during Piper model scan: {e}", exc_info=True)

    else:
        logger.warning(f"Piper model directory not found or is not a directory: {piper_dir}")

    if not models:
         logger.warning(f"No valid Piper models (.onnx + .onnx.json pairs) were found in {piper_dir}.")

    return models


# Routes
@app.route('/')
def index():
    """Render the main application page."""
    audio_files = get_audio_files()
    piper_models = get_piper_models()

    # Get ElevenLabs API keys from environment (similar to desktop app)
    elevenlabs_api_keys = {}
    key_prefix = "ELEVENLABS_API_KEY_"
    for key, value in os.environ.items():
        if key.startswith(key_prefix) and value:
            name = key.replace(key_prefix, "")
            if name:
                elevenlabs_api_keys[name] = True  # Just store that we have this key (don't expose the actual key)

    # Get speaker samples
    speaker_samples = []
    speaker_dir = tts_api.DEFAULT_SPEAKER_DIR
    if os.path.exists(speaker_dir):
        for filename in os.listdir(speaker_dir):
            if filename.endswith('.wav'):
                speaker_samples.append(filename)

    return render_template(
        'index.html',
        audio_files=audio_files,
        piper_models=piper_models,
        bark_voices=tts_api.default_bark_voices,
        elevenlabs_models=elevenlabs_engine.ELEVENLABS_MODELS,
        elevenlabs_keys=list(elevenlabs_api_keys.keys()),
        speaker_samples=speaker_samples
    )


@app.route('/audio/<filename>')
def serve_audio(filename):
    """Serve generated audio files."""
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)


@app.route('/speakers/<filename>')
def serve_speaker_sample(filename):
    """Serve speaker sample files."""
    return send_from_directory(tts_api.DEFAULT_SPEAKER_DIR, filename)


@app.route('/api/synthesize', methods=['POST'])
def synthesize():
    try:
        data = request.form # Synthesis uses form data
        text = data.get('text', '').strip()
        model_type = data.get('model_type', '')
        # ... (handle other model types if necessary) ...

        # Generate unique output filename and job ID
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        output_filename = f"{model_type.lower()}_{timestamp}_{unique_id}.wav"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        job_id = str(uuid.uuid4())
        synthesis_jobs[job_id] = { # Initialize job tracking
            'status': 'queued', 'message': 'Job queued',
            'output_filename': output_filename, 'start_time': time.time()
        }

        if model_type == 'ElevenLabs':
            # Use helper, passing request.form, specify is_form=True
            validated_key, key_source = get_elevenlabs_api_key_from_request(data, is_form=True)

            if not validated_key:
                # Key is invalid or missing - fail the job immediately
                msg = f'Invalid or missing API key ({key_source or "unknown"}) provided for synthesis.'
                synthesis_jobs[job_id]['status'] = 'failed'
                synthesis_jobs[job_id]['message'] = msg
                return jsonify({'success': False, 'job_id': job_id, 'message': msg}), 400 # Return error

            # Key is valid, collect other params
            voice_id = data.get('voice_id', '')
            model_id = data.get('model_id', 'eleven_multilingual_v2')

            if not voice_id:
                 msg = 'No ElevenLabs voice selected for synthesis.'
                 synthesis_jobs[job_id]['status'] = 'failed'
                 synthesis_jobs[job_id]['message'] = msg
                 return jsonify({'success': False, 'job_id': job_id, 'message': msg}), 400

            # Start synthesis in a background thread
            thread_params = {
                'voice_id': voice_id,
                'model_id': model_id,
                'api_key': validated_key # Pass the already validated key
            }
            threading.Thread(
                target=run_synthesis_job,
                args=(job_id, 'elevenlabs', text, output_path, thread_params),
                daemon=True
            ).start()
            return jsonify({'success': True, 'message': 'Synthesis job started', 'job_id': job_id})

        # --- Handle XTTSv2, Piper, Bark ---
        # (Ensure their logic also initializes the job_id in synthesis_jobs)
        elif model_type == 'XTTSv2':
             # ... (extract params, start thread, init job_id) ...
             language = data.get('language', 'en')
             # Handle speaker file upload/selection as before...
             speaker_wav_path = None
             if 'speaker_file' in request.files and request.files['speaker_file'].filename:
                 # ... (save uploaded file) ...
                 pass # Placeholder
             elif data.get('speaker_sample'):
                 # ... (get path for existing sample) ...
                 pass # Placeholder

             thread_params = {'language': language, 'speaker_wav_path': speaker_wav_path}
             threading.Thread(target=run_synthesis_job, args=(job_id, 'xtts', text, output_path, thread_params), daemon=True).start()
             return jsonify({'success': True, 'message': 'Synthesis job started', 'job_id': job_id})

        elif model_type == 'Piper':
             # ... (extract params, start thread, init job_id) ...
             model_onnx_path = data.get('model_onnx_path', '')
             model_json_path = data.get('model_json_path', '')
             if not model_onnx_path or not model_json_path:
                 # Handle error, update job status
                 return jsonify({'success': False, 'job_id': job_id, 'message': 'Piper model files not specified'}), 400

             thread_params = {'model_onnx_path': model_onnx_path, 'model_json_path': model_json_path}
             threading.Thread(target=run_synthesis_job, args=(job_id, 'piper', text, output_path, thread_params), daemon=True).start()
             return jsonify({'success': True, 'message': 'Synthesis job started', 'job_id': job_id})

        elif model_type == 'Bark':
             # ... (extract params, start thread, init job_id) ...
             voice_preset = data.get('voice_preset', '')
             model_name = data.get('model_name', 'suno/bark-small') # Or get from form if you add it
             if not voice_preset:
                  # Handle error, update job status
                  return jsonify({'success': False, 'job_id': job_id, 'message': 'No Bark voice preset selected'}), 400

             thread_params = {'voice_preset': voice_preset, 'model_name': model_name}
             threading.Thread(target=run_synthesis_job, args=(job_id, 'bark', text, output_path, thread_params), daemon=True).start()
             return jsonify({'success': True, 'message': 'Synthesis job started', 'job_id': job_id})

        else:
            msg = f'Unknown model type: {model_type}'
            synthesis_jobs[job_id]['status'] = 'failed'
            synthesis_jobs[job_id]['message'] = msg
            return jsonify({'success': False, 'job_id': job_id, 'message': msg}), 400

    except Exception as e:
        logger.error(f"Error processing synthesis request: {e}", exc_info=True)
        # Try to update job status if job_id was created
        if 'job_id' in locals() and job_id in synthesis_jobs:
            synthesis_jobs[job_id]['status'] = 'failed'
            synthesis_jobs[job_id]['message'] = f'Server Error: {str(e)}'
        return jsonify({'success': False, 'message': f'Server Error: {str(e)}'}), 500

def run_synthesis_job(job_id, engine_type, text, output_path, params):
    """Run a synthesis job in a background thread."""
    synthesis_jobs[job_id]['status'] = 'processing'
    synthesis_jobs[job_id]['message'] = f'Processing with {engine_type}...'

    success = False
    message = ''

    try:
        if engine_type == 'xtts':
            success, message = tts_api.synthesize_xtts(
                text=text,
                output_path=output_path,
                language=params.get('language', 'en'),
                speaker_wav_path=params.get('speaker_wav_path')
            )
        elif engine_type == 'piper':
            success, message = tts_api.synthesize_piper(
                text=text,
                output_path=output_path,
                model_onnx_path=params.get('model_onnx_path'),
                model_json_path=params.get('model_json_path')
            )
        elif engine_type == 'bark':
            success, message = tts_api.synthesize_bark(
                text=text,
                output_path=output_path,
                voice_preset=params.get('voice_preset'),
                model_name=params.get('model_name', 'suno/bark-small')
            )
        elif engine_type == 'elevenlabs':
            success, message = tts_api.synthesize_elevenlabs(
                text=text,
                output_path=output_path,
                voice_id=params.get('voice_id'),
                model_id=params.get('model_id', 'eleven_multilingual_v2'),
                api_key=params.get('api_key')
            )
        else:
            raise ValueError(f"Unknown engine type: {engine_type}")

        # Update job status
        synthesis_jobs[job_id]['status'] = 'completed' if success else 'failed'
        synthesis_jobs[job_id]['message'] = message
        synthesis_jobs[job_id]['success'] = success

        # Clean up temporary files if any
        if 'speaker_wav_path' in params and params['speaker_wav_path'] and os.path.exists(params['speaker_wav_path']):
            if params['speaker_wav_path'].startswith(app.config['UPLOAD_FOLDER']):
                try:
                    os.remove(params['speaker_wav_path'])
                    logger.info(f"Removed temporary speaker file: {params['speaker_wav_path']}")
                except Exception as e:
                    logger.error(f"Error removing temporary file: {e}")

    except Exception as e:
        logger.error(f"Error in synthesis job {job_id}: {e}")
        synthesis_jobs[job_id]['status'] = 'failed'
        synthesis_jobs[job_id]['message'] = f'Error: {str(e)}'
        synthesis_jobs[job_id]['success'] = False


def get_elevenlabs_api_key_from_request(request_data, is_form=False):
    """
    Gets the actual ElevenLabs API key from request data (dict from JSON or form).
    Returns the actual key string if found and valid, otherwise None.
    Also returns the source ('stored' or 'manual') if successful.
    """
    api_key = None
    api_key_source = None
    actual_key_value = None

    if is_form:
        # Data is from request.form (ImmutableMultiDict)
        api_key_manual = request_data.get('api_key_manual', '')
        api_key_name = request_data.get('api_key_name', '')
    else:
        # Data is from request.json (dict)
        api_key_manual = request_data.get('api_key', '') # Use 'api_key' for manual in JSON
        api_key_name = request_data.get('key_name', '')

    if api_key_manual:
        logger.info("Attempting to use manually provided ElevenLabs API key.")
        actual_key_value = api_key_manual
        api_key_source = 'manual'
    elif api_key_name:
        env_key = f"ELEVENLABS_API_KEY_{api_key_name}"
        retrieved_key = os.environ.get(env_key)
        if retrieved_key:
            logger.info(f"Attempting to use stored ElevenLabs API key: {api_key_name}")
            actual_key_value = retrieved_key
            api_key_source = 'stored'
        else:
            logger.error(f"Selected API key name '{api_key_name}' not found in environment variables!")
            return None, None # Key name selected but not found in env

    if not actual_key_value:
        logger.warning("No API key name or manual key provided in request.")
        return None, None # Neither provided

    # --- Validate the retrieved key ---
    # Use the engine's validation function
    validated_key = elevenlabs_engine.validate_api_key(actual_key_value)
    if validated_key:
        logger.info(f"API Key ({api_key_source}) validation successful.")
        return validated_key, api_key_source # Return the validated key and its source
    else:
        logger.warning(f"API Key ({api_key_source}) validation failed.")
        return None, api_key_source # Return None if validation fails, but still return source


@app.route('/api/job/<job_id>')
def get_job_status(job_id):
    """Get the status of a synthesis job."""
    if job_id not in synthesis_jobs:
        return jsonify({'success': False, 'message': 'Job not found'}), 404

    job = synthesis_jobs[job_id]
    response = {
        'status': job['status'],
        'message': job['message']
    }

    # Include additional information for completed jobs
    if job['status'] in ['completed', 'failed']:
        response['success'] = job.get('success', False)
        if job.get('success'):
            response['output_filename'] = job.get('output_filename')
            response['audio_url'] = url_for('serve_audio', filename=job.get('output_filename'))

        # Calculate duration
        start_time = job.get('start_time', 0)
        if start_time:
            duration = time.time() - start_time
            response['duration'] = round(duration, 2)

    return jsonify(response)


@app.route('/api/audio_files')
def get_audio_file_list():
    """Get a list of generated audio files."""
    audio_files = get_audio_files()
    return jsonify({
        'success': True,
        'files': audio_files
    })


@app.route('/api/delete_audio/<filename>', methods=['POST'])
def delete_audio(filename):
    """Delete an audio file."""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], secure_filename(filename))
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({'success': True, 'message': f'File {filename} deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Error deleting file: {str(e)}'}), 500


@app.route('/api/elevenlabs/validate_key', methods=['POST'])
def validate_elevenlabs_key_endpoint(): # Renamed slightly for clarity
    try:
        data = request.json
        # Use the helper, pass data directly, specify it's JSON (is_form=False)
        validated_key, key_source = get_elevenlabs_api_key_from_request(data, is_form=False)

        if validated_key:
            # Key is valid
            return jsonify({'success': True, 'message': 'API key is valid'})
        elif key_source:
            # Key was provided (source identified) but failed validation
             return jsonify({'success': False, 'message': f'Invalid API key ({key_source}) provided.'}), 400
        else:
            # No key was provided or found (e.g., name selected but not in env)
            return jsonify({'success': False, 'message': 'No API key provided or found'}), 400

    except Exception as e:
        logger.error(f"Error validating ElevenLabs key: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@app.route('/api/elevenlabs/voices', methods=['POST'])
def get_elevenlabs_voices():
    try:
        data = request.json
        # Use helper, expecting JSON payload
        validated_key, key_source = get_elevenlabs_api_key_from_request(data, is_form=False)

        if not validated_key:
            msg = f'Invalid or missing API key ({key_source or "unknown"}) provided.'
            return jsonify({'success': False, 'message': msg}), 400

        # Key is validated, proceed to get voices
        voices = elevenlabs_engine.get_elevenlabs_voices(validated_key)
        formatted_voices = [{'name': name, 'id': voice_id} for name, voice_id in voices]
        return jsonify({'success': True, 'voices': formatted_voices})

    except Exception as e:
        logger.error(f"Error fetching ElevenLabs voices: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@app.route('/api/elevenlabs/subscription', methods=['POST'])
def get_elevenlabs_subscription():
    try:
        data = request.json
        # Use helper, expecting JSON payload
        validated_key, key_source = get_elevenlabs_api_key_from_request(data, is_form=False)

        if not validated_key:
            msg = f'Invalid or missing API key ({key_source or "unknown"}) provided.'
            return jsonify({'success': False, 'message': msg}), 400

        # Key is validated, proceed to get subscription info
        subscription_info = elevenlabs_engine.get_subscription_info(validated_key)
        return jsonify({'success': True, 'subscription': subscription_info})

    except Exception as e:
        logger.error(f"Error fetching ElevenLabs subscription: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


# Start the application
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")  # Listen on all interfaces

    print(f"\n--- Multi TTS Web App ---")
    print(f"Starting server on http://{host}:{port}")
    print(f"Access from other computers using your IP address")
    print(f"Press Ctrl+C to stop the server")

    app.run(host=host, port=port, debug=True)