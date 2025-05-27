// Global variables
let currentFilename = null;
let currentQRFilename = null;
let uploadedImages = [];

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    loadUploadedImages();
    initializeDragAndDrop();
    initializeRangeValues();
});

/**
 * Initialize all event listeners
 */
function initializeEventListeners() {
    // File upload
    document.getElementById('imageUpload').addEventListener('change', uploadImage);
    document.getElementById('uploadArea').addEventListener('click', () => {
        document.getElementById('imageUpload').click();
    });

    // Real-time parameter updates
    const inputs = document.querySelectorAll('input, select');
    inputs.forEach(input => {
        if (input.type === 'range') {
            input.addEventListener('input', updateRangeValue);
        }
        input.addEventListener('change', onParameterChange);
    });

    // Update finder submode visibility
    document.getElementById('finderColorMode').addEventListener('change', updateFinderSubmodeVisibility);
    document.getElementById('enableFinderOverlay').addEventListener('change', updateOverlayVisibility);
    
    // Initialize visibility
    updateFinderSubmodeVisibility();
    updateOverlayVisibility();
}

/**
 * Update range value display
 */
function updateRangeValue(event) {
    const input = event.target;
    const valueSpan = document.getElementById(input.id + 'Value');
    if (valueSpan) {
        valueSpan.textContent = input.value;
    }
}

/**
 * Update finder submode visibility based on color mode
 */
function updateFinderSubmodeVisibility() {
    const colorMode = document.getElementById('finderColorMode').value;
    const submodeGroup = document.getElementById('finderSubmodeGroup');
    submodeGroup.style.display = colorMode === 'dynamic' ? 'block' : 'none';
}

/**
 * Update overlay visibility based on checkbox
 */
function updateOverlayVisibility() {
    const enabled = document.getElementById('enableFinderOverlay').checked;
    const paddingGroup = document.getElementById('overlayPaddingGroup');
    paddingGroup.style.display = enabled ? 'block' : 'none';
}

/**
 * Handle parameter changes with auto-regeneration
 */
function onParameterChange() {
    // Auto-regenerate if image is selected and QR code exists
    if (currentFilename && document.getElementById('qrPreview').src) {
        debounce(generateQR, 500)();
    }
}

/**
 * Debounce function to limit API calls
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Load previously uploaded images
 */
async function loadUploadedImages() {
    try {
        const response = await fetch('/api/images');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        uploadedImages = result.images || [];
        displayUploadedImages();
    } catch (error) {
        console.error('Error loading images:', error);
        showMessage('Error loading uploaded images', 'error');
    }
}

/**
 * Display uploaded images in the gallery
 */
function displayUploadedImages() {
    const container = document.getElementById('uploadedImages');
    if (uploadedImages.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No images uploaded yet</p>';
        return;
    }

    container.innerHTML = uploadedImages.map(filename => `
        <div class="uploaded-image ${filename === currentFilename ? 'selected' : ''}" 
             onclick="selectImage('${filename}')" 
             title="${filename}">
            <img src="/api/preview/${filename}" alt="${filename}" onerror="this.style.display='none'">
            <p>${filename.length > 15 ? filename.substring(0, 15) + '...' : filename}</p>
        </div>
    `).join('');
}

/**
 * Select an uploaded image
 */
function selectImage(filename) {
    currentFilename = filename;
    displayUploadedImages();
    showMessage('Image selected: ' + filename, 'success');
}

/**
 * Handle image upload
 */
