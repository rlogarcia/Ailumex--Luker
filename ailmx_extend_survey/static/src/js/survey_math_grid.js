// AILUMEX - GRID matemático
// Guardado igual que reading_grid
// El audio se serializa en base64 y se envía junto con las celdas

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
                cell.dataset.state = cell.dataset.state || 'empty';

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

            initAudioRecorder(wrapper, hiddenInput);
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

        // El payload incluye celdas y audio (si existe)
        var audioData = wrapper._audioBase64 || null;

        var payload = {
            cells: cellValues,
            audio: {
                has_audio: !!audioData,
                base64: audioData || '',
                mimetype: wrapper._audioMimetype || 'audio/webm',
                filename: wrapper._audioFilename || 'respuesta.webm'
            }
        };

        hiddenInput.value = JSON.stringify(payload);
    }

    function updateStats(wrapper) {
        var ok = 0;
        var err = 0;
        var skip = 0;

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
            if (cell.dataset.state && cell.dataset.state !== 'empty') {
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
        var symbol = state === 'ok' ? '✔' : state === 'err' ? '✖' : state === 'skip' ? '⚠' : '⛔';

        var line = document.createElement('div');
        line.textContent = index + ' - ' + text + ' - ' + symbol;
        log.appendChild(line);
    }

    function initAudioRecorder(wrapper, hiddenInput) {
        var recorderPanel = wrapper.querySelector('.ailmx_audio_recorder');
        if (!recorderPanel) return;

        var btnRecord = recorderPanel.querySelector('.ailmx_btn_record');
        var btnStop   = recorderPanel.querySelector('.ailmx_btn_stop');
        var btnPlay   = recorderPanel.querySelector('.ailmx_btn_play');
        var btnDelete = recorderPanel.querySelector('.ailmx_btn_delete');
        var statusEl  = recorderPanel.querySelector('.ailmx_rec_status');
        var timerEl   = recorderPanel.querySelector('.ailmx_rec_timer');
        var waveEl    = recorderPanel.querySelector('.ailmx_rec_wave');
        var audioEl   = recorderPanel.querySelector('.ailmx_audio_playback');

        var mediaRecorder  = null;
        var audioChunks    = [];
        var audioBlob      = null;
        var timerInterval  = null;
        var seconds        = 0;

        // Inicializar propiedades en el wrapper
        wrapper._audioBase64   = null;
        wrapper._audioMimetype = 'audio/webm';
        wrapper._audioFilename = 'respuesta.webm';

        setState('idle');

        btnRecord.addEventListener('click', function () {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                setStatus('Tu navegador no soporta grabación de audio.', 'error');
                return;
            }

            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(function (stream) {
                    audioChunks = [];
                    audioBlob   = null;
                    seconds     = 0;

                    // Limpiar audio anterior del wrapper
                    wrapper._audioBase64 = null;
                    updateSerializedResponse(wrapper, hiddenInput);

                    mediaRecorder = new MediaRecorder(stream);

                    mediaRecorder.ondataavailable = function (e) {
                        if (e.data && e.data.size > 0) {
                            audioChunks.push(e.data);
                        }
                    };

                    mediaRecorder.onstop = function () {
                        var mimeType = mediaRecorder.mimeType || 'audio/webm';
                        var ext      = mimeType.includes('ogg') ? 'ogg' : mimeType.includes('mp4') ? 'mp4' : 'webm';

                        audioBlob = new Blob(audioChunks, { type: mimeType });
                        var url   = URL.createObjectURL(audioBlob);
                        audioEl.src = url;

                        stream.getTracks().forEach(function (t) { t.stop(); });

                        // Convertir a base64 y guardar en el wrapper
                        var reader = new FileReader();
                        reader.onloadend = function () {
                            // result = "data:audio/webm;base64,AAAA..."
                            // Guardamos solo la parte base64 sin el prefijo
                            var base64Full = reader.result;
                            var base64Data = base64Full.split(',')[1] || base64Full;

                            wrapper._audioBase64   = base64Data;
                            wrapper._audioMimetype = mimeType;
                            wrapper._audioFilename = 'respuesta_' + Date.now() + '.' + ext;

                            // Actualizar el hidden input con el audio incluido
                            updateSerializedResponse(wrapper, hiddenInput);

                            setState('recorded');
                            setStatus('Grabación lista para enviar.', 'ok');
                            stopTimer();
                        };
                        reader.readAsDataURL(audioBlob);
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
                    setStatus('Grabación lista para enviar.', 'ok');
                };
            }
        });

        btnDelete.addEventListener('click', function () {
            audioBlob  = null;
            audioChunks = [];
            audioEl.src = '';
            seconds    = 0;

            wrapper._audioBase64 = null;
            updateSerializedResponse(wrapper, hiddenInput);

            setState('idle');
            setStatus('Grabación eliminada.', '');
            updateTimerDisplay(0);
        });

        function setState(state) {
            btnRecord.style.display = (state === 'idle' || state === 'recorded') ? 'inline-flex' : 'none';
            btnStop.style.display   = (state === 'recording') ? 'inline-flex' : 'none';
            btnPlay.style.display   = (state === 'recorded')  ? 'inline-flex' : 'none';
            btnDelete.style.display = (state === 'recorded')  ? 'inline-flex' : 'none';
            waveEl.style.display    = (state === 'recording') ? 'flex' : 'none';

            if (state === 'idle') {
                setStatus('Presiona grabar para iniciar.', '');
                updateTimerDisplay(0);
            }
        }

        function setStatus(msg, type) {
            statusEl.textContent = msg;
            statusEl.className = 'ailmx_rec_status';
            if (type === 'error')     statusEl.classList.add('ailmx_rec_error');
            if (type === 'recording') statusEl.classList.add('ailmx_rec_recording');
            if (type === 'ok')        statusEl.classList.add('ailmx_rec_ok');
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
            var m   = Math.floor(s / 60);
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