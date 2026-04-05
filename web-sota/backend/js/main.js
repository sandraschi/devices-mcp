/**
 * Main JavaScript for Devices MCP
 * Handles UI interactions and API calls
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initializeTooltips();

    // Initialize any interactive elements
    initializeInteractiveElements();

    // Set up event listeners
    setupEventListeners();

    // Load initial data
    loadInitialData();
});

/**
 * Initialize tooltips using Tippy.js or native title attributes
 */
function initializeTooltips() {
    // Check if Tippy is available
    if (typeof tippy === 'function') {
        tippy('[data-tippy-content]');
    } else {
        // Fallback to native title attributes
        const elements = document.querySelectorAll('[data-tippy-content]');
        elements.forEach(el => {
            el.setAttribute('title', el.getAttribute('data-tippy-content'));
        });
    }
}

/**
 * Initialize interactive elements
 */
function initializeInteractiveElements() {
    // Initialize any interactive UI components
    const dropdowns = document.querySelectorAll('.dropdown');

    dropdowns.forEach(dropdown => {
        const toggle = dropdown.querySelector('.dropdown-toggle');
        const menu = dropdown.querySelector('.dropdown-menu');

        if (toggle && menu) {
            toggle.addEventListener('click', (e) => {
                e.stopPropagation();
                menu.classList.toggle('show');
            });
        }
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', () => {
        document.querySelectorAll('.dropdown-menu').forEach(menu => {
            menu.classList.remove('show');
        });
    });
}

/**
 * Set up event listeners for the application
 */
function setupEventListeners() {
    // Sidebar toggle functionality removed - sidebar is always visible

    // Handle search functionality
    const searchButton = document.getElementById('search-button');
    const searchInput = document.getElementById('search-input');

    if (searchButton && searchInput) {
        searchButton.addEventListener('click', () => {
            performSearch(searchInput.value);
        });

        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch(searchInput.value);
            }
        });
    }

    // Handle camera grid/list view toggle
    const gridViewBtn = document.getElementById('grid-view');
    const listViewBtn = document.getElementById('list-view');
    const cameraContainer = document.getElementById('camera-container');

    if (gridViewBtn && listViewBtn && cameraContainer) {
        gridViewBtn.addEventListener('click', () => {
            cameraContainer.classList.remove('list-view');
            cameraContainer.classList.add('grid-view');
            // Save preference to localStorage
            localStorage.setItem('cameraView', 'grid');
        });

        listViewBtn.addEventListener('click', () => {
            cameraContainer.classList.remove('grid-view');
            cameraContainer.classList.add('list-view');
            // Save preference to localStorage
            localStorage.setItem('cameraView', 'list');
        });

        // Load saved view preference
        const savedView = localStorage.getItem('cameraView') || 'grid';
        if (savedView === 'list') {
            cameraContainer.classList.add('list-view');
            listViewBtn.classList.add('active');
            gridViewBtn.classList.remove('active');
        } else {
            cameraContainer.classList.add('grid-view');
            gridViewBtn.classList.add('active');
            listViewBtn.classList.remove('active');
        }
    }

    // Handle camera card actions
    document.addEventListener('click', (e) => {
        // Handle fullscreen toggle
        if (e.target.closest('.btn-fullscreen')) {
            const cameraCard = e.target.closest('.camera-card');
            if (cameraCard) {
                toggleFullscreen(cameraCard);
            }
        }

        // Handle PTZ controls
        if (e.target.closest('.btn-ptz')) {
            const cameraId = e.target.closest('.camera-card')?.dataset?.cameraId;
            if (cameraId) {
                showPTZControls(cameraId);
            }
        }
    });

    // Handle form submissions
    const forms = document.querySelectorAll('form[data-ajax]');
    forms.forEach(form => {
        form.addEventListener('submit', handleFormSubmit);
    });
}

/**
 * Load initial data for the dashboard
 */
async function loadInitialData() {
    try {
        // Load camera status
        await updateCameraStatuses();

        // Load system status
        await updateSystemStatus();

        // Load recent events
        await loadRecentEvents();

        // Set up periodic refresh
        setInterval(updateCameraStatuses, 30000); // Update every 30 seconds
        setInterval(updateSystemStatus, 60000); // Update every minute

    } catch (error) {
        console.error('Error loading initial data:', error);
        showNotification('Failed to load initial data', 'error');
    }
}

