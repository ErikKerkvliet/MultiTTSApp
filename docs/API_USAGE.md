# Using the API

# Python Code Integration:

from tts_api import MultiTTSAPI

# Initialize API
api = MultiTTSAPI()

# Synthesize text with XTTSv2
success, message = api.synthesize_xtts(
    text="Hello, this is a test.",
    output_path="output.wav",
    language="en"
)
REST API Usage (with curl):
# Synthesize with XTTSv2
curl -X POST "http://localhost:8000/synthesize/xtts" \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello, this is a test.", "language": "en"}'

# Download the generated file
curl -X GET "http://localhost:8000/download/xtts_12345.wav" \
     -o "output.wav"
Running the REST API Server
To run the REST API server:

Install the required dependencies:
pip install fastapi uvicorn python-multipart

Run the server:
python rest_api_server.py
or
uvicorn rest_api_server:app --host 0.0.0.0 --port 8000

Access the API documentation at http://localhost:8000/docs