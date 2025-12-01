// ===================================
// VENDOR CLASSIFICATION - ENHANCED UI
// Modern animations & interactions
// ===================================

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    initializeCountUp();
});

/**
 * Initialize application
 */
function initializeApp() {
    console.log('🚀 Vendor Classification App initialized');
    
    // Smooth button interactions
    enhanceButtons();
    
    // Fade in cards on load
    fadeInElements();
    
    // Add file input visual feedback
    enhanceFileInput();
}

/**
 * Enhance button interactions
 */
function enhanceButtons() {
    const buttons = document.querySelectorAll('.btn, .upload-btn, .tab-btn, .btn-transfer');
    
    buttons.forEach(button => {
        // Add ripple effect on click
        button.addEventListener('click', function(e) {
            if (this.disabled) return;
            
            // Create ripple element
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                top: ${y}px;
                left: ${x}px;
                background: rgba(255, 255, 255, 0.5);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 600ms ease-out;
                pointer-events: none;
            `;
            
            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);
            
            setTimeout(() => ripple.remove(), 600);
        });
    });
    
    // Add CSS for ripple animation
    if (!document.getElementById('ripple-animation')) {
        const style = document.createElement('style');
        style.id = 'ripple-animation';
        style.textContent = `
            @keyframes ripple {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * Fade in elements on page load
 */
function fadeInElements() {
    const elements = document.querySelectorAll('.stat-card, .feature-card, .category-card');
    
    elements.forEach((element, index) => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            element.style.transition = 'opacity 400ms ease, transform 400ms ease';
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }, index * 50); // Stagger animation
    });
}

/**
 * Count-up animation for statistics
 */
function initializeCountUp() {
    const statNumbers = document.querySelectorAll('.stat-number');
    
    statNumbers.forEach(stat => {
        const text = stat.textContent.trim();
        
        // Check if it's a number (with or without currency/commas)
        const match = text.match(/[\d,]+/);
        if (match) {
            const numberStr = match[0].replace(/,/g, '');
            const targetNumber = parseInt(numberStr);
            
            if (!isNaN(targetNumber) && targetNumber > 0) {
                // Animate count-up
                animateCountUp(stat, targetNumber, text);
            }
        }
    });
}

/**
 * Animate count-up effect
 */
function animateCountUp(element, target, originalFormat) {
    const duration = 1500; // 1.5 seconds
    const steps = 60;
    const stepDuration = duration / steps;
    const increment = target / steps;
    let current = 0;
    
    const timer = setInterval(() => {
        current += increment;
        
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        
        // Format number with commas
        const formatted = Math.floor(current).toLocaleString();
        
        // Preserve original format (currency symbol, etc.)
        if (originalFormat.startsWith('$')) {
            element.textContent = '$' + formatted;
        } else if (originalFormat.includes('M')) {
            element.textContent = formatted + 'M';
        } else {
            element.textContent = formatted;
        }
    }, stepDuration);
}

/**
 * Enhance file input with visual feedback
 */
function enhanceFileInput() {
    const fileInput = document.getElementById('file');
    const fileLabel = document.querySelector('.file-label');
    const fileText = document.querySelector('.file-text');
    const fileName = document.querySelector('.file-name');
    
    if (!fileInput) return;
    
    fileInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            const file = this.files[0];
            const fileSize = (file.size / 1024 / 1024).toFixed(2); // MB
            
            fileText.textContent = '✓ File Selected';
            fileName.textContent = `${file.name} (${fileSize} MB)`;
            fileName.style.display = 'block';
            
            // Add success styling
            if (fileLabel) {
                fileLabel.style.borderColor = '#10B981';
                fileLabel.style.background = 'linear-gradient(135deg, #D1FAE5 0%, #ECFDF5 100%)';
            }
        } else {
            fileText.textContent = 'Choose File';
            fileName.textContent = 'No file selected';
            fileName.style.display = 'none';
            
            // Reset styling
            if (fileLabel) {
                fileLabel.style.borderColor = '';
                fileLabel.style.background = '';
            }
        }
    });
    
    // Drag and drop enhancement
    if (fileLabel) {
        ['dragenter', 'dragover'].forEach(eventName => {
            fileLabel.addEventListener(eventName, (e) => {
                e.preventDefault();
                fileLabel.style.borderColor = '#3A2B6F';
                fileLabel.style.background = 'linear-gradient(135deg, #ECE8FA 0%, #F1EEFA 100%)';
                fileLabel.style.transform = 'scale(1.02)';
            });
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            fileLabel.addEventListener(eventName, (e) => {
                e.preventDefault();
                fileLabel.style.borderColor = '';
                fileLabel.style.background = '';
                fileLabel.style.transform = '';
            });
        });
        
        fileLabel.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                // Trigger change event
                fileInput.dispatchEvent(new Event('change'));
            }
        });
    }
}

