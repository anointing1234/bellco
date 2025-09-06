// Function to handle logout
async function handleLogout() {
    try {
        // Send POST request to Django logout endpoint
        await fetch('/logout/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // Include CSRF token for Django's CSRF protection
                'X-CSRFToken': getCookie('csrftoken')
            },
            credentials: 'same-origin' // Ensure cookies are sent
        });
        // Clear session storage
        sessionStorage.clear();
        // Clear local storage (optional)
        localStorage.clear();
        // Redirect to login page
        window.location.href = '/login/'; // Adjust to your login URL
    } catch (error) {
        console.error('Logout failed:', error);
        // Fallback: redirect to login page
        window.location.href = '/login/';
    }
}

// Helper function to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Listen for visibility change events
document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'hidden') {
        handleLogout();
    }
});

// Handle window focus loss
window.addEventListener('blur', function() {
    handleLogout();
});

// Handle window close event (limited support in some browsers)
window.addEventListener('beforeunload', function() {
    handleLogout();
});