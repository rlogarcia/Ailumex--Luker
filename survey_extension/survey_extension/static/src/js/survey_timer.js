/** @odoo-module **/
/**
 * ============================================================================
 * Archivo: survey_timer.js
 * Propósito: Lógica completa del cronómetro para encuestas y preguntas
 * Versión: 1.0
 * 
 * Funcionalidades:
 * - Cronómetro general para toda la encuesta
 * - Cronómetro individual por pregunta
 * - Contador regresivo (countdown)
 * - Tracking de tiempo
 * - Auto-submit cuando se agota el tiempo
 * - Alertas visuales y sonoras
 * - Persistencia de tiempo en localStorage
 * ============================================================================
 */

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";

/**
 * Utilidades de formato
 */
const formatTime = (seconds) => {
    if (seconds < 0) seconds = 0;
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return {
        minutes: mins.toString().padStart(2, "0"),
        seconds: secs.toString().padStart(2, "0"),
        total: seconds,
    };
};

const parseBoolean = (value) => {
    if (typeof value === "boolean") return value;
    if (typeof value === "number") return !!value;
    if (typeof value === "string") {
        const normalized = value.trim().toLowerCase();
        return normalized === "true" || normalized === "1";
    }
    return false;
};

/**
 * Sonido de alerta (beep)
 */
const playAlertSound = () => {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800;
        oscillator.type = "sine";
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
    } catch (error) {
        console.warn("No se pudo reproducir el sonido de alerta:", error);
    }
};

// ============================================================================
// CRONÓMETRO GENERAL DE ENCUESTA
// ============================================================================

