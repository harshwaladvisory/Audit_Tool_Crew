// Cover Letter Generator - Professional JavaScript
// Theme: Harshwal Purple (#413178)
// Matches RRF Status Tracker Design

document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    initializeFileUpload();
    initializeFormValidation();
    initializeDownloadHandlers();
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            const closeBtn = alert.querySelector('.btn-close');
            if (closeBtn) {
                closeBtn.click();
            }
        });
    }, 5000);
});

/**
 * Initialize file upload functionality
 */
function initializeFileUpload() {
    const fileInput = document.getElementById('excel_file');
    const submitBtn = document.getElementById('submitBtn');
    const form = document.getElementById('uploadForm');
    
    if (!fileInput || !submitBtn || !form) return;
    
    // File input change handler
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const isValid = validateFile(file);
            if (isValid) {
                showFileInfo(file);
            }
        }
    });
    
    // Form submit handler
    form.addEventListener('submit', function(e) {
        const file = fileInput.files[0];
        const clientName = document.getElementById('client_name')?.value.trim();
        const draftType = document.getElementById('draft_type')?.value.trim();
        const taxYear = document.getElementById('tax_year')?.value.trim();
        
        // Validate before submission
        if (!file) {
            e.preventDefault();
            showAlert('Please select an Excel file', 'error');
            return;
        }
        
        if (!clientName) {
            e.preventDefault();
            showAlert('Please enter a client name', 'error');
            return;
        }
        
        if (!draftType) {
            e.preventDefault();
            showAlert('Please select a draft type', 'error');
            return;
        }
        
        if (!taxYear) {
            e.preventDefault();
            showAlert('Please enter a tax year', 'error');
            return;
        }
        
        if (!validateFile(file)) {
            e.preventDefault();
            return;
        }
        
        // Show loading state
        showLoadingState(submitBtn);
    });
}

/**
 * Show file information after selection
 */
function showFileInfo(file) {
    const fileSize = formatFileSize(file.size);
    const fileName = file.name;
    
    console.log(`File selected: ${fileName} (${fileSize})`);
    
    // Update any file info display elements if they exist
    const fileInfoElements = document.querySelectorAll('.file-info-text');
    fileInfoElements.forEach(function(element) {
        element.textContent = `${fileName} (${fileSize})`;
        element.style.color = 'var(--primary-color)';
        element.style.fontWeight = '600';
    });
}

/**
 * Validate uploaded file
 */
function validateFile(file) {
    // Check file size (16MB max)
    const maxSize = 16 * 1024 * 1024; // 16MB in bytes
    if (file.size > maxSize) {
        showAlert('File size must be less than 16MB', 'error');
        return false;
    }
    
    // Check file type
    const allowedTypes = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
        'application/vnd.ms-excel' // .xls
    ];
    
    const fileName = file.name.toLowerCase();
    const isValidExtension = fileName.endsWith('.xlsx') || fileName.endsWith('.xls');
    const isValidMimeType = allowedTypes.includes(file.type);
    
    if (!isValidExtension && !isValidMimeType) {
        showAlert('Please select a valid Excel file (.xlsx or .xls)', 'error');
        return false;
    }
    
    return true;
}

/**
 * Initialize form validation
 */
function initializeFormValidation() {
    const clientNameInput = document.getElementById('client_name');
    const taxYearInput = document.getElementById('tax_year');
    
    // Client name validation
    if (clientNameInput) {
        clientNameInput.addEventListener('input', function(e) {
            const value = e.target.value.trim();
            
            // Remove invalid characters
            const sanitized = value.replace(/[<>"/\\&]/g, '');
            if (sanitized !== value) {
                e.target.value = sanitized;
                showAlert('Invalid characters removed from client name', 'warning');
            }
            
            // Validate length
            if (sanitized.length > 100) {
                e.target.value = sanitized.substring(0, 100);
                showAlert('Client name must be less than 100 characters', 'warning');
            }
        });
    }
    
    // Tax year validation
    if (taxYearInput) {
        taxYearInput.addEventListener('input', function(e) {
            const value = parseInt(e.target.value);
            const currentYear = new Date().getFullYear();
            
            if (value > currentYear + 10) {
                e.target.value = currentYear + 10;
                showAlert(`Tax year cannot be more than ${currentYear + 10}`, 'warning');
            }
            
            if (value < 2000) {
                e.target.value = 2000;
                showAlert('Tax year cannot be less than 2000', 'warning');
            }
        });
    }
}

/**
 * Initialize download handlers
 */
function initializeDownloadHandlers() {
    const downloadLinks = document.querySelectorAll('a[href*="/download/"]');
    
    downloadLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            const btn = e.target.closest('a');
            if (btn) {
                showLoadingState(btn);
                
                // Reset loading state after download
                setTimeout(function() {
                    resetLoadingState(btn);
                }, 3000);
            }
        });
    });
}

/**
 * Show loading state on button
 */
function showLoadingState(button) {
    if (!button) return;
    
    button.disabled = true;
    button.classList.add('loading');
    
    // Store original text
    if (!button.hasAttribute('data-original-text')) {
        button.setAttribute('data-original-text', button.innerHTML);
    }
    
    // Update button text
    const icon = button.querySelector('i');
    if (icon) {
        icon.className = 'fas fa-spinner fa-spin me-2';
    }
    
    const textNode = Array.from(button.childNodes).find(node => 
        node.nodeType === Node.TEXT_NODE && node.textContent.trim()
    );
    
    if (textNode) {
        textNode.textContent = ' Processing...';
    } else {
        const span = document.createElement('span');
        span.textContent = 'Processing...';
        button.appendChild(span);
    }
}

/**
 * Reset loading state on button
 */
function resetLoadingState(button) {
    if (!button) return;
    
    button.disabled = false;
    button.classList.remove('loading');
    
    // Restore original text
    const originalText = button.getAttribute('data-original-text');
    if (originalText) {
        button.innerHTML = originalText;
        button.removeAttribute('data-original-text');
    }
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    // Remove existing alerts
    const existingAlerts = document.querySelectorAll('.alert.custom-alert');
    existingAlerts.forEach(alert => alert.remove());
    
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show custom-alert`;
    alertDiv.setAttribute('role', 'alert');
    
    const icon = type === 'error' ? 'exclamation-triangle' : 
                 type === 'warning' ? 'exclamation-triangle' : 
                 type === 'success' ? 'check-circle' : 'info-circle';
    
    alertDiv.innerHTML = `
        <i class="fas fa-${icon} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert at top of container
    const container = document.querySelector('.container-fluid');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        // Auto-dismiss after 5 seconds
        setTimeout(function() {
            const closeBtn = alertDiv.querySelector('.btn-close');
            if (closeBtn) {
                closeBtn.click();
            }
        }, 5000);
    }
}

/**
 * Format file size for display
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Utility function to debounce input events
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
 * Smooth scroll utility
 */
function smoothScrollTo(element) {
    if (element) {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }
}

// Export functions for potential external use
window.CoverLetterGenerator = {
    showAlert,
    validateFile,
    formatFileSize,
    debounce,
    smoothScrollTo,
    showLoadingState,
    resetLoadingState
};

// Theme management (if needed in future)
document.addEventListener('DOMContentLoaded', function () {
    // Restore theme from localStorage
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        document.documentElement.setAttribute('data-bs-theme', savedTheme);
    }

    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function () {
            const currentTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            document.documentElement.setAttribute('data-bs-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }
});

console.log('✅ Cover Letter Generator - Professional Theme Loaded (Harshwal Purple)');