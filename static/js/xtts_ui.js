// static/js/xtts_ui.js - UPDATED FOR MODEL SELECTION

const XttsUI = (() => {
    // --- DOM Elements ---
    let speakerSampleSelect, speakerWavUpload, xttsLanguageSelect, xttsModelSelect;
    let speakerSampleWrapper, speakerUploadWrapper, speakerRecordingWrapper;
    let recordBtn, stopRecordBtn, useRecordBtn, discardRecordBtn;
    let recordingStatus, recordingPreview, clearSpeakerBtn;
    let modelDescription, voiceCloningIndicator;

    // --- State ---
    let activeSpeakerSource = null;
    let mediaRecorder = null;
    let audioChunks = [];
    let recordedSpeakerBlob = null;
    let isRecording = false;
    let recordingStartTime;
    let recordingTimerInterval;

    // Language name mapping
    const languageNames = {
        "en": "English", "es": "Spanish", "fr": "French", "de": "German",
        "it": "Italian", "pt": "Portuguese", "pl": "Polish", "tr": "Turkish",
        "ru": "Russian", "nl": "Dutch", "cs": "Czech", "ar": "Arabic",
        "zh-cn": "Chinese", "ja": "Japanese", "hu": "Hungarian",
        "ko": "Korean", "hi": "Hindi"
    };

    // --- Private Helper Functions ---
    function _updateModelInfo() {
        if (!xttsModelSelect || !modelDescription) return;

        const selectedOption = xttsModelSelect.options[xttsModelSelect.selectedIndex];
        if (!selectedOption) return;

        const modelKey = selectedOption.value;
        const modelType = selectedOption.dataset.type;

        // Update description from the option text and type
        let description = selectedOption.textContent;
        if (modelType === 'xtts') {
            description += " - Supports voice cloning with speaker samples";
        } else if (modelType === 'multispeaker') {
            description += " - Multiple built-in voices available";
        } else if (modelType === 'standard') {
            description += " - High-quality single speaker model";
        }

        modelDescription.textContent = description;

        // Show/hide voice cloning indicator
        if (voiceCloningIndicator) {
            if (modelType === 'xtts') {
                voiceCloningIndicator.style.display = 'block';
            } else {
                voiceCloningIndicator.style.display = 'none';
            }
        }

        console.log(`XTTS: Model info updated for ${modelKey} (${modelType})`);
    }

    function _updateLanguageOptions() {
        if (!xttsModelSelect || !xttsLanguageSelect) return;

        const selectedOption = xttsModelSelect.options[xttsModelSelect.selectedIndex];
        const supportedLanguages = selectedOption.dataset.languages || '';
        const languageList = supportedLanguages.split(',').filter(lang => lang.trim());

        // Clear existing options
        xttsLanguageSelect.innerHTML = '';

        // Add new options based on selected model
        languageList.forEach(langCode => {
            const langName = languageNames[langCode] || langCode.toUpperCase();
            const option = document.createElement('option');
            option.value = langCode;
            option.textContent = `${langName} (${langCode})`;
            xttsLanguageSelect.appendChild(option);
        });

        // Set default to Dutch if available, otherwise English, otherwise first option
        if (languageList.includes('nl')) {
            xttsLanguageSelect.value = 'nl';
        } else if (languageList.includes('en')) {
            xttsLanguageSelect.value = 'en';
        } else if (languageList.length > 0) {
            xttsLanguageSelect.value = languageList[0];
        }

        console.log(`XTTS: Updated language options for model. Available: ${languageList.join(', ')}`);
    }

    function _updateRecordingStatus(message, statusClass = '') {
        if (!recordingStatus) return;
        recordingStatus.textContent = `Status: ${message}`;
        recordingStatus.className = 'mt-2 small';
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
            if (recordingPreview.src) URL.revokeObjectURL(recordingPreview.src);
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
            setActiveSpeakerSource(null);
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = event => audioChunks.push(event.data);

            mediaRecorder.onstop = () => {
                if (audioChunks.length > 0) {
                    recordedSpeakerBlob = new Blob(audioChunks, { type: 'audio/wav' });
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
        // Select elements
        speakerSampleSelect = document.getElementById('speaker-sample-select');
        speakerWavUpload = document.getElementById('speaker-wav-upload');
        xttsLanguageSelect = document.getElementById('xtts-language');
        xttsModelSelect = document.getElementById('xtts-model'); // NEW
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
        modelDescription = document.getElementById('model-description'); // NEW
        voiceCloningIndicator = document.getElementById('voice-cloning-indicator'); // NEW

        // Attach listeners
        if (speakerSampleSelect) speakerSampleSelect.addEventListener('change', () => setActiveSpeakerSource(speakerSampleSelect.value ? 'sample' : null));
        if (speakerWavUpload) speakerWavUpload.addEventListener('change', () => setActiveSpeakerSource(speakerWavUpload.files.length > 0 ? 'upload' : null));
        if (recordBtn) recordBtn.addEventListener('click', _startRecording);
        if (stopRecordBtn) stopRecordBtn.addEventListener('click', _stopRecording);
        if (useRecordBtn) useRecordBtn.addEventListener('click', _useRecording);
        if (discardRecordBtn) discardRecordBtn.addEventListener('click', _discardRecording);
        if (clearSpeakerBtn) clearSpeakerBtn.addEventListener('click', clearSpeakerRefs);

        // NEW: Model selection listeners
        if (xttsModelSelect) {
            xttsModelSelect.addEventListener('change', () => {
                _updateLanguageOptions();
                _updateModelInfo();
            });
            // Initialize on load
            _updateLanguageOptions();
            _updateModelInfo();
        }

        _resetRecordingState();
        console.log("XTTS UI Initialized with model selection");
    }

    function setActiveSpeakerSource(sourceType) {
        console.log(`XTTS: Setting active speaker source: ${sourceType}`);
        activeSpeakerSource = sourceType;

        // Reset inactive sources & UI
        if (sourceType !== 'sample' && speakerSampleSelect) speakerSampleSelect.value = '';
        if (sourceType !== 'upload' && speakerWavUpload) speakerWavUpload.value = '';
        if (sourceType !== 'recording') {
             if (recordedSpeakerBlob && recordingPreview.src) URL.revokeObjectURL(recordingPreview.src);
             recordedSpeakerBlob = null;
            _resetRecordingUI(true);
        }

        // Update visual active state
        [speakerSampleWrapper, speakerUploadWrapper, speakerRecordingWrapper].forEach(wrapper => {
            if (wrapper) wrapper.classList.remove('speaker-source-active');
        });

        if (sourceType === 'sample' && speakerSampleWrapper) speakerSampleWrapper.classList.add('speaker-source-active');
        else if (sourceType === 'upload' && speakerUploadWrapper) speakerUploadWrapper.classList.add('speaker-source-active');
        else if (sourceType === 'recording' && speakerRecordingWrapper && recordedSpeakerBlob) speakerRecordingWrapper.classList.add('speaker-source-active');
        else activeSpeakerSource = null;

        console.log(`XTTS: Active speaker source is now: ${activeSpeakerSource}`);
    }

     function clearSpeakerRefs() {
         setActiveSpeakerSource(null);
         console.log("XTTS: All speaker references cleared.");
     }

    function getFormData(formData) {
        // Check model and language selection
        if (!xttsModelSelect || !xttsLanguageSelect) {
            console.error("XTTS Error: Model or language select elements not found.");
            return false;
        }

        const selectedModel = xttsModelSelect.value;
        const selectedLanguage = xttsLanguageSelect.value;

        if (!selectedModel || !selectedLanguage) {
            console.error("XTTS Error: Model or language not selected.");
            return false;
        }

        // Add model and language
        formData.append('model_key', selectedModel); // NEW: Model key
        formData.append('language', selectedLanguage);
        console.log(`XTTS: Getting form data. Model: ${selectedModel}, Language: ${selectedLanguage}, Active source: ${activeSpeakerSource}`);

        // Add speaker reference if active
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
             console.log(`XTTS: No specific speaker reference appended (using default voice).`);
        }

        return true;
    }

    // Expose public methods
    return {
        init: init,
        getFormData: getFormData
    };
})();