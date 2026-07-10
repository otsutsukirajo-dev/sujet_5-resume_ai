const SUMMARY_STEPS = [
    { icon: 'fa-file-import', label: 'Extraction du texte du document' },
    { icon: 'fa-scissors', label: 'Découpage en segments analysables' },
    { icon: 'fa-brain', label: 'Analyse par le modèle IA' },
    { icon: 'fa-code-merge', label: 'Fusion des résumés partiels' },
    { icon: 'fa-check-double', label: 'Finalisation du résumé' },
];

// Durées approximatives (ms) avant de passer à l'étape suivante.
// La dernière étape reste affichée jusqu'à la vraie réponse du serveur.
const SUMMARY_STEP_DELAYS = [900, 1400, 4000, 1800, 999999];

const SummaryModule = {
    _stepTimer: null,
    _currentStep: 0,

    _renderSteps(loadingEl) {
        loadingEl.innerHTML = `
            <div class="progress-steps" style="display:flex; flex-direction:column; gap:14px; width:100%; max-width:360px; margin:0 auto;">
                ${SUMMARY_STEPS.map((step, i) => `
                    <div class="progress-step" data-step="${i}" style="display:flex; align-items:center; gap:12px; opacity:0.35; transition:opacity 0.3s ease;">
                        <div class="progress-step__icon" style="width:28px; height:28px; border-radius:50%; border:1.5px solid var(--rule-strong); display:flex; align-items:center; justify-content:center; flex-shrink:0; transition:all 0.3s ease;">
                            <i class="fa-solid ${step.icon}" style="font-size:12px;"></i>
                        </div>
                        <span style="font-size:13px;">${step.label}</span>
                    </div>
                `).join('')}
            </div>
        `;
    },

    _setActiveStep(loadingEl, index) {
        const steps = loadingEl.querySelectorAll('.progress-step');
        steps.forEach((el, i) => {
            const icon = el.querySelector('.progress-step__icon');
            if (i < index) {
                el.style.opacity = '0.6';
                icon.style.borderColor = 'var(--amber)';
                icon.style.background = 'var(--amber)';
                icon.style.color = 'var(--paper, #F6F3EC)';
                icon.querySelector('i').className = 'fa-solid fa-check';
            } else if (i === index) {
                el.style.opacity = '1';
                icon.style.borderColor = 'var(--amber)';
                icon.style.background = 'transparent';
                icon.style.color = 'var(--amber)';
                icon.querySelector('i').className = 'fa-solid fa-spinner fa-spin';
            } else {
                el.style.opacity = '0.35';
                icon.style.borderColor = 'var(--rule-strong)';
                icon.style.background = 'transparent';
                icon.style.color = 'inherit';
            }
        });
    },

    _startProgress(loadingEl) {
        this._currentStep = 0;
        this._renderSteps(loadingEl);
        this._setActiveStep(loadingEl, 0);

        const advance = () => {
            this._currentStep++;
            if (this._currentStep >= SUMMARY_STEPS.length) return;
            this._setActiveStep(loadingEl, this._currentStep);
            this._stepTimer = setTimeout(advance, SUMMARY_STEP_DELAYS[this._currentStep]);
        };

        this._stepTimer = setTimeout(advance, SUMMARY_STEP_DELAYS[0]);
    },

    _stopProgress() {
        if (this._stepTimer) {
            clearTimeout(this._stepTimer);
            this._stepTimer = null;
        }
    },

    async generate() {
        const textInput = document.getElementById('text-input');
        const textValue = textInput ? textInput.value.trim() : '';
        if (!currentSelectedFile && !textValue) return;

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

        SummaryModule._startProgress(loading);

        try {
            let data;
            if (currentSelectedFile) {
                data = await ApiService.upload('/summarize', currentSelectedFile);
            } else {
                data = await ApiService.post('/summarize', { text: textValue });
            }

            SummaryModule._stopProgress();
            textEl.textContent = data.summary;

            loading.classList.remove('visible');
            textWrap.classList.add('visible');
            actions.classList.add('visible');
            badge.classList.add('visible');

            if (window.HistoryModule) window.HistoryModule.load();
        } catch (error) {
            SummaryModule._stopProgress();
            loading.classList.remove('visible');
            empty.classList.remove('hidden');
            alert(error.message);
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('btn-summarize');
    const textInput = document.getElementById('text-input');
    if (btn) btn.addEventListener('click', SummaryModule.generate);
    if (textInput) {
        textInput.addEventListener('input', () => {
            const hasText = textInput.value.trim().length > 0;
            const hasFile = typeof currentSelectedFile !== 'undefined' && currentSelectedFile;
            if (btn) btn.disabled = !(hasText || hasFile);
        });
    }
});