/**
 * Show category tab
 */
function showCategory(categoryName, buttonElement) {
    // Hide all category content
    const allCategories = document.querySelectorAll('.category-content');
    allCategories.forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all tabs
    const allTabs = document.querySelectorAll('.tab-btn');
    allTabs.forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected category with fade-in animation
    const selectedCategory = document.getElementById(`category-${categoryName}`);
    if (selectedCategory) {
        selectedCategory.classList.add('active');
    }
    
    // Activate clicked tab
    if (buttonElement) {
        const actualButton = buttonElement.closest('.tab-btn') || buttonElement;
        if (actualButton && actualButton.classList.contains('tab-btn')) {
            actualButton.classList.add('active');
        }
    }
    
    // Re-initialize editable cells for newly shown table
    setTimeout(() => {
        initializeEditableCells();
    }, 100);
}

/**
 * Initialize editable table cells
 */
function initializeEditableCells() {
    let editingCell = null;
    
    const editableCells = document.querySelectorAll('.editable');
    editableCells.forEach(cell => {
        // Remove old event listeners by cloning
        const newCell = cell.cloneNode(true);
        cell.parentNode.replaceChild(newCell, cell);
    });
    
    // Re-attach event listeners
    document.querySelectorAll('.editable').forEach(cell => {
        cell.addEventListener('click', function() {
            if (editingCell === this) return;
            
            if (editingCell) {
                saveEdit(editingCell);
            }
            
            startEdit(this);
            editingCell = this;
        });
    });
    
    // Save on Enter, cancel on Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && editingCell) {
            saveEdit(editingCell);
            editingCell = null;
        }
        if (e.key === 'Escape' && editingCell) {
            cancelEdit(editingCell);
            editingCell = null;
        }
    });
    
    // Save when clicking outside
    document.addEventListener('click', function(e) {
        if (editingCell && !editingCell.contains(e.target)) {
            saveEdit(editingCell);
            editingCell = null;
        }
    });
}

/**
 * Start editing a cell
 */
function startEdit(cell) {
    const field = cell.dataset.field;
    const currentValue = getCurrentValue(cell, field);
    
    cell.classList.add('editing');
    
    if (field === 'classification') {
        createClassificationSelect(cell, currentValue);
    } else if (field === 'form') {
        createFormSelect(cell, currentValue);
    } else {
        createTextInput(cell, currentValue);
    }
}

/**
 * Get current cell value
 */
function getCurrentValue(cell, field) {
    if (field === 'classification') {
        const badge = cell.querySelector('.classification-badge');
        return badge ? badge.textContent.trim() : '';
    } else if (field === 'form') {
        const badge = cell.querySelector('.form-badge');
        return badge ? badge.textContent.trim() : '';
    } else {
        const textSpan = cell.querySelector('span');
        const text = textSpan ? textSpan.textContent.trim() : '';
        return text === 'Click to add notes' || text === '-' ? '' : text;
    }
}

/**
 * Create classification dropdown
 */
function createClassificationSelect(cell, currentValue) {
    const classifications = ['1099-Eligible', 'Non-Reportable', 'W-9 Required'];
    
    const select = document.createElement('select');
    select.className = 'edit-input';
    
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'Select...';
    select.appendChild(defaultOption);
    
    classifications.forEach(classification => {
        const option = document.createElement('option');
        option.value = classification;
        option.textContent = classification;
        if (classification === currentValue) {
            option.selected = true;
        }
        select.appendChild(option);
    });
    
    cell.innerHTML = '';
    cell.appendChild(select);
    select.focus();
}

/**
 * Create form dropdown
 */
function createFormSelect(cell, currentValue) {
    const forms = ['1099-NEC', '1099-MISC', 'Not Required', 'W-9 Needed'];
    
    const select = document.createElement('select');
    select.className = 'edit-input';
    
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'Select...';
    select.appendChild(defaultOption);
    
    forms.forEach(form => {
        const option = document.createElement('option');
        option.value = form;
        option.textContent = form;
        if (form === currentValue) {
            option.selected = true;
        }
        select.appendChild(option);
    });
    
    cell.innerHTML = '';
    cell.appendChild(select);
    select.focus();
}

/**
 * Create text input
 */
function createTextInput(cell, currentValue) {
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'edit-input';
    input.value = currentValue;
    
    cell.innerHTML = '';
    cell.appendChild(input);
    input.focus();
    input.select();
}

/**
 * Save cell edit
 */
