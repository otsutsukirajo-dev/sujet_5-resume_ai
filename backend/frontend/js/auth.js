const AuthService = {
    async login(email, password) {
        try {
            const data = await ApiService.post('/login', { email, password }, AUTH_BASE_URL);
            localStorage.setItem('jwt_token', data.access_token);
            localStorage.setItem('refresh_token', data.refresh_token);
            localStorage.setItem('user_email', data.user.email);
            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    },

    async register(email, password) {
        try {
            await ApiService.post('/register', { email, password }, AUTH_BASE_URL);
            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    },

    async logout() {
        try {
            await ApiService.post('/logout', {}, AUTH_BASE_URL);
        } catch (e) {
            // même si ça échoue, on déconnecte quand même localement
        }
        localStorage.clear();
        window.location.href = 'login.html';
    },

    isAuthenticated() {
        return localStorage.getItem('jwt_token') !== null;
    },

    getUser() {
        return localStorage.getItem('user_email') || '';
    }
};