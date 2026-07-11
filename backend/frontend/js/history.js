const HistoryModule = {
    async load() {
        const container = document.getElementById('history-list');
        if (!container) return;

        try {
            const data = await ApiService.get('/history');
            const items = data.items || [];
            container.innerHTML = '';

            const statTotal = document.getElementById('stat-total');
            if (statTotal) statTotal.textContent = data.total ?? items.length;

            const statLast = document.getElementById('stat-last');
            if (statLast) {
                statLast.textContent = items.length > 0
                    ? new Date(items[0].created_at).toLocaleDateString()
                    : '—';
            }

            if (items.length === 0) {
                container.innerHTML = '<p class="history-empty">Aucun résumé pour le moment.</p>';
                return;
            }

            items.forEach(item => {
                const div = document.createElement('div');
                div.className = 'history-item';
                div.innerHTML = `
                    <i class="fa-regular fa-file-lines history-item__icon"></i>
                    <div class="history-item__body">
                        <p class="history-item__name">${Utils.escapeHtml(item.filename)}</p>
                        <p class="history-item__date">${new Date(item.created_at).toLocaleDateString()}</p>
                    </div>
                    <i class="fa-solid fa-chevron-right history-item__icon"></i>
                `;

                div.addEventListener('click', () => {
                    document.getElementById('result-empty').classList.add('hidden');
                    document.getElementById('result-loading').classList.remove('visible');

                    const textWrap = document.getElementById('result-text-wrap');
                    const textEl = document.getElementById('result-text');
                    textEl.textContent = item.summary;
                    textWrap.classList.add('visible');

                    document.getElementById('result-actions').classList.add('visible');
                    document.getElementById('status-badge').classList.add('visible');
                });

                container.appendChild(div);
            });
        } catch (e) {
            console.error('Erreur historique:', e);
        }
    }
};

// IMPORTANT : dans un script classique (non-module), une déclaration `const`
// au niveau global n'est PAS automatiquement attachée à `window`.
// dashboard.js teste `if (window.HistoryModule)` avant d'appeler .load(),
// donc sans cette ligne, la condition est toujours fausse et load() n'est
// jamais exécuté — silencieusement, sans erreur console, sans requête réseau.
window.HistoryModule = HistoryModule;
