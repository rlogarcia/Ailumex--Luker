document.addEventListener('DOMContentLoaded', function () {
    var submitLock = false;
    var autoVoiceStore = {};

    function initAutoVoiceWrappers() {
        var wrappers = document.querySelectorAll('.ailmx_auto_voice_wrapper');

        wrappers.forEach(function (wrapper) {
            if (wrapper.dataset.autoVoiceInitialized === '1') {
                return;
            }

            wrapper.dataset.autoVoiceInitialized = '1';
            wrapper.dataset.autoVoiceState = 'idle';
            wrapper._audioBase64 = null;
            wrapper._audioMimetype = 'audio/webm';
            wrapper._audioFilename = 'respuesta_auto.webm';
            wrapper._mediaRecorder = null;
            wrapper._mediaStream = null;
            wrapper._audioChunks = [];
            wrapper._timerInterval = null;
            wrapper._seconds = 0;
            wrapper._isFinalizing = false;

            autoStartRecording(wrapper);
        });
    }

    function getQuestionId(wrapper) {
        return wrapper ? String(wrapper.dataset.questionId || '') : '';
    }

    function getStatusEl(wrapper) {
        return wrapper.querySelector('.ailmx_auto_voice_status');
    }

    function getTimerEl(wrapper) {
        return wrapper.querySelector('.ailmx_auto_voice_timer');
    }

    function getWaveEl(wrapper) {
        return wrapper.querySelector('.ailmx_auto_voice_wave');
    }

    function getAudioEl(wrapper) {
        return wrapper.querySelector('.ailmx_auto_voice_playback');
    }

    function setStatus(wrapper, message, type) {
        var el = getStatusEl(wrapper);
        if (!el) return;

        el.textContent = message;
        el.className = 'ailmx_auto_voice_status';

        if (type === 'error') el.classList.add('ailmx_auto_voice_status_error');
        if (type === 'recording') el.classList.add('ailmx_auto_voice_status_recording');
        if (type === 'ok') el.classList.add('ailmx_auto_voice_status_ok');
    }

    function updateTimer(wrapper, seconds) {
        var el = getTimerEl(wrapper);
        if (!el) return;

        var m = Math.floor(seconds / 60);
        var s = seconds % 60;
        el.textContent = m + ':' + (s < 10 ? '0' : '') + s;
    }

    function startTimer(wrapper) {
        stopTimer(wrapper);
        wrapper._seconds = 0;
        updateTimer(wrapper, 0);

        wrapper._timerInterval = setInterval(function () {
            wrapper._seconds += 1;
            updateTimer(wrapper, wrapper._seconds);
        }, 1000);
    }

    function stopTimer(wrapper) {
        if (wrapper._timerInterval) {
            clearInterval(wrapper._timerInterval);
            wrapper._timerInterval = null;
        }
    }

    function autoStartRecording(wrapper) {
        if (!window.isSecureContext) {
            setStatus(wrapper, 'La grabación automática requiere HTTPS o localhost.', 'error');
            return;
        }

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            setStatus(wrapper, 'Tu navegador no soporta grabación de audio.', 'error');
            return;
        }

        var mimeType = '';
        if (window.MediaRecorder && MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
            mimeType = 'audio/webm;codecs=opus';
        } else if (window.MediaRecorder && MediaRecorder.isTypeSupported('audio/webm')) {
            mimeType = 'audio/webm';
        } else if (window.MediaRecorder && MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
            mimeType = 'audio/ogg;codecs=opus';
        }

        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(function (stream) {
                wrapper._mediaStream = stream;
                wrapper._audioChunks = [];
                wrapper._audioBase64 = null;

                var qid = getQuestionId(wrapper);
                if (qid) {
                    delete autoVoiceStore[qid];
                }

                var recorder = mimeType
                    ? new MediaRecorder(stream, { mimeType: mimeType })
                    : new MediaRecorder(stream);

                wrapper._mediaRecorder = recorder;
                wrapper._audioMimetype = recorder.mimeType || mimeType || 'audio/webm';

                recorder.ondataavailable = function (e) {
                    if (e.data && e.data.size > 0) {
                        wrapper._audioChunks.push(e.data);
                    }
                };

                recorder.onstop = function () {
                    buildBlobFromChunks(wrapper, function () {
                        wrapper.dataset.autoVoiceState = 'recorded';
                        setStatus(wrapper, 'Grabación automática lista para enviar.', 'ok');
                        stopTimer(wrapper);
                        if (getWaveEl(wrapper)) {
                            getWaveEl(wrapper).style.display = 'none';
                        }
                    });
                };

                recorder.start(100);
                wrapper.dataset.autoVoiceState = 'recording';

                if (getWaveEl(wrapper)) {
                    getWaveEl(wrapper).style.display = 'flex';
                }

                setStatus(wrapper, 'Grabando...', 'recording');
                startTimer(wrapper);
            })
            .catch(function (err) {
                setStatus(wrapper, 'No se pudo acceder al micrófono: ' + err.message, 'error');
            });
    }

    function buildBlobFromChunks(wrapper, callback) {
        var audioBlob = new Blob(wrapper._audioChunks, {
            type: wrapper._audioMimetype || 'audio/webm'
        });

        var audioEl = getAudioEl(wrapper);
        if (audioEl) {
            audioEl.src = URL.createObjectURL(audioBlob);
        }

        var ext = 'webm';
        if ((wrapper._audioMimetype || '').includes('ogg')) ext = 'ogg';
        if ((wrapper._audioMimetype || '').includes('mp4')) ext = 'mp4';

        var reader = new FileReader();
        reader.onloadend = function () {
            var base64Full = reader.result || '';
            wrapper._audioBase64 = base64Full.split(',')[1] || '';
            wrapper._audioFilename = 'respuesta_auto_' + Date.now() + '.' + ext;

            var qid = getQuestionId(wrapper);
            if (qid && wrapper._audioBase64) {
                autoVoiceStore[qid] = {
                    has_audio: true,
                    base64: wrapper._audioBase64,
                    mimetype: wrapper._audioMimetype || 'audio/webm',
                    filename: wrapper._audioFilename || 'respuesta_auto.webm'
                };
                console.log('[AILMX] autoVoiceStore guardado para pregunta', qid, autoVoiceStore[qid]);
            } else {
                console.warn('[AILMX] No se pudo guardar audio en store', {
                    qid: qid,
                    hasBase64: !!wrapper._audioBase64
                });
            }

            if (wrapper._mediaStream) {
                wrapper._mediaStream.getTracks().forEach(function (t) { t.stop(); });
                wrapper._mediaStream = null;
            }

            wrapper._isFinalizing = false;

            if (callback) {
                callback();
            }
        };
        reader.readAsDataURL(audioBlob);
    }

    function finalizeWrapperRecording(wrapper, callback) {
        if (!wrapper) {
            if (callback) callback();
            return;
        }

        if (wrapper._isFinalizing) {
            return;
        }

        if (wrapper.dataset.autoVoiceState === 'recorded') {
            if (callback) callback();
            return;
        }

        if (wrapper.dataset.autoVoiceState !== 'recording') {
            if (callback) callback();
            return;
        }

        wrapper._isFinalizing = true;
        setStatus(wrapper, 'Cerrando grabación automática...', 'recording');

        var recorder = wrapper._mediaRecorder;
        if (!recorder) {
            wrapper._isFinalizing = false;
            if (callback) callback();
            return;
        }

        if (recorder.state === 'recording') {
            recorder.addEventListener('stop', function handler() {
                recorder.removeEventListener('stop', handler);
                if (callback) callback();
            });
            recorder.stop();
        } else {
            buildBlobFromChunks(wrapper, function () {
                wrapper.dataset.autoVoiceState = 'recorded';
                setStatus(wrapper, 'Grabación automática lista para enviar.', 'ok');
                stopTimer(wrapper);
                if (getWaveEl(wrapper)) {
                    getWaveEl(wrapper).style.display = 'none';
                }
                if (callback) callback();
            });
        }
    }

    function getRecordingWrapper() {
        return document.querySelector('.ailmx_auto_voice_wrapper[data-auto-voice-state="recording"]');
    }

    function injectAudioIntoBody(body) {
        if (!body || !body.params || !body.params.question_id) {
            return body;
        }

        var qid = String(body.params.question_id);
        var payload = autoVoiceStore[qid];

        if (payload && payload.base64) {
            body.params[qid + '_auto_audio'] = JSON.stringify(payload);
            console.log('[AILMX] Audio inyectado en payload para pregunta', qid);
        } else {
            console.warn('[AILMX] No hay audio en store para pregunta', qid, autoVoiceStore);
        }

        return body;
    }

    function patchFetch() {
        var originalFetch = window.fetch;

        window.fetch = async function (url, options) {
            try {
                if (options && options.body && typeof options.body === 'string') {
                    var body = JSON.parse(options.body);
                    body = injectAudioIntoBody(body);
                    options.body = JSON.stringify(body);
                }
            } catch (e) {
                console.warn('[AILMX] Error parcheando fetch:', e);
            }

            return originalFetch.call(this, url, options);
        };
    }

    function patchXHR() {
        var OriginalXHR = window.XMLHttpRequest;

        function PatchedXHR() {
            var xhr = new OriginalXHR();
            var originalOpen = xhr.open.bind(xhr);
            var originalSend = xhr.send.bind(xhr);
            var currentUrl = '';

            xhr.open = function (method, url) {
                currentUrl = url;
                return originalOpen.apply(xhr, arguments);
            };

            xhr.send = function (body) {
                try {
                    if (currentUrl && currentUrl.includes('/survey/submit/') && body && typeof body === 'string') {
                        var parsed = JSON.parse(body);
                        parsed = injectAudioIntoBody(parsed);
                        body = JSON.stringify(parsed);
                    }
                } catch (e) {
                    console.warn('[AILMX] Error parcheando XHR:', e);
                }

                return originalSend.call(xhr, body);
            };

            return xhr;
        }

        PatchedXHR.prototype = OriginalXHR.prototype;
        window.XMLHttpRequest = PatchedXHR;
    }

    function interceptSubmitButtons() {
        document.addEventListener('click', function (ev) {
            var btn = ev.target.closest('.o_survey_navigation_submit, .o_survey_form_content button[type="submit"]');
            if (!btn) return;
            if (submitLock) return;

            var wrapper = getRecordingWrapper();
            if (!wrapper) {
                return;
            }

            ev.preventDefault();
            ev.stopPropagation();

            submitLock = true;

            finalizeWrapperRecording(wrapper, function () {
                setTimeout(function () {
                    submitLock = false;
                    btn.click();
                }, 120);
            });
        }, true);
    }

    initAutoVoiceWrappers();

    var surveyBody = document.querySelector('.o_survey_form_content');
    if (surveyBody) {
        new MutationObserver(initAutoVoiceWrappers).observe(surveyBody, {
            childList: true,
            subtree: true
        });
    }

    interceptSubmitButtons();
    patchFetch();
    patchXHR();
});