publicWidget.registry.SurveyTimerGeneral = publicWidget.Widget.extend({
    selector: ".o_survey_timer_general",
    
    events: {},
    
    /**
     * Inicialización del widget
     */
    start() {
        const result = this._super.apply(this, arguments);
        return Promise.resolve(result).then(() => {
            this._initializeTimer();
            // Si el formulario está en la pantalla de inicio (antes de "Start Survey"),
            // no iniciar el cronómetro aquí. El cronómetro debe arrancar cuando la
            // encuesta esté en progreso (answer.state == 'in_progress').
            const $form = this.$el.closest('form');
            const isStartScreen = $form && $form.data('is-start-screen');
            if (isStartScreen) {
                console.debug('Cronómetro general: esperando a que la encuesta inicie (start screen)');
                // Caso SPA / no recarga completa: si el usuario ya hizo click en Start,
                // es posible que exista una marca en localStorage. En ese caso, iniciar.
                try {
                    const surveyId = $form.data('survey-token') || $form.attr('name');
                    const started = localStorage.getItem(`survey_start_clicked_${surveyId}`);
                    if (started) {
                        console.debug('Cronómetro general: start clicked previamente (SPA), arrancando cronómetro.');
                        this._startTimer();
                        return;
                    }
                } catch (e) {
                    /* ignore */
                }
                // Escuchar evento global 'survey:started' para arrancar el cronómetro
                this._onSurveyStartedHandler = (ev, data) => {
                    try {
                        if (!data || !data.surveyId || data.surveyId === this.surveyId) {
                            console.debug('Cronómetro general: recibiendo evento survey:started, arrancando cronómetro.');
                            this._startTimer();
                        }
                    } catch (err) {
                        console.warn('Error manejando survey:started en SurveyTimerGeneral', err);
                    }
                };
                $(document).on('survey:started.surveyTimer', this._onSurveyStartedHandler);
                return;
            }
            this._startTimer();
        });
    },
    
    /**
     * Limpieza al destruir el widget
     */
    destroy() {
        // Quitar listener si estaba registrado
        try {
            if (this._onSurveyStartedHandler) {
                $(document).off('survey:started.surveyTimer', this._onSurveyStartedHandler);
                this._onSurveyStartedHandler = null;
            }
        } catch (e) {
            /* ignore */
        }
        this._stopTimer();
        this._super.apply(this, arguments);
    },
    
    /**
     * Inicializar variables del cronómetro
     */
    _initializeTimer() {
        // Elementos del DOM
        this.$card = this.$(".o_timer_card");
        this.$icon = this.$(".o_timer_icon");
        this.$minutesDisplay = this.$(".o_timer_minutes");
        this.$secondsDisplay = this.$(".o_timer_seconds");
        this.$progress = this.$(".o_timer_progress");
        this.$warning = this.$(".o_timer_warning");
        this.$expired = this.$(".o_timer_expired");
        
        // Configuración (lectura robusta de atributos data-*)
        const getData = (key) => {
            // key: kebab-case like 'time-limit'
            const camel = key.replace(/-([a-z])/g, (g) => g[1].toUpperCase());
            let val;
            try {
                val = this.$el.data(key);
            } catch (e) {
                val = undefined;
            }
            if (val === undefined) {
                try { val = this.$el.data(camel); } catch (e) { val = undefined; }
            }
            if (val === undefined) {
                val = this.$el.attr(`data-${key}`);
            }
            // Normalizar strings booleanos/proxies de Odoo que a veces vienen como 'False'/'True'
            if (typeof val === 'string') {
                const low = val.trim().toLowerCase();
                if (low === 'false' || low === 'none' || low === 'null') {
                    val = undefined;
                }
            }
            return val;
        };

        this.surveyId = getData('survey-id') || this.$el.data('survey-id');
    this.timeLimit = parseInt(getData('time-limit'), 10) || 0;
    this.warningThreshold = parseInt(getData('warning-threshold'), 10) || 20;
        this.autoSubmit = parseBoolean(getData('auto-submit'));
        this.soundEnabled = parseBoolean(getData('sound-enabled'));
        
        // Estado
    this.startTime = null;
    // Si timeLimit <= 0 tratamos como modo "count-up" (contar tiempo transcurrido)
    this.countUp = (this.timeLimit <= 0);
    // En modo countUp usamos timeElapsed; en modo countdown usamos timeRemaining
    this.timeElapsed = 0;
    this.timeRemaining = this.countUp ? 0 : this.timeLimit;
        this.timerInterval = null;
        this.hasPlayedWarningSound = false;
        this.isExpired = false;
        
        // Clave para localStorage
        this.storageKey = `survey_timer_${this.surveyId}`;
        
        // Intentar recuperar estado previo
        this._loadState();
        
        console.log("Cronómetro general inicializado:", {
            surveyId: this.surveyId,
            timeLimit: this.timeLimit,
            timeRemaining: this.timeRemaining,
        });
    },
    
    /**
     * Iniciar el cronómetro
     */
    _startTimer() {
        // Evitar doble arranque si ya se inició por un mecanismo directo
        try {
            const startedFlag = this.$el.attr('data-timer-started') || this.$el.data('timerStarted');
            if (startedFlag) {
                console.debug('SurveyTimerGeneral: ya iniciado (flag) — omitiendo _startTimer');
                return;
            }
            this.$el.attr('data-timer-started', '1');
        } catch (e) {
            /* ignore */
        }

        if (this.countUp) {
            // Si no hay límite configurado, pasar a modo contador ascendente.
            console.info('SurveyTimerGeneral: modo count-up (sin límite) — el temporizador contará el tiempo transcurrido.');
        }
        
        if (!this.startTime) {
            this.startTime = Date.now();
            this._saveState();
        }
        
        // Actualizar display inmediatamente
        this._updateDisplay();
        
        // Iniciar intervalo de actualización (cada segundo)
        this.timerInterval = setInterval(() => {
            this._tick();
        }, 1000);
    },
    
    /**
     * Detener el cronómetro
     */
    _stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    },
    
    /**
     * Tick del cronómetro (cada segundo)
     */
    _tick() {
        if (this.isExpired) return;
        const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
        if (this.countUp) {
            this.timeElapsed = elapsed;
            // En countUp no se marca expired automáticamente
        } else {
            this.timeRemaining = Math.max(0, this.timeLimit - elapsed);
        }

        this._updateDisplay();
        this._updateState();
        this._saveState();

        if (!this.countUp && this.timeRemaining <= 0) {
            this._onTimerExpired();
        }
    },
    
    /**
     * Actualizar el display del cronómetro
     */
    _updateDisplay() {
        let time;
        if (this.countUp) {
            time = formatTime(this.timeElapsed);
            this.$minutesDisplay.text(time.minutes);
            this.$secondsDisplay.text(time.seconds);
            // En modo countUp mantenemos la barra llena o eliminamos el porcentaje dinámico
            this.$progress.css("width", `100%`);
            this.$progress.attr("aria-valuenow", 100);
        } else {
            time = formatTime(this.timeRemaining);
            this.$minutesDisplay.text(time.minutes);
            this.$secondsDisplay.text(time.seconds);
            // Actualizar barra de progreso
            const percentage = (this.timeRemaining / Math.max(1, this.timeLimit)) * 100;
            this.$progress.css("width", `${percentage}%`);
            this.$progress.attr("aria-valuenow", percentage);
        }
    },
    
    /**
     * Actualizar el estado visual del cronómetro
     */
    _updateState() {
        const percentage = (this.timeRemaining / this.timeLimit) * 100;
        
        // Remover clases anteriores
        this.$card.removeClass("timer-normal timer-warning timer-danger");
        
        if (percentage <= 0) {
            this.$card.addClass("timer-danger");
        } else if (percentage <= this.warningThreshold) {
            this.$card.addClass("timer-warning");
            this.$warning.removeClass("d-none");
            
            // Reproducir sonido de advertencia (solo una vez)
            if (this.soundEnabled && !this.hasPlayedWarningSound) {
                playAlertSound();
                this.hasPlayedWarningSound = true;
            }
        } else {
            this.$card.addClass("timer-normal");
            this.$warning.addClass("d-none");
        }
    },
    
    /**
     * Manejar cuando el tiempo se agota
     */
    _onTimerExpired() {
        if (this.isExpired) return;
        
        console.log("⏰ Tiempo agotado para la encuesta");
        
        this.isExpired = true;
        this._stopTimer();
        
        this.$card.addClass("timer-danger");
        this.$expired.removeClass("d-none");
        this.$warning.addClass("d-none");
        
        // Reproducir sonido final
        if (this.soundEnabled) {
            playAlertSound();
            setTimeout(() => playAlertSound(), 300);
        }
        
        // Auto-submit si está habilitado
        if (this.autoSubmit) {
            this._autoSubmitSurvey();
        }
        
        this._saveState();
    },
    
    /**
     * Auto-enviar la encuesta
     */
    _autoSubmitSurvey() {
        console.log("🚀 Auto-enviando encuesta...");
        
        // Mostrar mensaje al usuario
        this.$expired.html(`
            <i class="fa fa-spinner fa-spin me-2"></i>
            <strong>Tiempo agotado.</strong> Enviando encuesta automáticamente...
        `);
        
        // Esperar 2 segundos antes de enviar (para que el usuario vea el mensaje)
        setTimeout(() => {
            const $submitBtn = $("button[type='submit'].o_survey_submit");
            if ($submitBtn.length) {
                $submitBtn.click();
            } else {
                // Intentar enviar el formulario directamente
                $("form.o_survey_form").submit();
            }
        }, 2000);
    },
    
    /**
     * Guardar estado en localStorage
     */
    _saveState() {
        try {
            const state = {
                startTime: this.startTime,
                timeRemaining: this.timeRemaining,
                isExpired: this.isExpired,
            };
            localStorage.setItem(this.storageKey, JSON.stringify(state));
        } catch (error) {
            console.warn("No se pudo guardar el estado del cronómetro:", error);
        }
    },
    
    /**
     * Cargar estado desde localStorage
     */
    _loadState() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            if (saved) {
                const state = JSON.parse(saved);
                this.startTime = state.startTime;
                this.timeRemaining = state.timeRemaining || this.timeLimit;
                this.isExpired = state.isExpired || false;
                
                console.log("Estado del cronómetro recuperado:", state);
            }
        } catch (error) {
            console.warn("No se pudo cargar el estado del cronómetro:", error);
        }
    },
});

