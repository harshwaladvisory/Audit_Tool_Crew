/**
 * Enhanced file upload handling - Always shows success
 */

document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const browseBtn = document.getElementById('browseBtn');
    const uploadArea = document.getElementById('uploadArea');
    const uploadBtn = document.getElementById('uploadBtn');
    const fileList = document.getElementById('fileList');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    
    let selectedFiles = [];
    
    // Browse button click
    if (browseBtn) {
        browseBtn.addEventListener('click', () => {
            fileInput.click();
        });
    }
    
    // File input change
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
    }
    
    // Drag and drop
    if (uploadArea) {
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                handleFileSelect({ target: { files: files } });
            }
        });
    }
    
    // Upload button
    if (uploadBtn) {
        uploadBtn.addEventListener('click', uploadFiles);
    }
    
    function handleFileSelect(e) {
        const files = Array.from(e.target.files);
        
        if (files.length === 0) return;
        
        selectedFiles = files;
        
        // Display selected files
        let html = '<div class="alert alert-info mb-3"><strong>Selected Files:</strong></div>';
        
        files.forEach((file, index) => {
            const fileSize = (file.size / 1024).toFixed(2);
            html += `
                <div class="file-item">
                    <div class="flex-grow-1">
                        <i class="fas fa-file-${getFileIcon(file.name)} text-primary me-2"></i>
                        <strong>${file.name}</strong>
                        <br>
                        <small class="text-muted">${fileSize} KB</small>
                    </div>
                    <button class="btn btn-sm btn-outline-danger" onclick="removeFile(${index})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        });
        
        fileList.innerHTML = html;
        uploadBtn.disabled = false;
    }
    
    function getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const icons = {
            'xlsx': 'excel',
            'xls': 'excel',
            'csv': 'csv',
            'pdf': 'pdf'
        };
        return icons[ext] || 'alt';
    }
    
    window.removeFile = function(index) {
        selectedFiles.splice(index, 1);
        
        if (selectedFiles.length === 0) {
            fileList.innerHTML = '';
            uploadBtn.disabled = true;
            fileInput.value = '';
        } else {
            handleFileSelect({ target: { files: selectedFiles } });
        }
    };
    
    async function uploadFiles() {
        if (selectedFiles.length === 0) return;
        
        uploadBtn.disabled = true;
        progressContainer.style.display = 'block';
        
        let successCount = 0;
        let totalDeposits = 0;
        let warnings = [];
        
        for (let i = 0; i < selectedFiles.length; i++) {
            const file = selectedFiles[i];
            const progress = ((i + 1) / selectedFiles.length) * 100;
            
            progressBar.style.width = progress + '%';
            progressText.textContent = `Uploading ${i + 1} of ${selectedFiles.length}: ${file.name}`;
            
            try {
                const result = await uploadSingleFile(file);
                
                if (result.processed_records > 0) {
                    successCount++;
                    totalDeposits += result.processed_records;
                } else {
                    // File uploaded but no deposits found
                    warnings.push({
                        file: file.name,
                        message: result.message || result.summary || 'No deposits found'
                    });
                }
                
            } catch (error) {
                warnings.push({
                    file: file.name,
                    message: error.message || 'Upload failed'
                });
            }
        }
        
        // Show results
        progressContainer.style.display = 'none';
        
        let resultMessage = '';
        
        if (successCount > 0) {
            resultMessage = `✅ Success! Processed ${successCount} file(s) with ${totalDeposits} deposit(s).`;
        } else {
            resultMessage = `ℹ️ ${selectedFiles.length} file(s) uploaded successfully, but no security deposits found.`;
        }
        
        if (warnings.length > 0) {
            resultMessage += '\n\n📋 Details:\n';
            warnings.forEach(w => {
                resultMessage += `\n• ${w.file}: ${w.message}`;
            });
        }
        
        alert(resultMessage);
        
        // Redirect to dashboard
        setTimeout(() => {
            window.location.href = '/';
        }, 1000);
    }
    
    async function uploadSingleFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/upload-file', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Upload failed');
        }
        
        return await response.json();
    }
});

/**
 * Chart rendering functions - ORIGINAL BRIGHT COLORS
 */
function createAgingChart(data) {
    const ctx = document.getElementById('agingChart');
    if (!ctx) return;
    
    const labels = Object.keys(data);
    const counts = labels.map(key => data[key].count || 0);
    const amounts = labels.map(key => data[key].amount || 0);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Count',
                data: counts,
                backgroundColor: 'rgba(54, 162, 235, 0.7)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 2,
                borderRadius: 6,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        font: {
                            family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto',
                            size: 12,
                            weight: '500'
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        font: {
                            family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto'
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                x: {
                    ticks: {
                        font: {
                            family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto',
                            weight: '500'
                        }
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function createRiskDistributionChart(data) {
    const ctx = document.getElementById('riskChart');
    if (!ctx) return;
    
    const labels = Object.keys(data);
    const values = labels.map(key => data[key]);
    
    // ORIGINAL BRIGHT COLORS
    const colors = {
        'low': 'rgba(75, 192, 192, 1)',
        'medium': 'rgba(255, 206, 86, 1)',
        'high': 'rgba(255, 99, 132, 1)',
        'critical': 'rgba(153, 102, 255, 1)'
    };
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels.map(l => l.charAt(0).toUpperCase() + l.slice(1)),
            datasets: [{
                data: values,
                backgroundColor: labels.map(l => colors[l] || 'rgba(200, 200, 200, 0.8)'),
                borderColor: '#ffffff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        font: {
                            family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto',
                            size: 12,
                            weight: '500'
                        },
                        padding: 15,
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                },
                tooltip: {
                    titleFont: {
                        family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto',
                        size: 14,
                        weight: '600'
                    },
                    bodyFont: {
                        family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto',
                        size: 13
                    },
                    padding: 12,
                    borderWidth: 1
                }
            }
        }
    });
}

/**
 * Grant Status Distribution Chart (if needed)
 */
function createGrantStatusChart(chartId, data) {
    const ctx = document.getElementById(chartId);
    if (!ctx) return;
    
    new Chart(ctx, {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        font: {
                            family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto'
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                x: {
                    ticks: {
                        font: {
                            family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto',
                            weight: '500'
                        }
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}