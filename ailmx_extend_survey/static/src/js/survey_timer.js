// ==========================================================
// AILUMEX - Timer por pregunta en encuestas
// Archivo: static/src/js/survey_timer.js
//
// Este script:
// 1. Busca el contenedor del timer en la pregunta actual
// 2. Lee data-time-limit y data-time-unit
// 3. Construye el cronómetro visual
// 4. Hace cuenta regresiva
// 5. Avanza automáticamente cuando llega a 0
// 6. Solo se reinicializa cuando realmente cambia la pregunta
// ==========================================================

document.addEventListener('DOMContentLoaded', function () {

    // Intervalo actualmente activo
    var currentIntervalId = null;

    // Referencia al contenedor del timer actualmente inicializado
    var currentTimerContainer = null;

    // Evita dobles inicializaciones simultáneas
    var isInitializingTimer = false;

    /**
     * FUNCIÓN: formatTime
     * Convierte segundos a formato MM:SS
     */
    function formatTime(seconds) {
        if (seconds < 0) {
            seconds = 0;
        }

        var mins = Math.floor(seconds / 60);
        var secs = seconds % 60;

        return mins + ':' + (secs < 10 ? '0' : '') + secs;
    }

    /**
     * FUNCIÓN: stopCurrentTimer
     * Detiene el intervalo actual si existe.
     */
    function stopCurrentTimer() {
        if (currentIntervalId) {
            clearInterval(currentIntervalId);
            currentIntervalId = null;
        }
    }

    /**
     * FUNCIÓN: advanceToNextQuestion
     * Simula clic en siguiente / enviar de la pregunta
     */
    function advanceToNextQuestion() {
        var nextBtn = document.querySelector('.o_survey_navigation_submit');

        if (nextBtn) {
            setTimeout(function () {
                nextBtn.click();
            }, 200);
            return;
        }

        var surveyForm = document.querySelector('.o_survey_form_content');
        if (surveyForm) {
            var submitBtn = surveyForm.querySelector('button[type="submit"]');
            if (submitBtn) {
                setTimeout(function () {
                    submitBtn.click();
                }, 200);
            }
        }
    }

    /**
     * FUNCIÓN: initTimer
     * Inicializa el cronómetro para un contenedor específico.
     *
     * IMPORTANTE:
     * Solo reinicializa si el contenedor cambió realmente.
     */
    function initTimer(container) {
        if (isInitializingTimer) {
            return;
        }

        if (!container) {
            return;
        }

        // Si estamos viendo exactamente el mismo contenedor que ya estaba activo,
        // no hacemos nada. Esto evita que un clic, datepicker o cambio menor
        // mate el timer actual.
        if (currentTimerContainer === container) {
            return;
        }

        isInitializingTimer = true;

        try {
            // Como sí cambió el contenedor/pregunta, detenemos el timer anterior
            stopCurrentTimer();

            // Leemos los datos del temporizador
            var timeLimit = parseInt(container.getAttribute('data-time-limit'), 10);
            var timeUnit = container.getAttribute('data-time-unit') || 'seconds';

            // Si el valor no es válido, ocultamos el contenedor
            if (!timeLimit || timeLimit <= 0) {
                container.style.display = 'none';
                currentTimerContainer = null;
                return;
            }

            // Convertimos a segundos
            var totalSeconds = (timeUnit === 'minutes') ? timeLimit * 60 : timeLimit;
            var remainingSeconds = totalSeconds;

            // Limpiamos contenido anterior
            container.innerHTML = '';

            // ===== Fila superior =====
            var timerRow = document.createElement('div');
            timerRow.className = 'sispar-timer-row';

            // Ícono SVG
            var iconSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            iconSvg.setAttribute('viewBox', '0 0 24 24');
            iconSvg.setAttribute('width', '20');
            iconSvg.setAttribute('height', '20');
            iconSvg.setAttribute('fill', 'none');
            iconSvg.setAttribute('stroke', 'currentColor');
            iconSvg.setAttribute('stroke-width', '2');
            iconSvg.setAttribute('stroke-linecap', 'round');
            iconSvg.setAttribute('stroke-linejoin', 'round');
            iconSvg.setAttribute('class', 'sispar-timer-icon');
            iconSvg.innerHTML = '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>';

            // Display del contador
            var counterDisplay = document.createElement('span');
            counterDisplay.className = 'sispar-timer-display';
            counterDisplay.textContent = formatTime(remainingSeconds);

            // Label
            var labelText = document.createElement('span');
            labelText.className = 'sispar-timer-label';
            labelText.textContent = 'Tiempo restante';

            timerRow.appendChild(iconSvg);
            timerRow.appendChild(counterDisplay);
            timerRow.appendChild(labelText);

            // ===== Barra de progreso =====
            var progressWrapper = document.createElement('div');
            progressWrapper.className = 'sispar-progress-wrapper';

            var progressBar = document.createElement('div');
            progressBar.className = 'sispar-progress-bar';
            progressBar.style.width = '100%';

            progressWrapper.appendChild(progressBar);

            // Renderizar timer
            container.appendChild(timerRow);
            container.appendChild(progressWrapper);
            container.style.display = 'block';

            // Guardamos referencia al contenedor actual
            currentTimerContainer = container;

            // ===== Iniciar countdown =====
            currentIntervalId = setInterval(function () {
                remainingSeconds--;

                // Actualiza texto
                counterDisplay.textContent = formatTime(remainingSeconds);

                // Actualiza barra
                var percentage = (remainingSeconds / totalSeconds) * 100;
                if (percentage < 0) {
                    percentage = 0;
                }
                progressBar.style.width = percentage + '%';

                // Estado crítico cuando quedan 10 segundos o menos
                if (remainingSeconds <= 10) {
                    progressBar.classList.add('sispar-progress-danger');
                    counterDisplay.classList.add('sispar-counter-danger');
                }

                // Fin del tiempo
                if (remainingSeconds <= 0) {
                    stopCurrentTimer();
                    currentTimerContainer = null;
                    advanceToNextQuestion();
                }
            }, 1000);

        } finally {
            isInitializingTimer = false;
        }
    }

    /**
     * FUNCIÓN: getCurrentTimerContainer
     * Busca el contenedor actual del timer en el DOM.
     */
    function getCurrentTimerContainer() {
        return document.getElementById('sispar_timer_container');
    }

    /**
     * FUNCIÓN: bootTimerWhenReady
     * Espera a que exista el cuerpo de la encuesta y monta el observer.
     */
    function bootTimerWhenReady() {
        var surveyBody = document.querySelector('.o_survey_form_content');

        if (!surveyBody) {
            setTimeout(bootTimerWhenReady, 400);
            return;
        }

        // Inicialización inicial
        initTimer(getCurrentTimerContainer());

        // Observer para detectar cambios reales de pregunta
        var observer = new MutationObserver(function () {
            var newContainer = getCurrentTimerContainer();

            // Solo reinicializar si apareció un contenedor distinto al actual
            if (newContainer && newContainer !== currentTimerContainer) {
                setTimeout(function () {
                    initTimer(newContainer);
                }, 100);
            }

            // Si ya no hay contenedor, limpiamos referencia e intervalo
            if (!newContainer && currentTimerContainer) {
                stopCurrentTimer();
                currentTimerContainer = null;
            }
        });

        observer.observe(surveyBody, {
            childList: true,
            subtree: true
        });
    }

    // Arranque principal
    bootTimerWhenReady();
});