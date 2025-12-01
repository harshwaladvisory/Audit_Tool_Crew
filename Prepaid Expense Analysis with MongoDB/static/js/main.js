// Modern Prepaid Expense Analyzer - Enhanced JavaScript
// Production-ready with animations and accessibility

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    initializeMobileMenu();
    initializeFileUpload();
    initializeAlerts();
    initializeFormValidation();
    initializeAnimations();
    initializeTableFeatures();
    initializeAccessibility();
}

// ============================================
// Mobile Menu
// ============================================
function initializeMobileMenu() {
    const menuToggle = document.querySelector('.mobile-menu-toggle');
    const mobileNav = document.querySelector('.mobile-nav');
    
    if (!menuToggle || !mobileNav) return;
    
    menuToggle.addEventListener('click', () => {
        mobileNav.classList.toggle('active');
        
        // Update icon
        const icon = menuToggle.querySelector('i');
        if (mobileNav.classList.contains('active')) {
            icon.classList.remove('fa-bars');
            icon.classList.add('fa-times');
        } else {
            icon.classList.remove('fa-times');
            icon.classList.add('fa-bars');
        }
    });
    
    // Close mobile menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!menuToggle.contains(e.target) && !mobileNav.contains(e.target)) {
            mobileNav.classList.remove('active');
            const icon = menuToggle.querySelector('i');
            icon.classList.remove('fa-times');
            icon.classList.add('fa-bars');
        }
    });
    
    // Close mobile menu when navigating
    mobileNav.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            mobileNav.classList.remove('active');
            const icon = menuToggle.querySelector('i');
            icon.classList.remove('fa-times');
            icon.classList.add('fa-bars');
        });
    });
}

