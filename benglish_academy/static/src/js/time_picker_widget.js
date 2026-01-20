/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Component, useState, useRef, onWillUpdateProps } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Widget TimePicker Visual para campos Float de hora en Odoo
 * 
 * Propósito: Proporcionar un selector de tiempo visual tipo reloj analógico
 * con entrada manual sincronizada para campos Float que representan horas (0-24).
 * 
 * Características:
 * - Reloj analógico visual con agujas de hora y minuto
 * - Input manual sincronizado en formato HH:MM
 * - Conversión automática entre Float (decimal) y HH:MM
 * - Incrementos de 5 minutos para facilidad de uso
 * - Validación de rangos 0-24h
 */
export class TimePickerWidget extends Component {
    static template = "benglish_academy.TimePickerWidget";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.state = useState({
            hours: 0,
            minutes: 0,
            showPicker: false,
        });

        this.inputRef = useRef("timeInput");
        this._updateFromValue(this.props);
        onWillUpdateProps((nextProps) => {
            if (this._getRecordValue(nextProps) !== this._getRecordValue(this.props)) {
                this._updateFromValue(nextProps);
            }
        });
    }

    _getRecordValue(props) {
        const raw = props.record.data[props.name];
        return Number.isFinite(raw) ? raw : 0;
    }

    /**
     * Convierte el valor Float (0-24) a horas y minutos
     */
    _updateFromValue(props) {
        const value = this._getRecordValue(props);
        this.state.hours = Math.floor(value);
        this.state.minutes = Math.round((value % 1) * 60);
        
        // Normalizar minutos si son 60 o más
        if (this.state.minutes >= 60) {
            this.state.hours += 1;
            this.state.minutes = 0;
        }
        if (this.state.hours >= 24) {
            this.state.hours = 0;
        }
    }

    /**
     * Obtiene el valor formateado HH:MM
     */
    get formattedTime() {
        const h = String(this.state.hours).padStart(2, '0');
        const m = String(this.state.minutes).padStart(2, '0');
        return `${h}:${m}`;
    }

    /**
     * Convierte horas y minutos a valor Float
     */
    get floatValue() {
        return this.state.hours + (this.state.minutes / 60);
    }

    /**
     * Calcula el ángulo de rotación para la aguja de las horas (0-360°)
     */
    get hourAngle() {
        const hours = this.state.hours % 12; // Convertir a formato 12h para el reloj
        const minutes = this.state.minutes;
        // Cada hora = 30° (360/12), más ajuste por minutos
        return (hours * 30) + (minutes * 0.5);
    }

    /**
     * Calcula el ángulo de rotación para la aguja de los minutos (0-360°)
     */
    get minuteAngle() {
        // Cada minuto = 6° (360/60)
        return this.state.minutes * 6;
    }

    /**
     * Muestra/oculta el picker
     */
    togglePicker() {
        if (!this.props.readonly) {
            this.state.showPicker = !this.state.showPicker;
        }
    }

    /**
     * Cierra el picker
     */
    closePicker() {
        this.state.showPicker = false;
    }

    /**
     * Maneja el click en el reloj analógico para cambiar la hora
     */
    onClockClick(ev) {
        if (this.props.readonly) return;

        const clock = ev.currentTarget;
        const rect = clock.getBoundingClientRect();
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        
        // Obtener posición relativa al centro del reloj
        const x = ev.clientX - rect.left - centerX;
        const y = ev.clientY - rect.top - centerY;
        
        // Calcular ángulo en radianes
        let angle = Math.atan2(y, x);
        // Convertir a grados y ajustar para que 0° esté arriba (12 en punto)
        let degrees = (angle * 180 / Math.PI) + 90;
        if (degrees < 0) degrees += 360;
        
        // Determinar si está más cerca del centro (horas) o del borde (minutos)
        const distance = Math.sqrt(x * x + y * y);
        const radius = Math.min(centerX, centerY);
        
        if (distance < radius * 0.6) {
            // Click en el área interior - cambiar horas
            this.state.hours = Math.floor(degrees / 30);
            if (this.state.hours === 0) this.state.hours = 0; // Mantener en formato 24h
        } else {
            // Click en el área exterior - cambiar minutos (incrementos de 5)
            const rawMinutes = Math.floor(degrees / 6);
            this.state.minutes = Math.round(rawMinutes / 5) * 5;
            if (this.state.minutes >= 60) this.state.minutes = 0;
        }
        
        this._saveValue();
    }

    /**
     * Incrementa las horas
     */
    incrementHour() {
        if (this.props.readonly) return;
        this.state.hours = (this.state.hours + 1) % 24;
        this._saveValue();
    }

    /**
     * Decrementa las horas
     */
    decrementHour() {
        if (this.props.readonly) return;
        this.state.hours = (this.state.hours - 1 + 24) % 24;
        this._saveValue();
    }

    /**
     * Incrementa los minutos (en intervalos de 5)
     */
    incrementMinute() {
        if (this.props.readonly) return;
        this.state.minutes = (this.state.minutes + 5) % 60;
        if (this.state.minutes === 0 && this.state.hours < 23) {
            // Si llega a 60, incrementar hora
            // this.state.hours = (this.state.hours + 1) % 24;
        }
        this._saveValue();
    }

    /**
     * Decrementa los minutos (en intervalos de 5)
     */
    decrementMinute() {
        if (this.props.readonly) return;
        this.state.minutes = (this.state.minutes - 5 + 60) % 60;
        this._saveValue();
    }

    /**
     * Maneja el cambio en el input manual
     */
    onInputChange(ev) {
        if (this.props.readonly) return;
        
        const value = ev.target.value;
        const match = value.match(/^(\d{1,2}):(\d{2})$/);
        
        if (match) {
            let hours = parseInt(match[1], 10);
            let minutes = parseInt(match[2], 10);
            
            // Validar rangos
            if (hours >= 0 && hours < 24 && minutes >= 0 && minutes < 60) {
                this.state.hours = hours;
                this.state.minutes = minutes;
                this._saveValue();
            }
        }
    }

    /**
     * Maneja el blur del input para forzar formato correcto
     */
    onInputBlur(ev) {
        if (this.props.readonly) return;
        
        const value = ev.target.value;
        
        // Intentar parsear diferentes formatos
        let hours = 0;
        let minutes = 0;
        
        // Formato HH:MM o H:MM
        let match = value.match(/^(\d{1,2}):(\d{2})$/);
        if (match) {
            hours = parseInt(match[1], 10);
            minutes = parseInt(match[2], 10);
        } else {
            // Formato solo números (HHMM o HHH)
            match = value.match(/^(\d{1,4})$/);
            if (match) {
                const num = match[1];
                if (num.length <= 2) {
                    hours = parseInt(num, 10);
                } else if (num.length === 3) {
                    hours = parseInt(num.substring(0, 1), 10);
                    minutes = parseInt(num.substring(1), 10);
                } else {
                    hours = parseInt(num.substring(0, 2), 10);
                    minutes = parseInt(num.substring(2), 10);
                }
            }
        }
        
        // Validar y normalizar
        hours = Math.max(0, Math.min(23, hours));
        minutes = Math.max(0, Math.min(59, minutes));
        
        this.state.hours = hours;
        this.state.minutes = minutes;
        
        // Actualizar el input con el formato correcto
        if (this.inputRef.el) {
            this.inputRef.el.value = this.formattedTime;
        }
        
        this._saveValue();
    }

    /**
     * Guarda el valor en el registro de Odoo
     */
    _saveValue() {
        const floatValue = this.floatValue;
        this.props.record.update({ [this.props.name]: floatValue });
    }
}

export const timePickerField = {
    component: TimePickerWidget,
    displayName: _t("Time Picker"),
    supportedTypes: ["float"],
    isEmpty: () => false,
};

registry.category("fields").add("time_picker", timePickerField);
registry.category("fields").add("time_clock_widget", timePickerField);
