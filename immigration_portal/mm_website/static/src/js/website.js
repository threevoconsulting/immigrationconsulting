/** @odoo-module **/

/**
 * Migration Monitor Website JavaScript
 * Handles newsletter subscription and other interactive features
 */

document.addEventListener('DOMContentLoaded', function() {
    // Newsletter Form Handler
    initNewsletterForm();
    
    // Smooth Scroll for anchor links
    initSmoothScroll();
    
    // Animation on scroll
    initScrollAnimations();
});

/**
 * Initialize Newsletter Form
 */
function initNewsletterForm() {
    const form = document.getElementById('newsletterForm');
    const emailInput = document.getElementById('newsletterEmail');
    const messageDiv = document.getElementById('newsletterMessage');
    
    if (!form) return;
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const email = emailInput.value.trim();
        if (!email) {
            showMessage(messageDiv, 'Please enter your email address.', 'error');
            return;
        }
        
        // Disable form while submitting
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i>Subscribing...';
        
        try {
            const response = await fetch('/newsletter/subscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: { email: email },
                    id: Math.floor(Math.random() * 1000000)
                })
            });
            
            const data = await response.json();
            
            if (data.result && data.result.success) {
                showMessage(messageDiv, data.result.message, 'success');
                emailInput.value = '';
            } else {
                showMessage(messageDiv, data.result?.message || 'An error occurred. Please try again.', 'error');
            }
        } catch (error) {
            console.error('Newsletter subscription error:', error);
            showMessage(messageDiv, 'An error occurred. Please try again.', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
}

/**
 * Show message in message div
 */
function showMessage(div, message, type) {
    if (!div) return;
    
    div.textContent = message;
    div.className = 'mm-newsletter-message mt-3 ' + type;
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        div.textContent = '';
        div.className = 'mm-newsletter-message mt-3';
    }, 5000);
}

/**
 * Initialize Smooth Scroll for anchor links
 */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                e.preventDefault();
                
                const headerOffset = 80; // Account for fixed header
                const elementPosition = targetElement.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
                
                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

/**
 * Initialize Scroll Animations
 */
function initScrollAnimations() {
    // Only apply to elements with the animate class
    const animatedElements = document.querySelectorAll('.mm-animate-on-scroll');
    
    if (animatedElements.length === 0) return;
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('mm-animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });
    
    animatedElements.forEach(el => observer.observe(el));
}

/**
 * UTM Parameter Tracking
 * Captures UTM parameters from URL and adds to forms
 */
function initUTMTracking() {
    const urlParams = new URLSearchParams(window.location.search);
    const utmParams = ['utm_source', 'utm_medium', 'utm_campaign'];
    
    document.querySelectorAll('form').forEach(form => {
        utmParams.forEach(param => {
            const value = urlParams.get(param);
            if (value) {
                let input = form.querySelector(`input[name="${param}"]`);
                if (!input) {
                    input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = param;
                    form.appendChild(input);
                }
                input.value = value;
            }
        });
    });
}

// Initialize UTM tracking when DOM is ready
document.addEventListener('DOMContentLoaded', initUTMTracking);
