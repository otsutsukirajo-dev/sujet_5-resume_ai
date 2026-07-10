document.addEventListener('DOMContentLoaded', () => {
    if (!AuthService.isAuthenticated()) {
        window.location.href = 'login.html';
        return;
    }

    const userEmail = AuthService.getUser();

    const emailEl = document.getElementById('user-email');
    if (emailEl) emailEl.textContent = userEmail;

    const avatar = document.getElementById('user-avatar');
    if (avatar && userEmail) {
        const initials = userEmail
            .split('@')[0]
            .split(/[._-]/)
            .map(part => part[0])
            .join('')
            .substring(0, 2)
            .toUpperCase();
        avatar.textContent = initials;
    }

    const logoutBtn = document.getElementById('btn-logout');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => AuthService.logout());
    }

    if (window.HistoryModule) {
        HistoryModule.load();
    }
});
