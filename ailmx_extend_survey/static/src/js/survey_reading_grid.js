// Funcionalidades actuales:
// - Render interactivo por celda (reading_grid)
// - Clic normal     -> correcta
// - Doble clic      -> error
// - Clic derecho    -> omitida
// - Contadores en tiempo real
// - Historial / trazabilidad visual
// - Serialización local en input hidden
// - Progreso actual
// - Botón de parada
// - Interceptor XHR para inyectar respuesta al submit de Odoo Survey
//   (cubre reading_grid y math_grid, incluyendo audio base64)

document.addEventListener('DOMContentLoaded', function () {

    function initReadingGrids() {
        var wrappers = document.querySelectorAll('.ailmx_reading_grid_wrapper');

        wrappers.forEach(function (wrapper) {
            if (wrapper.dataset.gridInitialized === '1') return;

            wrapper.dataset.gridInitialized = '1';
            wrapper.dataset.stopped = '0';
            wrapper.dataset.lastSelectedIndex = '';

            var cells      = wrapper.querySelectorAll('.ailmx_reading_grid_cell');
            var hiddenInput = wrapper.querySelector('.ailmx_reading_grid_response');
            var stopBtn    = wrapper.querySelector('.ailmx_grid_stop_btn');

            cells.forEach(function (cell, index) {
                cell.dataset.index = index;
                cell.dataset.state = 'empty';

                cell.addEventListener('click', function (event) {
                    event.preventDefault();
                    if (isStopped(wrapper)) return;
                    setLastSelectedCell(wrapper, cell);
                    if (cell.dataset.pendingClick === '1') return;
                    cell.dataset.pendingClick = '1';
                    setTimeout(function () {
                        if (cell.dataset.pendingClick === '1') {
                            markCell(wrapper, cell, 'ok', hiddenInput);
                        }
                        cell.dataset.pendingClick = '0';
                    }, 200);
                });

                cell.addEventListener('dblclick', function (event) {
                    event.preventDefault();
                    if (isStopped(wrapper)) return;
                    setLastSelectedCell(wrapper, cell);
                    cell.dataset.pendingClick = '0';
                    markCell(wrapper, cell, 'err', hiddenInput);
                });

                cell.addEventListener('contextmenu', function (event) {
                    event.preventDefault();
                    if (isStopped(wrapper)) return;
                    setLastSelectedCell(wrapper, cell);
                    cell.dataset.pendingClick = '0';
                    markCell(wrapper, cell, 'skip', hiddenInput);
                });
            });

            if (stopBtn) {
                stopBtn.addEventListener('click', function () {
                    if (isStopped(wrapper)) return;
                    var selectedCell = getLastSelectedCell(wrapper);
                    if (!selectedCell) return;
                    markStop(wrapper, selectedCell, hiddenInput);
                });
            }

            updateSerializedResponse(wrapper, hiddenInput);
            updateStats(wrapper);
            updateProgress(wrapper);
        });
    }

    function isStopped(wrapper) {
        return wrapper.dataset.stopped === '1';
    }

    function setLastSelectedCell(wrapper, cell) {
        wrapper.dataset.lastSelectedIndex = cell.dataset.index || '';
    }

    function getLastSelectedCell(wrapper) {
        var index = wrapper.dataset.lastSelectedIndex;
        if (index === '') return null;
        return wrapper.querySelector(
            '.ailmx_reading_grid_cell[data-index="' + index + '"]'
        );
    }

    function markCell(wrapper, cell, state, hiddenInput) {
        cell.classList.remove(
            'ailmx_cell_ok', 'ailmx_cell_err',
            'ailmx_cell_skip', 'ailmx_cell_stop', 'ailmx_cell_empty'
        );

        if (state === 'ok')        cell.classList.add('ailmx_cell_ok');
        else if (state === 'err')  cell.classList.add('ailmx_cell_err');
        else if (state === 'skip') cell.classList.add('ailmx_cell_skip');
        else                       cell.classList.add('ailmx_cell_empty');

        cell.dataset.state = state;
        updateSerializedResponse(wrapper, hiddenInput);
        updateStats(wrapper);
        updateProgress(wrapper);
        appendLog(wrapper, cell, state);
    }

    function markStop(wrapper, cell, hiddenInput) {
        cell.classList.remove(
            'ailmx_cell_ok', 'ailmx_cell_err',
            'ailmx_cell_skip', 'ailmx_cell_empty'
        );
        cell.classList.add('ailmx_cell_stop');
        cell.dataset.state = 'stop';
        wrapper.dataset.stopped = '1';

        var stopBtn = wrapper.querySelector('.ailmx_grid_stop_btn');
        if (stopBtn) stopBtn.disabled = true;

        updateSerializedResponse(wrapper, hiddenInput);
        updateStats(wrapper);
        updateProgress(wrapper);
        appendLog(wrapper, cell, 'stop');
    }

    function updateSerializedResponse(wrapper, hiddenInput) {
        if (!hiddenInput) return;

        var cells  = wrapper.querySelectorAll('.ailmx_reading_grid_cell');
        var values = [];

        cells.forEach(function (cell) {
            values.push({
                index: cell.dataset.index,
                row:   cell.dataset.row || null,
                col:   cell.dataset.col || null,
                text:  cell.innerText.trim(),
                state: cell.dataset.state || 'empty'
            });
        });

        hiddenInput.value = JSON.stringify(values);
    }

    function updateStats(wrapper) {
        var ok = 0, err = 0, skip = 0;

        wrapper.querySelectorAll('.ailmx_reading_grid_cell').forEach(function (cell) {
            if (cell.dataset.state === 'ok')        ok++;
            else if (cell.dataset.state === 'err')  err++;
            else if (cell.dataset.state === 'skip') skip++;
        });

        var okNode    = wrapper.querySelector('.stat_ok');
        var errNode   = wrapper.querySelector('.stat_err');
        var skipNode  = wrapper.querySelector('.stat_skip');
        var totalNode = wrapper.querySelector('.stat_total');

        if (okNode)    okNode.innerText    = ok;
        if (errNode)   errNode.innerText   = err;
        if (skipNode)  skipNode.innerText  = skip;
        if (totalNode) totalNode.innerText = ok + err + skip;
    }

    function updateProgress(wrapper) {
        var cells     = wrapper.querySelectorAll('.ailmx_reading_grid_cell');
        var total     = cells.length;
        var completed = 0;

        cells.forEach(function (cell) {
            if (cell.dataset.state && cell.dataset.state !== 'empty') completed++;
        });

        var currentNode = wrapper.querySelector('.ailmx_progress_current');
        var totalNode   = wrapper.querySelector('.ailmx_progress_total');

        if (currentNode) currentNode.innerText = completed;
        if (totalNode)   totalNode.innerText   = total;
    }

    function appendLog(wrapper, cell, state) {
        var log = wrapper.querySelector('.ailmx_grid_log');
        if (!log) return;

        var index  = parseInt(cell.dataset.index || '0', 10) + 1;
        var text   = cell.innerText.trim();
        var symbol = state === 'ok' ? '✔' : state === 'err' ? '✖' : state === 'skip' ? '⚠' : '⛔';

        var line = document.createElement('div');
        line.textContent = index + ' - ' + text + ' - ' + symbol;
        log.appendChild(line);
    }

    initReadingGrids();

    var surveyBody = document.querySelector('.o_survey_form_content');
    if (surveyBody) {
        new MutationObserver(initReadingGrids).observe(surveyBody, {
            childList: true,
            subtree: true
        });
    }

    // =========================================================
    // INTERCEPTOR XHR
    // Inyecta el valor del GRID (lectura o matemático) en el
    // payload del submit de Odoo Survey antes de enviarlo.
    //
    // Para reading_grid: el hidden input contiene un array JSON
    // Para math_grid:    el hidden input contiene {cells, audio}
    //   - params[questionId] recibe solo el array de celdas
    //   - params[questionId + '_audio'] recibe los datos del audio
    // =========================================================
    var OriginalXHR = window.XMLHttpRequest;

    function PatchedXHR() {
        var xhr         = new OriginalXHR();
        var originalSend = xhr.send.bind(xhr);
        var originalOpen = xhr.open.bind(xhr);
        var currentUrl   = '';

        xhr.open = function (method, url) {
            currentUrl = url;
            return originalOpen.apply(xhr, arguments);
        };

        xhr.send = function (body) {
            if (currentUrl.includes('/survey/submit/') && body) {
                try {
                    var data   = JSON.parse(body);
                    var params = data && data.params;

                    if (params) {
                        var questionId = params.question_id;

                        if (questionId) {

                            // --- Buscar reading_grid ---
                            var wrapper       = document.querySelector(
                                '.ailmx_reading_grid_wrapper[data-question-id="' + questionId + '"]'
                            );
                            var inputSelector = '.ailmx_reading_grid_response';
                            var isMathGrid    = false;

                            // --- Si no es reading_grid, buscar math_grid ---
                            if (!wrapper) {
                                wrapper       = document.querySelector(
                                    '.ailmx_math_grid_wrapper[data-question-id="' + questionId + '"]'
                                );
                                inputSelector = '.ailmx_math_grid_response';
                                isMathGrid    = true;
                            }

                            if (wrapper) {
                                var hiddenInput = wrapper.querySelector(inputSelector);

                                if (hiddenInput && hiddenInput.value) {

                                    if (isMathGrid) {
                                        // El payload de math_grid es {cells, audio}
                                        // Se envía todo junto en un solo campo para que llegue al backend
                                        try {
                                            var payload = JSON.parse(hiddenInput.value);

                                            params[String(questionId)] = JSON.stringify({
                                                cells: payload.cells || [],
                                                audio: payload.audio || { has_audio: false, base64: '', mimetype: '', filename: '' }
                                            });

                                        } catch (e) {
                                            // Si falla el parse, enviamos el valor crudo
                                            params[String(questionId)] = hiddenInput.value;
                                        }

                                    } else {
                                        // reading_grid: array directo
                                        params[String(questionId)] = hiddenInput.value;
                                    }

                                    body = JSON.stringify(data);
                                }
                            }
                        }
                    }
                } catch (e) {
                    // Si algo falla, el XHR sigue normal
                }
            }

            return originalSend.call(xhr, body);
        };

        return xhr;
    }

    PatchedXHR.prototype = OriginalXHR.prototype;
    window.XMLHttpRequest = PatchedXHR;

});