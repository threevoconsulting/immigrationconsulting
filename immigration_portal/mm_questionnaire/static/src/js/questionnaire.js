/**
 * Immigration Portal - Questionnaire Module JavaScript
 * Handles auto-save, section navigation, and repeater functionality
 */

(function() {
    'use strict';
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initQuestionnaire);
    } else {
        initQuestionnaire();
    }
    
    function initQuestionnaire() {

    // Configuration
    const CONFIG = {
        saveDebounceMs: 800,
        saveIndicatorDurationMs: 2000,
    };

    // State
    let saveTimeout = null;
    let pendingSaves = new Map();

    // =====================
    // Utility Functions
    // =====================

    function getCaseId() {
        const form = document.getElementById('questionnaire-form');
        return form ? form.dataset.caseId : null;
    }

    function getQtype() {
        const form = document.getElementById('questionnaire-form');
        return form ? form.dataset.qtype : null;
    }

    function showSaveIndicator() {
        const saving = document.querySelector('.mm-save-indicator');
        const saved = document.querySelector('.mm-saved-indicator');
        if (saving) saving.style.display = 'inline';
        if (saved) saved.style.display = 'none';
    }

    function showSavedIndicator() {
        const saving = document.querySelector('.mm-save-indicator');
        const saved = document.querySelector('.mm-saved-indicator');
        if (saving) saving.style.display = 'none';
        if (saved) saved.style.display = 'inline';

        setTimeout(() => {
            if (saved) saved.style.display = 'none';
        }, CONFIG.saveIndicatorDurationMs);
    }

    function showError(message) {
        console.error('Questionnaire Error:', message);
        // Could add toast notification here
    }

    // =====================
    // JSON-RPC Helper
    // =====================

    async function jsonRpc(url, params) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: params,
                id: Math.floor(Math.random() * 1000000),
            }),
        });

        const data = await response.json();
        if (data.error) {
            throw new Error(data.error.message || 'Unknown error');
        }
        return data.result;
    }

    // =====================
    // Auto-Save Functionality
    // =====================

    async function saveField(fieldName, fieldValue, model = 'profile') {
        const caseId = getCaseId();
        const qtype = getQtype();

        if (!caseId) {
            console.error('No case ID found');
            return;
        }

        showSaveIndicator();

        try {
            const result = await jsonRpc('/my/immigration/questionnaire/save', {
                case_id: caseId,
                field_name: fieldName,
                field_value: fieldValue,
                model: model,
                qtype: qtype,
            });

            if (result.success) {
                showSavedIndicator();
            } else {
                showError(result.error || 'Failed to save');
            }
        } catch (error) {
            showError(error.message);
        }
    }

    function debouncedSave(fieldName, fieldValue, model) {
        // Clear any pending save for this field
        if (pendingSaves.has(fieldName)) {
            clearTimeout(pendingSaves.get(fieldName));
        }

        // Set up debounced save
        const timeoutId = setTimeout(() => {
            saveField(fieldName, fieldValue, model);
            pendingSaves.delete(fieldName);
        }, CONFIG.saveDebounceMs);

        pendingSaves.set(fieldName, timeoutId);
    }

    function handleAutoSave(event) {
        const element = event.target;
        const fieldName = element.dataset.field || element.name;
        const model = element.dataset.model || 'profile';

        let fieldValue;
        if (element.type === 'checkbox') {
            fieldValue = element.checked;
        } else if (element.type === 'radio') {
            if (!element.checked) return; // Only save if this radio is checked
            fieldValue = element.value;
        } else {
            fieldValue = element.value;
        }

        debouncedSave(fieldName, fieldValue, model);
    }

    // =====================
    // Section Navigation
    // =====================

    async function completeSection(section) {
        const caseId = getCaseId();
        const qtype = getQtype();

        try {
            const result = await jsonRpc('/my/immigration/questionnaire/complete-section', {
                case_id: caseId,
                qtype: qtype,
                section: section,
            });

            return result.success;
        } catch (error) {
            showError(error.message);
            return false;
        }
    }

    function handleNextButton(event) {
        event.preventDefault();
        const button = event.currentTarget;
        const section = parseInt(button.dataset.section);
        const nextUrl = button.dataset.nextUrl;

        // Complete current section then navigate
        completeSection(section).then(success => {
            if (success) {
                window.location.href = nextUrl;
            } else {
                // Navigate anyway - section completion is not blocking
                window.location.href = nextUrl;
            }
        });
    }

    // =====================
    // Submit Questionnaire
    // =====================

    async function submitQuestionnaire(event) {
        event.preventDefault();
        const button = event.currentTarget;
        const caseId = button.dataset.caseId;
        const qtype = button.dataset.qtype;

        button.disabled = true;
        button.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i> Submitting...';

        try {
            const result = await jsonRpc('/my/immigration/questionnaire/submit', {
                case_id: caseId,
                qtype: qtype,
            });

            if (result.success) {
                window.location.href = result.redirect_url;
            } else {
                alert(result.error || 'Failed to submit questionnaire');
                button.disabled = false;
                button.innerHTML = '<i class="fa fa-paper-plane me-2"></i> Submit Questionnaire';
            }
        } catch (error) {
            showError(error.message);
            button.disabled = false;
            button.innerHTML = '<i class="fa fa-paper-plane me-2"></i> Submit Questionnaire';
        }
    }

    // =====================
    // Repeater Functions - Children
    // =====================

    async function addChild() {
        const caseId = getCaseId();

        try {
            const result = await jsonRpc('/my/immigration/questionnaire/add-child', {
                case_id: caseId,
                name: 'New Child',
            });

            if (result.success) {
                // Reload page to show new child
                window.location.reload();
            } else {
                showError(result.error);
            }
        } catch (error) {
            showError(error.message);
        }
    }

    async function updateChild(childId, field, value) {
        const caseId = getCaseId();

        try {
            const params = {
                case_id: caseId,
                child_id: childId,
            };
            params[field] = value;

            const result = await jsonRpc('/my/immigration/questionnaire/update-child', params);

            if (result.success) {
                showSavedIndicator();
            } else {
                showError(result.error);
            }
        } catch (error) {
            showError(error.message);
        }
    }

    async function deleteChild(childId) {
        if (!confirm('Are you sure you want to remove this child?')) return;

        const caseId = getCaseId();

        try {
            const result = await jsonRpc('/my/immigration/questionnaire/delete-child', {
                case_id: caseId,
                child_id: childId,
            });

            if (result.success) {
                // Remove the element from DOM
                const element = document.querySelector(`[data-child-id="${childId}"]`);
                if (element) {
                    element.remove();
                }
            } else {
                showError(result.error);
            }
        } catch (error) {
            showError(error.message);
        }
    }

    // =====================
    // Repeater Functions - Education
    // =====================

    async function addEducation() {
        const caseId = getCaseId();

        try {
            const result = await jsonRpc('/my/immigration/questionnaire/add-education', {
                case_id: caseId,
                institution_name: '',
                credential_type: 'bachelors',
                field_of_study: '',
            });

            if (result.success) {
                window.location.reload();
            } else {
                showError(result.error);
            }
        } catch (error) {
            showError(error.message);
        }
    }

    async function updateEducation(educationId, field, value) {
        const caseId = getCaseId();

        try {
            const params = {
                case_id: caseId,
                education_id: educationId,
            };
            params[field] = value;

            const result = await jsonRpc('/my/immigration/questionnaire/update-education', params);

            if (result.success) {
                showSavedIndicator();
            } else {
                showError(result.error);
            }
        } catch (error) {
            showError(error.message);
        }
    }

    async function deleteEducation(educationId) {
        if (!confirm('Are you sure you want to remove this education record?')) return;

        const caseId = getCaseId();

        try {
            const result = await jsonRpc('/my/immigration/questionnaire/delete-education', {
                case_id: caseId,
                education_id: educationId,
            });

            if (result.success) {
                const element = document.querySelector(`[data-education-id="${educationId}"]`);
                if (element) {
                    element.remove();
                }
            } else {
                showError(result.error);
            }
        } catch (error) {
            showError(error.message);
        }
    }

    // =====================
    // Repeater Functions - Experience
    // =====================

    async function addExperience() {
        const caseId = getCaseId();

        try {
            const result = await jsonRpc('/my/immigration/questionnaire/add-experience', {
                case_id: caseId,
                employer_name: '',
                job_title: '',
            });

            if (result.success) {
                window.location.reload();
            } else {
                showError(result.error);
            }
        } catch (error) {
            showError(error.message);
        }
    }

    async function updateExperience(experienceId, field, value) {
        const caseId = getCaseId();

        try {
            const params = {
                case_id: caseId,
                experience_id: experienceId,
            };
            params[field] = value;

            const result = await jsonRpc('/my/immigration/questionnaire/update-experience', params);

            if (result.success) {
                showSavedIndicator();
            } else {
                showError(result.error);
            }
        } catch (error) {
            showError(error.message);
        }
    }

    async function deleteExperience(experienceId) {
        if (!confirm('Are you sure you want to remove this work experience?')) return;

        const caseId = getCaseId();

        try {
            const result = await jsonRpc('/my/immigration/questionnaire/delete-experience', {
                case_id: caseId,
                experience_id: experienceId,
            });

            if (result.success) {
                const element = document.querySelector(`[data-experience-id="${experienceId}"]`);
                if (element) {
                    element.remove();
                }
            } else {
                showError(result.error);
            }
        } catch (error) {
            showError(error.message);
        }
    }

    // =====================
    // Repeater Functions - Language
    // =====================

    async function addLanguage() {
        const caseId = getCaseId();

        try {
            const result = await jsonRpc('/my/immigration/questionnaire/add-language', {
                case_id: caseId,
                language: 'english',
                test_type: 'ielts_general',
            });

            if (result.success) {
                window.location.reload();
            } else {
                showError(result.error);
            }
        } catch (error) {
            showError(error.message);
        }
    }

    async function updateLanguage(languageId, field, value) {
        const caseId = getCaseId();

        try {
            const params = {
                case_id: caseId,
                language_id: languageId,
            };
            params[field] = value;

            const result = await jsonRpc('/my/immigration/questionnaire/update-language', params);

            if (result.success) {
                showSavedIndicator();
                // Update CLB scores display if returned
                if (result.clb_scores) {
                    // Could update CLB badges here without reload
                }
            } else {
                showError(result.error);
            }
        } catch (error) {
            showError(error.message);
        }
    }

    async function deleteLanguage(languageId) {
        if (!confirm('Are you sure you want to remove this language test?')) return;

        const caseId = getCaseId();

        try {
            const result = await jsonRpc('/my/immigration/questionnaire/delete-language', {
                case_id: caseId,
                language_id: languageId,
            });

            if (result.success) {
                const element = document.querySelector(`[data-language-id="${languageId}"]`);
                if (element) {
                    element.remove();
                }
            } else {
                showError(result.error);
            }
        } catch (error) {
            showError(error.message);
        }
    }

    // =====================
    // Event Listeners Setup
    // =====================

    function setupEventListeners() {
        // Auto-save on profile fields
        document.querySelectorAll('.mm-auto-save').forEach(element => {
            const eventType = (element.type === 'checkbox' || element.type === 'radio')
                ? 'change'
                : 'blur';
            element.addEventListener(eventType, handleAutoSave);

            // Also save on change for selects
            if (element.tagName === 'SELECT') {
                element.addEventListener('change', handleAutoSave);
            }
        });

        // Toggle trigger for conditional sections (e.g., family details)
        document.querySelectorAll('.mm-toggle-trigger').forEach(checkbox => {
            const targetId = checkbox.dataset.toggleTarget;
            if (targetId) {
                const targetElement = document.getElementById(targetId);
                if (targetElement) {
                    checkbox.addEventListener('change', function() {
                        targetElement.style.display = this.checked ? '' : 'none';
                    });
                }
            }
        });

        // Dynamic language label toggle
        const firstLanguageSelect = document.querySelector('.mm-first-language-select');
        if (firstLanguageSelect) {
            console.log('Language select found, setting up listener');
            
            function updateOtherLanguageLabel() {
                const otherLanguageSpan = document.querySelector('.mm-other-language');
                if (otherLanguageSpan) {
                    const otherLang = firstLanguageSelect.value === 'french' ? 'English' : 'French';
                    console.log('Updating other language to:', otherLang);
                    otherLanguageSpan.textContent = otherLang;
                }
            }
            
            // Update on change
            firstLanguageSelect.addEventListener('change', updateOtherLanguageLabel);
            
            // Also update immediately on page load to ensure correct state
            updateOtherLanguageLabel();
        }

        // Next button
        document.querySelectorAll('.mm-btn-next').forEach(button => {
            button.addEventListener('click', handleNextButton);
        });

        // Submit button
        document.querySelectorAll('.mm-submit-questionnaire').forEach(button => {
            button.addEventListener('click', submitQuestionnaire);
        });

        // Child repeater
        const addChildBtn = document.getElementById('btn-add-child');
        if (addChildBtn) {
            addChildBtn.addEventListener('click', addChild);
        }

        document.querySelectorAll('.mm-delete-child').forEach(button => {
            button.addEventListener('click', () => deleteChild(button.dataset.childId));
        });

        document.querySelectorAll('.mm-child-field').forEach(element => {
            element.addEventListener('blur', (e) => {
                const childId = e.target.dataset.childId;
                const field = e.target.dataset.field;
                const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
                updateChild(childId, field, value);
            });
        });

        // Education repeater
        const addEducationBtn = document.getElementById('btn-add-education');
        if (addEducationBtn) {
            addEducationBtn.addEventListener('click', addEducation);
        }

        document.querySelectorAll('.mm-delete-education').forEach(button => {
            button.addEventListener('click', () => deleteEducation(button.dataset.educationId));
        });

        document.querySelectorAll('.mm-education-field').forEach(element => {
            element.addEventListener('blur', (e) => {
                const educationId = e.target.dataset.educationId;
                const field = e.target.dataset.field;
                const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
                updateEducation(educationId, field, value);
            });
            // Handle select changes immediately
            if (element.tagName === 'SELECT') {
                element.addEventListener('change', (e) => {
                    const educationId = e.target.dataset.educationId;
                    const field = e.target.dataset.field;
                    updateEducation(educationId, field, e.target.value);
                });
            }
        });

        // Experience repeater
        const addExperienceBtn = document.getElementById('btn-add-experience');
        if (addExperienceBtn) {
            addExperienceBtn.addEventListener('click', addExperience);
        }

        document.querySelectorAll('.mm-delete-experience').forEach(button => {
            button.addEventListener('click', () => deleteExperience(button.dataset.experienceId));
        });

        document.querySelectorAll('.mm-experience-field').forEach(element => {
            element.addEventListener('blur', (e) => {
                const experienceId = e.target.dataset.experienceId;
                const field = e.target.dataset.field;
                const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
                updateExperience(experienceId, field, value);
            });
            if (element.tagName === 'SELECT') {
                element.addEventListener('change', (e) => {
                    const experienceId = e.target.dataset.experienceId;
                    const field = e.target.dataset.field;
                    updateExperience(experienceId, field, e.target.value);
                });
            }
        });

        // Language repeater
        const addLanguageBtn = document.getElementById('btn-add-language');
        if (addLanguageBtn) {
            addLanguageBtn.addEventListener('click', addLanguage);
        }

        document.querySelectorAll('.mm-delete-language').forEach(button => {
            button.addEventListener('click', () => deleteLanguage(button.dataset.languageId));
        });

        document.querySelectorAll('.mm-language-field').forEach(element => {
            element.addEventListener('blur', (e) => {
                const languageId = e.target.dataset.languageId;
                const field = e.target.dataset.field;
                const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
                updateLanguage(languageId, field, value);
            });
            if (element.tagName === 'SELECT') {
                element.addEventListener('change', (e) => {
                    const languageId = e.target.dataset.languageId;
                    const field = e.target.dataset.field;
                    updateLanguage(languageId, field, e.target.value);
                });
            }
        });
    }

    // Initialize
    setupEventListeners();
    
    } // end initQuestionnaire
})();