async function uploadImage(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
        showMessage('File size too large. Please select a file smaller than 10MB.', 'error');
        return;
    }

    // Validate file type
    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/bmp', 'image/gif', 'image/tiff', 'image/webp', 'image/svg+xml'];
    if (!allowedTypes.includes(file.type)) {
        showMessage('Unsupported file type. Please select a valid image file.', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        showMessage('Uploading image...', 'info');
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        if (result.success) {
            currentFilename = result.filename;
            uploadedImages.push(result.filename);
            displayUploadedImages();
            showMessage('Image uploaded successfully!', 'success');
        } else {
            showMessage('Upload failed: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showMessage('Upload error: ' + error.message, 'error');
    }
}

/**
 * Generate QR code with current parameters
 */
async function generateQR() {
    if (!currentFilename) {
        showMessage('Please upload and select an image first!', 'error');
        return;
    }

    // Validate QR data
    const qrData = document.getElementById('qrData').value.trim();
    if (!qrData) {
        showMessage('Please enter QR code data (URL or text)', 'error');
        return;
    }

    const formData = new FormData();
    
    // Add all parameters
    formData.append('filename', currentFilename);
    formData.append('data', qrData);
    formData.append('background_image_mode', document.getElementById('backgroundMode').value);
    formData.append('finder_shape', document.getElementById('finderShape').value);
    formData.append('finder_color_mode', document.getElementById('finderColorMode').value);
    formData.append('finder_dynamic_submode', document.getElementById('finderDynamicSubmode').value);
    formData.append('data_module_shape', document.getElementById('dataModuleShape').value);
    formData.append('data_module_color_mode', document.getElementById('dataModuleColorMode').value);
    formData.append('box_size', parseInt(document.getElementById('boxSize').value));
    formData.append('border', parseInt(document.getElementById('border').value));
    formData.append('padding', parseInt(document.getElementById('padding').value));
    formData.append('error_correction', document.getElementById('errorCorrection').value);
    formData.append('background_alpha', parseInt(document.getElementById('backgroundAlpha').value));
    formData.append('background_padding', parseInt(document.getElementById('backgroundPadding').value));
    formData.append('enable_finder_overlay', document.getElementById('enableFinderOverlay').checked);
    formData.append('finder_overlay_padding', parseInt(document.getElementById('finderOverlayPadding').value));
    formData.append('reduce_innermost_brightness', document.getElementById('reduceInnermost').checked);

    try {
        // Show loading state
        setLoadingState(true);

        const response = await fetch('/api/generate', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        
        if (result.success) {
            currentQRFilename = result.filename;
            document.getElementById('qrPreview').src = `/api/download/${result.filename}?t=${Date.now()}`;
            document.getElementById('previewArea').style.display = 'block';
            document.getElementById('placeholderText').style.display = 'none';
            showMessage('QR code generated successfully!', 'success');
        } else {
            showMessage('Generation failed: ' + result.message, 'error');
            document.getElementById('placeholderText').style.display = 'block';
        }
    } catch (error) {
        console.error('Generation error:', error);
        showMessage('Generation error: ' + error.message, 'error');
        document.getElementById('placeholderText').style.display = 'block';
    } finally {
        setLoadingState(false);
    }
}

/**
 * Download the generated QR code
 */
function downloadQR() {
    if (currentQRFilename) {
        const link = document.createElement('a');
        link.href = `/api/download/${currentQRFilename}`;
        link.download = currentQRFilename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showMessage('Download started!', 'success');
    } else {
        showMessage('No QR code available for download', 'error');
    }
}

/**
 * Set loading state
 */
function setLoadingState(isLoading) {
    const loading = document.getElementById('loading');
    const generateBtn = document.getElementById('generateBtn');
    const previewArea = document.getElementById('previewArea');
    
    if (isLoading) {
        loading.classList.add('show');
        previewArea.style.display = 'none';
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';
    } else {
        loading.classList.remove('show');
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate QR Code';
    }
}

/**
 * Show message to user
 */
function showMessage(message, type = 'info') {
    // Remove existing messages
    const existingMessages = document.querySelectorAll('.error-message, .success-message, .info-message');
    existingMessages.forEach(msg => msg.remove());

    // Create new message
    const messageDiv = document.createElement('div');
    messageDiv.textContent = message;
    
    // Set CSS class based on type
    switch (type) {
        case 'error':
            messageDiv.className = 'error-message';
            break;
        case 'success':
            messageDiv.className = 'success-message';
            break;
        default:
            messageDiv.className = 'success-message'; // Default to success styling
    }

    // Insert after header
    const header = document.querySelector('.header');
    header.insertAdjacentElement('afterend', messageDiv);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.remove();
        }
    }, 5000);
}

/**
 * Initialize drag and drop functionality
 */
