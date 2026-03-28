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
// 6. Se reinicializa cuando Odoo cambia de pregunta
// ==========================================================

document.addEventListener('DOMContentLoaded', function () {

    // Variable global del archivo para guardar el intervalo actual
    // y poder detenerlo antes de crear uno nuevo.
    var currentIntervalId = null;

    // Flag para evitar reinicializaciones múltiples simultáneas
    var isInitializingTimer = false;

    /**
     * FUNCIÓN: formatTime
     * Convierte segundos a MM:SS
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
     * FUNCIÓN PRINCIPAL: initTimer
     * Busca el contenedor y arma el cronómetro.
     */
    function initTimer() {
        // Evita que initTimer se ejecute varias veces al mismo tiempo
        if (isInitializingTimer) {
            return;
        }

        isInitializingTimer = true;

        try {
            // Primero detenemos cualquier timer anterior
            stopCurrentTimer();

            // Buscamos el contenedor del timer
            var container = document.getElementById('sispar_timer_container');

            // Si no existe, salimos silenciosamente
            if (!container) {
                return;
            }

            // Si ya fue inicializado para esta misma pregunta, no repetir
            if (container.dataset.timerInitialized === '1') {
                return;
            }

            // Leemos datos
            var timeLimit = parseInt(container.getAttribute('data-time-limit'), 10);
            var timeUnit = container.getAttribute('data-time-unit') || 'seconds';

            // Si no hay tiempo válido, ocultamos y salimos
            if (!timeLimit || timeLimit <= 0) {
                container.style.display = 'none';
                return;
            }

            // Convertimos a segundos
            var totalSeconds = (timeUnit === 'minutes') ? timeLimit * 60 : timeLimit;
            var remainingSeconds = totalSeconds;

            // Limpiamos contenido previo
            container.innerHTML = '';

            // ===== Fila del timer =====
            var timerRow = document.createElement('div');
            timerRow.className = 'sispar-timer-row';

            // SVG del reloj
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

            // Pintamos en el contenedor
            container.appendChild(timerRow);
            container.appendChild(progressWrapper);
            container.style.display = 'block';

            // Marcamos que este contenedor ya fue inicializado
            container.dataset.timerInitialized = '1';

            // ===== Iniciar countdown =====
            currentIntervalId = setInterval(function () {
                remainingSeconds--;

                // Actualiza display
                counterDisplay.textContent = formatTime(remainingSeconds);

                // Actualiza barra
                var percentage = (remainingSeconds / totalSeconds) * 100;
                if (percentage < 0) {
                    percentage = 0;
                }
                progressBar.style.width = percentage + '%';

                // Estado de alerta
                if (remainingSeconds <= 10) {
                    progressBar.classList.add('sispar-progress-danger');
                    counterDisplay.classList.add('sispar-counter-danger');
                }

                // Fin del tiempo
                if (remainingSeconds <= 0) {
                    stopCurrentTimer();
                    advanceToNextQuestion();
                }
            }, 1000);

        } finally {
            isInitializingTimer = false;
        }
    }

    /**
     * FUNCIÓN: bootTimerWhenReady
     * Espera a que el contenedor principal de la encuesta exista.
     */
    function bootTimerWhenReady() {
        var surveyBody = document.querySelector('.o_survey_form_content');

        // Si aún no existe, reintentar en breve
        if (!surveyBody) {
            setTimeout(bootTimerWhenReady, 400);
            return;
        }

        // Inicializa la primera pregunta
        initTimer();

        // Observer para cambios de pregunta
        var observer = new MutationObserver(function (mutationsList) {
            var shouldReinit = false;

            for (var i = 0; i < mutationsList.length; i++) {
                var mutation = mutationsList[i];

                // Solo nos interesan nodos agregados/eliminados
                if (mutation.type !== 'childList') {
                    continue;
                }

                // Ignoramos cambios que ocurran dentro del propio timer
                var target = mutation.target;
                if (target && target.closest && target.closest('#sispar_timer_container')) {
                    continue;
                }

                // Si se agregaron nodos reales, probablemente cambió la pregunta
                if (mutation.addedNodes && mutation.addedNodes.length > 0) {
                    shouldReinit = true;
                    break;
                }
            }

            if (shouldReinit) {
                // Pequeño delay para dejar que Odoo termine de renderizar
                setTimeout(function () {
                    initTimer();
                }, 100);
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