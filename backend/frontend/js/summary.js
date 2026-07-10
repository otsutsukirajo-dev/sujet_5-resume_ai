const SummaryModule = {
    async generate() {
        if (!currentSelectedFile) return;

        const empty = document.getElementById('result-empty');
        const loading = document.getElementById('result-loading');
        const textWrap = document.getElementById('result-text-wrap');
        const textEl = document.getElementById('result-text');
        const actions = document.getElementById('result-actions');
        const badge = document.getElementById('status-badge');

        empty.classList.add('hidden');
        textWrap.classList.remove('visible');
        actions.classList.remove('visible');
        badge.classList.remove('visible');
        loading.classList.add('visible');

        try {
            const data = await ApiService.upload('/summarize', currentSelectedFile);

            textEl.textContent = data.summary;

            loading.classList.remove('visible');
            textWrap.classList.add('visible');
            actions.classList.add('visible');
            badge.classList.add('visible');

            if (window.HistoryModule) window.HistoryModule.load();
        } catch (error) {
            loading.classList.remove('visible');
            empty.classList.remove('hidden');
            alert(error.message);
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('btn-summarize');
    if (btn) btn.addEventListener('click', SummaryModule.generate);
});
