const AUTH_BASE_URL = 'http://localhost:5000/auth';
const API_BASE_URL = 'http://localhost:5000/api';

const ApiService = {
    getHeaders() {
        const token = localStorage.getItem('jwt_token');
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    },

    async handleResponse(response) {
        if (!response.ok) {
            if (response.status === 401) {
                localStorage.clear();
                if (!window.location.pathname.endsWith('login.html')) {
                    window.location.href = 'login.html';
                }
            }
            const err = await response.json().catch(() => ({}));
            throw new Error(err.error || `Erreur serveur (${response.status})`);
        }
        return response.json();
    },

    async post(endpoint, data, base = API_BASE_URL) {
        const res = await fetch(`${base}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...this.getHeaders() },
            body: JSON.stringify(data)
        });
        return this.handleResponse(res);
    },

    async get(endpoint, base = API_BASE_URL) {
        const res = await fetch(`${base}${endpoint}`, {
            method: 'GET',
            headers: this.getHeaders()
        });
        return this.handleResponse(res);
    },

    async upload(endpoint, file) {
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: formData
        });
        return this.handleResponse(res);
    }
};
