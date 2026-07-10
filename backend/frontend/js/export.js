document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('btn-export-txt');
    if (!btn) return;

    btn.addEventListener('click', () => {
        const textContent = document.getElementById('result-text').textContent;
        if (!textContent) return;

        const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `resume_ai_${Date.now()}.txt`;
        a.click();
        URL.revokeObjectURL(url);
    });
});
