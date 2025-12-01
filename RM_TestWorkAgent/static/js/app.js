// Global app object
const RMApp = {
    apiBase: '/api',
    currentRun: null,
    
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = `
            <i class="fas fa-${type === 'error' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 5000);
    },
    
    async apiCall(endpoint, options = {}) {
        try {
            const response = await fetch(`${this.apiBase}${endpoint}`, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({ error: 'Unknown error' }));
                throw new Error(error.error || `HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            this.showToast(error.message || 'An error occurred', 'error');
            throw error;
        }
    },
    
    async loadRuns(selectId = 'runSelect') {
        try {
            const response = await this.apiCall('/runs');
            const select = document.getElementById(selectId);
            
            if (!select) return;
            
            select.innerHTML = '<option value="">Select a run...</option>';
            
            if (response.success && response.runs && response.runs.length > 0) {
                response.runs.forEach(run => {
                    const option = document.createElement('option');
                    option.value = run.id;
                    option.textContent = `${run.name} (${run.status})`;
                    select.appendChild(option);
                });
            } else {
                select.innerHTML = '<option value="">No runs available</option>';
            }
        } catch (error) {
            console.error('Error loading runs:', error);
        }
    },
    
    async createRun(name) {
        try {
            const response = await this.apiCall('/runs', {
                method: 'POST',
                body: JSON.stringify({ name: name || 'New Run' })
            });
            
            if (response.success) {
                this.showToast('Run created successfully!', 'success');
                return response.run_id;
            }
        } catch (error) {
            console.error('Error creating run:', error);
            return null;
        }
    },
    
    async deleteRun(runId, runName) {
        if (!confirm(`Are you sure you want to delete "${runName}"? This action cannot be undone.`)) {
            return false;
        }
        
        try {
            const response = await this.apiCall(`/runs/${runId}`, {
                method: 'DELETE'
            });
            
            if (response.success) {
                this.showToast(response.message || 'Run deleted successfully', 'success');
                setTimeout(() => window.location.reload(), 1000);
                return true;
            }
        } catch (error) {
            console.error('Error deleting run:', error);
            return false;
        }
    },
    
    async uploadGL(runId, file) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('run_id', runId);
            
            const response = await fetch(`${this.apiBase}/upload/gl`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast(result.message || 'GL uploaded successfully!', 'success');
                return result;
            } else {
                throw new Error(result.error || 'Upload failed');
            }
        } catch (error) {
            console.error('Error uploading GL:', error);
            this.showToast(error.message || 'Upload failed', 'error');
            throw error;
        }
    },
    
    async uploadTB(runId, file) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('run_id', runId);
            
            const response = await fetch(`${this.apiBase}/upload/tb`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast(result.message || 'TB uploaded successfully!', 'success');
                return result;
            } else {
                throw new Error(result.error || 'Upload failed');
            }
        } catch (error) {
            console.error('Error uploading TB:', error);
            this.showToast(error.message || 'Upload failed', 'error');
            throw error;
        }
    },
    
    async generateSamples(runId) {
        try {
            const response = await this.apiCall(`/runs/${runId}/generate-samples`, {
                method: 'POST'
            });
            
            if (response.success) {
                this.showToast(response.message || 'Samples generated!', 'success');
                return response;
            }
        } catch (error) {
            console.error('Error generating samples:', error);
            return null;
        }
    }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('RM App initialized');
    
    if (document.getElementById('runSelect')) {
        RMApp.loadRuns();
    }
});

// Export for global access
window.RMApp = RMApp;

// Global delete function for inline onclick
function deleteRun(runId, runName) {
    RMApp.deleteRun(runId, runName);
}