// ============================================
// File Upload Enhancement
// ============================================
function initializeFileUpload() {
    const fileInput = document.getElementById('file');
    const dropZone = document.getElementById('dropZone');
    
    if (!fileInput || !dropZone) return;
    
    // Click to browse
    dropZone.addEventListener('click', () => fileInput.click());
    
    // Drag and drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('dragover');
        }, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('dragover');
        }, false);
    });
    
    dropZone.addEventListener('drop', handleDrop, false);
    fileInput.addEventListener('change', handleFileSelect);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            fileInput.files = files;
            handleFileSelect({ target: fileInput });
        }
    }
    
    function handleFileSelect(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        // Validate file
        const validation = validateFile(file);
        if (!validation.valid) {
            showAlert('danger', validation.message);
            e.target.value = '';
            hideFilePreview();
            return;
        }
        
        // Show preview
        showFilePreview(file);
        
        // Auto-detect file type
        autoDetectFileType(file);
    }
    
    function validateFile(file) {
        const maxSize = 16 * 1024 * 1024; // 16MB
        const allowedExtensions = ['.xlsx', '.xls', '.csv', '.pdf'];
        
        if (file.size > maxSize) {
            return {
                valid: false,
                message: 'File size exceeds 16MB limit. Please choose a smaller file.'
            };
        }
        
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        if (!allowedExtensions.includes(extension)) {
            return {
                valid: false,
                message: 'Invalid file format. Please upload Excel (.xlsx, .xls), CSV, or PDF files only.'
            };
        }
        
        return { valid: true };
    }
    
    function showFilePreview(file) {
        const preview = document.getElementById('filePreview');
        const fileInfo = document.getElementById('fileInfo');
        
        if (!preview || !fileInfo) return;
        
        const fileSize = (file.size / 1024 / 1024).toFixed(2);
        const lastModified = new Date(file.lastModified).toLocaleDateString();
        
        fileInfo.innerHTML = `
            <div class="row">
                <div class="col-md-6 mb-2">
                    <strong><i class="fas fa-file me-2"></i>Filename:</strong><br>
                    <span class="text-muted">${escapeHtml(file.name)}</span>
                </div>
                <div class="col-md-6 mb-2">
                    <strong><i class="fas fa-weight me-2"></i>Size:</strong><br>
                    <span class="text-muted">${fileSize} MB</span>
                </div>
                <div class="col-md-6">
                    <strong><i class="fas fa-file-code me-2"></i>Type:</strong><br>
                    <span class="text-muted">${getFileTypeDisplay(file.type, file.name)}</span>
                </div>
                <div class="col-md-6">
                    <strong><i class="fas fa-calendar me-2"></i>Modified:</strong><br>
                    <span class="text-muted">${lastModified}</span>
                </div>
            </div>
        `;
        
        preview.style.display = 'block';
        
        // Animate in
        preview.style.opacity = '0';
        preview.style.transform = 'translateY(-10px)';
        setTimeout(() => {
            preview.style.transition = 'all 200ms ease';
            preview.style.opacity = '1';
            preview.style.transform = 'translateY(0)';
        }, 10);
    }
    
    function hideFilePreview() {
        const preview = document.getElementById('filePreview');
        if (preview) {
            preview.style.display = 'none';
        }
    }
    
    function autoDetectFileType(file) {
        const fileName = file.name.toLowerCase();
        const fileTypeSelect = document.getElementById('file_type');
        
        if (!fileTypeSelect || fileTypeSelect.value) return;
        
        let detectedType = '';
        
        if (fileName.includes('gl') || fileName.includes('general') || fileName.includes('ledger')) {
            detectedType = 'GL';
        } else if (fileName.includes('tb') || fileName.includes('trial') || fileName.includes('balance')) {
            detectedType = 'TB';
        } else if (fileName.includes('invoice') || fileName.includes('bill')) {
            detectedType = 'INVOICE';
        }
        
        if (detectedType) {
            fileTypeSelect.value = detectedType;
            showAlert('info', `File type auto-detected as: ${getFileTypeLabel(detectedType)}`);
        }
    }
    
    function getFileTypeDisplay(mimeType, fileName) {
        if (fileName.endsWith('.xlsx')) return 'Excel (XLSX)';
        if (fileName.endsWith('.xls')) return 'Excel (XLS)';
        if (fileName.endsWith('.csv')) return 'CSV';
        if (fileName.endsWith('.pdf')) return 'PDF Document';
        return 'Unknown';
    }
    
    function getFileTypeLabel(type) {
        const labels = {
            'GL': 'General Ledger',
            'TB': 'Trial Balance',
            'INVOICE': 'Invoices'
        };
        return labels[type] || type;
    }
    
    // Form submission handling
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function() {
            const uploadProgress = document.getElementById('uploadProgress');
            const uploadBtn = document.getElementById('uploadBtn');
            
            if (uploadProgress) uploadProgress.style.display = 'block';
            if (uploadBtn) {
                uploadBtn.disabled = true;
                uploadBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
            }
        });
    }
}

// ============================================
// Alert System
// ============================================
function initializeAlerts() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert && alert.parentElement) {
                bsAlert.close();
            }
        }, 5000);
    });
}

