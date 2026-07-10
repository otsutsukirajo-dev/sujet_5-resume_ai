document.addEventListener('DOMContentLoaded', () => {
    // Vérification de sécurité d'accès direct
    if (!AuthService.isAuthenticated()) {
        window.location.href = 'login.html';
        return;
    }

    // Affichage infos utilisateur
const userEmail = AuthService.getUser();

const welcome = document.getElementById('user-welcome');
if (welcome) welcome.textContent = userEmail;

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

    // Gestion de déconnexion
    const logoutBtn = document.getElementById('btn-logout');
    if(logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            AuthService.logout();
        });
    }

    // Charger l'historique initial
    if (window.HistoryModule) {
        HistoryModule.load();
    }
});