/**
 * Update camera statuses from the API
 */
async function updateCameraStatuses() {
    try {
        const response = await fetch('/api/cameras/status');
        if (!response.ok) throw new Error('Failed to fetch camera statuses');

        const data = await response.json();

        // Update UI with camera statuses
        data.cameras.forEach(camera => {
            updateCameraStatusUI(camera);
        });

        // Update camera count in the UI (only if element exists)
        const onlineCount = data.cameras.filter(c => c.isOnline).length;
        const countEl = document.querySelector('.status-card:nth-child(1) .count');
        if (countEl) {
            countEl.textContent = `${onlineCount}/${data.cameras.length}`;
        }

    } catch (error) {
        console.error('Error updating camera statuses:', error);
    }
}

/**
 * Update the UI for a single camera status
 */
function updateCameraStatusUI(camera) {
    const cameraElement = document.querySelector(`[data-camera-id="${camera.id}"]`);
    if (!cameraElement) return;

    // Update status indicator
    const statusBadge = cameraElement.querySelector('.status-badge');
    if (statusBadge) {
        statusBadge.className = `status-badge ${camera.isOnline ? 'online' : 'offline'}`;
        statusBadge.textContent = camera.isOnline ? 'Online' : 'Offline';
    }

    // Update last seen time
    const lastSeenElement = cameraElement.querySelector('.camera-last-seen');
    if (lastSeenElement && camera.lastSeen) {
        lastSeenElement.textContent = `Last seen: ${formatRelativeTime(camera.lastSeen)}`;
    }
}

/**
 * Update system status information
 */
async function updateSystemStatus() {
    try {
        const response = await fetch('/api/system/status');
        if (!response.ok) throw new Error('Failed to fetch system status');

        const data = await response.json();

        // Update system status in the UI (only if elements exist)
        const cpuEl = document.querySelector('.system-cpu .progress');
        const memEl = document.querySelector('.system-memory .progress');
        const storageEl = document.querySelector('.system-storage .progress');
        if (cpuEl) cpuEl.style.width = `${data.cpu}%`;
        if (memEl) memEl.style.width = `${data.memory}%`;
        if (storageEl) storageEl.style.width = `${data.storage}%`;

    } catch (error) {
        console.error('Error updating system status:', error);
    }
}

/**
 * Load recent events
 */
async function loadRecentEvents() {
    try {
        const response = await fetch('/api/events/recent');
        if (!response.ok) throw new Error('Failed to fetch recent events');

        const events = await response.json();

        // Update events list in the UI
        const eventsContainer = document.querySelector('.events-list');
        if (eventsContainer) {
            eventsContainer.innerHTML = events.map(event => `
                <div class="event-item">
                    <div class="event-icon">
                        <i class="${getEventIcon(event.type)}"></i>
                    </div>
                    <div class="event-details">
                        <h4>${event.title}</h4>
                        <p>${event.description}</p>
                        <span class="event-time">${formatRelativeTime(event.timestamp)}</span>
                    </div>
                    ${event.thumbnail ? `
                        <div class="event-thumbnail">
                            <img src="${event.thumbnail}" alt="Event thumbnail">
                        </div>
                    ` : ''}
                </div>
            `).join('');
        }

    } catch (error) {
        console.error('Error loading recent events:', error);
    }
}

/**
 * Handle form submissions with AJAX
 */
async function handleFormSubmit(e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);
    const submitButton = form.querySelector('button[type="submit"]');
    const originalButtonText = submitButton?.textContent;

    try {
        // Disable submit button and show loading state
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        }

        const response = await fetch(form.action || window.location.href, {
            method: form.method,
            body: form.method.toLowerCase() === 'get' ? null : formData,
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        const data = await response.json();

        if (response.ok) {
            // Handle successful form submission
            showNotification(data.message || 'Operation completed successfully', 'success');

            // If form has a success callback, call it
            if (form.dataset.success) {
                const successCallback = window[form.dataset.success];
                if (typeof successCallback === 'function') {
                    successCallback(data, form);
                }
            }

            // Reset form if needed
            if (form.dataset.resetOnSuccess !== 'false') {
                form.reset();
            }

            // Reload data if needed
            if (form.dataset.reloadOnSuccess === 'true') {
                setTimeout(() => window.location.reload(), 1000);
            }

        } else {
            // Handle form errors
            throw new Error(data.message || 'An error occurred');
        }

    } catch (error) {
        console.error('Form submission error:', error);
        showNotification(error.message || 'An error occurred', 'error');

    } finally {
        // Re-enable submit button
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.textContent = originalButtonText;
        }
    }
}

