
document.addEventListener('DOMContentLoaded', function () {

    function findSurveyToken() {
        var tokenInput = document.querySelector('input[name="token"]');
        if (tokenInput && tokenInput.value) {
            return tokenInput.value;
        }

        var pathParts = window.location.pathname.split('/');
        return pathParts[pathParts.length - 1] || '';
    }

    function bindImageInputs() {
        var inputs = document.querySelectorAll('.ailmx_image_attachment_input');

        inputs.forEach(function (input) {
            if (input.dataset.boundImageUpload === '1') {
                return;
            }

            input.dataset.boundImageUpload = '1';

            input.addEventListener('change', function () {
                var file = input.files && input.files[0];
                var questionId = input.getAttribute('data-question-id');
                var statusNode = document.querySelector(
                    '.ailmx_image_attachment_status[data-question-id="' + questionId + '"]'
                );

                if (!file) {
                    if (statusNode) {
                        statusNode.textContent = 'No se ha seleccionado ninguna imagen.';
                    }
                    return;
                }

                var token = findSurveyToken();

                if (!token) {
                    if (statusNode) {
                        statusNode.textContent = 'No se pudo identificar la aplicación actual.';
                    }
                    return;
                }

                var formData = new FormData();
                formData.append('question_id', questionId);
                formData.append('token', token);
                formData.append('image_file', file);

                if (statusNode) {
                    statusNode.textContent = 'Cargando imagen...';
                }

                fetch('/ailmx/survey/upload_image', {
                    method: 'POST',
                    body: formData,
                    credentials: 'same-origin',
                })
                    .then(function (response) {
                        return response.json();
                    })
                    .then(function (data) {
                        if (data && data.success) {
                            if (statusNode) {
                                statusNode.textContent = 'Imagen cargada: ' + data.filename;
                            }
                        } else {
                            if (statusNode) {
                                statusNode.textContent = data.error || 'No se pudo cargar la imagen.';
                            }
                        }
                    })
                    .catch(function () {
                        if (statusNode) {
                            statusNode.textContent = 'Error de comunicación al cargar la imagen.';
                        }
                    });
            });
        });
    }

    function bootImageUploadWhenReady() {
        var surveyBody = document.querySelector('.o_survey_form_content');

        if (!surveyBody) {
            setTimeout(bootImageUploadWhenReady, 400);
            return;
        }

        bindImageInputs();

        var observer = new MutationObserver(function () {
            setTimeout(function () {
                bindImageInputs();
            }, 100);
        });

        observer.observe(surveyBody, {
            childList: true,
            subtree: true
        });
    }

    bootImageUploadWhenReady();
});