// ============================================================================
// CRONÓMETRO DE PREGUNTA INDIVIDUAL
// ============================================================================

publicWidget.registry.SurveyTimerQuestion = publicWidget.Widget.extend({
    selector: ".o_survey_timer_question",
    
    events: {},
    
    /**
     * Inicialización del widget
     */
    start() {
        const result = this._super.apply(this, arguments);
        return Promise.resolve(result).then(() => {
            this._initializeTimer();
            // Evitar iniciar el cronómetro si estamos en la pantalla de inicio
            // (antes de que el usuario presione Start). Buscamos el formulario
            // padre y comprobamos su atributo data-is-start-screen.
            const $form = this.$el.closest('form');
            const isStartScreen = $form && $form.data('is-start-screen');
            if (isStartScreen) {
                console.debug('Cronómetro de pregunta: esperando a que la encuesta inicie (start screen)');
                try {
                    const surveyId = $form.data('survey-token') || $form.attr('name');
                    const started = localStorage.getItem(`survey_start_clicked_${surveyId}`);
                    if (started) {
                        console.debug('Cronómetro de pregunta: start clicked previamente (SPA), arrancando cronómetro.');
                        this._startTimer();
                        return;
                    }
                } catch (e) {
                    /* ignore */
                }
                // Escuchar evento global 'survey:started' para arrancar el cronómetro
                this._onSurveyStartedHandler = (ev, data) => {
                    try {
                        if (!data || !data.surveyId) {
                            // Si no hay surveyId en payload asumimos que aplica
                            console.debug('Cronómetro de pregunta: recibiendo evento survey:started, arrancando cronómetro.');
                            this._startTimer();
                        } else {
                            // Si se proporcionó surveyId, podríamos validar (opcional)
                            this._startTimer();
                        }
                    } catch (err) {
                        console.warn('Error manejando survey:started en SurveyTimerQuestion', err);
                    }
                };
                $(document).on('survey:started.surveyTimer', this._onSurveyStartedHandler);
                return;
            }
            this._startTimer();
        });
    },
    
    /**
     * Limpieza al destruir el widget
     */
    destroy() {
        this._stopTimer();
        this._finalizeTracking();
        // Quitar listener si estaba registrado
        try {
            if (this._onSurveyStartedHandler) {
                $(document).off('survey:started.surveyTimer', this._onSurveyStartedHandler);
                this._onSurveyStartedHandler = null;
            }
        } catch (e) {
            /* ignore */
        }
        this._super.apply(this, arguments);
    },
    
    /**
     * Inicializar variables del cronómetro
     */
    _initializeTimer() {
        // Elementos del DOM
        this.$card = this.$(".o_timer_card");
        this.$minutesDisplay = this.$(".o_timer_minutes");
        this.$secondsDisplay = this.$(".o_timer_seconds");
        this.$progress = this.$(".o_timer_progress");
        this.$status = this.$(".o_timer_status");
        this.$warning = this.$(".o_timer_warning");
        this.$expired = this.$(".o_timer_expired");
        
        // Inputs ocultos para guardar datos
        this.$timeSpent = this.$(".o_question_time_spent");
        this.$timeExceeded = this.$(".o_question_time_exceeded");
        
        // Configuración (lectura robusta de atributos data-*)
        const getDataQ = (key) => {
            const camel = key.replace(/-([a-z])/g, (g) => g[1].toUpperCase());
            let val;
            try { val = this.$el.data(key); } catch (e) { val = undefined; }
            if (val === undefined) { try { val = this.$el.data(camel); } catch (e) { val = undefined; } }
            if (val === undefined) { val = this.$el.attr(`data-${key}`); }
            return val;
        };

        this.questionId = getDataQ('question-id') || this.$el.data('question-id');
        this.timeLimit = parseInt(getDataQ('time-limit'), 10) || 60;
        this.warningPercentage = parseInt(getDataQ('warning-percentage'), 10) || 25;
        this.actionOnTimeout = getDataQ('action-on-timeout') || "none";
        this.allowOvertime = parseBoolean(getDataQ('allow-overtime'));
        
        // Estado
        this.startTime = Date.now();
        this.timeRemaining = this.timeLimit;
        this.timeElapsed = 0;
        this.timerInterval = null;
        this.isExpired = false;
        this.isOvertime = false;
        
        // Encontrar el contenedor de la pregunta
        this.$questionContainer = this.$el.closest(".o_survey_question");
        
        console.log("Cronómetro de pregunta inicializado:", {
            questionId: this.questionId,
            timeLimit: this.timeLimit,
            actionOnTimeout: this.actionOnTimeout,
        });
    },
    
    /**
     * Iniciar el cronómetro
     */
    _startTimer() {
        // Actualizar display inmediatamente
        try {
            const startedFlag = this.$el.attr('data-timer-started') || this.$el.data('timerStarted');
            if (!startedFlag) {
                this.$el.attr('data-timer-started', '1');
            }
        } catch (e) { /* ignore */ }
        this._updateDisplay();
        
        // Iniciar intervalo de actualización
        this.timerInterval = setInterval(() => {
            this._tick();
        }, 1000);
    },
    
    /**
     * Detener el cronómetro
     */
    _stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    },
    
    /**
     * Tick del cronómetro
     */
    _tick() {
        this.timeElapsed = Math.floor((Date.now() - this.startTime) / 1000);
        
        if (!this.isOvertime) {
            this.timeRemaining = Math.max(0, this.timeLimit - this.timeElapsed);
        }
        
        this._updateDisplay();
        this._updateState();
        this._saveTimeSpent();
        
        if (this.timeRemaining <= 0 && !this.isExpired) {
            this._onTimerExpired();
        }
    },
    
    /**
     * Actualizar el display
     */
    _updateDisplay() {
        const timeToShow = this.isOvertime ? this.timeElapsed - this.timeLimit : this.timeRemaining;
        const time = formatTime(timeToShow);
        
        this.$minutesDisplay.text(time.minutes);
        this.$secondsDisplay.text(time.seconds);
        
        if (!this.isOvertime) {
            const percentage = (this.timeRemaining / this.timeLimit) * 100;
            this.$progress.css("width", `${percentage}%`);
            this.$progress.attr("aria-valuenow", percentage);
        }
    },
    
    /**
     * Actualizar el estado visual
     */
    _updateState() {
        const percentage = (this.timeRemaining / this.timeLimit) * 100;
        
        this.$card.removeClass("timer-normal timer-warning timer-danger timer-overtime");
        
        if (this.isOvertime) {
            this.$card.addClass("timer-overtime");
            this.$status.text("Tiempo extra");
        } else if (percentage <= 0) {
            this.$card.addClass("timer-danger");
        } else if (percentage <= this.warningPercentage) {
            this.$card.addClass("timer-warning");
            this.$warning.removeClass("d-none");
        } else {
            this.$card.addClass("timer-normal");
            this.$warning.addClass("d-none");
        }
    },
    
    /**
     * Manejar cuando el tiempo se agota
     */
    _onTimerExpired() {
        if (this.isExpired) return;
        
        console.log(`⏰ Tiempo agotado para pregunta ${this.questionId}`);
        
        this.isExpired = true;
        
        this.$card.addClass("timer-danger");
        this.$expired.removeClass("d-none");
        this.$warning.addClass("d-none");
        
        // Ejecutar acción configurada
        this._executeTimeoutAction();
        
        // Si se permite tiempo extra, cambiar a modo overtime
        if (this.allowOvertime) {
            this.isOvertime = true;
            this.$card.addClass("timer-overtime");
            this.$status.text("Tiempo extra");
            this.$timeExceeded.val("1");
        } else {
            this._stopTimer();
        }
    },
    
    /**
     * Ejecutar la acción configurada al agotar el tiempo
     */
    _executeTimeoutAction() {
        console.log(`Ejecutando acción: ${this.actionOnTimeout}`);
        
        switch (this.actionOnTimeout) {
            case "block":
                this._blockQuestion();
                break;
            case "auto_next":
                this._goToNextQuestion();
                break;
            case "auto_submit":
                this._submitQuestion();
                break;
            case "none":
            default:
                // Solo mostrar alerta, no hacer nada más
                break;
        }
    },
    
    /**
     * Bloquear la pregunta
     */
    _blockQuestion() {
        console.log("Bloqueando pregunta...");
        
        this.$questionContainer.find("input, textarea, select").prop("disabled", true);
        this.$questionContainer.find("button").prop("disabled", true);
        
        this.$expired.html(`
            <i class="fa fa-lock me-2"></i>
            <strong>Pregunta bloqueada</strong> - El tiempo ha expirado
        `);
    },
    
    /**
     * Ir a la siguiente pregunta
     */
    _goToNextQuestion() {
        console.log("Yendo a la siguiente pregunta...");
        
        this.$expired.html(`
            <i class="fa fa-arrow-right me-2"></i>
            <strong>Pasando a la siguiente pregunta...</strong>
        `);
        
        setTimeout(() => {
            const $nextBtn = $("button.o_survey_next, button.o_survey_submit");
            if ($nextBtn.length) {
                $nextBtn.click();
            }
        }, 1500);
    },
    
    /**
     * Enviar la respuesta actual
     */
    _submitQuestion() {
        console.log("Enviando respuesta de la pregunta...");
        
        this.$expired.html(`
            <i class="fa fa-check me-2"></i>
            <strong>Guardando respuesta...</strong>
        `);
        
        // Aquí podrías hacer una llamada AJAX para guardar solo esta pregunta
        // Por ahora, simular con timeout
        setTimeout(() => {
            this._goToNextQuestion();
        }, 1000);
    },
    
    /**
     * Guardar tiempo gastado en input oculto
     */
    _saveTimeSpent() {
        if (this.$timeSpent.length) {
            this.$timeSpent.val(this.timeElapsed);
        }
    },
    
    /**
     * Finalizar tracking al destruir
     */
    _finalizeTracking() {
        this._saveTimeSpent();
        console.log(`Tiempo final registrado para pregunta ${this.questionId}: ${this.timeElapsed}s`);
    },
});