/**
 * Show a notification to the user
 */
function showNotification(message, type = 'info') {
    // Check if a notification system is available
    if (typeof toastr !== 'undefined') {
        toastr[type](message);
        return;
    }

    // Fallback to native alert
    if (type === 'error') {
        alert(`Error: ${message}`);
    } else {
        alert(message);
    }
}

/**
 * Toggle fullscreen for a camera feed
 */
function toggleFullscreen(element) {
    if (!document.fullscreenElement) {
        element.requestFullscreen().catch(err => {
            console.error(`Error attempting to enable fullscreen: ${err.message}`);
        });
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        }
    }
}

/**
 * Show PTZ controls for a camera
 */
function showPTZControls(cameraId) {
    // This would show a modal or panel with PTZ controls
    console.log(`Show PTZ controls for camera ${cameraId}`);

    // For now, just show a notification
    showNotification(`PTZ controls for camera ${cameraId} would appear here`, 'info');
}

/**
 * Format a date as a relative time string
 */
function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    let interval = Math.floor(seconds / 31536000);
    if (interval >= 1) {
        return `${interval} year${interval === 1 ? '' : 's'} ago`;
    }

    interval = Math.floor(seconds / 2592000);
    if (interval >= 1) {
        return `${interval} month${interval === 1 ? '' : 's'} ago`;
    }

    interval = Math.floor(seconds / 86400);
    if (interval >= 1) {
        return `${interval} day${interval === 1 ? '' : 's'} ago`;
    }

    interval = Math.floor(seconds / 3600);
    if (interval >= 1) {
        return `${interval} hour${interval === 1 ? '' : 's'} ago`;
    }

    interval = Math.floor(seconds / 60);
    if (interval >= 1) {
        return `${interval} minute${interval === 1 ? '' : 's'} ago`;
    }

    return 'Just now';
}

/**
 * Perform search across cameras and recordings
 */
async function performSearch(query) {
    if (!query || query.trim() === '') {
        showNotification('Please enter a search term', 'warning');
        return;
    }

    const trimmedQuery = query.trim().toLowerCase();

    try {
        // Show loading state
        const searchButton = document.getElementById('search-button');
        const originalHTML = searchButton.innerHTML;
        searchButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        searchButton.disabled = true;

        // Search cameras
        const cameraResponse = await fetch('/api/cameras');
        const cameraData = await cameraResponse.json();

        // Search recordings (if API exists)
        let recordingResults = [];
        try {
            const recordingResponse = await fetch('/api/recordings/search?q=' + encodeURIComponent(trimmedQuery));
            if (recordingResponse.ok) {
                recordingResults = await recordingResponse.json();
            }
        } catch (e) {
            // Recordings search may not be implemented yet
            console.log('Recordings search not available');
        }

        // Filter cameras by name and status
        const cameraResults = cameraData.cameras.filter(camera =>
            camera.name.toLowerCase().includes(trimmedQuery) ||
            camera.id.toLowerCase().includes(trimmedQuery) ||
            camera.status.toLowerCase().includes(trimmedQuery) ||
            (camera.type && camera.type.toLowerCase().includes(trimmedQuery))
        );

        // Display results
        displaySearchResults(cameraResults, recordingResults, trimmedQuery);

    } catch (error) {
        console.error('Search error:', error);
        showNotification('Search failed. Please try again.', 'error');
    } finally {
        // Restore search button
        const searchButton = document.getElementById('search-button');
        searchButton.innerHTML = '<i class="fas fa-search"></i>';
        searchButton.disabled = false;
    }
}

/**
 * Display search results in a modal or overlay
 */
