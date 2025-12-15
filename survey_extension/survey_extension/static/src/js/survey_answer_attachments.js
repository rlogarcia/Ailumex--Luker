/** @odoo-module **/

/**
 * File: c:\\ModulosOdoo18\\survey_extension\\static\\src\\js\\survey_answer_attachments.js
 *
 * Propósito:
 *   Maneja la interfaz y la lógica del lado cliente para la gestión de
 *   adjuntos en preguntas de encuestas públicas (Survey) en Odoo.
 *
 * Qué hace (resumen):
 *   - Construye elementos DOM para mostrar adjuntos (nombre, mime, enlace).
 *   - Gestiona zonas de adjuntos (lectura/escritura) y el contador visible.
 *   - Sube archivos al endpoint server-side responsable de guardar adjuntos.
 *   - Elimina adjuntos mediante RPC hacia el servidor.
 *   - Muestra notificaciones al usuario sobre errores o estados.
 *   - Intenta vincular un dispositivo (device_uuid + metadata) al iniciar la
 *     participación en la encuesta para fins de auditoría/telemetría.
 *
 * Estructura por bloques:
 *   - Constantes y utilidades: mensajes de error y helpers DOM/estado.
 *   - Extensión de SurveyFormWidget: hooks para start(), next-screen y
 *     handlers de UI para añadir/eliminar/subir adjuntos.
 *
 * Notas importantes:
 *   - No altera la lógica server-side; requiere que existan los endpoints:
 *       POST  /survey_extension/attachment/upload
 *       RPC   /survey_extension/attachment/remove
 *       RPC   /survey_extension/mark_start
 *   - Se añadió documentación inline (JSDoc en español) para cada función
 *     sin modificar su comportamiento.
 */

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

const SurveyFormWidget = publicWidget.registry.SurveyFormWidget;

// Mensajes de error usados por la UI. Las claves coinciden con errores
// devueltos por el servidor para mapearlos a textos localizados.
const ERROR_MESSAGES = {
    invalid_question: _t('No se reconoció la pregunta objetivo.'),
    missing_file: _t('Selecciona un archivo para continuar.'),
    readonly: _t('La encuesta ya no permite cargar archivos.'),
    no_answer: _t('No se encontró una participación activa.'),
    forbidden: _t('No tienes permisos para modificar este archivo.'),
    not_found: _t('El archivo ya fue eliminado.'),
    unsupported_question: _t('Esta pregunta no permite adjuntar archivos.'),
};

/**
 * buildAttachmentItem(data, readonly)
 * Construye el elemento DOM que representa un adjunto en la lista.
 *
 * Parámetros:
 *  - data: objeto con { link_id, attachment_id, url, name, mimetype }
 *  - readonly: booleano que indica si la zona es de solo lectura (sin botón eliminar)
 *
 * Devuelve: jQuery element con la estructura del adjunto listo para insertar.
 */
function buildAttachmentItem(data, readonly) {
    const $item = $('<div/>', {
        class: 'o_survey_attachment_item d-flex align-items-center gap-2',
        'data-link-id': data.link_id,
        'data-attachment-id': data.attachment_id,
    });
    const $link = $('<a/>', {
        class: 'o_survey_attachment_link',
        href: data.url,
        target: '_blank',
        rel: 'noopener',
        text: data.name,
    }).prepend($('<i/>', { class: 'fa fa-paperclip me-1' }));
    $item.append($link);
    if (data.mimetype) {
        $item.append($('<span/>', { class: 'text-muted small', text: data.mimetype }));
    }
    if (!readonly) {
        const $remove = $('<button/>', {
            type: 'button',
            class: 'btn btn-sm btn-link text-danger o_survey_attachment_remove',
            'data-link-id': data.link_id,
        }).append($('<i/>', { class: 'fa fa-times' }));
        $item.append($remove);
    }
    return $item;
}

/**
 * isReadonlyArea($area)
 * Comprueba si una zona de adjuntos está marcada como readonly.
 * Acepta el atributo data-readonly que puede ser booleano o string.
 */
function isReadonlyArea($area) {
    const value = $area.data('readonly');
    if (typeof value === 'boolean') {
        return value;
    }
    if (typeof value === 'string') {
        return value.toLowerCase() === 'true';
    }
    return false;
}

/**
 * updateAttachmentCounter($area)
 * Actualiza el contador oculto/visible de adjuntos relacionado a la zona.
 * Busca el elemento `.o_survey_attachment_counter` y escribe la cantidad.
 */
function updateAttachmentCounter($area) {
    const $counter = $area.find('.o_survey_attachment_counter');
    if (!$counter.length) {
        return;
    }
    const $list = $area.find('.o_survey_attachment_list');
    const count = $list.length ? $list.children('.o_survey_attachment_item').length : 0;
    $counter.val(String(count));
}

/**
 * notify(widget, params)
 * Envia una notificación al usuario.
 * Primero intenta usar las utilidades del widget (displayNotification o
 * trigger_up), y si falla muestra un alert como fallback.
 *
 * Params esperados: { title?, message, type? }
 */
