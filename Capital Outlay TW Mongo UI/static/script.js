// CapEx Analyzer JavaScript - Enhanced Modern UI
// ALL ORIGINAL FUNCTIONALITY PRESERVED

document.addEventListener('DOMContentLoaded', function() {
    // PRESERVED: Initialize upload form handler
    const uploadForm = document.getElementById('uploadForm');
    const analysisForm = document.getElementById('analysisForm');
    const resultsSection = document.getElementById('resultsSection');
    
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleFileUpload);
    }
    
    if (analysisForm) {
        analysisForm.addEventListener('submit', handleAnalysis);
    }
    
    // PRESERVED: Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// PRESERVED: Original upload function
async function handleFileUpload(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const files = formData.getAll('files[]');
    
    if (files.length === 0 || files[0].name === '') {
        showAlert('Please select at least one file to upload.', 'warning');
        return;
    }
    
    const submitBtn = event.target.querySelector('button[type="submit"]');
    setButtonLoading(submitBtn, true);
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(result.message, 'success');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showAlert(result.error || 'Upload failed', 'error');
        }
    } catch (error) {
        showAlert('Upload failed: ' + error.message, 'error');
    } finally {
        setButtonLoading(submitBtn, false);
    }
}

// PRESERVED: Original analysis function
async function handleAnalysis(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const params = {
        cap_threshold: parseFloat(formData.get('cap_threshold')),
        isi_level: parseFloat(formData.get('isi_level')),
        coverage_target: parseFloat(formData.get('coverage_target')) / 100,
        materiality: parseFloat(formData.get('materiality'))
    };
    
    const submitBtn = document.getElementById('analyzeBtn');
    setButtonLoading(submitBtn, true);
    
    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(params)
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            showAlert('Analysis completed successfully!', 'success');
            displayResults(result);
        } else {
            showAlert(result.error || 'Analysis failed', 'error');
        }
    } catch (error) {
        showAlert('Analysis failed: ' + error.message, 'error');
    } finally {
        setButtonLoading(submitBtn, false);
    }
}

// ENHANCED: Modern results display (preserves all data)
function displayResults(result) {
    const resultsSection = document.getElementById('resultsSection');
    const resultsContent = document.getElementById('resultsContent');
    
    if (!resultsSection || !resultsContent) return;
    
    // Create modern results HTML
    const html = `
        <!-- Start New Processing Button -->
        <div class="d-flex justify-content-end mb-3">
            <button class="btn btn-outline-brand" onclick="startNewProcessing()">
                <i class="fas fa-plus-circle me-2"></i>
                Start New Processing
            </button>
        </div>

        <div class="row g-4 mb-4">
            <!-- KPI Metrics with Modern Cards -->
            <div class="col-md-3">
                <div class="kpi-card">
                    <h5 class="card-title">Population</h5>
                    <h2 class="text-primary">${result.metrics.population_count.toLocaleString()}</h2>
                    <small class="text-muted">Total Items</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="kpi-card">
                    <h5 class="card-title">Sample Size</h5>
                    <h2 class="text-success">${result.metrics.sample_count.toLocaleString()}</h2>
                    <small class="text-muted">Items Selected</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="kpi-card">
                    <h5 class="card-title">CapEx Value</h5>
                    <h2 class="text-info">${result.metrics.capex_value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h2>
                    <small class="text-muted">Total Amount</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="kpi-card">
                    <h5 class="card-title">Exceptions</h5>
                    <h2 class="text-${result.metrics.exceptions > 0 ? 'danger' : 'success'}">
                        ${result.metrics.exceptions}
                    </h2>
                    <small class="text-muted">Items Flagged</small>
                </div>
            </div>
        </div>

        <div class="row g-4">
            <!-- Summary Card -->
            <div class="col-md-6">
                <div class="card modern-card h-100">
                    <div class="card-header modern-card-header">
                        <h6 class="mb-0 fw-semibold">Analysis Summary</h6>
                    </div>
                    <div class="card-body">
                        <p class="mb-3">${result.summary}</p>
                        
                        <h6 class="mb-2 fw-semibold">Key Findings:</h6>
                        <ul class="mb-0">
                            <li>Population analyzed: <strong>${result.metrics.population_count.toLocaleString()}</strong> transactions</li>
                            <li>R&M Value: <strong>${result.metrics.rnm_value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></li>
                            <li>Items flagged for review: <strong>${result.metrics.items_flagged.toLocaleString()}</strong></li>
                            ${result.metrics.largest_exception ? 
                                `<li>Largest exception: <strong>${result.metrics.largest_exception.doc_no_or_asset}</strong> 
                                (${result.metrics.largest_exception.amount.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})})</li>` : ''}
                        </ul>
                    </div>
                </div>
            </div>
            
            <!-- Files Card -->
            <div class="col-md-6">
                <div class="card modern-card h-100">
                    <div class="card-header modern-card-header">
                        <h6 class="mb-0 fw-semibold">Generated Files</h6>
                    </div>
                    <div class="card-body">
                        <div class="d-flex flex-column gap-2">
                            ${result.files_created.map(file => `
                                <div class="d-flex justify-content-between align-items-center p-3 bg-light rounded">
                                    <span class="d-flex align-items-center">
                                        <i class="fas fa-${file.endsWith('.xlsx') ? 'file-excel text-success' : 'file-text text-primary'} me-2"></i>
                                        <span class="fw-medium">${file}</span>
                                    </span>
                                    <a href="/files/${file}" class="btn btn-sm btn-outline-brand">
                                        <i class="fas fa-download"></i>
                                    </a>
                                </div>
                            `).join('')}
                        </div>
                        
                        ${result.open_requests && result.open_requests.length > 0 ? `
                            <div class="mt-4">
                                <h6 class="mb-2 fw-semibold">Open Requests:</h6>
                                <div class="alert alert-warning modern-alert mb-0">
                                    <ul class="mb-0 ps-3">
                                        ${result.open_requests.map(request => `
                                            <li><small>⚠️ ${request}</small></li>
                                        `).join('')}
                                    </ul>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    resultsContent.innerHTML = html;
    resultsSection.style.display = 'block';
    
    // Smooth scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// PRESERVED: Original delete file function
