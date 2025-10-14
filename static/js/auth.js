// static/js/auth.js
document.addEventListener('DOMContentLoaded', () => {
    // --- Elements from the original file ---
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const showRegisterLink = document.getElementById('show-register');
    const showLoginLink = document.getElementById('show-login');
    const loginContainer = document.getElementById('login-container');
    const registerContainer = document.getElementById('register-container');
    const errorMessage = document.getElementById('error-message');
    const roleSelect = document.getElementById('register-role');
    const departmentInput = document.getElementById('register-department');

    // --- NEW: JWT auto-login check ---
    const token = localStorage.getItem('token');
    if (token) {
        try {
            // Decode token payload to get the role without a server round-trip
            const payload = JSON.parse(atob(token.split('.')[1]));
            // Redirect immediately if token is valid
            if (payload && payload.role) {
                window.location.href = `/dashboard/${payload.role}`;
            }
        } catch (e) {
            console.error("Invalid token found:", e);
            localStorage.removeItem('token'); // Clean up invalid token
        }
    }

    // --- UNCHANGED: Form toggling logic ---
    showRegisterLink.addEventListener('click', (e) => {
        e.preventDefault();
        loginContainer.style.display = 'none';
        registerContainer.style.display = 'block';
        errorMessage.textContent = '';
    });

    showLoginLink.addEventListener('click', (e) => {
        e.preventDefault();
        registerContainer.style.display = 'none';
        loginContainer.style.display = 'block';
        errorMessage.textContent = '';
    });

    roleSelect.addEventListener('change', () => {
        if (roleSelect.value === 'student') {
            departmentInput.style.display = 'block';
            departmentInput.required = true;
        } else {
            departmentInput.style.display = 'none';
            departmentInput.required = false;
        }
    });

    // --- UPDATED: Login form with JWT handling ---
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;

        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ email, password }),
        });

        const data = await response.json();
        if (response.ok) {
            // Save the token to localStorage
            localStorage.setItem('token', data.token);
            // Redirect based on role
            window.location.href = `/dashboard/${data.role}`;
        } else {
            errorMessage.textContent = data.error || 'Login failed.';
        }
    });

    // --- UNCHANGED: Complete registration form logic ---
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('register-name').value;
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        const role = document.getElementById('register-role').value;
        const department = document.getElementById('register-department').value;
        
        const userData = { name, email, password, role };
        if (role === 'student') {
            userData.department = department;
        }

        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(userData),
        });

        const data = await response.json();
        if (response.ok) {
            alert('Registration successful! Please login.');
            showLoginLink.click(); // Switch back to the login form
            loginForm.reset();
            registerForm.reset();
        } else {
            errorMessage.textContent = data.error || 'Registration failed.';
        }
    });
});