function notify(widget, params) {
    if (widget && typeof widget.displayNotification === 'function') {
        widget.displayNotification(params);
        return;
    }
    if (widget && typeof widget.trigger_up === 'function') {
        try {
            widget.trigger_up('display_notification', params);
            return;
        } catch (error) {
            // Continue with fallback below when bubbling notifications fails.
        }
    }
    const title = params.title ? `${params.title}: ` : '';
    window.alert(`${title}${params.message}`);
}

/*
 * Extiende `SurveyFormWidget` para añadir soporte de adjuntos en la UI pública
 * de encuestas. Se registran handlers para añadir/quitar archivos, inicializar
 * zonas y para subir/eliminar adjuntos vía llamadas al servidor.
 */
SurveyFormWidget.include({
    start() {
        // start(): se ejecuta al inicializar el widget de encuesta.
        // - Asegura los handlers de adjuntos
        // - Inicializa las áreas de adjuntos existentes
        // - Intenta vincular el dispositivo (device UUID + metadata) llamando
        //   al endpoint /survey_extension/mark_start mediante rpc().
        return this._super.apply(this, arguments).then(() => {
            // Asegurar UI de adjuntos
            this._ensureAttachmentHandlers();
            this._initAttachmentAreas();

            // ===== Vincular DISPOSITIVO automáticamente =====
            try {
                // 1) Generar/leer UUID persistente por navegador/dispositivo
                let uuid = window.localStorage.getItem('survey_device_uuid');
                if (!uuid) {
                    uuid = 'DEV-' + Math.random().toString(36).slice(2) + '-' + Date.now();
                    window.localStorage.setItem('survey_device_uuid', uuid);
                }

                // 2) Leer tokens desde el <form data-survey-token data-answer-token> (Odoo 18)
                let formEl = this.el.querySelector('form[data-survey-token][data-answer-token]');
                if (!formEl) {
                    formEl = document.querySelector('form[data-survey-token][data-answer-token]');
                }
                const surveyToken = formEl ? formEl.dataset.surveyToken : null;
                const answerToken = formEl ? formEl.dataset.answerToken : null;

                // 3) Recopilar información completa del dispositivo
                const deviceInfo = {
                    device_uuid: uuid,
                    user_agent: navigator.userAgent || '',
                    screen_width: window.screen.width || 0,
                    screen_height: window.screen.height || 0,
                    viewport_width: window.innerWidth || 0,
                    viewport_height: window.innerHeight || 0,
                    platform: navigator.platform || '',
                    language: navigator.language || '',
                    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || '',
                    timestamp: new Date().toISOString(),
                };

                // 4) Llamar al endpoint con device_uuid para crear/vincular survey.device
                if (surveyToken && answerToken) {
                    rpc('/survey_extension/mark_start', {
                        survey_token: surveyToken,
                        answer_token: answerToken,
                        ...deviceInfo  // ← ENVIAR TODA LA INFORMACIÓN DEL DISPOSITIVO
                    }).catch(() => { /* silencioso */ });
                }
            } catch (err) {
                // No romper la UI si algo falla
                console.warn('survey_extension: device bind failed', err);
            }
            // ===== Fin vínculo de dispositivo =====
        });
    },

    _onNextScreenDone() {
        // Ejecutado al finalizar una pantalla; re-inicializa áreas porque la
        // siguiente pantalla puede contener nuevas zonas de adjuntos.
        const result = this._super.apply(this, arguments);
        this._initAttachmentAreas();
        return result;
    },

    _ensureAttachmentHandlers() {
        // Registra los handlers de la UI una sola vez para evitar dobles bindings.
        if (this._attachmentHandlersBound) {
            return;
        }
        this._attachmentHandlersBound = true;
        this.$el.on('click', '.o_survey_attachment_add', this._onAttachmentAddClick.bind(this));
        this.$el.on('change', '.o_survey_attachment_input', this._onAttachmentInputChange.bind(this));
        this.$el.on('click', '.o_survey_attachment_remove', this._onAttachmentRemoveClick.bind(this));
    },

    _initAttachmentAreas() {
        // Inicializa cada zona de adjuntos: muestra/oculta mensaje vacío,
        // marca readonly cuando corresponda y actualiza contador.
        this.$('.o_survey_attachment_area').each((_, element) => {
            const $area = $(element);
            const hasList = $area.find('.o_survey_attachment_list').length;
            if (!hasList) {
                $area.find('.o_survey_attachment_empty').toggleClass('d-none', false);
            } else {
                $area.find('.o_survey_attachment_empty').toggleClass('d-none', true);
            }
            if (isReadonlyArea($area)) {
                $area.addClass('o_survey_attachment_readonly');
            }
            updateAttachmentCounter($area);
        });
    },

    _onAttachmentAddClick(event) {
        // Handler al pulsar el botón "añadir". Dispara el input[type=file]
        // correspondiente a la zona, salvo que esté en readonly.
        event.preventDefault();
        const $area = $(event.currentTarget).closest('.o_survey_attachment_area');
        if (isReadonlyArea($area)) {
            return;
        }
        const $input = $area.find('.o_survey_attachment_input');
        if ($input.length) {
            $input.trigger('click');
        }
    },

    async _onAttachmentInputChange(event) {
        // Cuando el input[file] cambia, toma los archivos seleccionados y
        // llama al método de subida. Limpia el input para permitir re-subidas.
        const $input = $(event.currentTarget);
        const $area = $input.closest('.o_survey_attachment_area');
        const files = Array.from(event.currentTarget.files || []);
        if (!files.length) {
            return;
        }
        await this._uploadAttachments($area, files);
        $input.val('');
    },

    async _uploadAttachments($area, files) {
        // Envía los archivos seleccionados al endpoint de subida.
        // Valida que existan los tokens y CSRF necesarios antes de proceder.
        const surveyToken = $area.data('surveyToken');
        const answerToken = $area.data('answerToken');
        const questionId = $area.data('questionId');
        const csrfToken = this.$('input[name="csrf_token"]').val();
        if (!(surveyToken && answerToken && questionId && csrfToken)) {
            notify(this, {
                title: _t('Error'),
                message: _t('No fue posible preparar el envío del archivo.'),
                type: 'danger',
            });
            return;
        }
        const formData = new FormData();
        formData.append('csrf_token', csrfToken);
        formData.append('survey_token', surveyToken);
        formData.append('answer_token', answerToken);
        formData.append('question_id', questionId);
        files.forEach((file) => formData.append('file', file));

        let response;
        try {
            response = await fetch('/survey_extension/attachment/upload', {
                method: 'POST',
                body: formData,
                credentials: 'include',
            });
        } catch (error) {
            // Notificar error de red
            notify(this, {
                title: _t('Error de red'),
                message: _t('No fue posible subir el archivo. Inténtalo nuevamente.'),
                type: 'danger',
            });
            return;
        }

        let payload;
        try {
            payload = await response.json();
        } catch (error) {
            // Respuesta no JSON
            notify(this, {
                title: _t('Error'),
                message: _t('Respuesta inesperada del servidor.'),
                type: 'danger',
            });
            return;
        }

        // Manejo de errores según status o payload
        if (!response.ok || payload.error) {
            let message;
            if (payload && payload.error === 'file_too_large') {
                const limit = payload.limit ? `${payload.limit} MB` : '';
                message = limit ? _t('El archivo excede el tamaño permitido (%s).', limit) : _t('El archivo excede el tamaño permitido.');
            } else if (payload && payload.error) {
                message = ERROR_MESSAGES[payload.error] || payload.error;
            } else {
                message = _t('No se pudo guardar el archivo.');
            }
            notify(this, {
                title: _t('Error'),
                message,
                type: 'danger',
            });
            return;
        }

        // Insertar los adjuntos retornados por el servidor en la UI
        const attachments = payload.attachments || [];
        attachments.forEach((attachment) => this._appendAttachment($area, attachment));
    },

    _appendAttachment($area, attachment) {
        // Inserta un nuevo elemento de adjunto en la lista (crea la lista si
        // no existía). Respeta el modo readonly de la zona para mostrar/ocultar
        // el botón de eliminar.
        let $list = $area.find('.o_survey_attachment_list');
        const readonly = isReadonlyArea($area);
        if (!$list.length) {
            $list = $('<div/>', {
                class: 'o_survey_attachment_list d-flex flex-column gap-2',
            });
            $area.prepend($list);
        }
        const $newItem = buildAttachmentItem(attachment, readonly);
        $list.append($newItem);
        $area.find('.o_survey_attachment_empty').addClass('d-none');
        updateAttachmentCounter($area);
    },

    async _onAttachmentRemoveClick(event) {
        // Handler para eliminar un adjunto. Llama al RPC del servidor y, si
        // responde OK, remueve el elemento del DOM y actualiza el contador.
        event.preventDefault();
        const $button = $(event.currentTarget);
        const $area = $button.closest('.o_survey_attachment_area');
        if (isReadonlyArea($area)) {
            return;
        }
        const linkId = $button.data('linkId');
        if (!linkId) {
            return;
        }
        $button.prop('disabled', true);
        let result;
        try {
            result = await rpc('/survey_extension/attachment/remove', {
                survey_token: $area.data('surveyToken'),
                answer_token: $area.data('answerToken'),
                link_id: linkId,
            });
        } catch (error) {
            notify(this, {
                title: _t('Error de red'),
                message: _t('No fue posible eliminar el archivo.'),
                type: 'danger',
            });
            $button.prop('disabled', false);
            return;
        }

        $button.prop('disabled', false);
        if (result && result.error) {
            notify(this, {
                title: _t('Error'),
                message: ERROR_MESSAGES[result.error] || result.error,
                type: 'danger',
            });
            return;
        }

        const $list = $area.find('.o_survey_attachment_list');
        $area
            .find(`.o_survey_attachment_item[data-link-id="${linkId}"]`)
            .remove();
        if (!$list.children().length) {
            $list.remove();
            $area.find('.o_survey_attachment_empty').removeClass('d-none');
        }
        updateAttachmentCounter($area);
    },
});
