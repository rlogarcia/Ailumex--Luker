
// Funcionalidades actuales:
// - Render interactivo por celda
// - Clic normal     -> correcta
// - Doble clic      -> error
// - Clic derecho    -> omitida
// - Contadores en tiempo real
// - Historial / trazabilidad visual
// - Serialización local en input hidden
// - Progreso actual
// - Botón de parada

document.addEventListener('DOMContentLoaded', function () {

    /**
     * Inicializa todas las grillas de lectura presentes en la página.
     */
    function initReadingGrids() {
        var wrappers = document.querySelectorAll('.ailmx_reading_grid_wrapper');

        wrappers.forEach(function (wrapper) {
            if (wrapper.dataset.gridInitialized === '1') {
                return;
            }

            wrapper.dataset.gridInitialized = '1';
            wrapper.dataset.stopped = '0';
            wrapper.dataset.lastSelectedIndex = '';

            var cells = wrapper.querySelectorAll('.ailmx_reading_grid_cell');
            var hiddenInput = wrapper.querySelector('.ailmx_reading_grid_response');
            var stopBtn = wrapper.querySelector('.ailmx_grid_stop_btn');

            cells.forEach(function (cell, index) {
                // Guardamos índice y estado inicial
                cell.dataset.index = index;
                cell.dataset.state = 'empty';

                // ======================================================
                // CLIC NORMAL -> CORRECTA
                // ======================================================
                cell.addEventListener('click', function (event) {
                    event.preventDefault();

                    if (isStopped(wrapper)) {
                        return;
                    }

                    // Guardamos esta celda como la última seleccionada
                    setLastSelectedCell(wrapper, cell);

                    // Evitamos conflicto entre click y dblclick
                    if (cell.dataset.pendingClick === '1') {
                        return;
                    }

                    cell.dataset.pendingClick = '1';

                    setTimeout(function () {
                        // Si sigue pendiente, fue clic simple
                        if (cell.dataset.pendingClick === '1') {
                            markCell(wrapper, cell, 'ok', hiddenInput);
                        }

                        cell.dataset.pendingClick = '0';
                    }, 200);
                });

                // ======================================================
                // DOBLE CLIC -> ERROR
                // ======================================================
                cell.addEventListener('dblclick', function (event) {
                    event.preventDefault();

                    if (isStopped(wrapper)) {
                        return;
                    }

                    // Guardamos esta celda como la última seleccionada
                    setLastSelectedCell(wrapper, cell);

                    // Cancelamos el clic simple pendiente
                    cell.dataset.pendingClick = '0';

                    markCell(wrapper, cell, 'err', hiddenInput);
                });

                // ======================================================
                // CLIC DERECHO -> OMITIDA
                // ======================================================
                cell.addEventListener('contextmenu', function (event) {
                    event.preventDefault();

                    if (isStopped(wrapper)) {
                        return;
                    }

                    // Guardamos esta celda como la última seleccionada
                    setLastSelectedCell(wrapper, cell);

                    // Cancelamos clic simple pendiente si existía
                    cell.dataset.pendingClick = '0';

                    markCell(wrapper, cell, 'skip', hiddenInput);
                });
            });

            // ==========================================================
            // BOTÓN PARADA
            // Marca como parada la última celda sobre la que el usuario
            // haya interactuado.
            // ==========================================================
            if (stopBtn) {
                stopBtn.addEventListener('click', function () {
                    if (isStopped(wrapper)) {
                        return;
                    }

                    var selectedCell = getLastSelectedCell(wrapper);

                    // Si todavía no se ha tocado ninguna celda, no hacemos nada
                    if (!selectedCell) {
                        return;
                    }

                    markStop(wrapper, selectedCell, hiddenInput);
                });
            }

            // Inicializamos visuales
            updateSerializedResponse(wrapper, hiddenInput);
            updateStats(wrapper);
            updateProgress(wrapper);
        });
    }

    /**
     * Indica si la grilla está detenida.
     */
    function isStopped(wrapper) {
        return wrapper.dataset.stopped === '1';
    }

    /**
     * Guarda la última celda con la que el usuario interactuó.
     */
    function setLastSelectedCell(wrapper, cell) {
        wrapper.dataset.lastSelectedIndex = cell.dataset.index || '';
    }

    /**
     * Recupera la última celda seleccionada/interactuada.
     */
    function getLastSelectedCell(wrapper) {
        var index = wrapper.dataset.lastSelectedIndex;
        if (index === '') {
            return null;
        }

        return wrapper.querySelector(
            '.ailmx_reading_grid_cell[data-index="' + index + '"]'
        );
    }

    /**
     * Marca una celda con un estado específico.
     * Esta versión NO avanza automáticamente a otra celda.
     */
    function markCell(wrapper, cell, state, hiddenInput) {
        // Limpiar estados visuales previos
        cell.classList.remove(
            'ailmx_cell_ok',
            'ailmx_cell_err',
            'ailmx_cell_skip',
            'ailmx_cell_stop',
            'ailmx_cell_empty'
        );

        // Asignar nuevo estado
        if (state === 'ok') {
            cell.classList.add('ailmx_cell_ok');
        } else if (state === 'err') {
            cell.classList.add('ailmx_cell_err');
        } else if (state === 'skip') {
            cell.classList.add('ailmx_cell_skip');
        } else {
            cell.classList.add('ailmx_cell_empty');
        }

        cell.dataset.state = state;

        updateSerializedResponse(wrapper, hiddenInput);
        updateStats(wrapper);
        updateProgress(wrapper);
        appendLog(wrapper, cell, state);
    }

    /**
     * Marca una celda como parada y bloquea la grilla.
     */
    function markStop(wrapper, cell, hiddenInput) {
        // Limpiar estados previos de esa celda
        cell.classList.remove(
            'ailmx_cell_ok',
            'ailmx_cell_err',
            'ailmx_cell_skip',
            'ailmx_cell_empty'
        );

        // Marcar estado stop
        cell.classList.add('ailmx_cell_stop');
        cell.dataset.state = 'stop';

        // La grilla queda detenida
        wrapper.dataset.stopped = '1';

        // Desactivar botón de parada
        var stopBtn = wrapper.querySelector('.ailmx_grid_stop_btn');
        if (stopBtn) {
            stopBtn.disabled = true;
        }

        updateSerializedResponse(wrapper, hiddenInput);
        updateStats(wrapper);
        updateProgress(wrapper);
        appendLog(wrapper, cell, 'stop');
    }

    /**
     * Serializa el estado actual de toda la grilla
     * y lo guarda en el input oculto local.
     */
    function updateSerializedResponse(wrapper, hiddenInput) {
        if (!hiddenInput) {
            return;
        }

        var cells = wrapper.querySelectorAll('.ailmx_reading_grid_cell');
        var values = [];

        cells.forEach(function (cell) {
            values.push({
                index: cell.dataset.index,
                row: cell.dataset.row || null,
                col: cell.dataset.col || null,
                text: cell.innerText.trim(),
                state: cell.dataset.state || 'empty'
            });
        });

        hiddenInput.value = JSON.stringify(values);
    }

    /**
     * Actualiza contadores visuales:
     * correctas, errores, omitidas y total.
     */
    function updateStats(wrapper) {
        var ok = 0;
        var err = 0;
        var skip = 0;

        var cells = wrapper.querySelectorAll('.ailmx_reading_grid_cell');

        cells.forEach(function (cell) {
            var state = cell.dataset.state;

            if (state === 'ok') {
                ok++;
            } else if (state === 'err') {
                err++;
            } else if (state === 'skip') {
                skip++;
            }
        });

        var okNode = wrapper.querySelector('.stat_ok');
        var errNode = wrapper.querySelector('.stat_err');
        var skipNode = wrapper.querySelector('.stat_skip');
        var totalNode = wrapper.querySelector('.stat_total');

        if (okNode) {
            okNode.innerText = ok;
        }
        if (errNode) {
            errNode.innerText = err;
        }
        if (skipNode) {
            skipNode.innerText = skip;
        }
        if (totalNode) {
            totalNode.innerText = ok + err + skip;
        }
    }

    /**
     * Actualiza el progreso actual.
     *
     * Ahora ya no muestra "siguiente celda obligatoria",
     * sino cuántas celdas han sido marcadas frente al total.
     */
    function updateProgress(wrapper) {
        var cells = wrapper.querySelectorAll('.ailmx_reading_grid_cell');
        var total = cells.length;
        var completed = 0;

        cells.forEach(function (cell) {
            var state = cell.dataset.state;
            if (state && state !== 'empty') {
                completed++;
            }
        });

        var currentNode = wrapper.querySelector('.ailmx_progress_current');
        var totalNode = wrapper.querySelector('.ailmx_progress_total');

        if (currentNode) {
            currentNode.innerText = completed;
        }

        if (totalNode) {
            totalNode.innerText = total;
        }
    }

    /**
     * Agrega una línea al historial / trazabilidad visual.
     */
    function appendLog(wrapper, cell, state) {
        var log = wrapper.querySelector('.ailmx_grid_log');
        if (!log) {
            return;
        }

        var index = parseInt(cell.dataset.index || '0', 10) + 1;
        var text = cell.innerText.trim();

        var symbol = '';
        if (state === 'ok') {
            symbol = '✔';
        } else if (state === 'err') {
            symbol = '✖';
        } else if (state === 'skip') {
            symbol = '⚠';
        } else if (state === 'stop') {
            symbol = '⛔';
        }

        var line = document.createElement('div');
        line.textContent = index + ' - ' + text + ' - ' + symbol;

        log.appendChild(line);
    }

    /**
     * Inicialización inicial.
     */
    initReadingGrids();

    /**
     * Si Odoo cambia de pregunta dinámicamente,
     * volvemos a revisar si hay nuevas grillas.
     */
    var surveyBody = document.querySelector('.o_survey_form_content');

    if (surveyBody) {
        new MutationObserver(initReadingGrids).observe(surveyBody, {
            childList: true,
            subtree: true
        });
    }

    // Interceptar el submit XHR de Odoo Survey para inyectar el valor del GRID
    var OriginalXHR = window.XMLHttpRequest;

    function PatchedXHR() {
        var xhr = new OriginalXHR();
        var originalSend = xhr.send.bind(xhr);
        var originalOpen = xhr.open.bind(xhr);
        var currentUrl = '';

        xhr.open = function (method, url) {
            currentUrl = url;
            return originalOpen.apply(xhr, arguments);
        };

        xhr.send = function (body) {
            if (currentUrl.includes('/survey/submit/') && body) {
                try {
                    var data = JSON.parse(body);
                    var params = data && data.params;

                    if (params) {
                        var questionId = params.question_id;

                        if (questionId) {
                            var wrapper = document.querySelector(
                                '.ailmx_reading_grid_wrapper[data-question-id="' + questionId + '"]'
                            );

                            if (wrapper) {
                                var hiddenInput = wrapper.querySelector('.ailmx_reading_grid_response');

                                if (hiddenInput && hiddenInput.value) {
                                    params[String(questionId)] = hiddenInput.value;
                                    body = JSON.stringify(data);
                                }
                            }
                        }
                    }
                } catch (e) {
                }
            }

            return originalSend.call(xhr, body);
        };

        return xhr;
    }

    PatchedXHR.prototype = OriginalXHR.prototype;
    window.XMLHttpRequest = PatchedXHR;
});