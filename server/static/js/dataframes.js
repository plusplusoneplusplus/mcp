/**
 * DataFrame Web Interface JavaScript API Client
 * Provides centralized API calls, error handling, and utility functions
 */

class DataFrameAPI {
    constructor() {
        this.baseUrl = '/api/dataframes';
        this.loadingStates = new Set();
        this.progressCallbacks = new Map();
    }

    /**
     * Generic API request handler with error handling and loading states
     */
    async request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`;
        const requestId = `${options.method || 'GET'}_${endpoint}`;

        this.setLoading(requestId, true);

        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error?.message || data.error || 'Unknown API error');
            }

            return data;
        } catch (error) {
            this.handleError(error, endpoint);
            throw error;
        } finally {
            this.setLoading(requestId, false);
        }
    }

    /**
     * Loading state management
     */
    setLoading(requestId, isLoading) {
        if (isLoading) {
            this.loadingStates.add(requestId);
        } else {
            this.loadingStates.delete(requestId);
        }

        // Emit loading state change event
        document.dispatchEvent(new CustomEvent('dataframe-loading-change', {
            detail: {
                requestId,
                isLoading,
                hasActiveRequests: this.loadingStates.size > 0
            }
        }));
    }

    /**
     * Error handling with user feedback
     */
    handleError(error, context = '') {
        console.error(`DataFrame API Error${context ? ` (${context})` : ''}:`, error);

        // Emit error event for UI handling
        document.dispatchEvent(new CustomEvent('dataframe-error', {
            detail: { error, context }
        }));
    }

    /**
     * Get all DataFrames with optional filtering
     */
    async getDataFrames(filters = {}) {
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== null && value !== undefined && value !== '') {
                params.append(key, value);
            }
        });

        const queryString = params.toString();
        const endpoint = queryString ? `?${queryString}` : '';

        return await this.request(endpoint);
    }

    /**
     * Get specific DataFrame metadata
     */
    async getDataFrame(dfId) {
        return await this.request(`/${dfId}`);
    }

    /**
     * Get DataFrame data with pagination and filtering
     */
    async getDataFrameData(dfId, options = {}) {
        const params = new URLSearchParams({
            page: options.page || 1,
            page_size: options.pageSize || 50,
            ...options.filters || {}
        });

        return await this.request(`/${dfId}/data?${params}`);
    }

    /**
     * Get DataFrame summary statistics
     */
    async getDataFrameSummary(dfId) {
        return await this.request(`/${dfId}/summary`);
    }

    /**
     * Execute pandas expression on DataFrame
     */
    async executeExpression(dfId, expression, options = {}) {
        return await this.request(`/${dfId}/execute`, {
            method: 'POST',
            body: JSON.stringify({
                pandas_expression: expression,
                return_type: options.returnType || 'auto',
                timeout: options.timeout || 30
            })
        });
    }

    /**
     * Upload file and create DataFrame with enhanced progress tracking and cancellation
     */
    async uploadFile(file, options = {}) {
        const formData = new FormData();
        formData.append('file', file);

        // Add optional parameters
        if (options.format) formData.append('format', options.format);
        if (options.displayName) formData.append('display_name', options.displayName);
        if (options.hasHeader !== undefined) formData.append('has_header', options.hasHeader);

        // Handle progress tracking
        const requestId = `upload_${file.name}_${Date.now()}`;

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            // Store xhr for potential cancellation
            this.activeUploads = this.activeUploads || new Map();
            this.activeUploads.set(requestId, xhr);

            // Progress tracking with detailed stages
            xhr.upload.addEventListener('progress', (event) => {
                if (event.lengthComputable) {
                    const progress = (event.loaded / event.total) * 100;
                    let message = 'Uploading file...';

                    if (progress < 10) {
                        message = 'Starting upload...';
                    } else if (progress < 50) {
                        message = 'Uploading file...';
                    } else if (progress < 90) {
                        message = 'Almost done...';
                    } else {
                        message = 'Processing file...';
                    }

                    this.notifyProgress(requestId, progress, message);
                }
            });

            xhr.addEventListener('load', () => {
                this.setLoading(requestId, false);
                this.activeUploads.delete(requestId);

                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const data = JSON.parse(xhr.responseText);
                        if (data.success) {
                            this.notifyProgress(requestId, 100, 'Upload completed successfully');
                            resolve(data);
                        } else {
                            reject(new Error(data.error?.message || data.error || 'Upload failed'));
                        }
                    } catch (error) {
                        reject(new Error('Invalid response format'));
                    }
                } else {
                    reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
                }
            });

            xhr.addEventListener('error', () => {
                this.setLoading(requestId, false);
                this.activeUploads.delete(requestId);
                reject(new Error('Network error during upload'));
            });

            xhr.addEventListener('abort', () => {
                this.setLoading(requestId, false);
                this.activeUploads.delete(requestId);
                reject(new Error('Upload cancelled'));
            });

            this.setLoading(requestId, true);
            this.notifyProgress(requestId, 0, 'Preparing upload...');

            xhr.open('POST', `${this.baseUrl}/upload`);
            xhr.send(formData);
        });
    }

    /**
     * Cancel active upload
     */
    cancelUpload(requestId) {
        if (this.activeUploads && this.activeUploads.has(requestId)) {
            const xhr = this.activeUploads.get(requestId);
            xhr.abort();
            this.activeUploads.delete(requestId);
            return true;
        }
        return false;
    }

    /**
     * Get active uploads
     */
    getActiveUploads() {
        return this.activeUploads ? Array.from(this.activeUploads.keys()) : [];
    }

    /**
     * Detect file format from filename
     */
    static detectFileFormat(filename) {
        const extension = filename.toLowerCase().split('.').pop();
        const formatMap = {
            'csv': 'csv',
            'json': 'json',
            'xlsx': 'excel',
            'xls': 'excel',
            'parquet': 'parquet',
            'pq': 'parquet'
        };
        return formatMap[extension] || 'auto';
    }

    /**
     * Validate file before upload
     */
    static validateFile(file, options = {}) {
        const errors = [];
        const maxSize = options.maxSize || 100 * 1024 * 1024; // 100MB default
        const allowedTypes = options.allowedTypes || [
            'text/csv',
            'application/json',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel',
            'application/octet-stream' // For parquet files
        ];

        // Check file size
        if (file.size > maxSize) {
            errors.push(`File size (${DataFrameFormatter.formatMemorySize(file.size)}) exceeds maximum allowed size (${DataFrameFormatter.formatMemorySize(maxSize)})`);
        }

        // Check file type (basic check)
        const detectedFormat = this.detectFileFormat(file.name);
        if (detectedFormat === 'auto' && !allowedTypes.includes(file.type)) {
            errors.push(`File type "${file.type}" is not supported. Please use CSV, JSON, Excel, or Parquet files.`);
        }

        return {
            isValid: errors.length === 0,
            errors,
            detectedFormat
        };
    }

    /**
     * Load DataFrame from URL with progress tracking
     */
    async loadFromUrl(url, options = {}) {
        const requestId = `load-url_${Date.now()}`;

        // Start progress tracking
        this.notifyProgress(requestId, 0, 'Initiating URL load...');

        try {
            // Simulate progress updates for URL loading
            const progressInterval = setInterval(() => {
                const currentProgress = Math.min(90, Math.random() * 80 + 10);
                this.notifyProgress(requestId, currentProgress, 'Loading data from URL...');
            }, 500);

            const result = await this.request('/load-url', {
                method: 'POST',
                body: JSON.stringify({
                    url,
                    format: options.format || 'auto',
                    display_name: options.displayName,
                    has_header: options.hasHeader !== undefined ? options.hasHeader : true
                })
            });

            clearInterval(progressInterval);
            this.notifyProgress(requestId, 100, 'Data loaded successfully');

            return result;
        } catch (error) {
            this.notifyProgress(requestId, 0, 'Load failed');
            throw error;
        }
    }

    /**
     * Delete DataFrame
     */
    async deleteDataFrame(dfId) {
        return await this.request(`/${dfId}`, {
            method: 'DELETE'
        });
    }

    /**
     * Batch delete DataFrames
     */
    async batchDelete(dfIds) {
        return await this.request('/batch-delete', {
            method: 'POST',
            body: JSON.stringify({ df_ids: dfIds })
        });
    }

    /**
     * Cleanup expired DataFrames
     */
    async cleanupExpired() {
        return await this.request('/cleanup', {
            method: 'POST'
        });
    }

    /**
     * Export DataFrame
     */
    async exportDataFrame(dfId, options = {}) {
        const requestData = {
            format: options.format || 'csv',
            include_index: options.includeIndex !== undefined ? options.includeIndex : true,
            include_header: options.includeHeader !== undefined ? options.includeHeader : true
        };

        const response = await this.request(`/${dfId}/export`, {
            method: 'POST',
            body: JSON.stringify(requestData)
        });

        // Handle file download
        if (response.file_data) {
            this.downloadFile(response.file_data, response.filename, response.content_type);
        }

        return response;
    }

    /**
     * Get storage statistics
     */
    async getStorageStats() {
        return await this.request('/stats');
    }

    /**
     * Progress notification helper
     */
    notifyProgress(requestId, progress, message = '') {
        document.dispatchEvent(new CustomEvent('dataframe-progress', {
            detail: { requestId, progress, message }
        }));
    }

    /**
     * Download file helper
     */
    downloadFile(base64Data, filename, contentType = 'application/octet-stream') {
        try {
            // Convert base64 to blob
            const byteCharacters = atob(base64Data);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: contentType });

            // Create download link
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Error downloading file:', error);
            throw new Error('Failed to download file');
        }
    }

    /**
     * Check if any requests are currently loading
     */
    isLoading() {
        return this.loadingStates.size > 0;
    }

    /**
     * Get current loading states
     */
    getLoadingStates() {
        return Array.from(this.loadingStates);
    }
}

/**
 * Data formatting utilities
 */
class DataFrameFormatter {
    /**
     * Format memory size in bytes to human readable format
     */
    static formatMemorySize(bytes) {
        if (bytes === 0) return '0 B';

        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    /**
     * Format large numbers with thousand separators
     */
    static formatNumber(num) {
        return num.toLocaleString();
    }

    /**
     * Format date to local string
     */
    static formatDate(dateString) {
        if (!dateString) return 'Never';
        return new Date(dateString).toLocaleString();
    }

    /**
     * Format DataFrame shape display
     */
    static formatShape(shape) {
        if (!Array.isArray(shape) || shape.length !== 2) return 'Unknown';
        return `${this.formatNumber(shape[0])} × ${shape[1]}`;
    }

    /**
     * Format cell value for table display
     */
    static formatCellValue(value, dtype = null) {
        if (value === null || value === undefined) {
            return { value: 'null', className: 'null-value' };
        }

        if (typeof value === 'number') {
            if (dtype && (dtype.includes('int') || dtype.includes('float'))) {
                return {
                    value: this.formatNumber(value),
                    className: 'number'
                };
            }
        }

        if (typeof value === 'string' && value.length > 50) {
            return {
                value: value.substring(0, 47) + '...',
                title: value,
                className: 'truncated'
            };
        }

        return { value: String(value), className: '' };
    }

    /**
     * Get status badge info for DataFrame
     */
    static getStatusBadge(dataframe) {
        if (dataframe.is_expired) {
            return { class: 'expired', text: 'Expired' };
        }

        if (dataframe.expires_at) {
            const expiresAt = new Date(dataframe.expires_at);
            const now = new Date();
            const hoursUntilExpiry = (expiresAt - now) / (1000 * 60 * 60);

            if (hoursUntilExpiry < 24) {
                return { class: 'warning', text: `Expires ${expiresAt.toLocaleString()}` };
            }
        }

        return { class: 'active', text: 'Active' };
    }

    /**
     * Truncate text with ellipsis
     */
    static truncateText(text, maxLength = 30) {
        if (!text || text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    }
}

/**
 * UI Helper utilities
 */
class DataFrameUI {
    /**
     * Show loading spinner in element
     */
    static showLoading(elementId, message = 'Loading...') {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    ${message}
                </div>
            `;
            element.style.display = 'block';
        }
    }

    /**
     * Hide loading spinner
     */
    static hideLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = 'none';
        }
    }

    /**
     * Show status message
     */
    static showStatus(elementId, message, isError = false) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = message;
            element.style.color = isError ? '#dc3545' : '#28a745';
            element.style.display = 'block';

            // Auto-hide success messages after 5 seconds
            if (!isError) {
                setTimeout(() => this.clearStatus(elementId), 5000);
            }
        }
    }

    /**
     * Clear status message
     */
    static clearStatus(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = '';
            element.style.display = 'none';
        }
    }

    /**
     * Show toast notification
     */
    static showToast(message, type = 'info', duration = 3000) {
        // Create toast element if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                display: flex;
                flex-direction: column;
                gap: 10px;
            `;
            document.body.appendChild(toastContainer);
        }

        // Create toast
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.style.cssText = `
            padding: 12px 16px;
            border-radius: 4px;
            color: white;
            font-size: 14px;
            max-width: 300px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            transform: translateX(100%);
            transition: transform 0.3s ease;
            background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#0077cc'};
        `;
        toast.textContent = message;

        toastContainer.appendChild(toast);

        // Animate in
        setTimeout(() => {
            toast.style.transform = 'translateX(0)';
        }, 10);

        // Auto remove
        setTimeout(() => {
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, duration);
    }

    /**
     * Create confirmation dialog
     */
    static confirm(title, message, onConfirm, onCancel = null) {
        // Create modal if it doesn't exist
        let modal = document.getElementById('dynamic-confirm-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'dynamic-confirm-modal';
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 id="dynamic-confirm-title"></h3>
                    <p id="dynamic-confirm-message"></p>
                    <div style="text-align: right; margin-top: 2em;">
                        <button class="btn btn-secondary" id="dynamic-confirm-cancel">Cancel</button>
                        <button class="btn btn-danger" id="dynamic-confirm-ok" style="margin-left: 0.5em;">Confirm</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            // Close on background click
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideModal('dynamic-confirm-modal');
                }
            });
        }

        // Set content
        document.getElementById('dynamic-confirm-title').textContent = title;
        document.getElementById('dynamic-confirm-message').textContent = message;

        // Set up event handlers
        const cancelBtn = document.getElementById('dynamic-confirm-cancel');
        const okBtn = document.getElementById('dynamic-confirm-ok');

        const cleanup = () => {
            this.hideModal('dynamic-confirm-modal');
            cancelBtn.onclick = null;
            okBtn.onclick = null;
        };

        cancelBtn.onclick = () => {
            cleanup();
            if (onCancel) onCancel();
        };

        okBtn.onclick = () => {
            cleanup();
            onConfirm();
        };

        // Show modal
        this.showModal('dynamic-confirm-modal');
    }

    /**
     * Show modal
     */
    static showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'block';
            document.body.style.overflow = 'hidden';
        }
    }

    /**
     * Hide modal
     */
    static hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }
    }

    /**
     * Create data table from array of objects
     */
    static createDataTable(data, columns, dtypes = {}, options = {}) {
        if (!data || data.length === 0) {
            return '<div class="empty-state">No data to display</div>';
        }

        const maxCellLength = options.maxCellLength || 50;
        const showIndex = options.showIndex !== false;

        let html = '<table class="data-table"><thead><tr>';

        if (showIndex) {
            html += '<th>Index</th>';
        }

        columns.forEach(col => {
            html += `<th>${col}</th>`;
        });

        html += '</tr></thead><tbody>';

        data.forEach((row, index) => {
            html += '<tr>';

            if (showIndex) {
                html += `<td class="index-cell">${index}</td>`;
            }

            columns.forEach(col => {
                const cellData = DataFrameFormatter.formatCellValue(row[col], dtypes[col]);
                const titleAttr = cellData.title ? ` title="${cellData.title}"` : '';
                html += `<td class="${cellData.className}"${titleAttr}>${cellData.value}</td>`;
            });

            html += '</tr>';
        });

        html += '</tbody></table>';
        return html;
    }

    /**
     * Update pagination controls
     */
    static updatePagination(containerId, currentPage, totalPages, onPageChange) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const prevDisabled = currentPage <= 1 ? 'disabled' : '';
        const nextDisabled = currentPage >= totalPages ? 'disabled' : '';

        container.innerHTML = `
            <button ${prevDisabled} onclick="${onPageChange}(${currentPage - 1})">← Previous</button>
            <span class="page-info">Page ${currentPage} of ${totalPages}</span>
            <button ${nextDisabled} onclick="${onPageChange}(${currentPage + 1})">Next →</button>
        `;
    }
}

// Global instance
window.dataframeAPI = new DataFrameAPI();
window.DataFrameFormatter = DataFrameFormatter;
window.DataFrameUI = DataFrameUI;

// Global event listeners for API events
document.addEventListener('dataframe-error', (event) => {
    const { error, context } = event.detail;
    DataFrameUI.showToast(`Error${context ? ` (${context})` : ''}: ${error.message}`, 'error', 5000);
});

document.addEventListener('dataframe-loading-change', (event) => {
    const { hasActiveRequests } = event.detail;

    // Update global loading indicator if it exists
    const globalLoader = document.getElementById('global-loading-indicator');
    if (globalLoader) {
        globalLoader.style.display = hasActiveRequests ? 'block' : 'none';
    }
});

document.addEventListener('dataframe-progress', (event) => {
    const { requestId, progress, message } = event.detail;

    // Update progress indicators
    const progressElements = document.querySelectorAll(`[data-progress-id="${requestId}"]`);
    progressElements.forEach(element => {
        const progressBar = element.querySelector('.progress-bar');
        const progressText = element.querySelector('.progress-text');

        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }

        if (progressText) {
            progressText.textContent = `${Math.round(progress)}% - ${message}`;
        }
    });
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DataFrameAPI, DataFrameFormatter, DataFrameUI };
}
