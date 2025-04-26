// static/js/main.js

window.addEventListener('load', () => {

    // --- Common DOM Elements ---
    const modelSelect = document.getElementById('model-select');
    const paramsTitle = document.getElementById('params-title');
    const textInput = document.getElementById('text-input');
    const synthesizeBtn = document.getElementById('synthesize-btn');
    const statusMessage = document.getElementById('status-message');

    // Parameter Section Divs
    const xttsParamsDiv = document.getElementById('xtts-params');
    const piperParamsDiv = document.getElementById('piper-params');
    const barkParamsDiv = document.getElementById('bark-params');
    const elevenlabsParamsDiv = document.getElementById('elevenlabs-params');

    // Audio List & Playback Elements
    const audioListDiv = document.getElementById('audio-list');
    const audioPlayer = document.getElementById('audio-player');
    const playBtn = document.getElementById('play-btn');
    const pauseBtn = document.getElementById('pause-btn');
    const stopBtn = document.getElementById('stop-btn');
    const seekSlider = document.getElementById('seek-slider');
    const currentTimeSpan = document.getElementById('current-time');
    const durationSpan = document.getElementById('duration');

    // Progress & Result Elements
    const progressOverlay = document.getElementById('progress-overlay');
    const progressMessage = document.getElementById('progress-message');
    const progressBar = document.getElementById('progress-bar');
    const progressTime = document.getElementById('progress-time');
    const resultModalElement = document.getElementById('result-modal');
    const resultModal = new bootstrap.Modal(resultModalElement);
    const resultTitle = document.getElementById('result-title');
    const resultMessage = document.getElementById('result-message');
    const resultPlayerContainer = document.getElementById('result-player-container');
    const resultPlayer = document.getElementById('result-player');

    // --- Main State Variables ---
    let currentModel = 'XTTSv2';
    let currentJobId = null;
    let jobPollingInterval = null;
    let jobStartTime = null;
    let isSeeking = false;

    // --- UI Modules (assuming they expose methods like init, getFormData) ---
    const uiModules = {
    XTTSv2: typeof XttsUI !== 'undefined' ? XttsUI : null, // Check if defined
    Piper: typeof PiperUI !== 'undefined' ? PiperUI : null,
    Bark: typeof BarkUI !== 'undefined' ? BarkUI : null,
    ElevenLabs: typeof ElevenLabsUI !== 'undefined' ? ElevenLabsUI : null
};


    // --- Helper Functions (Common - GEEN WIJZIGINGEN HIER NODIG) ---
    function updateStatusMessage(message, isError = false) {
        if(statusMessage) { // Check if element exists before using
            statusMessage.textContent = message;
            statusMessage.classList.toggle('text-danger', isError);
            statusMessage.classList.toggle('text-muted', !isError);
        } else {
            console.warn("Status message element not found");
        }
    }

    function showProgress(message) {
        // Add checks for elements before using them
        if(progressMessage) progressMessage.textContent = message;
        jobStartTime = Date.now();
        updateProgressTime();
        if(progressBar) {
            progressBar.style.width = '100%';
            progressBar.classList.add('progress-bar-animated');
        }
        if(progressOverlay) progressOverlay.style.display = 'flex';
        if(synthesizeBtn) synthesizeBtn.disabled = true;
    }

     function updateProgressTime() {
        if (jobStartTime && progressTime) { // Check progressTime
            const elapsed = Math.round((Date.now() - jobStartTime) / 1000);
            progressTime.textContent = `Time elapsed: ${elapsed}s`;
        } else if (progressTime) {
             progressTime.textContent = '';
        }
    }

    function hideProgress() {
        if(progressOverlay) progressOverlay.style.display = 'none';
        if(synthesizeBtn) synthesizeBtn.disabled = false;
        jobStartTime = null;
        clearInterval(jobPollingInterval);
        jobPollingInterval = null;
        currentJobId = null;
        updateProgressTime();
    }

    function showResultModal(success, message, audioUrl = null) {
        // --- BELANGRIJKE CHECK ---
        // Ensure modal elements are selected before proceeding
        if (!resultModal || !resultTitle || !resultMessage || !resultPlayerContainer || !resultPlayer) {
            console.error("Result modal elements not found or initialized! Cannot show modal.");
            // Optionally show a basic alert as fallback
            alert(`Result: ${success ? 'Success' : 'Failed'}\nMessage: ${message}`);
            return;
        }
        // --- EINDE CHECK ---

        const titleIcon = success ? 'bi-check-circle-fill text-success' : 'bi-exclamation-triangle-fill text-danger';
        // Now it's safe to set innerHTML/textContent
        resultTitle.innerHTML = `<i class="bi ${titleIcon} me-2"></i>${success ? 'Synthesis Complete' : 'Synthesis Failed'}`;
        resultMessage.textContent = message;

        if (success && audioUrl) {
            resultPlayer.src = audioUrl;
            resultPlayerContainer.style.display = 'block';
            resultPlayer.load();
        } else {
            resultPlayerContainer.style.display = 'none';
            resultPlayer.removeAttribute('src');
        }
        resultModal.show();
    }

    // --- Model Switching Logic ---
    function switchModelView(selectedModel) {
        console.log(`Main: Switching view to ${selectedModel}`);
        currentModel = selectedModel;
        if(paramsTitle) paramsTitle.textContent = `${selectedModel} Parameters`;

        // Hide/Show correct divs
        if(xttsParamsDiv) xttsParamsDiv.style.display = selectedModel === 'XTTSv2' ? 'block' : 'none';
        if(piperParamsDiv) piperParamsDiv.style.display = selectedModel === 'Piper' ? 'block' : 'none';
        if(barkParamsDiv) barkParamsDiv.style.display = selectedModel === 'Bark' ? 'block' : 'none';
        if(elevenlabsParamsDiv) elevenlabsParamsDiv.style.display = selectedModel === 'ElevenLabs' ? 'block' : 'none';

        // Reset ElevenLabs status if switching away and module exists
        if (selectedModel !== 'ElevenLabs' && uiModules.ElevenLabs?.resetStatus) {
             uiModules.ElevenLabs.resetStatus();
        }
        updateStatusMessage(`Switched to ${selectedModel}. Configure parameters and enter text.`);
    }

    // --- Synthesis Submission Logic ---
    function handleSynthesisSubmit(event) {
        event.preventDefault();

        const text = textInput.value.trim();
        console.log(`Main: Synthesis text: ${text}`);
        if (!text) {
            showResultModal(false, "Please enter some text to synthesize.");
            return;
        }

        const formData = new FormData();
        formData.append('text', text);
        formData.append('model_type', currentModel);

        // Get model-specific parameters from the corresponding UI module
        const currentUiModule = uiModules[currentModel];
        console.log(uiModules)

        if (currentUiModule && currentUiModule.getFormData) {
            // Pass formData; module appends its specific params
            // getFormData should return false on validation error within the module
            if (!currentUiModule.getFormData(formData)) {
                 showResultModal(false, `Please check the parameters for ${currentModel}.`);
                 console.error(`Failed to get form data from ${currentModel} UI module.`);
                 return; // Stop submission if module indicates an error
            }
        } else {
            showResultModal(false, `UI module not configured for ${currentModel}.`);
             console.error(`UI module or getFormData not found for ${currentModel}.`);
            return;
        }

        // --- Start the process ---
        updateStatusMessage(`Starting ${currentModel} synthesis...`);
        showProgress(`Starting ${currentModel} synthesis...`);

         // Log FormData contents for debugging (optional)
         console.log("--- FormData to be sent ---");
         for (let [key, value] of formData.entries()) {
             console.log(`${key}:`, (value instanceof Blob) ? `Blob(size=${value.size}, type=${value.type})` : value);
         }
          console.log("--------------------------");


        fetch('/api/synthesize', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.message || `Server error: ${response.status}`); });
            }
            return response.json();
        })
        .then(data => {
            if (data.success && data.job_id) {
                currentJobId = data.job_id;
                updateStatusMessage(`Synthesis job ${currentJobId} started. Polling status...`);
                progressMessage.textContent = 'Synthesis job started. Waiting for progress...';
                pollJobStatus(currentJobId);
            } else {
                throw new Error(data.message || 'Failed to start synthesis job.');
            }
        })
        .catch(error => {
            console.error('Error starting synthesis:', error);
            updateStatusMessage(`Error: ${error.message}`, true);
            hideProgress();
            showResultModal(false, `Failed to start synthesis: ${error.message}`);
        });
    }

    // --- Job Polling Logic ---
    function pollJobStatus(jobId) {
        clearInterval(jobPollingInterval);
        jobPollingInterval = null;
        updateProgressTime(); // Update time immediately

        jobPollingInterval = setInterval(async () => {
             updateProgressTime(); // Keep updating time
             if (!currentJobId || currentJobId !== jobId) {
                 console.warn("Polling stopped: Job ID changed or cleared.");
                 clearInterval(jobPollingInterval);
                 jobPollingInterval = null;
                 return;
             }

            try {
                const response = await fetch(`/api/job/${jobId}`);
                 if (!response.ok) {
                     console.error(`Polling error: ${response.status}`);
                      updateStatusMessage(`Error polling job ${jobId}: ${response.status}`, true);
                     clearInterval(jobPollingInterval);
                     jobPollingInterval = null;
                     hideProgress();
                     showResultModal(false, `Error checking job status: ${response.status}`);
                     return;
                 }

                const data = await response.json();
                if(progressMessage) progressMessage.textContent = data.message || 'Processing...';

                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(jobPollingInterval);
                     jobPollingInterval = null;
                     hideProgress();
                     updateStatusMessage(data.message || `Job ${jobId} ${data.status}.`, !data.success);
                     showResultModal(data.success, data.message, data.audio_url || null);
                     if (data.success) {
                        updateAudioList(); // Refresh list on success
                     }
                     currentJobId = null;
                } else if (data.status === 'processing' || data.status === 'queued') {
                    updateStatusMessage(data.message || `Job ${jobId} is ${data.status}...`);
                } else {
                    console.warn(`Unknown job status received: ${data.status}`);
                    updateStatusMessage(`Job ${jobId} has unknown status: ${data.status}`);
                }
            } catch (error) {
                console.error(`Error during job polling for ${jobId}:`, error);
                updateStatusMessage(`Error polling job ${jobId}: ${error.message}`, true);
                clearInterval(jobPollingInterval);
                jobPollingInterval = null;
                 hideProgress();
                showResultModal(false, `Error checking job status: ${error.message}`);
                currentJobId = null;
            }
        }, 2000); // Poll every 2 seconds
    }

    // --- Audio List & Deletion Logic ---
    async function updateAudioList() {
        console.log("Main: Updating audio list...");
        if (!audioListDiv) return;
        audioListDiv.innerHTML = '<div class="audio-list-empty">Loading audio files...</div>'; // Show loading state

        try {
            const response = await fetch('/api/audio_files'); // Endpoint to get file list
            const data = await response.json();
            audioListDiv.innerHTML = ''; // Clear loading/previous content

            if (data.success && data.files) {
                if (data.files.length === 0) {
                    audioListDiv.innerHTML = '<div class="audio-list-empty">No audio files generated yet.</div>';
                } else {
                    let bg = false; // Default background color
                    data.files.forEach(file => {
                        bgColor = bg ? 'bg-light' : 'bg-white'; // Alternate background color
                        bg = !bg; // Toggle background color
                        const item = document.createElement('div');
                        item.className = 'audio-item'; // Wordt een flex container via CSS
                        item.classList.add(bgColor);
                        item.dataset.filename = file.filename;
                        item.dataset.path = `/audio/${encodeURIComponent(file.filename)}`;

                        // --- START GEWIJZIGDE HTML STRUCTUUR ---
                        item.innerHTML = `
                            <span class="audio-filename flex-grow-1" title="${file.filename}" style="cursor: pointer;">
                                <i class="bi bi-file-earmark-music me-2 text-secondary"></i>
                                ${file.filename}
                            </span>

                            <button class="btn btn-sm btn-outline-danger delete-audio" style="padding: 0px; float:right; margin-right:5px" data-filename="${file.filename}" title="Delete ${file.filename}">
                                <i class="bi bi-trash m-0"></i>
                            </button>
                            <span class="audio-meta" style="float:right;">
                                ${file.size_mb} MB
                            </span>
                        `;
                        // --- EINDE GEWIJZIGDE HTML STRUCTUUR ---

                        audioListDiv.appendChild(item);
                    });
                     attachAudioListListeners(); // Re-attach listeners
                }
            } else {
                console.error("Failed to fetch audio files:", data.message);
                audioListDiv.innerHTML = '<div class="audio-list-empty text-danger">Error loading audio files.</div>';
            }
        } catch (error) {
            console.error("Error fetching audio files:", error);
            audioListDiv.innerHTML = '<div class="audio-list-empty text-danger">Network error loading audio files.</div>';
        }
    }

    function attachAudioListListeners() {
         // Click on item for playback
         document.querySelectorAll('#audio-list .audio-item').forEach(item => {
            item.addEventListener('click', function(event) {
                if (event.target.closest('.delete-audio')) return; // Ignore clicks on delete button

                document.querySelectorAll('#audio-list .audio-item.selected').forEach(activeItem => {
                    activeItem.classList.remove('selected');
                });
                this.classList.add('selected');

                const audioPath = this.dataset.path;
                if (audioPath) loadAndPlayAudio(audioPath);
            });
        });

        // Delete button click
        document.querySelectorAll('#audio-list .delete-audio').forEach(button => {
            button.addEventListener('click', async function(event) {
                event.stopPropagation();
                const filename = this.dataset.filename;
                if (confirm(`Are you sure you want to delete ${filename}?`)) {
                    console.log(`Main: Attempting to delete ${filename}`);
                     try {
                         // Endpoint to delete a file
                        const response = await fetch(`/api/delete_audio/${encodeURIComponent(filename)}`, { method: 'POST' });
                        const data = await response.json();
                        if (response.ok && data.success) {
                            console.log(`Main: ${filename} deleted.`);
                            updateStatusMessage(`${filename} deleted.`);
                            updateAudioList(); // Refresh list
                            if (audioPlayer.currentSrc && audioPlayer.currentSrc.endsWith(encodeURIComponent(filename))) {
                                 stopAudio(); // Stop playback if deleted file was playing
                            }
                        } else {
                            throw new Error(data.message || `Failed to delete ${filename}`);
                        }
                    } catch (error) {
                         console.error(`Main: Error deleting ${filename}:`, error);
                         updateStatusMessage(`Error deleting ${filename}: ${error.message}`, true);
                         showResultModal(false, `Error deleting file: ${error.message}`);
                    }
                }
            });
        });
    }

    // --- Audio Playback Logic ---
     function formatTime(seconds) {
         const minutes = Math.floor(seconds / 60);
         const secs = Math.floor(seconds % 60);
         return `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
     }

     function updatePlaybackUI() {
         if (!audioPlayer.duration || isNaN(audioPlayer.duration)) return;
         const currentTime = audioPlayer.currentTime;
         const duration = audioPlayer.duration;

         if(currentTimeSpan) currentTimeSpan.textContent = formatTime(currentTime);
         if(durationSpan) durationSpan.textContent = formatTime(duration);

         if (!isSeeking && seekSlider) {
            seekSlider.value = (currentTime / duration) * 100 || 0;
         }
     }

      function loadAndPlayAudio(src) {
          stopAudio(); // Stop previous
          audioPlayer.src = src;
          audioPlayer.load();
          updateStatusMessage(`Loading ${src.split('/').pop()}...`);

          audioPlayer.onloadedmetadata = () => {
               console.log("Main: Audio metadata loaded. Duration:", audioPlayer.duration);
               if(durationSpan) durationSpan.textContent = formatTime(audioPlayer.duration);
               if(seekSlider) {
                    seekSlider.max = 100;
                    seekSlider.value = 0;
                    seekSlider.disabled = false;
               }
               if(playBtn) playBtn.disabled = false;
               if(pauseBtn) pauseBtn.disabled = true;
               if(stopBtn) stopBtn.disabled = true;
               playAudio(); // Autoplay
          };
           audioPlayer.onerror = (e) => {
                console.error("Main: Error loading audio:", e, audioPlayer.error);
                updateStatusMessage(`Error loading audio: ${src.split('/').pop()}`, true);
                showResultModal(false, `Error loading audio file: ${audioPlayer.error?.message || 'Unknown error'}`);
                resetPlaybackControls();
           };
     }

     function playAudio() {
         if (!audioPlayer.src || audioPlayer.readyState < 2) return;
         audioPlayer.play().then(() => {
             if(playBtn) playBtn.disabled = true;
             if(pauseBtn) pauseBtn.disabled = false;
             if(stopBtn) stopBtn.disabled = false;
             updateStatusMessage(`Playing ${audioPlayer.src.split('/').pop()}`);
         }).catch(error => {
             console.error("Main: Playback error:", error);
              updateStatusMessage(`Playback error: ${error.message}`, true);
             showResultModal(false, `Could not play audio: ${error.message}`);
             resetPlaybackControls();
         });
     }

     function pauseAudio() {
         if (!audioPlayer.paused) {
             audioPlayer.pause();
             if(playBtn) playBtn.disabled = false;
             if(pauseBtn) pauseBtn.disabled = true;
             if(stopBtn) stopBtn.disabled = false;
             updateStatusMessage(`Paused ${audioPlayer.src.split('/').pop()}`);
         }
     }

     function stopAudio() {
         if (audioPlayer.src) {
             audioPlayer.pause();
             audioPlayer.currentTime = 0;
             if(playBtn) playBtn.disabled = false;
             if(pauseBtn) pauseBtn.disabled = true;
             if(stopBtn) stopBtn.disabled = true;
             if(seekSlider) seekSlider.value = 0;
             if(currentTimeSpan) currentTimeSpan.textContent = '00:00';
             if (audioPlayer.duration && !isNaN(audioPlayer.duration)) {
                 if(durationSpan) durationSpan.textContent = formatTime(audioPlayer.duration);
                 if(seekSlider) seekSlider.disabled = false;
             } else {
                 resetPlaybackControls(); // Full reset if duration invalid
             }
             updateStatusMessage(`Stopped. Ready to play selected file.`);
         } else {
             resetPlaybackControls();
         }
     }

    function resetPlaybackControls() {
        if(audioPlayer) audioPlayer.removeAttribute('src');
        if(playBtn) playBtn.disabled = true;
        if(pauseBtn) pauseBtn.disabled = true;
        if(stopBtn) stopBtn.disabled = true;
        if(seekSlider) {
            seekSlider.value = 0;
            seekSlider.disabled = true;
            seekSlider.max = 100;
        }
        if(currentTimeSpan) currentTimeSpan.textContent = '00:00';
        if(durationSpan) durationSpan.textContent = '00:00';
        document.querySelectorAll('#audio-list .audio-item.selected').forEach(activeItem => {
            activeItem.classList.remove('selected');
        });
        console.log("Main: Playback controls reset.");
    }

    // --- Initialization ---
    function initialize() {
        // Initialize UI Modules
        Object.values(uiModules).forEach(module => {
            if (module && module.init) {
                module.init();
            }
        });

        // Attach Main Event Listeners
        if(modelSelect) modelSelect.addEventListener('change', (e) => switchModelView(e.target.value));
        if(synthesizeBtn) synthesizeBtn.addEventListener('click', handleSynthesisSubmit);

        // Playback Listeners
        if(playBtn) playBtn.addEventListener('click', playAudio);
        if(pauseBtn) pauseBtn.addEventListener('click', pauseAudio);
        if(stopBtn) stopBtn.addEventListener('click', stopAudio);
        if(seekSlider) {
            seekSlider.addEventListener('input', () => {
                 if (audioPlayer.duration && !isNaN(audioPlayer.duration)) {
                     const seekTime = (seekSlider.value / 100) * audioPlayer.duration;
                     if(currentTimeSpan) currentTimeSpan.textContent = formatTime(seekTime);
                 }
            });
            seekSlider.addEventListener('mousedown', () => { isSeeking = true; });
            seekSlider.addEventListener('mouseup', () => {
                isSeeking = false;
                if (audioPlayer.duration && !isNaN(audioPlayer.duration)) {
                     const seekTime = (seekSlider.value / 100) * audioPlayer.duration;
                     audioPlayer.currentTime = seekTime;
                }
            });
            seekSlider.addEventListener('touchstart', () => { isSeeking = true; });
            seekSlider.addEventListener('touchend', () => {
                isSeeking = false;
                if (audioPlayer.duration && !isNaN(audioPlayer.duration)) {
                     const seekTime = (seekSlider.value / 100) * audioPlayer.duration;
                     audioPlayer.currentTime = seekTime;
                 }
             });
        }
        let statusMessage = document.getElementById('status-message');

        if(audioPlayer) {
            audioPlayer.addEventListener('timeupdate', updatePlaybackUI);
            audioPlayer.addEventListener('ended', stopAudio);
        }

        // Initial State Setup
        switchModelView(modelSelect ? modelSelect.value : 'XTTSv2'); // Set initial view
        updateAudioList(); // Load initial audio list
        resetPlaybackControls(); // Ensure player is reset
        updateStatusMessage("Ready."); // Initial status
        console.log("Main Application Initialized");
    }

    // Run Initialization
    initialize();

}); // End DOMContentLoaded