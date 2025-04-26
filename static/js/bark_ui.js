// static/js/bark_ui.js

const BarkUI = (() => {
    // --- DOM Elements ---
    let barkVoicePresetSelect, barkModelNameSelect;

    // --- Public Functions ---
    function init() {
        barkVoicePresetSelect = document.getElementById('bark-voice-preset');
        barkModelNameSelect = document.getElementById('bark-model-name');
        console.log("Bark UI Initialized");
    }

    function getFormData(formData) {
        if (!barkVoicePresetSelect || !barkModelNameSelect) return false; // Not initialized

        formData.append('voice_preset', barkVoicePresetSelect.value);
        formData.append('model_name', barkModelNameSelect.value);
        console.log(`Bark: Appending preset: ${barkVoicePresetSelect.value}, quality: ${barkModelNameSelect.value}`);
        return true;
    }

    return {
        init: init,
        getFormData: getFormData
    };
})();