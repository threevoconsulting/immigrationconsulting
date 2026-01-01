/**
 * E-Sign Portal JavaScript
 * Handles signature capture and form submission
 */

(function() {
    'use strict';
    
    // Current signature type (draw or type)
    var currentSignatureType = 'draw';
    
    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
        initSignaturePad();
    });
    
    function initSignaturePad() {
        var canvas = document.getElementById('signature-pad');
        if (!canvas) {
            return;
        }
        
        // Check if SignaturePad is available
        if (typeof SignaturePad === 'undefined') {
            console.error('SignaturePad library not loaded');
            return;
        }
        
        // Get container and set canvas size
        var container = canvas.parentElement;
        var containerWidth = container.offsetWidth || 600;
        
        // Set canvas dimensions
        canvas.width = containerWidth;
        canvas.height = 200;
        canvas.style.width = containerWidth + 'px';
        canvas.style.height = '200px';
        
        // Initialize SignaturePad
        var signaturePad = new SignaturePad(canvas, {
            backgroundColor: 'rgb(255, 255, 255)',
            penColor: 'rgb(0, 0, 0)',
            minWidth: 0.5,
            maxWidth: 2.5
        });
        
        // Store reference globally
        window.signaturePad = signaturePad;
        
        // Handle window resize
        var resizeTimeout;
        window.addEventListener('resize', function() {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(function() {
                if (window.signaturePad) {
                    var data = window.signaturePad.toData();
                    var newWidth = container.offsetWidth || 600;
                    canvas.width = newWidth;
                    canvas.height = 200;
                    canvas.style.width = newWidth + 'px';
                    canvas.style.height = '200px';
                    window.signaturePad.clear();
                    if (data.length > 0) {
                        window.signaturePad.fromData(data);
                    }
                }
            }, 200);
        });
        
        // Typed signature preview
        var typedInput = document.getElementById('typed-signature');
        var typedPreview = document.getElementById('typed-signature-preview');
        
        if (typedInput && typedPreview) {
            typedInput.addEventListener('input', function() {
                typedPreview.textContent = this.value;
                updateSubmitButton();
            });
        }
        
        // Agreement checkbox handler
        var agreementCheckbox = document.getElementById('agreement-checkbox');
        var submitButton = document.getElementById('submit-signature');
        
        if (agreementCheckbox && submitButton) {
            agreementCheckbox.addEventListener('change', function() {
                updateSubmitButton();
            });
        }
        
        // Watch for signature changes on canvas
        canvas.addEventListener('pointerup', updateSubmitButton);
        canvas.addEventListener('mouseup', updateSubmitButton);
        canvas.addEventListener('touchend', updateSubmitButton);
    }
    
    // Toggle between draw and type signature modes
    function toggleSignatureType(type) {
        currentSignatureType = type;
        
        var drawPanel = document.getElementById('draw-signature-panel');
        var typePanel = document.getElementById('type-signature-panel');
        var btnDraw = document.getElementById('btn-draw-signature');
        var btnType = document.getElementById('btn-type-signature');
        
        if (type === 'draw') {
            drawPanel.style.display = 'block';
            typePanel.style.display = 'none';
            btnDraw.classList.add('active');
            btnType.classList.remove('active');
        } else {
            drawPanel.style.display = 'none';
            typePanel.style.display = 'block';
            btnDraw.classList.remove('active');
            btnType.classList.add('active');
        }
        
        updateSubmitButton();
    }
    
    // Clear the drawn signature
    function clearSignature() {
        if (window.signaturePad) {
            window.signaturePad.clear();
            updateSubmitButton();
        }
    }
    
    // Update submit button state based on form validity
    function updateSubmitButton() {
        var submitButton = document.getElementById('submit-signature');
        var agreementCheckbox = document.getElementById('agreement-checkbox');
        
        if (!submitButton || !agreementCheckbox) {
            return;
        }
        
        var hasSignature = false;
        
        if (currentSignatureType === 'draw') {
            hasSignature = window.signaturePad && !window.signaturePad.isEmpty();
        } else {
            var typedInput = document.getElementById('typed-signature');
            hasSignature = typedInput && typedInput.value.trim().length > 0;
        }
        
        var isValid = hasSignature && agreementCheckbox.checked;
        submitButton.disabled = !isValid;
    }
    
    // Convert typed signature to canvas image
    function typedSignatureToDataURL(text) {
        var canvas = document.createElement('canvas');
        canvas.width = 400;
        canvas.height = 100;
        var ctx = canvas.getContext('2d');
        
        // White background
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Draw text
        ctx.fillStyle = '#000000';
        ctx.font = '48px "Brush Script MT", cursive';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, canvas.width / 2, canvas.height / 2);
        
        return canvas.toDataURL('image/png');
    }
    
    // Submit the signature
    function submitSignature() {
        var submitButton = document.getElementById('submit-signature');
        var token = document.getElementById('signature-token').value;
        var csrfToken = document.getElementById('csrf-token').value;
        
        // Disable button and show loading
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i>Signing...';
        
        // Get signature data
        var signatureData;
        var typedName = null;
        
        if (currentSignatureType === 'draw') {
            if (!window.signaturePad || window.signaturePad.isEmpty()) {
                alert('Please draw your signature first.');
                resetSubmitButton();
                return;
            }
            signatureData = window.signaturePad.toDataURL('image/png');
        } else {
            var typedInput = document.getElementById('typed-signature');
            typedName = typedInput.value.trim();
            if (!typedName) {
                alert('Please type your name.');
                resetSubmitButton();
                return;
            }
            signatureData = typedSignatureToDataURL(typedName);
        }
        
        // Create form data
        var formData = new FormData();
        formData.append('csrf_token', csrfToken);
        formData.append('signature_type', currentSignatureType);
        formData.append('signature_data', signatureData);
        if (typedName) {
            formData.append('typed_name', typedName);
        }
        
        // Submit via fetch
        fetch('/my/immigration/sign/' + token + '/submit', {
            method: 'POST',
            body: formData
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                submitButton.innerHTML = '<i class="fa fa-check me-2"></i>Signed Successfully!';
                submitButton.classList.remove('btn-primary');
                submitButton.classList.add('btn-success');
                
                setTimeout(function() {
                    window.location.href = data.redirect_url;
                }, 1000);
            } else {
                alert('Error: ' + (data.error || 'Unknown error occurred'));
                resetSubmitButton();
            }
        })
        .catch(function(error) {
            console.error('Submit error:', error);
            alert('An error occurred while submitting your signature. Please try again.');
            resetSubmitButton();
        });
    }
    
    // Reset submit button to original state
    function resetSubmitButton() {
        var submitButton = document.getElementById('submit-signature');
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.innerHTML = '<i class="fa fa-check me-2"></i>Sign Document';
            submitButton.classList.remove('btn-success');
            submitButton.classList.add('btn-primary');
        }
        updateSubmitButton();
    }
    
    // Make functions globally accessible for onclick handlers
    window.toggleSignatureType = toggleSignatureType;
    window.clearSignature = clearSignature;
    window.submitSignature = submitSignature;
    
})();