// ============================================================================
// GESTOR GLOBAL DE CRONÓMETROS
// ============================================================================

publicWidget.registry.SurveyTimerManager = publicWidget.Widget.extend({
    selector: ".o_survey_form",
    
    /**
     * Inicialización
     */
    start() {
        const result = this._super.apply(this, arguments);
        return Promise.resolve(result).then(() => {
            this._setupFormSubmitHandler();
            // Si estamos en la pantalla de inicio, escuchar el botón de "Start"
            // para marcar que el usuario inició la encuesta (útil en escenarios
            // donde no hay recarga completa de la página).
            const $form = this.$el;
            const surveyId = $form.data('survey-token') || $form.attr('name');
            if ($form.data('is-start-screen')) {
                // Handler reutilizable: soporta click en botón y submit del formulario
                const startHandler = (ev) => {
                    try {
                        localStorage.setItem(`survey_start_clicked_${surveyId}`, '1');
                    } catch (e) {
                        /* ignore */
                    }
                    // Disparar evento global para que los widgets del cronómetro
                    // que están en la pantalla de inicio puedan arrancar inmediatamente
                    try {
                        $(document).trigger('survey:started', { surveyId: surveyId });
                    } catch (err) {
                        console.warn('No se pudo disparar evento survey:started', err);
                    }
                    // Intentar fallback directo: arrancar timers existentes en DOM
                    try {
                        this._directStartTimers();
                    } catch (err) {
                        console.warn('Fallback directo: no se pudo iniciar timers directamente', err);
                    }
                };

                // Escuchar click en cualquier botón submit (más robusto que depender del value)
                $form.on('click', "button[type='submit']", (ev) => {
                    // Solo actuar si estamos en la pantalla de inicio
                    startHandler(ev);
                });
                // También escuchar submit del formulario (por si el botón no es clickeado directamente)
                $form.on('submit', (ev) => {
                    // En el flujo normal el submit continúa; aquí sólo nos aseguramos de marca/trigger
                    startHandler(ev);
                });
            }
        });
    },
    
    /**
     * Configurar handler para el envío del formulario
     */
    _setupFormSubmitHandler() {
        const $form = this.$el;
        
        $form.on("submit", (event) => {
            // Aquí podrías agregar validaciones adicionales
            // Por ejemplo, verificar si hay preguntas bloqueadas
            
            console.log("📝 Formulario enviado con datos de cronómetro");
            
            // Limpiar localStorage
            this._clearTimerStorage();
            // Limpiar cualquier timer directo creado por el fallback
            try { this._clearDirectTimers(); } catch (e) { /* ignore */ }
        });
    },

    /**
     * Fallback: arrancar timers directamente sobre elementos DOM si los widgets
     * no se inicializaron a tiempo. Esto actualiza el display de forma mínima
     * para evitar que el usuario vea 00:00 tras pulsar Start.
     */
    _directStartTimers() {
        // Cronómetro general
        const $generals = this.$('.o_survey_timer_general').not('[data-direct-timer-started]');
        $generals.each((i, el) => {
            try {
                const $el = $(el);
                const timeLimit = parseInt($el.attr('data-time-limit') || $el.data('timeLimit') || $el.data('time-limit'), 10) || 0;
                if (timeLimit <= 0) return;
                $el.attr('data-direct-timer-started', '1');
                // almacenar intervalo para limpiar después
                const startedAt = Date.now();
                const key = 'directTimerInterval_general_' + (i || 0);
                const intervalId = setInterval(() => {
                    try {
                        const elapsed = Math.floor((Date.now() - startedAt) / 1000);
                        const remaining = Math.max(0, timeLimit - elapsed);
                        $el.find('.o_timer_minutes').text(String(Math.floor(remaining/60)).padStart(2,'0'));
                        $el.find('.o_timer_seconds').text(String(remaining%60).padStart(2,'0'));
                        const percent = (remaining / timeLimit) * 100;
                        $el.find('.o_timer_progress').css('width', percent + '%');
                    } catch (e) { /* ignore per-elem */ }
                }, 1000);
                // store on element
                $el.data('directTimerInterval', intervalId);
            } catch (err) { console.warn('directStartTimers general error', err); }
        });

        // Cronómetros por pregunta
        const $questions = this.$('.o_survey_timer_question').not('[data-direct-timer-started]');
        $questions.each((i, el) => {
            try {
                const $el = $(el);
                const timeLimit = parseInt($el.attr('data-time-limit') || $el.data('timeLimit') || $el.data('time-limit'), 10) || 0;
                if (timeLimit <= 0) return;
                $el.attr('data-direct-timer-started', '1');
                const startedAt = Date.now();
                const intervalId = setInterval(() => {
                    try {
                        const elapsed = Math.floor((Date.now() - startedAt) / 1000);
                        const remaining = Math.max(0, timeLimit - elapsed);
                        $el.find('.o_timer_minutes').text(String(Math.floor(remaining/60)).padStart(2,'0'));
                        $el.find('.o_timer_seconds').text(String(remaining%60).padStart(2,'0'));
                        const percent = (remaining / timeLimit) * 100;
                        $el.find('.o_timer_progress').css('width', percent + '%');
                    } catch (e) { /* ignore per-elem */ }
                }, 1000);
                $el.data('directTimerInterval', intervalId);
            } catch (err) { console.warn('directStartTimers question error', err); }
        });
    },

    /** Clear direct intervals created by _directStartTimers */
    _clearDirectTimers() {
        // General
        this.$('.o_survey_timer_general').each((i, el) => {
            try {
                const $el = $(el);
                const intervalId = $el.data('directTimerInterval');
                if (intervalId) { clearInterval(intervalId); $el.removeData('directTimerInterval'); }
                $el.removeAttr('data-direct-timer-started');
            } catch (e) { /* ignore */ }
        });
        // Questions
        this.$('.o_survey_timer_question').each((i, el) => {
            try {
                const $el = $(el);
                const intervalId = $el.data('directTimerInterval');
                if (intervalId) { clearInterval(intervalId); $el.removeData('directTimerInterval'); }
                $el.removeAttr('data-direct-timer-started');
            } catch (e) { /* ignore */ }
        });
    },
    
    /**
     * Limpiar datos de cronómetro del localStorage
     */
    _clearTimerStorage() {
        try {
            const keys = Object.keys(localStorage);
            keys.forEach((key) => {
                if (key.startsWith("survey_timer_")) {
                    localStorage.removeItem(key);
                }
                // Limpiar marca de "start clicked" también
                if (key.startsWith('survey_start_clicked_')) {
                    localStorage.removeItem(key);
                }
            });
        } catch (error) {
            console.warn("No se pudo limpiar el localStorage:", error);
        }
    },
});
