/** @odoo-module **/

console.log("[FINISH_RULES] frontend cargado");

// ============================================================
// FRONTEND LIGERO DE REGLAS CONDICIONALES
// ============================================================
//
// La navegación real la decide el backend en:
// models/survey_condition_logic.py
//
// Este archivo hace 2 cosas:
// 1. Deja logs básicos para validar qué pregunta/regla se está enviando.
// 2. Ejecuta reglas de tipo "Según tiempo" y manda una marca al backend.
// ============================================================


// ============================================================
// UTILIDADES
// ============================================================

function parseJSONSafe(rawValue, fallback = []) {
    try {
        return JSON.parse(rawValue || "[]");
    } catch (error) {
        console.warn("[FINISH_RULES] No se pudo parsear finish_conditions_json:", error);
        return fallback;
    }
}

function normalizeValue(value) {
    if (value === null || value === undefined) {
        return "";
    }
    return String(value).trim();
}

function getSurveyRoot() {
    return document.querySelector(".o_survey_form_content");
}

function getCurrentQuestionId(surveyRoot) {
    if (!surveyRoot) {
        return null;
    }

    const input = surveyRoot.querySelector(".o_finish_conditions_question_id");
    if (!input) {
        return null;
    }

    const value = parseInt(input.value, 10);
    return Number.isInteger(value) ? value : null;
}

function getCurrentRules(surveyRoot) {
    if (!surveyRoot) {
        return [];
    }

    const input = surveyRoot.querySelector(".o_finish_conditions_json");
    if (!input) {
        return [];
    }

    return parseJSONSafe(input.value, []);
}


// ============================================================
// LECTURA DE RESPUESTA ACTUAL PARA LOGS
// ============================================================

function getLabelTextForInput(input) {
    if (!input) {
        return "";
    }

    const parentLabel = input.closest("label");

    if (parentLabel) {
        const clone = parentLabel.cloneNode(true);

        clone.querySelectorAll("input").forEach((el) => el.remove());

        clone.querySelectorAll(
            ".o_survey_choice_key, .o_survey_choice_key_box, .badge, .form-check-input, .o_survey_choice_icon"
        ).forEach((el) => el.remove());

        const text = normalizeValue(clone.innerText || clone.textContent || "");

        const parts = text
            .split("\n")
            .map((part) => normalizeValue(part))
            .filter(Boolean);

        return parts.length ? parts[parts.length - 1] : text;
    }

    if (input.id) {
        const explicitLabel = document.querySelector(`label[for="${input.id}"]`);

        if (explicitLabel) {
            const text = normalizeValue(explicitLabel.innerText || explicitLabel.textContent || "");

            const parts = text
                .split("\n")
                .map((part) => normalizeValue(part))
                .filter(Boolean);

            return parts.length ? parts[parts.length - 1] : text;
        }
    }

    return "";
}

function getCurrentAnswer(surveyRoot) {
    if (!surveyRoot) {
        return "";
    }

    const checkedRadio = surveyRoot.querySelector("input[type='radio']:checked");
    if (checkedRadio) {
        const labelText = getLabelTextForInput(checkedRadio);
        return labelText || checkedRadio.value || "";
    }

    const checkedCheckboxes = surveyRoot.querySelectorAll("input[type='checkbox']:checked");
    if (checkedCheckboxes.length) {
        return Array.from(checkedCheckboxes)
            .map((input) => {
                const labelText = getLabelTextForInput(input);
                return labelText || input.value || "";
            })
            .join(", ");
    }

    const textarea = surveyRoot.querySelector("textarea");
    if (textarea) {
        return textarea.value || "";
    }

    const input = surveyRoot.querySelector(
        "input[type='text'], input[type='number'], input[type='date'], input[type='datetime-local']"
    );
    if (input) {
        return input.value || "";
    }

    const select = surveyRoot.querySelector("select");
    if (select) {
        const selectedOption = select.options[select.selectedIndex];
        return selectedOption ? (selectedOption.text || selectedOption.value || "") : "";
    }

    return "";
}


// ============================================================
// LOGS DE SUBMIT NORMAL
// ============================================================

function bindFinishRulesLogs() {
    const nextButtons = document.querySelectorAll(
        ".o_survey_navigation_submit, .o_survey_form_content button[type='submit'], .o_survey_next, .js_next"
    );

    nextButtons.forEach((button) => {
        if (button.dataset.finishRulesBound === "1") {
            return;
        }

        button.dataset.finishRulesBound = "1";

        button.addEventListener(
            "click",
            function () {
                const surveyRoot = getSurveyRoot();
                const currentQuestionId = getCurrentQuestionId(surveyRoot);
                const rules = getCurrentRules(surveyRoot);
                const answer = getCurrentAnswer(surveyRoot);

                console.log("[FINISH_RULES] submit permitido hacia backend", {
                    currentQuestionId,
                    answer,
                    rules,
                });
            },
            true
        );
    });
}


