/**
 * Mitch Quick - Auction Flipping Tracker
 * Main JavaScript Application
 */

// Global application object
window.MitchQuick = {
    // Configuration
    config: {
        autoRefreshInterval: 300000, // 5 minutes
        priceUpdateCooldown: 60000,  // 1 minute
        maxRetries: 3
    },

    // State management
    state: {
        lastPriceUpdate: null,
        activeFilters: {},
        selectedItems: new Set(),
        autoRefreshEnabled: true
    },

    // Initialize application
    init: function() {
        this.setupEventListeners();
        this.initializeComponents();
        this.startAutoRefresh();
        console.log('Mitch Quick application initialized');
    },

    // Setup global event listeners
    setupEventListeners: function() {
        // HTMX event handlers
        document.body.addEventListener('htmx:beforeRequest', this.handleHTMXBeforeRequest.bind(this));
        document.body.addEventListener('htmx:afterRequest', this.handleHTMXAfterRequest.bind(this));
        document.body.addEventListener('htmx:responseError', this.handleHTMXError.bind(this));

        // Global keyboard shortcuts
        document.addEventListener('keydown', this.handleKeyboardShortcuts.bind(this));

        // Page visibility API for auto-refresh
        document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));

        // Form validation
        document.addEventListener('submit', this.handleFormSubmission.bind(this));

        // Bulk selection
        this.setupBulkSelection();
    },

    // Initialize components
    initializeComponents: function() {
        this.initializeDataTables();
        this.initializeTooltips();
        this.initializePopovers();
        this.initializeDatePickers();
        this.initializeNumberFormatters();
    },

    // HTMX event handlers
    handleHTMXBeforeRequest: function(evt) {
        // Show loading indicator for longer requests
        const indicator = evt.detail.elt.querySelector('.htmx-indicator');
        if (indicator) {
            indicator.style.display = 'inline-block';
        }
    },

    handleHTMXAfterRequest: function(evt) {
        const response = evt.detail.xhr;
        const pathInfo = evt.detail.pathInfo;

        // Hide loading indicator
        const indicator = evt.detail.elt.querySelector('.htmx-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }

        // Handle specific endpoints
        if (pathInfo.requestPath.includes('update-price')) {
            this.handlePriceUpdateResponse(response);
        } else if (pathInfo.requestPath.includes('update-watchlist-prices')) {
            this.handleBulkPriceUpdateResponse(response);
        }

        // Refresh tooltips after HTMX content update
        this.initializeTooltips();
    },

    handleHTMXError: function(evt) {
        console.error('HTMX Error:', evt.detail);
        this.showNotification('An error occurred. Please try again.', 'error');
    },

    // Handle price update responses
    handlePriceUpdateResponse: function(response) {
        if (response.status === 200) {
            try {
                const data = JSON.parse(response.responseText);
                if (data.success) {
                    this.showNotification(`Price updated: $${data.suggested_price}`, 'success');
                    this.state.lastPriceUpdate = Date.now();
                } else {
                    this.showNotification('Could not fetch price suggestion', 'warning');
                }
            } catch (e) {
                this.showNotification('Error processing price update', 'error');
            }
        }
    },

    handleBulkPriceUpdateResponse: function(response) {
        if (response.status === 200) {
            try {
                const data = JSON.parse(response.responseText);
                if (data.success) {
                    this.showNotification(`Updated ${data.updated_count} items`, 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    this.showNotification('Error: ' + data.error, 'error');
                }
            } catch (e) {
                this.showNotification('Error processing bulk update', 'error');
            }
        }
    },

    // Keyboard shortcuts
    handleKeyboardShortcuts: function(evt) {
        // Ctrl/Cmd + shortcuts
        if (evt.ctrlKey || evt.metaKey) {
            switch (evt.key) {
                case 'k': // Quick search
                    evt.preventDefault();
                    this.focusSearch();
                    break;
                case 'n': // New item
                    evt.preventDefault();
                    this.redirectTo('/items/create');
                    break;
                case 'r': // Refresh
                    evt.preventDefault();
                    location.reload();
                    break;
            }
        }

        // Global shortcuts
        switch (evt.key) {
            case 'Escape':
                this.closeModals();
                break;
        }
    },

    // Visibility change handler for auto-refresh
    handleVisibilityChange: function() {
        if (document.hidden) {
            this.state.autoRefreshEnabled = false;
        } else {
            this.state.autoRefreshEnabled = true;
            this.refreshDashboardData();
        }
    },

    // Form submission handler
    handleFormSubmission: function(evt) {
        const form = evt.target;
        if (form.tagName !== 'FORM') return;

        // Validate required fields
        const requiredFields = form.querySelectorAll('[required]');
        for (let field of requiredFields) {
            if (!field.value.trim()) {
                evt.preventDefault();
                field.focus();
                this.showNotification(`${field.labels[0]?.textContent || 'This field'} is required`, 'error');
                return;
            }
        }

        // Validate email fields
        const emailFields = form.querySelectorAll('input[type="email"]');
        for (let field of emailFields) {
            if (field.value && !this.validateEmail(field.value)) {
                evt.preventDefault();
                field.focus();
                this.showNotification('Please enter a valid email address', 'error');
                return;
            }
        }

        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
            
            // Reset button after delay
            setTimeout(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }, 5000);
        }
    },

    // Bulk selection functionality
    setupBulkSelection: function() {
        // Master checkbox
        const masterCheckbox = document.getElementById('selectAllCheckbox');
        if (masterCheckbox) {
            masterCheckbox.addEventListener('change', (evt) => {
                const checkboxes = document.querySelectorAll('.item-checkbox');
                checkboxes.forEach(cb => {
                    cb.checked = evt.target.checked;
                    this.toggleItemSelection(cb.value, cb.checked);
                });
                this.updateBulkActionUI();
            });
        }

        // Individual checkboxes
        document.querySelectorAll('.item-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (evt) => {
                this.toggleItemSelection(evt.target.value, evt.target.checked);
                this.updateBulkActionUI();
            });
        });
    },

    toggleItemSelection: function(itemId, selected) {
        if (selected) {
            this.state.selectedItems.add(itemId);
        } else {
            this.state.selectedItems.delete(itemId);
        }
    },

    updateBulkActionUI: function() {
        const count = this.state.selectedItems.size;
        const bulkActions = document.querySelector('.bulk-actions');
        const selectedCount = document.getElementById('selectedCount');

        if (bulkActions) {
            bulkActions.style.display = count > 0 ? 'block' : 'none';
        }
        if (selectedCount) {
            selectedCount.textContent = count;
        }
    },

    // Initialize DataTables for better table handling
    initializeDataTables: function() {
        const tables = document.querySelectorAll('.data-table');
        tables.forEach(table => {
            // Add sorting and filtering capabilities
            this.enhanceTable(table);
        });
    },

    enhanceTable: function(table) {
        // Add search functionality
        const searchInput = table.parentElement.querySelector('.table-search');
        if (searchInput) {
            searchInput.addEventListener('input', (evt) => {
                this.filterTable(table, evt.target.value);
            });
        }

        // Add column sorting
        const headers = table.querySelectorAll('th[data-sortable]');
        headers.forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', () => {
                this.sortTable(table, header);
            });
        });
    },

    filterTable: function(table, searchTerm) {
        const rows = table.querySelectorAll('tbody tr');
        const term = searchTerm.toLowerCase();

        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(term) ? '' : 'none';
        });
    },

    sortTable: function(table, header) {
        const columnIndex = Array.from(header.parentElement.children).indexOf(header);
        const rows = Array.from(table.querySelectorAll('tbody tr'));
        const isAscending = header.classList.contains('sort-asc');

        rows.sort((a, b) => {
            const aVal = a.children[columnIndex]?.textContent.trim() || '';
            const bVal = b.children[columnIndex]?.textContent.trim() || '';
            
            // Try to parse as numbers
            const aNum = parseFloat(aVal.replace(/[$,]/g, ''));
            const bNum = parseFloat(bVal.replace(/[$,]/g, ''));
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return isAscending ? bNum - aNum : aNum - bNum;
            } else {
                return isAscending ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
            }
        });

        // Clear sort classes
        header.parentElement.querySelectorAll('th').forEach(th => {
            th.classList.remove('sort-asc', 'sort-desc');
        });

        // Add sort class
        header.classList.add(isAscending ? 'sort-desc' : 'sort-asc');

        // Reorder rows
        const tbody = table.querySelector('tbody');
        rows.forEach(row => tbody.appendChild(row));
    },

    // Initialize Bootstrap components
    initializeTooltips: function() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    },

    initializePopovers: function() {
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    },

    initializeDatePickers: function() {
        // Set default dates for date inputs
        const dateInputs = document.querySelectorAll('input[type="date"]');
        dateInputs.forEach(input => {
            if (!input.value && input.hasAttribute('data-default-today')) {
                input.value = new Date().toISOString().split('T')[0];
            }
        });
    },

    initializeNumberFormatters: function() {
        // Format currency inputs
        const currencyInputs = document.querySelectorAll('input[data-currency]');
        currencyInputs.forEach(input => {
            input.addEventListener('blur', (evt) => {
                const value = parseFloat(evt.target.value);
                if (!isNaN(value)) {
                    evt.target.value = value.toFixed(2);
                }
            });
        });
    },

    // Auto-refresh functionality
    startAutoRefresh: function() {
        setInterval(() => {
            if (this.state.autoRefreshEnabled && !document.hidden) {
                this.refreshDashboardData();
            }
        }, this.config.autoRefreshInterval);
    },

    refreshDashboardData: function() {
        // Only refresh on dashboard page
        if (window.location.pathname === '/' || window.location.pathname === '/dashboard') {
            fetch('/dashboard/kpis')
                .then(response => response.json())
                .then(data => this.updateDashboardKPIs(data))
                .catch(error => console.error('Error refreshing dashboard:', error));
        }
    },

    updateDashboardKPIs: function(data) {
        // Update KPI displays
        const kpiElements = {
            'totalInvested': data.total_invested,
            'totalNetProfit': data.total_net_profit,
            'averageROI': data.average_roi,
            'itemsSold': data.items_sold
        };

        Object.entries(kpiElements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                if (typeof value === 'number') {
                    element.textContent = id.includes('ROI') ? value.toFixed(1) + '%' : 
                                         id.includes('total') ? '$' + value.toFixed(0) : value;
                }
            }
        });
    },

    // Utility functions
    validateEmail: function(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    },

    formatCurrency: function(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    },

    formatDate: function(date) {
        return new Intl.DateTimeFormat('en-US').format(new Date(date));
    },

    focusSearch: function() {
        const searchInput = document.querySelector('input[type="search"], input[placeholder*="search"]');
        if (searchInput) {
            searchInput.focus();
        }
    },

    redirectTo: function(url) {
        window.location.href = url;
    },

    closeModals: function() {
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) modalInstance.hide();
        });
    },

    showNotification: function(message, type = 'info') {
        // Create toast notification
        const toastContainer = this.getOrCreateToastContainer();
        const toast = this.createToast(message, type);
        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove toast after it's hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    },

    getOrCreateToastContainer: function() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        return container;
    },

    createToast: function(message, type) {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${this.getBootstrapColorClass(type)} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-${this.getIconClass(type)} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        return toast;
    },

    getBootstrapColorClass: function(type) {
        const colorMap = {
            'success': 'success',
            'error': 'danger',
            'warning': 'warning',
            'info': 'info'
        };
        return colorMap[type] || 'info';
    },

    getIconClass: function(type) {
        const iconMap = {
            'success': 'check-circle',
            'error': 'exclamation-triangle',
            'warning': 'exclamation-circle',
            'info': 'info-circle'
        };
        return iconMap[type] || 'info-circle';
    },

    // Export functionality
    exportToCSV: function(data, filename) {
        const csv = this.convertToCSV(data);
        this.downloadCSV(csv, filename);
    },

    convertToCSV: function(data) {
        if (!data || data.length === 0) return '';
        
        const headers = Object.keys(data[0]);
        const csvContent = [
            headers.join(','),
            ...data.map(row => headers.map(header => {
                const value = row[header] || '';
                return typeof value === 'string' && value.includes(',') ? `"${value}"` : value;
            }).join(','))
        ].join('\n');
        
        return csvContent;
    },

    downloadCSV: function(csvContent, filename) {
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    },

    // Performance monitoring
    logPerformance: function(action, startTime) {
        const duration = performance.now() - startTime;
        console.log(`[Performance] ${action}: ${duration.toFixed(2)}ms`);
        
        if (duration > 1000) {
            console.warn(`[Performance Warning] ${action} took ${duration.toFixed(2)}ms`);
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    MitchQuick.init();
});

// Global utility functions for templates
window.showConfirmDialog = function(title, message, callback) {
    MitchQuick.ModalUtils?.showConfirmation(title, message, 'Confirm', 'btn-danger', callback);
};

window.showROICalculator = function() {
    MitchQuick.ModalUtils?.showROICalculator();
};

window.formatCurrency = function(amount) {
    return MitchQuick.formatCurrency(amount);
};

window.showNotification = function(message, type) {
    MitchQuick.showNotification(message, type);
};

// Service Worker registration for offline support
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then(registration => {
                console.log('SW registered: ', registration);
            })
            .catch(registrationError => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}
