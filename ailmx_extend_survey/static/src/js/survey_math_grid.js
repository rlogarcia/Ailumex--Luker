document.addEventListener('DOMContentLoaded', function () {

    function initMathGrids() {
        var wrappers = document.querySelectorAll('.ailmx_math_grid_wrapper');

        wrappers.forEach(function (wrapper) {
            if (wrapper.dataset.gridInitialized === '1') return;

            wrapper.dataset.gridInitialized = '1';

            var cells = wrapper.querySelectorAll('.ailmx_math_grid_cell');
            var hiddenInput = wrapper.querySelector('.ailmx_math_grid_response');

            cells.forEach(function (cell, index) {
                cell.dataset.index = index;
                cell.dataset.state = cell.dataset.state || 'empty';

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

        var cells = wrapper.querySelectorAll('.ailmx_math_grid_cell');
        var cellValues = [];

        cells.forEach(function (cell, index) {
            cellValues.push({
                index: String(index),
                row: cell.getAttribute('data-row'),
                col: cell.getAttribute('data-col'),
                text: cell.textContent.trim(),
                correct: cell.getAttribute('data-correct') || '',
                state: cell.dataset.state || 'empty'
            });
        });

        // Mantener estructura histórica estable para backend/app
        var payload = {
            cells: cellValues,
            audio: {
                has_audio: false,
                base64: '',
                mimetype: '',
                filename: ''
            }
        };

        hiddenInput.value = JSON.stringify(payload);
    }

    function updateStats(wrapper) {
        var totalCells = wrapper.querySelectorAll('.ailmx_math_grid_cell').length;
        var selected = 0;

        wrapper.querySelectorAll('.ailmx_math_grid_cell').forEach(function (cell) {
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
        var cells = wrapper.querySelectorAll('.ailmx_math_grid_cell');
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

    initMathGrids();

    var surveyBody = document.querySelector('.o_survey_form_content');
    if (surveyBody) {
        new MutationObserver(initMathGrids).observe(surveyBody, {
            childList: true,
            subtree: true
        });
    }

});