// ============================================================
// REGLAS POR TIEMPO
// ============================================================

let ailmxTimeRuleTimer = null;
let ailmxTimeRuleKey = null;

window.ailmxTimeRuleTriggered = false;

function getTimeRuleFromCurrentQuestion() {
    const surveyRoot = getSurveyRoot();

    if (!surveyRoot) {
        return null;
    }

    const questionIdInput = surveyRoot.querySelector(".o_finish_conditions_question_id");
    const rulesInput = surveyRoot.querySelector(".o_finish_conditions_json");

    if (!questionIdInput || !rulesInput) {
        return null;
    }

    let rules = [];

    try {
        rules = JSON.parse(rulesInput.value || "[]");
    } catch (error) {
        console.warn("[FINISH_RULES] No se pudieron leer reglas de tiempo", error);
        return null;
    }

    return rules.find((rule) => rule.trigger_type === "time") || null;
}

function startConditionalTimeRule() {
    const surveyRoot = getSurveyRoot();

    if (!surveyRoot) {
        return;
    }

    const questionIdInput = surveyRoot.querySelector(".o_finish_conditions_question_id");
    const rule = getTimeRuleFromCurrentQuestion();

    if (!questionIdInput || !rule) {
        if (ailmxTimeRuleTimer) {
            clearTimeout(ailmxTimeRuleTimer);
            ailmxTimeRuleTimer = null;
            ailmxTimeRuleKey = null;
        }
        return;
    }

    const questionId = questionIdInput.value;
    const timeValue = parseInt(rule.time_value || 1, 10);
    const timeUnit = rule.time_unit || "minutes";

    const milliseconds = timeUnit === "seconds"
        ? timeValue * 1000
        : timeValue * 60 * 1000;

    const newKey = `${questionId}-${timeValue}-${timeUnit}-${rule.action}-${rule.target_question_id || ""}`;

    if (ailmxTimeRuleKey === newKey) {
        return;
    }

    if (ailmxTimeRuleTimer) {
        clearTimeout(ailmxTimeRuleTimer);
    }

    ailmxTimeRuleKey = newKey;

    console.log("[FINISH_RULES] iniciando regla de tiempo", {
        questionId,
        timeValue,
        timeUnit,
        milliseconds,
        rule,
    });

    ailmxTimeRuleTimer = setTimeout(function () {
        console.log("[FINISH_RULES] tiempo cumplido, enviando regla");

        window.ailmxTimeRuleTriggered = true;

        const nextButton =
            document.querySelector(".o_survey_navigation_submit") ||
            document.querySelector(".o_survey_form_content button[type='submit']") ||
            document.querySelector(".o_survey_next") ||
            document.querySelector(".js_next");

        if (nextButton) {
            nextButton.click();
        } else {
            console.warn("[FINISH_RULES] No se encontró botón para enviar regla de tiempo");
        }
    }, milliseconds);
}


// ============================================================
// INYECTAR MARCA DE TIEMPO EN EL SUBMIT JSON DE SURVEY
// ============================================================
//
// Odoo Survey envía las respuestas por JSON-RPC.
// Por eso no basta con crear un input hidden.
// Hay que interceptar el XMLHttpRequest y agregar:
// ailmx_time_rule_triggered = "1"
// dentro de payload.params.
// ============================================================

(function patchSurveySubmitXHR() {
    if (window.ailmxFinishRulesXHRPatched) {
        return;
    }

    window.ailmxFinishRulesXHRPatched = true;

    const originalOpen = XMLHttpRequest.prototype.open;
    const originalSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function (method, url) {
        this._ailmxSurveyUrl = url || "";
        return originalOpen.apply(this, arguments);
    };

    XMLHttpRequest.prototype.send = function (body) {
        if (
            window.ailmxTimeRuleTriggered &&
            this._ailmxSurveyUrl &&
            this._ailmxSurveyUrl.includes("/survey/submit/")
        ) {
            try {
                const payload = JSON.parse(body);

                if (!payload.params) {
                    payload.params = {};
                }

                payload.params.ailmx_time_rule_triggered = "1";

                console.log("[FINISH_RULES] marca de tiempo enviada al backend");

                window.ailmxTimeRuleTriggered = false;

                return originalSend.call(this, JSON.stringify(payload));
            } catch (error) {
                console.warn("[FINISH_RULES] no se pudo modificar payload de tiempo", error);
            }
        }

        return originalSend.apply(this, arguments);
    };
})();


// ============================================================
// INICIALIZACIÓN
// ============================================================

function initFinishConditions() {
    bindFinishRulesLogs();
    startConditionalTimeRule();

    const surveyBody = document.querySelector(".o_survey_form_content");

    if (surveyBody) {
        new MutationObserver(function () {
            bindFinishRulesLogs();
            startConditionalTimeRule();
        }).observe(surveyBody, {
            childList: true,
            subtree: true,
        });
    }
}

document.addEventListener("DOMContentLoaded", initFinishConditions);