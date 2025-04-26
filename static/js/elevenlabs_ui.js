// static/js/elevenlabs_ui.js

const ElevenLabsUI = (() => {
    // --- DOM Elements ---
    let keySelect, apiKeyInput, validateBtn, keyStatusSpan,
        creditsSpan, refreshCreditsBtn, voiceSelect, refreshVoicesBtn, modelSelect;

    // --- State ---
    let currentValidApiKeyRef = null; // Tracks *how* the key was validated ('stored_key_NAME' or manual key value)

    // --- API Calls (Private Helpers) ---
    async function _fetchAndSet(endpoint, payload, updateUICallback, errorMsgPrefix) {
        const btnToDisable = endpoint.includes('voices') ? refreshVoicesBtn : refreshCreditsBtn;
        if(btnToDisable) btnToDisable.disabled = true;

        try {
            const response = await fetch(`/api/elevenlabs/${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();

            if (response.ok && data.success) {
                updateUICallback(data); // Pass data to UI update function
                console.log(`${errorMsgPrefix}: Data fetched successfully.`);
            } else {
                console.error(`${errorMsgPrefix}: Failed -`, data.message);
                updateUICallback(null, data.message || 'Failed to fetch'); // Signal error to UI function
            }
        } catch (error) {
            console.error(`${errorMsgPrefix}: Error -`, error);
            updateUICallback(null, error.message || 'Network error'); // Signal error to UI function
        } finally {
             // Re-enable button only if key is still considered valid by this module
             if (currentValidApiKeyRef && btnToDisable) {
                 btnToDisable.disabled = false;
             }
        }
    }

    // --- UI Update Functions (Private Helpers) ---
     function _updateKeyStatus(message, level = 'muted') { // level: muted, info, success, warning, danger
        if (!keyStatusSpan) return;
        keyStatusSpan.textContent = message;
        keyStatusSpan.className = `text-${level}`; // Assumes Bootstrap text color classes
    }

     function _updateCreditsUI(data, error = null) {
         if (!creditsSpan) return;
         if (error || !data || !data.subscription) {
             creditsSpan.textContent = error ? `Error: ${error}` : 'Could not load credits.';
         } else {
             const sub = data.subscription;
             const used = sub.character_count || 0;
             const limit = sub.character_limit || 0;
             const remaining = limit - used;
             const percentage = limit > 0 ? Math.round((used / limit) * 100) : 0;
             const tier = sub.tier || 'N/A';
             creditsSpan.textContent = `Tier: ${tier} | Used: ${used.toLocaleString()}/${limit.toLocaleString()} chars (${percentage}%)`;
         }
     }

      function _updateVoicesUI(data, error = null) {
          if (!voiceSelect) return;
          voiceSelect.innerHTML = ''; // Clear existing options

          if (error || !data || !data.voices) {
               const option = document.createElement('option');
               option.value = "";
               option.textContent = error ? `-- Error: ${error} --` : '-- Error loading voices --';
               voiceSelect.appendChild(option);
               voiceSelect.disabled = true;
           } else if (data.voices.length === 0) {
                const option = document.createElement('option');
                option.value = "";
                option.textContent = '-- No voices found --';
                voiceSelect.appendChild(option);
                voiceSelect.disabled = true; // Or false if they might add voices later?
           } else {
               data.voices.forEach(voice => {
                   const option = document.createElement('option');
                   option.value = voice.id;
                   option.textContent = voice.name;
                   if (voice.name === 'Rachel') option.selected = true; // Default selection attempt
                   voiceSelect.appendChild(option);
               });
                if (!voiceSelect.value && data.voices.length > 0) voiceSelect.selectedIndex = 0; // Select first if default not found
               voiceSelect.disabled = false; // Enable select
           }
       }

    // --- Public Functions ---
    function init() {
        // Select elements
        keySelect = document.getElementById('elevenlabs-key-select');
        apiKeyInput = document.getElementById('elevenlabs-api-key');
        validateBtn = document.getElementById('validate-key-btn');
        keyStatusSpan = document.getElementById('key-status');
        creditsSpan = document.getElementById('elevenlabs-credits');
        refreshCreditsBtn = document.getElementById('refresh-credits-btn');
        voiceSelect = document.getElementById('elevenlabs-voice');
        refreshVoicesBtn = document.getElementById('refresh-voices-btn');
        modelSelect = document.getElementById('elevenlabs-model');

        // Attach listeners
        if (keySelect) keySelect.addEventListener('change', validateApiKey);
        if (validateBtn) validateBtn.addEventListener('click', validateApiKey);
        if (refreshVoicesBtn) refreshVoicesBtn.addEventListener('click', fetchVoices);
        if (refreshCreditsBtn) refreshCreditsBtn.addEventListener('click', fetchSubscription);

        resetStatus(); // Initial state
        console.log("ElevenLabs UI Initialized");
    }

    function resetStatus() {
         if(keyStatusSpan) _updateKeyStatus('Not validated', 'muted');
         if(creditsSpan) creditsSpan.textContent = 'Validate key to check credits.';
         if(voiceSelect) {
            voiceSelect.innerHTML = '<option value="">-- Validate API key first --</option>';
            voiceSelect.disabled = true;
         }
         if(refreshVoicesBtn) refreshVoicesBtn.disabled = true;
         if(refreshCreditsBtn) refreshCreditsBtn.disabled = true;
         currentValidApiKeyRef = null; // Clear validated key reference
         console.log("ElevenLabs status reset.");
     }

    async function validateApiKey() {
        let keyToSend = null;
        let keyNameToSend = null;
        let apiKeyReference = null; // How we'll refer to the validated key internally

        if (apiKeyInput && apiKeyInput.value.trim()) {
            keyToSend = apiKeyInput.value.trim();
            apiKeyReference = keyToSend; // Store the actual key for reference (use with caution)
            if (keySelect) keySelect.value = ''; // Clear dropdown
        } else if (keySelect && keySelect.value) {
            keyNameToSend = keySelect.value;
             apiKeyReference = `stored_key_${keyNameToSend}`; // Refer to it by name
            if (apiKeyInput) apiKeyInput.value = ''; // Clear manual input
        } else {
             _updateKeyStatus('No key selected or entered.', 'warning');
            resetStatus();
            return;
        }

        _updateKeyStatus('Validating...', 'info');
        if(validateBtn) validateBtn.disabled = true;
        resetStatus(); // Reset dependent fields before validation attempt

        try {
            const response = await fetch('/api/elevenlabs/validate_key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: keyToSend, key_name: keyNameToSend })
            });
            const data = await response.json();

            if (response.ok && data.success) {
                _updateKeyStatus('Valid', 'success');
                currentValidApiKeyRef = apiKeyReference; // Store reference to the *validated* key source
                console.log("EL Key Validated. Ref:", currentValidApiKeyRef);
                // Enable dependent actions & fetch data
                if(refreshVoicesBtn) refreshVoicesBtn.disabled = false;
                if(refreshCreditsBtn) refreshCreditsBtn.disabled = false;
                if(voiceSelect) voiceSelect.disabled = false;
                fetchVoices();
                fetchSubscription();
            } else {
                _updateKeyStatus(`Invalid (${data.message || 'Validation failed'})`, 'danger');
                resetStatus();
            }
        } catch (error) {
            console.error("Error validating API key:", error);
            _updateKeyStatus(`Error: ${error.message}`, 'danger');
            resetStatus();
        } finally {
             if(validateBtn) validateBtn.disabled = false;
        }
     }

     async function fetchVoices() {
         if (!currentValidApiKeyRef) {
             console.warn("EL: Cannot fetch voices, API key not validated.");
              _updateVoicesUI(null, 'Validate API key first');
             return;
         }
         console.log("EL: Fetching voices...");
         if(voiceSelect) voiceSelect.innerHTML = '<option value="">Loading voices...</option>';
         if(voiceSelect) voiceSelect.disabled = true;

         let payload = {};
         if (currentValidApiKeyRef.startsWith('stored_key_')) payload.key_name = currentValidApiKeyRef.replace('stored_key_', '');
         else payload.api_key = currentValidApiKeyRef; // Assumed manual key

         await _fetchAndSet('voices', payload, _updateVoicesUI, "EL Voices");
     }

     async function fetchSubscription() {
         if (!currentValidApiKeyRef) {
             console.warn("EL: Cannot fetch subscription, API key not validated.");
              _updateCreditsUI(null, 'Validate API key first');
             return;
         }
         console.log("EL: Fetching subscription...");
         if(creditsSpan) creditsSpan.textContent = 'Checking credits...';

         let payload = {};
         if (currentValidApiKeyRef.startsWith('stored_key_')) payload.key_name = currentValidApiKeyRef.replace('stored_key_', '');
         else payload.api_key = currentValidApiKeyRef; // Assumed manual key

         await _fetchAndSet('subscription', payload, _updateCreditsUI, "EL Subscription");
     }

    function getFormData(formData) {
        if (!currentValidApiKeyRef) {
            console.error("EL: Cannot get form data, API key not validated.");
            return false; // Indicate failure
        }
        if (!voiceSelect || !voiceSelect.value) {
             console.error("EL: Cannot get form data, voice not selected.");
            return false; // Indicate failure
        }
        if (!modelSelect) return false;

        // Append key reference based on validation method
        if (currentValidApiKeyRef.startsWith('stored_key_')) {
            formData.append('api_key_name', currentValidApiKeyRef.replace('stored_key_', ''));
            console.log(`EL: Appending key name: ${currentValidApiKeyRef.replace('stored_key_', '')}`);
        } else {
            formData.append('api_key_manual', currentValidApiKeyRef); // Append the manual key itself
             console.log(`EL: Appending manual key.`);
        }

        formData.append('voice_id', voiceSelect.value);
        formData.append('model_id', modelSelect.value);
         console.log(`EL: Appending voice: ${voiceSelect.value}, model: ${modelSelect.value}`);
        return true; // Indicate success
    }

    // Public interface
    return {
        init: init,
        resetStatus: resetStatus,
        getFormData: getFormData
    };
})();