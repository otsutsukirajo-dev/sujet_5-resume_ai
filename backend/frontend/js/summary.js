const SummaryModule = {
    async generate() {
        if (!currentSelectedFile) return;

        const placeholder = document.getElementById('summary-placeholder');
        const loading = document.getElementById('summary-loading');
        const textDisplay = document.getElementById('summary-text');
        const actions = document.getElementById('export-actions');

        placeholder.classList.add('hidden');
        textDisplay.classList.add('hidden');
        actions.classList.add('hidden');
        loading.classList.remove('hidden');

        try {
            const data = await ApiService.upload('/summarize', currentSelectedFile);
            
            // Sécurité anti-XSS via textContent
            textDisplay.textContent = data.summary;
            
            loading.classList.add('hidden');
            textDisplay.classList.remove('hidden');
            actions.classList.remove('hidden');
document.getElementById('status-badge').classList.remove('hidden');
            
            // Mettre à jour l'historique parallèlement
            if (window.HistoryModule) window.HistoryModule.load();
        } catch (error) {
            loading.classList.add('hidden');
            placeholder.classList.remove('hidden');
            alert(error.message);
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('btn-summarize');
    if (btn) btn.addEventListener('click', SummaryModule.generate);
});