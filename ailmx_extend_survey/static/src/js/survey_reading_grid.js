document.addEventListener('DOMContentLoaded', function () {

    function initReadingGrids() {
        var wrappers = document.querySelectorAll('.ailmx_reading_grid_wrapper');

        wrappers.forEach(function (wrapper) {
            if (wrapper.dataset.gridInitialized === '1') return;

            wrapper.dataset.gridInitialized = '1';
            wrapper.dataset.currentIndex = '0';
            wrapper.dataset.stopped = '0';

            var cells = wrapper.querySelectorAll('.ailmx_reading_grid_cell');
            var hiddenInput = wrapper.querySelector('.ailmx_reading_grid_response');
            var stopBtn = wrapper.querySelector('.ailmx_grid_stop_btn');

            cells.forEach(function (cell, index) {

                cell.dataset.index = index;
                cell.dataset.state = 'empty';

                if (index === 0) {
                    cell.classList.add('ailmx_cell_active');
                }

                // CLICK NORMAL
                cell.addEventListener('click', function (e) {
                    e.preventDefault();

                    if (isStopped(wrapper)) return;
                    if (!isCurrentCell(wrapper, cell)) return;

                    if (cell.dataset.pendingClick === '1') return;

                    cell.dataset.pendingClick = '1';

                    setTimeout(function () {
                        if (cell.dataset.pendingClick === '1') {
                            markCell(wrapper, cell, 'ok', hiddenInput);
                        }
                        cell.dataset.pendingClick = '0';
                    }, 200);
                });

                // DOBLE CLICK
                cell.addEventListener('dblclick', function (e) {
                    e.preventDefault();

                    if (isStopped(wrapper)) return;
                    if (!isCurrentCell(wrapper, cell)) return;

                    cell.dataset.pendingClick = '0';
                    markCell(wrapper, cell, 'err', hiddenInput);
                });

                // CLICK DERECHO
                cell.addEventListener('contextmenu', function (e) {
                    e.preventDefault();

                    if (isStopped(wrapper)) return;
                    if (!isCurrentCell(wrapper, cell)) return;

                    cell.dataset.pendingClick = '0';
                    markCell(wrapper, cell, 'skip', hiddenInput);
                });
            });

            // BOTÓN PARADA
            if (stopBtn) {
                stopBtn.addEventListener('click', function () {

                    if (isStopped(wrapper)) return;

                    var currentCell = getCurrentCell(wrapper);
                    if (!currentCell) return;

                    markStop(wrapper, currentCell, hiddenInput);
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

    function isCurrentCell(wrapper, cell) {
        return parseInt(wrapper.dataset.currentIndex) === parseInt(cell.dataset.index);
    }

    function getCurrentCell(wrapper) {
        var index = wrapper.dataset.currentIndex;
        return wrapper.querySelector('.ailmx_reading_grid_cell[data-index="' + index + '"]');
    }

    /**
     * MARCAR CELDA (CORREGIDO)
     */
    function markCell(wrapper, cell, state, hiddenInput) {

        // LIMPIAR TODAS LAS CLASES DE ESTADO
        cell.classList.remove(
            'ailmx_cell_ok',
            'ailmx_cell_err',
            'ailmx_cell_skip',
            'ailmx_cell_stop',
            'ailmx_cell_active',
            'ailmx_cell_empty'
        );

        // ASIGNAR NUEVO ESTADO
        if (state === 'ok') {
            cell.classList.add('ailmx_cell_ok');
        } else if (state === 'err') {
            cell.classList.add('ailmx_cell_err');
        } else if (state === 'skip') {
            cell.classList.add('ailmx_cell_skip');
        }

        cell.dataset.state = state;

        // AVANZAR
        var nextIndex = parseInt(wrapper.dataset.currentIndex) + 1;
        wrapper.dataset.currentIndex = nextIndex;

        var nextCell = wrapper.querySelector(
            '.ailmx_reading_grid_cell[data-index="' + nextIndex + '"]'
        );

        if (nextCell) {
            nextCell.classList.add('ailmx_cell_active');
        }

        updateSerializedResponse(wrapper, hiddenInput);
        updateStats(wrapper);
        updateProgress(wrapper);
        appendLog(wrapper, cell, state);
    }

    /**
     * PARADA
     */
    function markStop(wrapper, cell, hiddenInput) {

        cell.classList.remove(
            'ailmx_cell_ok',
            'ailmx_cell_err',
            'ailmx_cell_skip',
            'ailmx_cell_active'
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

        var cells = wrapper.querySelectorAll('.ailmx_reading_grid_cell');
        var values = [];

        cells.forEach(function (cell) {
            values.push({
                index: cell.dataset.index,
                text: cell.innerText.trim(),
                state: cell.dataset.state
            });
        });

        hiddenInput.value = JSON.stringify(values);
    }

    function updateStats(wrapper) {

        var ok = 0, err = 0, skip = 0;

        wrapper.querySelectorAll('.ailmx_reading_grid_cell').forEach(function (cell) {

            if (cell.dataset.state === 'ok') ok++;
            else if (cell.dataset.state === 'err') err++;
            else if (cell.dataset.state === 'skip') skip++;

        });

        wrapper.querySelector('.stat_ok').innerText = ok;
        wrapper.querySelector('.stat_err').innerText = err;
        wrapper.querySelector('.stat_skip').innerText = skip;
        wrapper.querySelector('.stat_total').innerText = ok + err + skip;
    }

    function updateProgress(wrapper) {

        var total = wrapper.querySelectorAll('.ailmx_reading_grid_cell').length;
        var current = parseInt(wrapper.dataset.currentIndex) + 1;

        if (current > total) current = total;

        wrapper.querySelector('.ailmx_progress_current').innerText = current;
        wrapper.querySelector('.ailmx_progress_total').innerText = total;
    }

    function appendLog(wrapper, cell, state) {

        var log = wrapper.querySelector('.ailmx_grid_log');
        if (!log) return;

        var index = parseInt(cell.dataset.index) + 1;
        var text = cell.innerText.trim();

        var symbol = {
            ok: '✔',
            err: '✖',
            skip: '⚠',
            stop: '⛔'
        }[state];

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
});