function showAlert(type, message, duration = 5000) {
    const container = document.querySelector('.container');
    if (!container) return;
    
    const alertClass = type === 'danger' ? 'danger' : 
                      type === 'success' ? 'success' : 
                      type === 'warning' ? 'warning' : 'info';
    
    const iconClass = type === 'danger' ? 'times-circle' : 
                     type === 'success' ? 'check-circle' : 
                     type === 'warning' ? 'exclamation-triangle' : 'info-circle';
    
    const alertElement = document.createElement('div');
    alertElement.className = `alert alert-${alertClass} alert-dismissible fade show`;
    alertElement.setAttribute('role', 'alert');
    alertElement.innerHTML = `
        <i class="fas fa-${iconClass} me-2"></i>
        ${escapeHtml(message)}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    container.insertBefore(alertElement, container.firstChild);
    
    if (duration > 0) {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alertElement);
            if (bsAlert && alertElement.parentElement) {
                bsAlert.close();
            }
        }, duration);
    }
}

// ============================================
// Form Validation
// ============================================
function initializeFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                const firstInvalid = form.querySelector(':invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                    showAlert('danger', 'Please complete all required fields.');
                }
            }
            
            form.classList.add('was-validated');
        });
        
        // Real-time validation for select fields
        const selects = form.querySelectorAll('select[required]');
        selects.forEach(select => {
            select.addEventListener('change', function() {
                if (this.value) {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                } else {
                    this.classList.remove('is-valid');
                    this.classList.add('is-invalid');
                }
            });
        });
    });
}

// ============================================
// Animations
// ============================================
function initializeAnimations() {
    // Animate stat cards on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '0';
                entry.target.style.transform = 'translateY(20px)';
                
                setTimeout(() => {
                    entry.target.style.transition = 'all 400ms ease';
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }, 100);
                
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observe stat cards
    document.querySelectorAll('.stat-card').forEach(card => {
        observer.observe(card);
    });
    
    // Animate numbers (count up effect)
    animateNumbers();
}

function animateNumbers() {
    const statValues = document.querySelectorAll('.stat-card-value');
    
    statValues.forEach(element => {
        const target = parseInt(element.textContent);
        if (isNaN(target)) return;
        
        const duration = 1000; // 1 second
        const steps = 30;
        const increment = target / steps;
        let current = 0;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                element.textContent = target;
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current);
            }
        }, duration / steps);
    });
}

// ============================================
// Table Features
// ============================================
function initializeTableFeatures() {
    // Add sorting to tables
    const tables = document.querySelectorAll('table.table-hover');
    
    tables.forEach(table => {
        const headers = table.querySelectorAll('th');
        headers.forEach((header, index) => {
            if (header.textContent.trim() && !header.classList.contains('no-sort')) {
                header.style.cursor = 'pointer';
                header.addEventListener('click', () => sortTable(table, index));
            }
        });
    });
}

function sortTable(table, columnIndex) {
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const header = table.querySelectorAll('th')[columnIndex];
    
    // Determine sort direction
    const isAsc = !header.classList.contains('sort-asc');
    
    // Reset all headers
    table.querySelectorAll('th').forEach(h => {
        h.classList.remove('sort-asc', 'sort-desc');
    });
    
    header.classList.add(isAsc ? 'sort-asc' : 'sort-desc');
    
    // Sort rows
    rows.sort((a, b) => {
        const aVal = getCellValue(a.cells[columnIndex]);
        const bVal = getCellValue(b.cells[columnIndex]);
        
        let comparison = 0;
        if (isNumeric(aVal) && isNumeric(bVal)) {
            comparison = parseFloat(aVal) - parseFloat(bVal);
        } else {
            comparison = aVal.localeCompare(bVal);
        }
        
        return isAsc ? comparison : -comparison;
    });
    
    // Re-append sorted rows
    rows.forEach(row => tbody.appendChild(row));
}

function getCellValue(cell) {
    if (!cell) return '';
    return (cell.textContent || cell.innerText || '').replace(/[$,\s]/g, '').trim();
}

function isNumeric(value) {
    return !isNaN(parseFloat(value)) && isFinite(value);
}

// ============================================
// Accessibility
// ============================================
function initializeAccessibility() {
    // Add ARIA labels to interactive elements
    document.querySelectorAll('.btn').forEach(btn => {
        if (!btn.hasAttribute('aria-label') && btn.title) {
            btn.setAttribute('aria-label', btn.title);
        }
    });
    
    // Keyboard navigation for cards
    document.querySelectorAll('.stat-card, .card').forEach(card => {
        const link = card.querySelector('a');
        if (link) {
            card.setAttribute('tabindex', '0');
            card.setAttribute('role', 'link');
            card.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    link.click();
                }
            });
        }
    });
}

// ============================================
// Utility Functions
// ============================================
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// ============================================
// Network Status
// ============================================
window.addEventListener('online', () => {
    showAlert('success', 'Connection restored', 3000);
});

window.addEventListener('offline', () => {
    showAlert('warning', 'Connection lost. Some features may not work.', 0);
});

// ============================================
// Page Visibility
// ============================================
document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
        // Page is visible - could refresh data if needed
        console.log('Page visible');
    }
});

// Export for external use
window.PrepaidExpenseAnalyzer = {
    showAlert,
    formatCurrency,
    sortTable
};