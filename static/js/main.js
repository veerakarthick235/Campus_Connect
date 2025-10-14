// static/js/main.js

// --- NEW: API Fetch Helper with JWT ---
async function fetchWithAuth(url, options = {}) {
    const token = localStorage.getItem('token');
    
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, { ...options, headers });

    if (response.status === 401) {
        // Token is invalid or expired, force logout
        logout();
        return;
    }
    return response;
}

function logout() {
    localStorage.removeItem('token');
    window.location.href = '/';
}

document.addEventListener('DOMContentLoaded', () => {
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }
    
    const userNameSpan = document.getElementById('user-name');
    if (userNameSpan) {
        fetchWithAuth('/api/current_user')
            .then(res => res.json())
            .then(user => {
                if (user && user.name) {
                    userNameSpan.textContent = `Welcome, ${user.name}`;
                }
            });
    }
});