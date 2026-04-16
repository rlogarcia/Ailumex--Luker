// Funcionalidades actuales:
// - Render interactivo por celda (reading_grid)
// - Click -> marcar / desmarcar
// - Contadores en tiempo real
// - Historial / trazabilidad visual
// - Serialización local en input hidden
// - Progreso actual
// - Interceptor XHR para inyectar respuesta al submit de Odoo Survey
//   (cubre reading_grid y math_grid, incluyendo audio base64)

document.addEventListener('DOMContentLoaded', function () {

    function initReadingGrids() {
        var wrappers = document.querySelectorAll('.ailmx_reading_grid_wrapper');

        wrappers.forEach(function (wrapper) {
            if (wrapper.dataset.gridInitialized === '1') return;

            wrapper.dataset.gridInitialized = '1';

            var cells = wrapper.querySelectorAll('.ailmx_reading_grid_cell');
            var hiddenInput = wrapper.querySelector('.ailmx_reading_grid_response');

            cells.forEach(function (cell, index) {
                cell.dataset.index = index;
                cell.dataset.state = 'empty';

                cell.addEventListener('click', function (event) {
                    event.preventDefault();
                    toggleCell(wrapper, cell, hiddenInput);
                });

                cell.addEventListener('contextmenu', function (event) {
                    event.preventDefault();
                });

                cell.addEventListener('dblclick', function (event) {
                    event.preventDefault();
                });
            });

            updateSerializedResponse(wrapper, hiddenInput);
            updateStats(wrapper);
            updateProgress(wrapper);
        });
    }

    function toggleCell(wrapper, cell, hiddenInput) {
        var newState = cell.dataset.state === 'selected' ? 'empty' : 'selected';
        setCellState(cell, newState);
        updateSerializedResponse(wrapper, hiddenInput);
        updateStats(wrapper);
        updateProgress(wrapper);
        appendLog(wrapper, cell, newState);
    }

    function setCellState(cell, state) {
        cell.classList.remove('ailmx_cell_selected', 'ailmx_cell_empty');

        if (state === 'selected') {
            cell.classList.add('ailmx_cell_selected');
        } else {
            cell.classList.add('ailmx_cell_empty');
        }

        cell.dataset.state = state;
    }

    function updateSerializedResponse(wrapper, hiddenInput) {
        if (!hiddenInput) return;

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

    function updateStats(wrapper) {
        var totalCells = wrapper.querySelectorAll('.ailmx_reading_grid_cell').length;
        var selected = 0;

        wrapper.querySelectorAll('.ailmx_reading_grid_cell').forEach(function (cell) {
            if (cell.dataset.state === 'selected') {
                selected++;
            }
        });

        var unselected = totalCells - selected;

        var selectedNode = wrapper.querySelector('.stat_selected');
        var unselectedNode = wrapper.querySelector('.stat_unselected');
        var totalNode = wrapper.querySelector('.stat_total');

        if (selectedNode) selectedNode.innerText = selected;
        if (unselectedNode) unselectedNode.innerText = unselected;
        if (totalNode) totalNode.innerText = selected;
    }

    function updateProgress(wrapper) {
        var cells = wrapper.querySelectorAll('.ailmx_reading_grid_cell');
        var total = cells.length;
        var completed = 0;

        cells.forEach(function (cell) {
            if (cell.dataset.state === 'selected') {
                completed++;
            }
        });

        var currentNode = wrapper.querySelector('.ailmx_progress_current');
        var totalNode = wrapper.querySelector('.ailmx_progress_total');

        if (currentNode) currentNode.innerText = completed;
        if (totalNode) totalNode.innerText = total;
    }

    function appendLog(wrapper, cell, state) {
        var log = wrapper.querySelector('.ailmx_grid_log');
        if (!log) return;

        var index = parseInt(cell.dataset.index || '0', 10) + 1;
        var text = cell.innerText.trim();
        var action = state === 'selected' ? 'Marcada' : 'Desmarcada';

        var line = document.createElement('div');
        line.textContent = index + ' - ' + text + ' - ' + action;
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
                            var inputSelector = '.ailmx_reading_grid_response';
                            var isMathGrid = false;

                            if (!wrapper) {
                                wrapper = document.querySelector(
                                    '.ailmx_math_grid_wrapper[data-question-id="' + questionId + '"]'
                                );
                                inputSelector = '.ailmx_math_grid_response';
                                isMathGrid = true;
                            }

                            if (wrapper) {
                                var hiddenInput = wrapper.querySelector(inputSelector);

                                if (hiddenInput && hiddenInput.value) {
                                    if (isMathGrid) {
                                        try {
                                            var payload = JSON.parse(hiddenInput.value);

                                            params[String(questionId)] = JSON.stringify({
                                                cells: payload.cells || [],
                                                audio: payload.audio || {
                                                    has_audio: false,
                                                    base64: '',
                                                    mimetype: '',
                                                    filename: ''
                                                }
                                            });

                                        } catch (e) {
                                            params[String(questionId)] = hiddenInput.value;
                                        }

                                    } else {
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