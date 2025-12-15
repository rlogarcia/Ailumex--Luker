/** @odoo-module **/
/**
 * Archivo: survey_device_capture.js
 * Propósito: Captura automática del ID y tipo de dispositivo al iniciar una encuesta
 */

import ajax from "@web/legacy/js/core/ajax";
import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * Widget para capturar información del dispositivo en encuestas
 */
publicWidget.registry.SurveyDeviceCapture = publicWidget.Widget.extend({
    selector: '.o_survey_form',
    
    /**
     * Inicializa el widget y captura información del dispositivo
     */
    start: function () {
        this._super.apply(this, arguments);
        this._captureDeviceInfo();
    },

    /**
     * Captura y envía información del dispositivo al backend
     */
    _captureDeviceInfo: function () {
        const form = this.$el.find('form').first();
        if (!form.length) {
            return;
        }

        const dataset = form[0].dataset || {};
        const surveyId = parseInt(dataset.surveyId || 0, 10) || null;
        const restrictByDevice = this._toBoolean(dataset.restrictDevice, false);
        const captureDeviceInfo = this._toBoolean(dataset.captureDeviceInfo, true);
        const allowedDeviceTypes = dataset.allowedDeviceTypes || 'all';

        // Generar o recuperar UUID del dispositivo
        const deviceId = this._getOrCreateDeviceId();
        this._setDeviceCookie(deviceId);
        
        // Detectar tipo de dispositivo
        const deviceType = this._detectDeviceType();

        // Validar que el dispositivo esté permitido por configuración
        if (!this._isDeviceTypeAllowed(deviceType, allowedDeviceTypes)) {
            this._showRestrictionMessage(
                this._getDeviceRestrictionMessage(allowedDeviceTypes),
                'warning'
            );
            this._disableForm();
            return;
        }
        
        // Recopilar información adicional del dispositivo
        const deviceInfo = captureDeviceInfo ? this._collectDeviceInfo() : null;

        // Añadir campos ocultos al formulario
        this._addHiddenField('x_device_id', deviceId);
        this._addHiddenField('x_device_type', deviceType);
        if (captureDeviceInfo && deviceInfo) {
            this._addHiddenField('x_device_info', JSON.stringify(deviceInfo));
        }

        // Validar restricción de un dispositivo por encuesta
        if (restrictByDevice && surveyId) {
            this._checkDeviceRestriction(surveyId, deviceId);
        }
    },

    /**
     * Obtiene o crea un UUID único para el dispositivo usando localStorage
     * @returns {string} UUID del dispositivo
     */
    _getOrCreateDeviceId: function () {
        const STORAGE_KEY = 'odoo_survey_device_uuid';
        let deviceId = localStorage.getItem(STORAGE_KEY);
        
        if (!deviceId) {
            // Generar UUID v4
            deviceId = this._generateUUID();
            localStorage.setItem(STORAGE_KEY, deviceId);
        }
        
        return deviceId;
    },

    /**
     * Genera un UUID v4
     * @returns {string} UUID generado
     */
    _generateUUID: function () {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    },

    /**
     * Guarda el identificador del dispositivo en una cookie accesible para el backend
     * @param {string} deviceId
     */
    _setDeviceCookie: function (deviceId) {
        const COOKIE_KEY = 'odoo_survey_device_uuid';
        const expires = new Date();
        expires.setDate(expires.getDate() + 365);
        const cookieValue = `${COOKIE_KEY}=${deviceId};path=/;SameSite=Lax;expires=${expires.toUTCString()}`;
        document.cookie = cookieValue;
    },

    /**
     * Detecta el tipo de dispositivo basado en el user agent y características
     * @returns {string} Tipo de dispositivo: desktop, mobile, tablet, other
     */
    _detectDeviceType: function () {
        const ua = navigator.userAgent.toLowerCase();
        const isMobile = /mobile|android|iphone|ipod|blackberry|windows phone/i.test(ua);
        const isTablet = /tablet|ipad|playbook|silk|kindle/i.test(ua) || 
                        (isMobile && !/mobile/i.test(ua));
        
        if (isTablet) {
            return 'tablet';
        } else if (isMobile) {
            return 'mobile';
        } else if (/windows|mac|linux|cros/i.test(ua)) {
            return 'desktop';
        } else {
            return 'other';
        }
    },

    /**
     * Recopila información detallada del dispositivo
     * @returns {object} Información del dispositivo
     */
    _collectDeviceInfo: function () {
        const nav = navigator;
        const screen = window.screen;
        
        return {
            userAgent: nav.userAgent,
            platform: nav.platform,
            language: nav.language,
            languages: nav.languages || [],
            cookieEnabled: nav.cookieEnabled,
            doNotTrack: nav.doNotTrack,
            screenWidth: screen.width,
            screenHeight: screen.height,
            screenColorDepth: screen.colorDepth,
            screenPixelDepth: screen.pixelDepth,
            windowWidth: window.innerWidth,
            windowHeight: window.innerHeight,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            timestamp: new Date().toISOString(),
            // Información del navegador
            vendor: nav.vendor,
            hardwareConcurrency: nav.hardwareConcurrency,
            maxTouchPoints: nav.maxTouchPoints,
            // Características adicionales
            online: nav.onLine,
            connection: nav.connection ? {
                effectiveType: nav.connection.effectiveType,
                downlink: nav.connection.downlink,
                rtt: nav.connection.rtt,
                saveData: nav.connection.saveData
            } : null
        };
    },

    /**
     * Añade un campo oculto al formulario
     * @param {string} name - Nombre del campo
     * @param {string} value - Valor del campo
     */
    _addHiddenField: function (name, value) {
        const form = this.$el.find('form').first();
        if (form.length === 0) {
            return;
        }
        
        // Eliminar campo existente si existe
        form.find(`input[name="${name}"]`).remove();
        
        // Crear nuevo campo oculto
        const hiddenField = $('<input>', {
            type: 'hidden',
            name: name,
            value: value
        });
        
        form.append(hiddenField);
    },

    /**
     * Llama al endpoint que verifica si el dispositivo ya participó.
     * @param {number} surveyId
     * @param {string} deviceId
     */
    _checkDeviceRestriction: function (surveyId, deviceId) {
        ajax.jsonRpc(`/survey/check_device/${surveyId}`, 'call', {
            device_id: deviceId,
        }).then((result) => {
            if (!result || result.allowed) {
                return;
            }
            this._showRestrictionMessage(result.message || 'Este dispositivo ya respondió esta encuesta.', 'danger');
            this._disableForm();
        }).catch((error) => {
            // En caso de fallo en el endpoint, no bloquear el flujo pero trazar el problema.
            console.error('Error verificando el dispositivo de la encuesta:', error);
        });
    },

    /**
     * Determina si el tipo de dispositivo actual está permitido.
     * @param {string} deviceType
     * @param {string} allowedSetting
     * @returns {boolean}
     */
    _isDeviceTypeAllowed: function (deviceType, allowedSetting) {
        switch (allowedSetting) {
            case 'desktop_only':
                return deviceType === 'desktop';
            case 'mobile_tablet':
                return deviceType === 'mobile' || deviceType === 'tablet';
            case 'tablet_only':
                return deviceType === 'tablet';
            case 'all':
            default:
                return true;
        }
    },

    /**
     * Mensaje para mostrar cuando el dispositivo no está dentro de los permitidos.
     * @param {string} allowedSetting
     * @returns {string}
     */
    _getDeviceRestrictionMessage: function (allowedSetting) {
        switch (allowedSetting) {
            case 'desktop_only':
                return 'Esta encuesta solo permite respuestas desde equipos de escritorio.';
            case 'mobile_tablet':
                return 'Esta encuesta solo permite respuestas desde dispositivos móviles o tablets.';
            case 'tablet_only':
                return 'Esta encuesta solo permite respuestas desde tablets.';
            default:
                return 'Este dispositivo no está autorizado para responder la encuesta.';
        }
    },

    /**
     * Deshabilita la posibilidad de enviar el formulario.
     */
    _disableForm: function () {
        const form = this.$el.find('form').first();
        if (!form.length) {
            return;
        }
        form.find('button, input[type="submit"], a.btn').prop('disabled', true).addClass('disabled');
        form.addClass('o_survey_device_restricted');
    },

    /**
     * Muestra un mensaje en el formulario público.
     * @param {string} message
     * @param {string} level Bootstrap contextual class (info, warning, danger)
     */
    _showRestrictionMessage: function (message, level) {
        const alertLevel = level || 'warning';
        let $alert = this.$el.find('.o_survey_device_alert');
        if (!$alert.length) {
            $alert = $('<div>', {
                class: `alert alert-${alertLevel} o_survey_device_alert`,
                role: 'alert',
            });
            this.$el.prepend($alert);
        } else {
            $alert.removeClass(function (index, className) {
                return (className.match(/alert-\w+/g) || []).join(' ');
            }).addClass(`alert alert-${alertLevel}`);
        }
        $alert.text(message).removeClass('d-none');
    },

    /**
     * Convierte valores provenientes de atributos data-* a booleanos.
     * @param {*} value
     * @param {boolean} defaultValue
     * @returns {boolean}
     */
    _toBoolean: function (value, defaultValue) {
        if (value === undefined || value === null || value === '') {
            return defaultValue;
        }
        if (typeof value === 'boolean') {
            return value;
        }
        const normalized = String(value).toLowerCase();
        return ['1', 'true', 'yes', 'y', 'on'].includes(normalized);
    },
});

export default publicWidget.registry.SurveyDeviceCapture;