async function deleteFile(filename) {
    if (!confirm(`Are you sure you want to delete ${filename}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/delete_file/${encodeURIComponent(filename)}`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const result = await response.json();
            showAlert(result.message || `Deleted ${filename}`, 'success');
            setTimeout(() => window.location.reload(), 800);
        } else {
            const result = await response.json().catch(() => ({}));
            showAlert(result.error || 'Delete failed', 'error');
        }
    } catch (error) {
        console.error('Delete error:', error);
        showAlert('Delete failed: ' + error.message, 'error');
    }
}

// NEW: Clear all uploaded files
async function clearAllFiles() {
    if (!confirm('Are you sure you want to delete ALL uploaded files? This cannot be undone.')) {
        return;
    }
    
    const fileItems = document.querySelectorAll('.uploaded-file-item');
    if (fileItems.length === 0) {
        showAlert('No files to delete', 'warning');
        return;
    }
    
    let successCount = 0;
    let failCount = 0;
    
    for (const item of fileItems) {
        const deleteBtn = item.querySelector('button[onclick*="deleteFile"]');
        if (deleteBtn) {
            const filename = deleteBtn.getAttribute('onclick').match(/'([^']+)'/)[1];
            try {
                const response = await fetch(`/delete_file/${encodeURIComponent(filename)}`, {
                    method: 'POST'
                });
                if (response.ok) {
                    successCount++;
                } else {
                    failCount++;
                }
            } catch (error) {
                console.error(`Error deleting ${filename}:`, error);
                failCount++;
            }
        }
    }
    
    if (successCount > 0) {
        showAlert(`Successfully deleted ${successCount} file(s)${failCount > 0 ? `, ${failCount} failed` : ''}`, 'success');
        setTimeout(() => window.location.reload(), 1000);
    } else {
        showAlert('Failed to delete files', 'error');
    }
}

// NEW: Start new processing (clear results section)
function startNewProcessing() {
    if (confirm('Start a new analysis? This will clear the current results.')) {
        const resultsSection = document.getElementById('resultsSection');
        if (resultsSection) {
            resultsSection.style.display = 'none';
            document.getElementById('resultsContent').innerHTML = '';
        }
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        showAlert('Ready to start new analysis. Upload files and configure parameters.', 'success');
    }
}

// PRESERVED: Original alert function
function showAlert(message, type) {
    const existingAlerts = document.querySelectorAll('.alert.temp-alert');
    existingAlerts.forEach(alert => alert.remove());
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show temp-alert modern-alert`;
    alertDiv.innerHTML = `
        <i class="fas fa-${type === 'error' ? 'exclamation-triangle' : type === 'warning' ? 'exclamation-circle' : 'check-circle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        setTimeout(() => {
            if (alertDiv && alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// PRESERVED: Original button loading function
function setButtonLoading(button, loading) {
    if (loading) {
        button.disabled = true;
        button.classList.add('btn-loading');
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
    } else {
        button.disabled = false;
        button.classList.remove('btn-loading');
        button.innerHTML = button.dataset.originalText || button.innerHTML;
    }
}

// PRESERVED: Form validation
function validateAnalysisForm() {
    const form = document.getElementById('analysisForm');
    const inputs = form.querySelectorAll('input[type="number"]');
    
    let valid = true;
    
    inputs.forEach(input => {
        const value = parseFloat(input.value);
        if (isNaN(value) || value < 0) {
            input.classList.add('is-invalid');
            valid = false;
        } else {
            input.classList.remove('is-invalid');
        }
    });
    
    return valid;
}

// PRESERVED: Add form validation event listeners
document.addEventListener('DOMContentLoaded', function() {
    const analysisForm = document.getElementById('analysisForm');
    if (analysisForm) {
        analysisForm.addEventListener('submit', function(e) {
            if (!validateAnalysisForm()) {
                e.preventDefault();
                showAlert('Please enter valid values for all parameters.', 'warning');
            }
        });
        
        const inputs = analysisForm.querySelectorAll('input[type="number"]');
        inputs.forEach(input => {
            input.addEventListener('blur', validateAnalysisForm);
            input.addEventListener('input', function() {
                if (this.classList.contains('is-invalid')) {
                    const value = parseFloat(this.value);
                    if (!isNaN(value) && value >= 0) {
                        this.classList.remove('is-invalid');
                        this.classList.add('is-valid');
                    }
                }
            });
        });
    }
});

// PRESERVED: Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

function formatNumber(number) {
    return new Intl.NumberFormat('en-US').format(number);
}

// PRESERVED: File drag and drop
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('files');
    const uploadForm = document.getElementById('uploadForm');
    
    if (fileInput && uploadForm) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadForm.addEventListener(eventName, preventDefaults, false);
            document.body.addEventListener(eventName, preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadForm.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadForm.addEventListener(eventName, unhighlight, false);
        });
        
        uploadForm.addEventListener('drop', handleDrop, false);
    }
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight(e) {
        uploadForm.classList.add('bg-light');
    }
    
    function unhighlight(e) {
        uploadForm.classList.remove('bg-light');
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (fileInput) {
            fileInput.files = files;
        }
    }
});