function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    if (ext === 'pdf') return '<i class="fa-solid fa-file-pdf text-red-500"></i>';
    if (ext === 'docx' || ext === 'doc') return '<i class="fa-solid fa-file-word text-blue-500"></i>';
    return '<i class="fa-solid fa-file-lines text-gray-400"></i>';
}
const HistoryModule = {
    async load() {
        const container = document.getElementById('history-list');
        if (!container) return;

        try {
            const items = await ApiService.get('/history');
            container.innerHTML = '';

            const statTotal = document.getElementById('stat-total');
            if (statTotal) statTotal.textContent = items.length;

            const statLast = document.getElementById('stat-last');
            if (statLast && items.length > 0) {
                statLast.textContent = new Date(items[0].date).toLocaleDateString();
            }

            if(items.length === 0) {
                container.innerHTML = '<p class="text-xs text-gray-400 italic text-center">Aucun historique.</p>';
                return;
            }

            items.forEach(item => {
                const div = document.createElement('div');
                div.className = "p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition text-xs flex justify-between items-center border border-gray-100";
                div.innerHTML = `
    <div class="flex items-center gap-2 truncate max-w-[85%]">
        ${getFileIcon(item.filename)}
        <div class="truncate">
            <p class="font-semibold text-gray-800 truncate">${Utils.escapeHtml(item.filename)}</p>
            <p class="text-[10px] text-gray-400">${new Date(item.date).toLocaleDateString()}</p>
        </div>
    </div>
    <i class="fa-solid fa-chevron-right text-gray-400"></i>
`;
                div.addEventListener('click', () => {
                    document.getElementById('summary-placeholder').classList.add('hidden');
                    document.getElementById('summary-loading').classList.add('hidden');
                    
                    const textDisplay = document.getElementById('summary-text');
                    textDisplay.textContent = item.summary;
                    textDisplay.classList.remove('hidden');
                    document.getElementById('export-actions').classList.remove('hidden');
                });

                container.appendChild(div);
            });
        } catch (e) {
            console.error("Erreur historique:", e);
        }
    }
};