function saveEdit(cell) {
    const field = cell.dataset.field;
    const input = cell.querySelector('.edit-input');
    const newValue = input ? input.value.trim() : '';
    const row = cell.closest('tr');
    const index = row.dataset.index;
    
    // Get global_index from vendor data
    const globalIndex = row.querySelector('[data-vendor-id]')?.closest('tr').querySelector('.vendor-name')?.textContent;
    const actualIndex = parseInt(index);
    
    // Update display
    updateCellDisplay(cell, field, newValue);
    
    // Send to server
    fetch('/update_vendor', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            index: actualIndex,
            field: field,
            value: newValue
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show brief success indicator
            cell.style.background = '#D1FAE5';
            setTimeout(() => {
                cell.style.background = '';
            }, 800);
        } else {
            console.error('Update failed:', data.error);
            alert('Failed to update vendor. Please try again.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Network error. Please check your connection.');
    });
    
    cell.classList.remove('editing');
}

/**
 * Cancel cell edit
 */
function cancelEdit(cell) {
    const field = cell.dataset.field;
    const currentValue = cell.dataset.originalValue || '';
    
    updateCellDisplay(cell, field, currentValue);
    cell.classList.remove('editing');
}

/**
 * Update cell display after edit
 */
function updateCellDisplay(cell, field, value) {
    cell.innerHTML = '';
    
    if (field === 'classification') {
        if (value) {
            const badge = document.createElement('span');
            const className = value.replace(/\s+/g, '_').replace(/-/g, '_').toLowerCase();
            badge.className = `classification-badge classification-${className}`;
            badge.textContent = value;
            cell.appendChild(badge);
        } else {
            const span = document.createElement('span');
            span.className = 'unclassified';
            span.textContent = 'Unclassified';
            cell.appendChild(span);
        }
    } else if (field === 'form') {
        if (value) {
            const badge = document.createElement('span');
            badge.className = 'form-badge';
            badge.textContent = value;
            cell.appendChild(badge);
        } else {
            const span = document.createElement('span');
            span.className = 'no-form';
            span.textContent = '-';
            cell.appendChild(span);
        }
    } else {
        const span = document.createElement('span');
        span.className = field === 'reason' ? 'reason-text' : 'notes-text';
        span.textContent = value || (field === 'notes' ? 'Click to add notes' : '-');
        cell.appendChild(span);
    }
}

/**
 * Classify all vendors with AI
 */
function classifyVendors() {
    const modal = document.getElementById('loading-modal');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const classifyBtn = document.getElementById('classify-btn');
    
    modal.style.display = 'flex';
    classifyBtn.disabled = true;
    
    // Simulate progress
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) progress = 90;
        
        progressFill.style.width = progress + '%';
        progressText.textContent = Math.round(progress) + '% complete';
    }, 500);
    
    fetch('/classify', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        clearInterval(progressInterval);
        progressFill.style.width = '100%';
        progressText.textContent = '100% complete';
        
        setTimeout(() => {
            modal.style.display = 'none';
            classifyBtn.disabled = false;
            
            if (data.success) {
                // Show success message
                showNotification('✓ Classification complete!', 'success');
                
                // Reload page to show results
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showNotification('Classification failed: ' + (data.error || 'Unknown error'), 'error');
            }
        }, 800);
    })
    .catch(error => {
        clearInterval(progressInterval);
        modal.style.display = 'none';
        classifyBtn.disabled = false;
        console.error('Error:', error);
        showNotification('Classification failed. Please try again.', 'error');
    });
}

/**
 * Transfer vendor between categories
 */
async function transferVendor(vendorIndex, newClassification) {
    if (!confirm(`Transfer this vendor to ${newClassification}?`)) {
        return;
    }
    
    try {
        const response = await fetch('/transfer_vendor', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                vendor_index: vendorIndex,
                new_classification: newClassification
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('✓ Vendor transferred successfully!', 'success');
            setTimeout(() => window.location.reload(), 800);
        } else {
            showNotification('Transfer failed: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Transfer error:', error);
        showNotification('Transfer failed. Please try again.', 'error');
    }
}

/**
 * Show notification toast
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 24px;
        right: 24px;
        background: ${type === 'success' ? '#10B981' : type === 'error' ? '#EF4444' : '#3B82F6'};
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 10px 24px rgba(21, 16, 45, 0.2);
        font-weight: 600;
        z-index: 9999;
        animation: slideInRight 300ms ease;
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 300ms ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add notification animations
if (!document.getElementById('notification-animations')) {
    const style = document.createElement('style');
    style.id = 'notification-animations';
    style.textContent = `
        @keyframes slideInRight {
            from {
                opacity: 0;
                transform: translateX(100px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        @keyframes slideOutRight {
            from {
                opacity: 1;
                transform: translateX(0);
            }
            to {
                opacity: 0;
                transform: translateX(100px);
            }
        }
    `;
    document.head.appendChild(style);
}

// Initialize editable cells on page load
if (document.querySelector('.vendors-table')) {
    initializeEditableCells();
}