// AILUMEX - GRID matemático
// Funcionalidades:
// - Clic normal     -> correcta
// - Doble clic      -> error
// - Clic derecho    -> omitida
// - Botón parada    -> marca parada y bloquea
// NOTA:
// En esta versión el audio NO se envía al backend todavía.
// Primero estabilizamos el guardado del grid matemático igual que reading_grid.

document.addEventListener('DOMContentLoaded', function () {

    function initMathGrids() {
        var wrappers = document.querySelectorAll('.ailmx_math_grid_wrapper');

        wrappers.forEach(function (wrapper) {
            if (wrapper.dataset.gridInitialized === '1') return;

            wrapper.dataset.gridInitialized = '1';
            wrapper.dataset.stopped = '0';
            wrapper.dataset.lastSelectedIndex = '';

            var cells = wrapper.querySelectorAll('.ailmx_math_grid_cell');
            var hiddenInput = wrapper.querySelector('.ailmx_math_grid_response');
            var stopBtn = wrapper.querySelector('.ailmx_grid_stop_btn');

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

            // El grabador puede quedarse visualmente,
            // pero por ahora NO persiste en backend.
            initAudioRecorder(wrapper);
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
        return wrapper.querySelector('.ailmx_math_grid_cell[data-index="' + index + '"]');
    }

    function markCell(wrapper, cell, state, hiddenInput) {
        cell.classList.remove(
            'ailmx_cell_ok', 'ailmx_cell_err',
            'ailmx_cell_skip', 'ailmx_cell_stop', 'ailmx_cell_empty'
        );

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

        var cells = wrapper.querySelectorAll('.ailmx_math_grid_cell');
        var values = [];

        cells.forEach(function (cell) {
            values.push({
                index: cell.dataset.index,
                row: cell.getAttribute('data-row'),
                col: cell.getAttribute('data-col'),
                text: cell.innerText.trim(),
                correct: cell.getAttribute('data-correct') || '',
                state: cell.dataset.state || 'empty'
            });
        });

        hiddenInput.value = JSON.stringify(values);
    }

    function updateStats(wrapper) {
        var ok = 0, err = 0, skip = 0;

        wrapper.querySelectorAll('.ailmx_math_grid_cell').forEach(function (cell) {
            if (cell.dataset.state === 'ok') ok++;
            else if (cell.dataset.state === 'err') err++;
            else if (cell.dataset.state === 'skip') skip++;
        });

        var okNode = wrapper.querySelector('.stat_ok');
        var errNode = wrapper.querySelector('.stat_err');
        var skipNode = wrapper.querySelector('.stat_skip');
        var totalNode = wrapper.querySelector('.stat_total');

        if (okNode) okNode.innerText = ok;
        if (errNode) errNode.innerText = err;
        if (skipNode) skipNode.innerText = skip;
        if (totalNode) totalNode.innerText = ok + err + skip;
    }

    function updateProgress(wrapper) {
        var cells = wrapper.querySelectorAll('.ailmx_math_grid_cell');
        var total = cells.length;
        var completed = 0;

        cells.forEach(function (cell) {
            if (cell.dataset.state && cell.dataset.state !== 'empty') completed++;
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
        var symbol = state === 'ok' ? '✔' : state === 'err' ? '✖' : state === 'skip' ? '⚠' : '⛔';

        var line = document.createElement('div');
        line.textContent = index + ' - ' + text + ' - ' + symbol;
        log.appendChild(line);
    }

    function initAudioRecorder(wrapper) {
        var recorderPanel = wrapper.querySelector('.ailmx_audio_recorder');
        if (!recorderPanel) return;

        var btnRecord = recorderPanel.querySelector('.ailmx_btn_record');
        var btnStop = recorderPanel.querySelector('.ailmx_btn_stop');
        var btnPlay = recorderPanel.querySelector('.ailmx_btn_play');
        var btnDelete = recorderPanel.querySelector('.ailmx_btn_delete');
        var statusEl = recorderPanel.querySelector('.ailmx_rec_status');
        var timerEl = recorderPanel.querySelector('.ailmx_rec_timer');
        var waveEl = recorderPanel.querySelector('.ailmx_rec_wave');
        var audioEl = recorderPanel.querySelector('.ailmx_audio_playback');

        var mediaRecorder = null;
        var audioChunks = [];
        var audioBlob = null;
        var timerInterval = null;
        var seconds = 0;

        setState('idle');

        btnRecord.addEventListener('click', function () {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                setStatus('Tu navegador no soporta grabación de audio.', 'error');
                return;
            }

            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(function (stream) {
                    audioChunks = [];
                    audioBlob = null;
                    seconds = 0;

                    mediaRecorder = new MediaRecorder(stream);

                    mediaRecorder.ondataavailable = function (e) {
                        if (e.data && e.data.size > 0) {
                            audioChunks.push(e.data);
                        }
                    };

                    mediaRecorder.onstop = function () {
                        audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                        var url = URL.createObjectURL(audioBlob);
                        audioEl.src = url;

                        stream.getTracks().forEach(function (t) { t.stop(); });

                        setState('recorded');
                        setStatus('Grabación local lista. Aún no se guarda en backend.', 'ok');
                        stopTimer();
                    };

                    mediaRecorder.start(100);
                    setState('recording');
                    setStatus('Grabando...', 'recording');
                    startTimer();
                })
                .catch(function (err) {
                    setStatus('No se pudo acceder al micrófono: ' + err.message, 'error');
                });
        });

        btnStop.addEventListener('click', function () {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
        });

        btnPlay.addEventListener('click', function () {
            if (audioEl.src) {
                audioEl.play();
                setStatus('Reproduciendo...', 'ok');
                audioEl.onended = function () {
                    setStatus('Grabación local lista.', 'ok');
                };
            }
        });

        btnDelete.addEventListener('click', function () {
            audioBlob = null;
            audioChunks = [];
            audioEl.src = '';
            seconds = 0;

            setState('idle');
            setStatus('Grabación eliminada.', '');
            updateTimerDisplay(0);
        });

        function setState(state) {
            btnRecord.style.display = (state === 'idle' || state === 'recorded') ? 'inline-flex' : 'none';
            btnStop.style.display = (state === 'recording') ? 'inline-flex' : 'none';
            btnPlay.style.display = (state === 'recorded') ? 'inline-flex' : 'none';
            btnDelete.style.display = (state === 'recorded') ? 'inline-flex' : 'none';
            waveEl.style.display = (state === 'recording') ? 'flex' : 'none';

            if (state === 'idle') {
                setStatus('Presiona grabar para iniciar.', '');
                updateTimerDisplay(0);
            }
        }

        function setStatus(msg, type) {
            statusEl.textContent = msg;
            statusEl.className = 'ailmx_rec_status';
            if (type === 'error') statusEl.classList.add('ailmx_rec_error');
            if (type === 'recording') statusEl.classList.add('ailmx_rec_recording');
            if (type === 'ok') statusEl.classList.add('ailmx_rec_ok');
        }

        function startTimer() {
            seconds = 0;
            timerInterval = setInterval(function () {
                seconds++;
                updateTimerDisplay(seconds);
            }, 1000);
        }

        function stopTimer() {
            if (timerInterval) {
                clearInterval(timerInterval);
                timerInterval = null;
            }
        }

        function updateTimerDisplay(s) {
            var m = Math.floor(s / 60);
            var sec = s % 60;
            timerEl.textContent = m + ':' + (sec < 10 ? '0' : '') + sec;
        }
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