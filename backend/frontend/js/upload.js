let currentSelectedFile = null;

document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const fileDetails = document.getElementById('file-details');
    const fileName = document.getElementById('file-name');
    const clearFile = document.getElementById('clear-file');
    const btnSummarize = document.getElementById('btn-summarize');

    if (!dropzone) return;

    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('bg-indigo-50'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('bg-indigo-50'));
    
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('bg-indigo-50');
        if(e.dataTransfer.files.length > 0) validateAndSetFile(e.dataTransfer.files[0]);
    });

    fileInput.addEventListener('change', (e) => {
        if(e.target.files.length > 0) validateAndSetFile(e.target.files[0]);
    });

    function validateAndSetFile(file) {
        const extensions = /(\.txt|\.pdf|\.docx)$/i;
        if (!extensions.exec(file.name)) {
            alert("Format non valide (PDF, TXT, DOCX uniquement).");
            return;
        }
        currentSelectedFile = file;
        fileName.textContent = file.name;
        fileDetails.classList.remove('hidden');
        fileDetails.classList.add('flex');
        btnSummarize.disabled = false;
    }

    clearFile.addEventListener('click', (e) => {
        e.stopPropagation();
        currentSelectedFile = null;
        fileInput.value = '';
        fileDetails.classList.add('hidden');
        btnSummarize.disabled = true;
    });
});