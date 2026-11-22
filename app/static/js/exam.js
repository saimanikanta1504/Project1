/**
 * Online Examination Engine (CBT Interface)
 * Client-Side Controller & State Synchronizer
 */

class ExaminationEngine {
    constructor(config) {
        this.attemptId = config.attemptId;
        this.questions = config.questions;
        this.remainingSeconds = config.remainingSeconds;
        this.saveAnswerUrl = config.saveAnswerUrl;
        this.clearAnswerUrl = config.clearAnswerUrl;
        this.logActivityUrl = config.logActivityUrl;
        this.submitExamUrl = config.submitExamUrl;
        this.csrfToken = config.csrfToken;

        this.currentIndex = 0;
        this.timerInterval = null;
        this.tabSwitchCount = 0;

        this.initElements();
        this.initEvents();
        this.renderQuestion(0);
        this.updatePalette();
        this.startTimer();
    }

    initElements() {
        this.timerDisplay = document.getElementById('timer-display');
        this.qNumberElem = document.getElementById('current-q-number');
        this.qMarksElem = document.getElementById('current-q-marks');
        this.qTextElem = document.getElementById('current-q-text');
        this.optionsContainer = document.getElementById('options-container');
        this.paletteGrid = document.getElementById('palette-grid');

        this.btnPrev = document.getElementById('btn-prev');
        this.btnSaveNext = document.getElementById('btn-save-next');
        this.btnClear = document.getElementById('btn-clear');
        this.btnReview = document.getElementById('btn-review');
        this.btnSubmitModal = document.getElementById('btn-submit-modal');
        this.submitForm = document.getElementById('exam-submit-form');

        // Summary modal elements
        this.summaryTotal = document.getElementById('modal-total-q');
        this.summaryAnswered = document.getElementById('modal-answered-q');
        this.summaryUnanswered = document.getElementById('modal-unanswered-q');
        this.summaryReview = document.getElementById('modal-review-q');
    }