function initializeDragAndDrop() {
    const uploadArea = document.getElementById('uploadArea');

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop area when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, unhighlight, false);
    });

    // Handle dropped files
    uploadArea.addEventListener('drop', handleDrop, false);

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight(e) {
        uploadArea.classList.add('dragover');
    }

    function unhighlight(e) {
        uploadArea.classList.remove('dragover');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files.length > 0) {
            const fileInput = document.getElementById('imageUpload');
            fileInput.files = files;
            uploadImage({ target: fileInput });
        }
    }
}

/**
 * Initialize range values on page load
 */
function initializeRangeValues() {
    const ranges = document.querySelectorAll('input[type="range"]');
    ranges.forEach(range => {
        updateRangeValue({ target: range });
    });
}

/**
 * Utility function to get form data as object
 */
function getFormData() {
    return {
        filename: currentFilename,
        data: document.getElementById('qrData').value,
        background_image_mode: document.getElementById('backgroundMode').value,
        finder_shape: document.getElementById('finderShape').value,
        finder_color_mode: document.getElementById('finderColorMode').value,
        finder_dynamic_submode: document.getElementById('finderDynamicSubmode').value,
        data_module_shape: document.getElementById('dataModuleShape').value,
        data_module_color_mode: document.getElementById('dataModuleColorMode').value,
        box_size: parseInt(document.getElementById('boxSize').value),
        border: parseInt(document.getElementById('border').value),
        padding: parseInt(document.getElementById('padding').value),
        error_correction: document.getElementById('errorCorrection').value,
        background_alpha: parseInt(document.getElementById('backgroundAlpha').value),
        background_padding: parseInt(document.getElementById('backgroundPadding').value),
        enable_finder_overlay: document.getElementById('enableFinderOverlay').checked,
        finder_overlay_padding: parseInt(document.getElementById('finderOverlayPadding').value),
        reduce_innermost_brightness: document.getElementById('reduceInnermost').checked
    };
}

/**
 * Reset form to default values
 */
function resetForm() {
    document.getElementById('qrData').value = 'https://www.example.com';
    document.getElementById('backgroundMode').value = 'Stretched';
    document.getElementById('finderShape').value = 'rounded_square';
    document.getElementById('finderColorMode').value = 'dynamic';
    document.getElementById('finderDynamicSubmode').value = 'single-color';
    document.getElementById('dataModuleShape').value = 'diamond';
    document.getElementById('dataModuleColorMode').value = 'adaptive';
    document.getElementById('boxSize').value = 25;
    document.getElementById('border').value = 4;
    document.getElementById('padding').value = 4;
    document.getElementById('errorCorrection').value = 'H';
    document.getElementById('backgroundAlpha').value = 255;
    document.getElementById('backgroundPadding').value = 60;
    document.getElementById('enableFinderOverlay').checked = true;
    document.getElementById('finderOverlayPadding').value = 15;
    document.getElementById('reduceInnermost').checked = true;
    
    // Update range displays
    initializeRangeValues();
    
    // Update visibility
    updateFinderSubmodeVisibility();
    updateOverlayVisibility();
}

/**
 * Export current settings as JSON
 */
function exportSettings() {
    const settings = getFormData();
    const dataStr = JSON.stringify(settings, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = 'qr-generator-settings.json';
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
}

/**
 * Import settings from JSON file
 */
function importSettings(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const settings = JSON.parse(e.target.result);
            applySettings(settings);
            showMessage('Settings imported successfully!', 'success');
        } catch (error) {
            showMessage('Error importing settings: Invalid JSON file', 'error');
        }
    };
    reader.readAsText(file);
}

/**
 * Apply settings to form
 */
function applySettings(settings) {
    Object.keys(settings).forEach(key => {
        const element = document.getElementById(key);
        if (element) {
            if (element.type === 'checkbox') {
                element.checked = settings[key];
            } else {
                element.value = settings[key];
            }
        }
    });
    
    // Update displays
    initializeRangeValues();
    updateFinderSubmodeVisibility();
    updateOverlayVisibility();
}

// Make functions available globally for onclick handlers
window.generateQR = generateQR;
window.downloadQR = downloadQR;
window.selectImage = selectImage;
window.resetForm = resetForm;
window.exportSettings = exportSettings;
window.importSettings = importSettings;