// Audit Liability Tool - JavaScript Functions

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // File upload validation
    initializeFileUpload();
    
    // Form validation
    initializeFormValidation();
    
    // Progress indicators
    initializeProgressIndicators();
});

function initializeFileUpload() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                validateFileUpload(file, input);
                updateFilePreview(file, input);
            }
        });
    });
}

function validateFileUpload(file, input) {
    const maxSize = 16 * 1024 * 1024; // 16MB
    const allowedTypes = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel'
    ];
    
    // Check file size
    if (file.size > maxSize) {
        showAlert('File size exceeds 16MB limit. Please select a smaller file.', 'error');
        input.value = '';
        return false;
    }
    
    // Check file type
    if (!allowedTypes.includes(file.type)) {
        showAlert('Please select a valid Excel file (.xlsx or .xls).', 'error');
        input.value = '';
        return false;
    }
    
    return true;
}

function updateFilePreview(file, input) {
    const container = input.closest('.file-upload-wrapper');
    let preview = container.querySelector('.file-preview');
    
    if (!preview) {
        preview = document.createElement('div');
        preview.className = 'file-preview mt-2';
        container.appendChild(preview);
    }
    
    preview.innerHTML = `
        <div class="alert alert-info mb-0">
            <i class="fas fa-file-excel me-2"></i>
            <strong>${file.name}</strong> (${formatFileSize(file.size)})
            <button type="button" class="btn btn-sm btn-outline-secondary ms-2" onclick="clearFileInput('${input.id}')">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
}

function clearFileInput(inputId) {
    const input = document.getElementById(inputId);
    const container = input.closest('.file-upload-wrapper');
    const preview = container.querySelector('.file-preview');
    
    input.value = '';
    if (preview) {
        preview.remove();
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function initializeFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(form)) {
                e.preventDefault();
                e.stopPropagation();
            }
            
            form.classList.add('was-validated');
        });
    });
}

function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            field.classList.add('is-invalid');
            
            // Add error message if not exists
            let feedback = field.parentNode.querySelector('.invalid-feedback');
            if (!feedback) {
                feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                feedback.textContent = 'This field is required.';
                field.parentNode.appendChild(feedback);
            }
        } else {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
        }
    });
    
    return isValid;
}

function initializeProgressIndicators() {
    // Update progress indicators for multi-step processes
    const progressSteps = document.querySelectorAll('.progress-step');
    
    progressSteps.forEach((step, index) => {
        step.addEventListener('click', function() {
            updateProgressStep(index);
        });
    });
}

function updateProgressStep(activeIndex) {
    const steps = document.querySelectorAll('.progress-step');
    
    steps.forEach((step, index) => {
        if (index <= activeIndex) {
            step.classList.add('active');
        } else {
            step.classList.remove('active');
        }
    });
}

function showAlert(message, type = 'info') {
    const alertContainer = document.querySelector('.container');
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <i class="fas fa-${type === 'error' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert after existing alerts or at the beginning
    const existingAlerts = alertContainer.querySelectorAll('.alert');
    if (existingAlerts.length > 0) {
        existingAlerts[existingAlerts.length - 1].insertAdjacentElement('afterend', alertDiv);
    } else {
        alertContainer.insertBefore(alertDiv, alertContainer.firstChild);
    }
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Utility functions for data formatting
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    }).format(date);
}

function formatPercentage(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'percent',
        minimumFractionDigits: 1,
        maximumFractionDigits: 1
    }).format(value / 100);
}

// Chart utilities
function createRiskChart(data) {
    const ctx = document.getElementById('riskChart');
    if (!ctx) return;
    
    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['High Risk', 'Medium Risk', 'Low Risk'],
            datasets: [{
                data: [data.high, data.medium, data.low],
                backgroundColor: ['#dc3545', '#ffc107', '#17a2b8'],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                title: {
                    display: true,
                    text: 'Risk Distribution'
                }
            }
        }
    });
}

function createSamplingChart(data) {
    const ctx = document.getElementById('samplingChart');
    if (!ctx) return;
    
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Month 1', 'Month 2', 'Month 3'],
            datasets: [{
                label: 'Sampled Transactions',
                data: data,
                backgroundColor: ['#007bff', '#28a745', '#ffc107'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: 'Monthly Sampling Distribution'
                }
            }
        }
    });
}

// Export functionality
function exportTableToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const rows = table.querySelectorAll('tr');
    const csvContent = Array.from(rows).map(row => {
        const cells = row.querySelectorAll('th, td');
        return Array.from(cells).map(cell => {
            return '"' + cell.textContent.replace(/"/g, '""') + '"';
        }).join(',');
    }).join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// Session storage for form data persistence
function saveFormData(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    
    sessionStorage.setItem(formId + '_data', JSON.stringify(data));
}

function loadFormData(formId) {
    const savedData = sessionStorage.getItem(formId + '_data');
    if (!savedData) return;
    
    const data = JSON.parse(savedData);
    const form = document.getElementById(formId);
    if (!form) return;
    
    Object.keys(data).forEach(key => {
        const field = form.querySelector(`[name="${key}"]`);
        if (field) {
            field.value = data[key];
        }
    });
}

// Initialize auto-save for forms
function initializeAutoSave() {
    const forms = document.querySelectorAll('form[data-autosave]');
    
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input, select, textarea');
        
        inputs.forEach(input => {
            input.addEventListener('change', () => {
                saveFormData(form.id);
            });
        });
        
        // Load saved data on page load
        loadFormData(form.id);
    });
}

// Loading state management
function setLoadingState(element, loading = true) {
    if (loading) {
        element.disabled = true;
        element.dataset.originalText = element.innerHTML;
        element.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
    } else {
        element.disabled = false;
        element.innerHTML = element.dataset.originalText;
    }
}

// Error handling
window.addEventListener('error', function(e) {
    console.error('JavaScript Error:', e.error);
    showAlert('An unexpected error occurred. Please refresh the page and try again.', 'error');
});

// Confirmation dialogs
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Table sorting
function sortTable(tableId, columnIndex) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        const aText = a.cells[columnIndex].textContent.trim();
        const bText = b.cells[columnIndex].textContent.trim();
        
        // Try to parse as numbers
        const aNum = parseFloat(aText.replace(/[^0-9.-]/g, ''));
        const bNum = parseFloat(bText.replace(/[^0-9.-]/g, ''));
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return aNum - bNum;
        }
        
        return aText.localeCompare(bText);
    });
    
    rows.forEach(row => tbody.appendChild(row));
}
