/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * File: c:\\ModulosOdoo18\\survey_extension\\static\\src\\js\\survey_conditional_questions.js
 *
 * Propósito:
 *   Gestionar preguntas condicionales en la UI pública de encuestas (Survey).
 *   Cuando una pregunta depende de la respuesta de otra, este módulo
 *   controla la visibilidad, limpieza de respuestas y el marcado `required`.
 *
 * Qué hace (resumen):
 *   - Indexa preguntas marcadas como condicionales y las oculta inicialmente.
 *   - Escucha cambios en inputs/selects y muestra/oculta preguntas hijas
 *     basadas en la respuesta configurada como disparador.
 *   - Limpia respuestas y desactiva validaciones cuando una pregunta queda oculta.
 *
 * Notas:
 *   - Trabaja sobre wrappers con clase `.js_question-wrapper` y atributos
 *     data: `data-conditional`, `data-question-id`, `data-conditional-question-id`,
 *     `data-conditional-answer-id`, `data-originally-required`.
 */

publicWidget.registry.SurveyConditionalQuestions = publicWidget.Widget.extend({
    selector: ".o_survey_form",

    // Eventos que disparan la comprobación de condiciones: radios, selects y checkboxes
    events: {
        "change input[type='radio']": "_onAnswerChange",
        "change select": "_onAnswerChange",
        "change input[type='checkbox']": "_onAnswerChange",
    },

    // start(): inicializa el widget y las preguntas condicionales
    start() {
        this._super(...arguments);
        this._initConditionalQuestions();
        this._checkAllConditions();
    },

    /**
     * _initConditionalQuestions()
     * Indexa todas las preguntas con `data-conditional='true'`, guarda su
     * configuración (elemento, dependencia y respuesta requerida), las oculta
     * y limpia su estado inicial (no required y sin respuesta).
     */
    _initConditionalQuestions() {
        this.conditionalQuestions = {};
        const $questions = this.$(".js_question-wrapper[data-conditional='true']");
        $questions.each((_, el) => {
            const $q = $(el);
            const qId = $q.data("question-id");
            const parentQ = $q.data("conditional-question-id");
            const triggerA = $q.data("conditional-answer-id");
            if (qId && parentQ && triggerA) {
                this.conditionalQuestions[qId] = {
                    element: $q,
                    dependsOn: String(parentQ),
                    requiredAnswer: String(triggerA),
                };
                $q.hide();
                this._toggleRequired($q, false);
                this._clearAnswer($q);
            }
        });
    },

    /**
     * _checkAllConditions()
     * Re-evalúa las condiciones para todas las preguntas indexadas. Útil al
     * cargar la página o al regresar en un wizard para restaurar visibilidad.
     */
    _checkAllConditions() {
        Object.values(this.conditionalQuestions).forEach((cfg) => {
            this._checkConditionsForQuestion(cfg.dependsOn);
        });
    },

    // Cuando cambia una respuesta, se verifica si hay preguntas dependientes
    _onAnswerChange(ev) {
        const $input = $(ev.currentTarget);
        const $wrapper = $input.closest(".js_question-wrapper,[data-question-id]");
        const qId = $wrapper.data("question-id");
        if (qId != null) {
            this._checkConditionsForQuestion(String(qId));
        }
    },

    /**
     * _checkConditionsForQuestion(questionId)
     * Recorre las preguntas condicionales y muestra/oculta cada hija cuyo
     * `dependsOn` coincida con `questionId`. Si la respuesta actual coincide
     * con `requiredAnswer` se muestra y activa el required; en caso contrario
     * se oculta, se limpia la respuesta y se desactiva el required.
     */
    _checkConditionsForQuestion(questionId) {
        Object.entries(this.conditionalQuestions).forEach(([childId, cfg]) => {
            if (cfg.dependsOn === String(questionId)) {
                const selected = this._getSelectedAnswer(questionId);
                if (selected != null && String(selected) === cfg.requiredAnswer) {
                    if (cfg.element.is(":hidden")) {
                        cfg.element.stop(true, true).slideDown(200);
                    }
                    this._toggleRequired(cfg.element, true);
                } else {
                    if (cfg.element.is(":visible")) {
                        cfg.element.stop(true, true).slideUp(200);
                    }
                    this._clearAnswer(cfg.element);
                    this._toggleRequired(cfg.element, false);
                }
            }
        });
    },

    /**
     * _getSelectedAnswer(questionId)
     * Devuelve la respuesta actualmente seleccionada para la pregunta dada.
     * Maneja radios (única), selects y checkboxes (devuelve el primero marcado).
     * Si no hay respuesta devuelve null.
     */
    _getSelectedAnswer(questionId) {
        const $q = this.$(`.js_question-wrapper[data-question-id='${questionId}']`);
        if (!$q.length) return null;

        // Radio (opción única)
        const $r = $q.find("input[type='radio']:checked");
        if ($r.length) return $r.data("answer-id") ?? $r.val();

        // Select
        const $s = $q.find("select");
        if ($s.length) {
            const $opt = $s.find("option:selected");
            return $opt.data("answer-id") ?? $opt.val();
        }

        // Checkbox (múltiple): tomamos el primero marcado (gatillo binario típico)
        const $c = $q.find("input[type='checkbox']:checked");
        if ($c.length) return $c.first().data("answer-id") ?? $c.first().val();

        return null;
        // Nota: para matrices u otros tipos, se podría ampliar aquí.
    },

    /**
     * _clearAnswer($q)
     * Limpia los inputs de una pregunta (radios, checkboxes, selects y campos
     * tipo texto) para evitar envíos con datos de preguntas ocultas.
     */
    _clearAnswer($q) {
        $q.find("input[type='radio'], input[type='checkbox']").prop("checked", false);
        $q.find("select").val("");
        $q.find("input[type='text'], textarea, input[type='number'], input[type='email']").val("");
    },

    /**
     * _toggleRequired($q, makeRequired)
     * Activa o desactiva el atributo `required` en los inputs de la pregunta
     * respetando si originalmente la pregunta era requerida. Evita asignar
     * `required` a inputs ocultos para no romper validaciones HTML5.
     */
    _toggleRequired($q, makeRequired) {
        const originally = Boolean($q.data("originally-required"));
        const $inputs = $q.find("input, select, textarea");
        const $label = $q.find(".js_question_label");

        if (makeRequired && originally) {
            // Evitar required en inputs ocultos (HTML5 valida incluso si display:none)
            $inputs.each((_, el) => {
                const $el = $(el);
                if ($el.is(":visible")) $el.prop("required", true);
            });
            $label.addClass("o_survey_required");
        } else {
            $inputs.prop("required", false);
            $label.removeClass("o_survey_required");
        }
    },
});

export default publicWidget.registry.SurveyConditionalQuestions;
