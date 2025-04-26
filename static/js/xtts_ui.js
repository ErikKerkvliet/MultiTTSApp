// static/js/xtts_ui.js

const XttsUI = (() => {
    // --- DOM Elements (Scoped to this module) ---
    let speakerSampleSelect, speakerWavUpload, xttsLanguageSelect,
        speakerSampleWrapper, speakerUploadWrapper, speakerRecordingWrapper,
        recordBtn, stopRecordBtn, useRecordBtn, discardRecordBtn,
        recordingStatus, recordingPreview, clearSpeakerBtn;

    // --- State (Scoped to this module) ---
    let activeSpeakerSource = null; // 'sample', 'upload', 'recording', or null
    let mediaRecorder = null;
    let audioChunks = [];
    let recordedSpeakerBlob = null;
    let isRecording = false;
    let recordingStartTime;
    let recordingTimerInterval;

    // --- Private Helper Functions ---
    function _updateRecordingStatus(message, statusClass = '') {
        if (!recordingStatus) return;
        recordingStatus.textContent = `Status: ${message}`;
        recordingStatus.className = 'mt-2 small'; // Reset base class
        if (statusClass === 'recording') recordingStatus.classList.add('text-danger', 'fw-bold');
        else if (statusClass === 'available') recordingStatus.classList.add('text-success');
        else if (statusClass === 'error') recordingStatus.classList.add('text-danger');
    }

    function _resetRecordingUI(fullReset = true) {
        if(recordBtn) recordBtn.disabled = false;
        if(stopRecordBtn) stopRecordBtn.disabled = true;
        if(useRecordBtn) useRecordBtn.disabled = true;
        if(discardRecordBtn) discardRecordBtn.disabled = true;
        if(recordingPreview) {
            recordingPreview.style.display = 'none';
            recordingPreview.removeAttribute('src');
            URL.revokeObjectURL(recordingPreview.src); // Clean up previous blob URL
        }
        if(fullReset && recordingStatus) _updateRecordingStatus("Idle");
        clearInterval(recordingTimerInterval);
        recordingTimerInterval = null;
    }

    function _resetRecordingState() {
         if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
        mediaRecorder = null;
        audioChunks = [];
        recordedSpeakerBlob = null;
        isRecording = false;
        recordingStartTime = null;
        _resetRecordingUI(true);
        if(speakerRecordingWrapper) speakerRecordingWrapper.classList.remove('speaker-source-active');
        if (activeSpeakerSource === 'recording') activeSpeakerSource = null;
    }

    async function _startRecording() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            _updateRecordingStatus("getUserMedia not supported!", "error");
            return;
        }
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            setActiveSpeakerSource(null); // Clear others
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = event => audioChunks.push(event.data);

            mediaRecorder.onstop = () => {
                if (audioChunks.length > 0) {
                    recordedSpeakerBlob = new Blob(audioChunks, { type: 'audio/wav' }); // Use WAV type
                    const audioUrl = URL.createObjectURL(recordedSpeakerBlob);
                    recordingPreview.src = audioUrl;
                    recordingPreview.style.display = 'block';
                    useRecordBtn.disabled = false;
                    discardRecordBtn.disabled = false;
                    _updateRecordingStatus("Recording finished. Preview available.", "available");
                } else {
                     _updateRecordingStatus("Recording stopped. No data.", "error");
                     _resetRecordingUI(true);
                }
                 stream.getTracks().forEach(track => track.stop());
                 clearInterval(recordingTimerInterval);
                 recordingTimerInterval = null;
                 isRecording = false;
                 if(recordBtn) recordBtn.disabled = false;
                 if(stopRecordBtn) stopRecordBtn.disabled = true;
            };

            mediaRecorder.onerror = (event) => {
                console.error("MediaRecorder error:", event.error);
                _updateRecordingStatus(`Rec error: ${event.error.name}`, "error");
                _resetRecordingState();
            };

            mediaRecorder.start();
            isRecording = true;
            if(recordBtn) recordBtn.disabled = true;
            if(stopRecordBtn) stopRecordBtn.disabled = false;
            if(useRecordBtn) useRecordBtn.disabled = true;
            if(discardRecordBtn) discardRecordBtn.disabled = true;
            if(recordingPreview) recordingPreview.style.display = 'none';
            recordingStartTime = Date.now();
            _updateRecordingStatus("Recording... 0s");
             recordingTimerInterval = setInterval(() => {
                  const elapsed = Math.round((Date.now() - recordingStartTime) / 1000);
                  _updateRecordingStatus(`Recording... ${elapsed}s`, "recording");
             }, 1000);

        } catch (err) {
            console.error("Mic access error:", err);
            _updateRecordingStatus(`Mic error: ${err.message}`, "error");
             _resetRecordingState();
        }
    }

    function _stopRecording() {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
            if(stopRecordBtn) stopRecordBtn.disabled = true;
            if(recordBtn) recordBtn.disabled = false;
            clearInterval(recordingTimerInterval);
            recordingTimerInterval = null;
        }
    }

    function _useRecording() {
        if (recordedSpeakerBlob) {
            setActiveSpeakerSource('recording');
             _updateRecordingStatus("Recording ready to use", "available");
             if(useRecordBtn) useRecordBtn.disabled = true;
             if(discardRecordBtn) discardRecordBtn.disabled = false;
        }
    }

    function _discardRecording() {
        _resetRecordingState();
        _updateRecordingStatus("Recording discarded. Idle.");
    }

    // --- Public Functions ---
    function init() {
        // Select elements after DOM is loaded
        speakerSampleSelect = document.getElementById('speaker-sample-select');
        speakerWavUpload = document.getElementById('speaker-wav-upload');
        xttsLanguageSelect = document.getElementById('xtts-language');
        speakerSampleWrapper = document.getElementById('speaker-sample-wrapper');
        speakerUploadWrapper = document.getElementById('speaker-upload-wrapper');
        speakerRecordingWrapper = document.getElementById('speaker-recording-wrapper');
        recordBtn = document.getElementById('record-btn');
        stopRecordBtn = document.getElementById('stop-record-btn');
        useRecordBtn = document.getElementById('use-record-btn');
        discardRecordBtn = document.getElementById('discard-record-btn');
        recordingStatus = document.getElementById('recording-status');
        recordingPreview = document.getElementById('recording-preview');
        clearSpeakerBtn = document.getElementById('clear-speaker');

        // Attach listeners
        if (speakerSampleSelect) speakerSampleSelect.addEventListener('change', () => setActiveSpeakerSource(speakerSampleSelect.value ? 'sample' : null));
        if (speakerWavUpload) speakerWavUpload.addEventListener('change', () => setActiveSpeakerSource(speakerWavUpload.files.length > 0 ? 'upload' : null));
        if (recordBtn) recordBtn.addEventListener('click', _startRecording);
        if (stopRecordBtn) stopRecordBtn.addEventListener('click', _stopRecording);
        if (useRecordBtn) useRecordBtn.addEventListener('click', _useRecording);
        if (discardRecordBtn) discardRecordBtn.addEventListener('click', _discardRecording);
        if (clearSpeakerBtn) clearSpeakerBtn.addEventListener('click', clearSpeakerRefs);

        _resetRecordingState(); // Initial cleanup
        console.log("XTTS UI Initialized");
    }

    function setActiveSpeakerSource(sourceType) {
        console.log(`XTTS: Setting active speaker source: ${sourceType}`);
        activeSpeakerSource = sourceType;

        // Reset inactive sources & UI
        if (sourceType !== 'sample' && speakerSampleSelect) speakerSampleSelect.value = '';
        if (sourceType !== 'upload' && speakerWavUpload) speakerWavUpload.value = '';
        if (sourceType !== 'recording') {
             if (recordedSpeakerBlob) URL.revokeObjectURL(recordingPreview.src); // Clean up blob URL if discarding recording source
             recordedSpeakerBlob = null;
            _resetRecordingUI(true); // Reset recording UI and status text
        }

        // Update visual active state
        [speakerSampleWrapper, speakerUploadWrapper, speakerRecordingWrapper].forEach(wrapper => {
            if (wrapper) wrapper.classList.remove('speaker-source-active');
        });

        if (sourceType === 'sample' && speakerSampleWrapper) speakerSampleWrapper.classList.add('speaker-source-active');
        else if (sourceType === 'upload' && speakerUploadWrapper) speakerUploadWrapper.classList.add('speaker-source-active');
        else if (sourceType === 'recording' && speakerRecordingWrapper && recordedSpeakerBlob) speakerRecordingWrapper.classList.add('speaker-source-active');
        else activeSpeakerSource = null; // Clear state if no valid source

        console.log(`XTTS: Active speaker source is now: ${activeSpeakerSource}`);
    }

     function clearSpeakerRefs() {
         setActiveSpeakerSource(null); // This clears all inputs and states
         console.log("XTTS: All speaker references cleared.");
     }

    function getFormData(formData) {
        // Basis check of de taal selector bestaat en een waarde heeft
        if (!xttsLanguageSelect || !xttsLanguageSelect.value) {
             console.error("XTTS Error: Language select element not found or no language selected.");
             // Optioneel: geef hier specifiekere feedback, of laat main.js de algemene fout tonen.
             return false; // Stop als taal niet geselecteerd is (onwaarschijnlijk met <select>)
        }

        // Voeg taal toe
        formData.append('language', xttsLanguageSelect.value);
        console.log(`XTTS: Getting form data. Active source: ${activeSpeakerSource}. Language: ${xttsLanguageSelect.value}`);

        // Voeg speaker referentie toe (als die actief is)
        // Gebruik optional chaining (?.) voor robuustheid voor het geval elementen niet gevonden zijn
        if (activeSpeakerSource === 'sample' && speakerSampleSelect?.value) {
            formData.append('speaker_sample', speakerSampleSelect.value);
            console.log(`XTTS: Appending sample: ${speakerSampleSelect.value}`);
        } else if (activeSpeakerSource === 'upload' && speakerWavUpload?.files?.length > 0) {
            formData.append('speaker_file', speakerWavUpload.files[0], speakerWavUpload.files[0].name);
             console.log(`XTTS: Appending upload: ${speakerWavUpload.files[0].name}`);
        } else if (activeSpeakerSource === 'recording' && recordedSpeakerBlob) {
            formData.append('speaker_file', recordedSpeakerBlob, 'recorded_speaker.wav');
             console.log(`XTTS: Appending recording blob.`);
        } else {
             // Geen actieve speaker bron geselecteerd, backend gebruikt default stem
             console.log(`XTTS: No specific speaker reference appended (using default voice).`);
        }

        // --- BELANGRIJK: Expliciet true retourneren ---
        // Als we hier komen, zijn de basis parameters (taal) oké.
        // De speaker ref is optioneel, dus we hoeven niet te falen als die mist.
        return true;
    }

    // Expose public methods (inclusief de gewijzigde getFormData)
    return {
        init: init,
        getFormData: getFormData
        // Andere publieke methoden indien nodig
    };

    // Expose public methods
    return {
        init: init,
        getFormData: getFormData
    };
})();