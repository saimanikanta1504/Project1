/**
 * Multi-College Online Examination Management System
 * Universal Application Client Scripts
 */

document.addEventListener('DOMContentLoaded', () => {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 6000);
    });
});

/**
 * Helper to fetch with CSRF header
 */
async function fetchWithCSRF(url, options = {}) {
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';

    const headers = options.headers || {};
    if (csrfToken) {
        headers['X-CSRFToken'] = csrfToken;
    }
    if (!headers['Content-Type'] && options.body && typeof options.body === 'string') {
        headers['Content-Type'] = 'application/json';
    }

    options.headers = headers;
    return fetch(url, options);
}
