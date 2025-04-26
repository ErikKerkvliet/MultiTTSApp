// static/js/piper_ui.js

const PiperUI = (() => {
    // --- DOM Elements ---
    let piperModelSelect, piperOnnxPathInput, piperJsonPathInput;

    // --- Private Helper Functions ---
    function _updatePiperPaths() {
        if (!piperModelSelect) return;
        const selectedOption = piperModelSelect.options[piperModelSelect.selectedIndex];
        if (selectedOption && selectedOption.value) {
            piperOnnxPathInput.value = selectedOption.dataset.onnx || '';
            piperJsonPathInput.value = selectedOption.dataset.json || '';
        } else {
            piperOnnxPathInput.value = '';
            piperJsonPathInput.value = '';
        }
    }

    // --- Public Functions ---
    function init() {
        piperModelSelect = document.getElementById('piper-model-select');
        piperOnnxPathInput = document.getElementById('piper-onnx-path');
        piperJsonPathInput = document.getElementById('piper-json-path');

        if (piperModelSelect) {
            piperModelSelect.addEventListener('change', _updatePiperPaths);
            _updatePiperPaths(); // Initial update
        }
        console.log("Piper UI Initialized");
    }

    function getFormData(formData) {
        if (!piperModelSelect || !piperOnnxPathInput || !piperJsonPathInput) return false; // Indicate failure

        const selectedOption = piperModelSelect.options[piperModelSelect.selectedIndex];
        const onnxPath = piperOnnxPathInput.value;
        const jsonPath = piperJsonPathInput.value;

        if (!selectedOption || !selectedOption.value || !onnxPath || !jsonPath) {
            console.error("Piper: Model, ONNX path, or JSON path missing.");
            // Optionally, signal error to main script here
            return false; // Indicate failure
        }
        formData.append('model_onnx_path', onnxPath);
        formData.append('model_json_path', jsonPath);
        console.log(`Piper: Appending ONNX: ${onnxPath}, JSON: ${jsonPath}`);
        return true; // Indicate success
    }

    return {
        init: init,
        getFormData: getFormData
    };
})();