function displaySearchResults(cameras, recordings, query) {
    const totalResults = cameras.length + recordings.length;

    if (totalResults === 0) {
        showNotification(`No results found for "${query}"`, 'info');
        return;
    }

    // Create results modal
    const modal = document.createElement('div');
    modal.className = 'search-results-modal';
    modal.innerHTML = `
        <div class="search-results-overlay" onclick="this.parentElement.remove()"></div>
        <div class="search-results-content">
            <div class="search-results-header">
                <h3>Search Results for "${query}"</h3>
                <button class="close-button" onclick="this.closest('.search-results-modal').remove()">&times;</button>
            </div>
            <div class="search-results-body">
                ${cameras.length > 0 ? `
                    <div class="results-section">
                        <h4>Cameras (${cameras.length})</h4>
                        <div class="results-list">
                            ${cameras.map(camera => `
                                <div class="result-item camera-result" onclick="window.location.href='/cameras'">
                                    <div class="result-icon">
                                        <i class="fas fa-video"></i>
                                    </div>
                                    <div class="result-details">
                                        <h5>${camera.name || camera.id}</h5>
                                        <p>Status: ${camera.status} ${camera.type ? `• Type: ${camera.type}` : ''}</p>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
                ${recordings.length > 0 ? `
                    <div class="results-section">
                        <h4>Recordings (${recordings.length})</h4>
                        <div class="results-list">
                            ${recordings.map(recording => `
                                <div class="result-item recording-result" onclick="window.location.href='/recordings'">
                                    <div class="result-icon">
                                        <i class="fas fa-film"></i>
                                    </div>
                                    <div class="result-details">
                                        <h5>${recording.name || recording.filename}</h5>
                                        <p>${recording.timestamp || recording.date}</p>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Add styles for the modal
    if (!document.getElementById('search-modal-styles')) {
        const styles = document.createElement('style');
        styles.id = 'search-modal-styles';
        styles.textContent = `
            .search-results-modal {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                z-index: 1000;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .search-results-overlay {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
            }
            .search-results-content {
                position: relative;
                background: white;
                border-radius: 8px;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
                max-width: 600px;
                max-height: 80vh;
                overflow: hidden;
                margin: 20px;
                width: 100%;
            }
            .search-results-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 20px;
                border-bottom: 1px solid #e5e7eb;
            }
            .search-results-header h3 {
                margin: 0;
                font-size: 1.25rem;
                color: #1f2937;
            }
            .close-button {
                background: none;
                border: none;
                font-size: 1.5rem;
                cursor: pointer;
                color: #6b7280;
                padding: 0;
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: background-color 0.2s;
            }
            .close-button:hover {
                background-color: #f3f4f6;
                color: #374151;
            }
            .search-results-body {
                max-height: calc(80vh - 80px);
                overflow-y: auto;
                padding: 0;
            }
            .results-section {
                padding: 20px;
                border-bottom: 1px solid #f3f4f6;
            }
            .results-section:last-child {
                border-bottom: none;
            }
            .results-section h4 {
                margin: 0 0 15px 0;
                color: #374151;
                font-size: 1rem;
            }
            .results-list {
                display: flex;
                flex-direction: column;
                gap: 10px;
            }
            .result-item {
                display: flex;
                align-items: center;
                padding: 12px;
                border-radius: 6px;
                cursor: pointer;
                transition: background-color 0.2s;
            }
            .result-item:hover {
                background-color: #f9fafb;
            }
            .result-icon {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background-color: #e5e7eb;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-right: 12px;
                color: #6b7280;
            }
            .camera-result .result-icon {
                background-color: #dbeafe;
                color: #2563eb;
            }
            .recording-result .result-icon {
                background-color: #fef3c7;
                color: #d97706;
            }
            .result-details h5 {
                margin: 0 0 4px 0;
                font-size: 0.95rem;
                color: #1f2937;
            }
            .result-details p {
                margin: 0;
                font-size: 0.8rem;
                color: #6b7280;
            }
        `;
        document.head.appendChild(styles);
    }

    showNotification(`Found ${totalResults} result${totalResults !== 1 ? 's' : ''}`, 'success');
}

/**
 * Get the appropriate icon for an event type
 */
function getEventIcon(eventType) {
    const icons = {
        'motion': 'fas fa-running',
        'recording': 'fas fa-record-vinyl',
        'alert': 'fas fa-exclamation-triangle',
        'info': 'fas fa-info-circle',
        'error': 'fas fa-exclamation-circle',
        'success': 'fas fa-check-circle',
        'warning': 'fas fa-exclamation-triangle'
    };

    return icons[eventType] || 'fas fa-info-circle';
}

// Export functions for use in other modules
window.TapoCameraMCP = {
    showNotification,
    toggleFullscreen,
    showPTZControls,
    formatRelativeTime
};