    initEvents() {
        this.btnPrev.addEventListener('click', () => this.navigatePrev());
        this.btnSaveNext.addEventListener('click', () => this.saveAndNext());
        this.btnClear.addEventListener('click', () => this.clearCurrentResponse());
        this.btnReview.addEventListener('click', () => this.toggleMarkForReview());
        this.btnSubmitModal.addEventListener('click', () => this.populateSubmitSummary());

        // Anti-cheat / Tab switch monitoring
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.recordIntegrityEvent('tab_switch', 'Focus lost: Tab switched or minimized.');
            }
        });

        window.addEventListener('blur', () => {
            this.recordIntegrityEvent('window_blur', 'Window blur: Focus transferred away from exam application.');
        });
    }

    startTimer() {
        this.updateTimerDisplay();
        this.timerInterval = setInterval(() => {
            this.remainingSeconds--;
            this.updateTimerDisplay();

            if (this.remainingSeconds <= 0) {
                clearInterval(this.timerInterval);
                this.handleTimeExpiry();
            }
        }, 1000);
    }

    updateTimerDisplay() {
        const minutes = Math.floor(this.remainingSeconds / 60);
        const seconds = this.remainingSeconds % 60;
        const formatted = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        
        if (this.timerDisplay) {
            this.timerDisplay.textContent = formatted;
            if (this.remainingSeconds <= 300) {
                this.timerDisplay.parentElement.classList.add('urgent');
            }
        }
    }

    handleTimeExpiry() {
        alert('Examination duration has concluded. Your answers will now be automatically evaluated.');
        this.submitForm.submit();
    }

    renderQuestion(index) {
        if (index < 0 || index >= this.questions.length) return;
        this.currentIndex = index;
        const q = this.questions[index];

        this.qNumberElem.textContent = `Question ${q.number} of ${this.questions.length}`;
        let marksText = `${q.marks} Mark(s)`;
        if (q.negative_marks > 0) {
            marksText += ` | Negative: -${q.negative_marks}`;
        }
        this.qMarksElem.textContent = marksText;
        this.qTextElem.textContent = q.text;

        // Render options
        this.optionsContainer.innerHTML = '';
        q.options.forEach(opt => {
            const item = document.createElement('div');
            item.className = 'cbt-option-item';
            if (q.selected_option_id === opt.id) {
                item.classList.add('selected');
            }

            item.innerHTML = `
                <input class="form-check-input cbt-option-radio" type="radio" 
                       name="question_opt" id="opt_${opt.id}" value="${opt.id}"
                       ${q.selected_option_id === opt.id ? 'checked' : ''}>
                <label class="form-check-label w-100 cursor-pointer" for="opt_${opt.id}">
                    <span class="fw-bold me-2">${String.fromCharCode(64 + opt.number)}.</span>
                    ${opt.text}
                </label>
            `;

            item.addEventListener('click', () => {
                const radio = item.querySelector('input');
                radio.checked = true;
                this.selectOption(opt.id);
            });

            this.optionsContainer.appendChild(item);
        });

        // Update Review button text/style
        if (q.is_marked_for_review) {
            this.btnReview.classList.replace('btn-outline-warning', 'btn-warning');
            this.btnReview.textContent = 'Marked for Review';
        } else {
            this.btnReview.classList.replace('btn-warning', 'btn-outline-warning');
            this.btnReview.textContent = 'Mark for Review';
        }

        // Previous button state
        this.btnPrev.disabled = (index === 0);

        // Next button label
        if (index === this.questions.length - 1) {
            this.btnSaveNext.textContent = 'Save & Review';
        } else {
            this.btnSaveNext.textContent = 'Save & Next';
        }

        this.updatePalette();
    }

    selectOption(optionId) {
        const q = this.questions[this.currentIndex];
        q.selected_option_id = optionId;

        // Refresh UI selected class
        const optionItems = this.optionsContainer.querySelectorAll('.cbt-option-item');
        optionItems.forEach(el => el.classList.remove('selected'));
        const activeRadio = this.optionsContainer.querySelector(`input[value="${optionId}"]`);
        if (activeRadio) {
            activeRadio.closest('.cbt-option-item').classList.add('selected');
        }

        this.persistAnswer(q.id, optionId, q.is_marked_for_review);
        this.updatePalette();
    }

    saveAndNext() {
        const q = this.questions[this.currentIndex];
        this.persistAnswer(q.id, q.selected_option_id, q.is_marked_for_review);

        if (this.currentIndex < this.questions.length - 1) {
            this.renderQuestion(this.currentIndex + 1);
        } else {
            this.updatePalette();
        }
    }

    navigatePrev() {
        if (this.currentIndex > 0) {
            this.renderQuestion(this.currentIndex - 1);
        }
    }

    clearCurrentResponse() {
        const q = this.questions[this.currentIndex];
        q.selected_option_id = null;

        const radios = this.optionsContainer.querySelectorAll('input[type="radio"]');
        radios.forEach(r => r.checked = false);

        const optionItems = this.optionsContainer.querySelectorAll('.cbt-option-item');
        optionItems.forEach(el => el.classList.remove('selected'));

        this.updatePalette();

        // Persist clear to backend
        fetch(this.clearAnswerUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify({ question_id: q.id })
        });
    }

    toggleMarkForReview() {
        const q = this.questions[this.currentIndex];
        q.is_marked_for_review = !q.is_marked_for_review;

        this.persistAnswer(q.id, q.selected_option_id, q.is_marked_for_review);
        this.renderQuestion(this.currentIndex);
    }

    persistAnswer(questionId, selectedOptionId, isMarkedForReview) {
        fetch(this.saveAnswerUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify({
                question_id: questionId,
                selected_option_id: selectedOptionId,
                is_marked_for_review: isMarkedForReview
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'expired') {
                window.location.href = data.redirect_url;
            }
        })
        .catch(err => console.error('Auto-save error:', err));
    }

    updatePalette() {
        this.paletteGrid.innerHTML = '';
        this.questions.forEach((q, idx) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'palette-btn';
            btn.textContent = q.number;

            if (idx === this.currentIndex) {
                btn.classList.add('active');
            }

            if (q.is_marked_for_review) {
                btn.classList.add('review');
            } else if (q.selected_option_id !== null && q.selected_option_id !== undefined) {
                btn.classList.add('answered');
            } else {
                btn.classList.add('unanswered');
            }

            btn.addEventListener('click', () => {
                this.renderQuestion(idx);
            });

            this.paletteGrid.appendChild(btn);
        });
    }

    populateSubmitSummary() {
        let answered = 0;
        let review = 0;
        this.questions.forEach(q => {
            if (q.selected_option_id) answered++;
            if (q.is_marked_for_review) review++;
        });
        const unanswered = this.questions.length - answered;

        this.summaryTotal.textContent = this.questions.length;
        this.summaryAnswered.textContent = answered;
        this.summaryUnanswered.textContent = unanswered;
        this.summaryReview.textContent = review;
    }

    recordIntegrityEvent(eventType, eventData) {
        this.tabSwitchCount++;
        const badge = document.getElementById('integrity-warning-badge');
        if (badge) {
            badge.classList.remove('d-none');
            badge.textContent = `Integrity Alerts: ${this.tabSwitchCount}`;
        }

        fetch(this.logActivityUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify({
                event_type: eventType,
                event_data: eventData
            })
        });
    }
}
