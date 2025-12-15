/** @odoo-module **/
/**
 * Lógica frontend para preguntas WPM (lectura y escritura).
 * Calcula palabras por minuto y sincroniza los datos con el backend.
 * 
 * INTEGRACIÓN CON CRONÓMETRO:
 * - Compatible con el sistema de cronómetro general y por pregunta
 * - El tiempo WPM se sincroniza con el cronómetro de pregunta si está activo
 * - Respeta los límites de tiempo configurados
 */

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";

const PAD_TWO = (value) => value.toString().padStart(2, "0");

const parseBoolean = (value) => {
    if (typeof value === "boolean") {
        return value;
    }
    if (typeof value === "number") {
        return !!value;
    }
    if (typeof value === "string") {
        const normalized = value.trim().toLowerCase();
        return normalized === "true" || normalized === "1";
    }
    return false;
};

const formatDuration = (seconds) => {
    if (!seconds || seconds < 0) {
        return "00:00";
    }
    const total = Math.floor(seconds);
    const mins = Math.floor(total / 60);
    const secs = total % 60;
    return `${PAD_TWO(mins)}:${PAD_TWO(secs)}`;
};

const countWords = (text) => {
    if (!text) {
        return 0;
    }
    const tokens = text.trim().split(/\s+/);
    return tokens.filter(Boolean).length;
};

const ensureReadingQuestionStart = ($question) => {
    const $startInput = $question.find(".o_wpm_start_timestamp");
    let startValue = $startInput.val();
    let startDate = startValue ? new Date(startValue) : null;

    if (!startValue || Number.isNaN(startDate?.getTime())) {
        startDate = new Date();
        $startInput.val(startDate.toISOString());
    }

    if (!$question.data("wpm-start-ms")) {
        $question.data("wpm-start-ms", startDate.getTime());
    }

    return startDate;
};

const finalizeReadingQuestion = ($question) => {
    const wordCount = parseInt($question.data("word-count"), 10) || 0;
    const startTime = ensureReadingQuestionStart($question);
    if (!startTime || Number.isNaN(startTime.getTime())) {
            console.warn("WPM reading timestamp inválido", $question.data("question-id"));
        return;
    }
    const endTime = new Date();
    const elapsedSeconds = Math.max((endTime - startTime) / 1000, 0);
    const wpm = elapsedSeconds > 0 ? (wordCount / elapsedSeconds) * 60 : 0;

    $question.find(".o_wpm_completed").val("1");
    $question.find(".o_wpm_time_input").val(elapsedSeconds.toFixed(2));
    $question.find(".o_wpm_word_count_input").val(wordCount);
    $question.find(".o_wpm_score_input").val(wpm.toFixed(2));
    $question.find(".o_wpm_end_timestamp").val(endTime.toISOString());
    $question.find(".o_wpm_answer_flag").val("1");

        console.debug("WPM lectura calculado", {
            questionId: $question.data("question-id"),
            wordCount,
            elapsedSeconds,
            wpm,
        });
};

const finalizeTypingQuestion = ($question) => {
    const $textarea = $question.find(".o_wpm_typing_area");
    const rawText = $textarea.val() || "";
    const trimmed = rawText.trim();

    const $startInput = $question.find(".o_wpm_start_timestamp");
    let startTime = null;
    if ($startInput.val()) {
        const parsed = new Date($startInput.val());
        startTime = Number.isNaN(parsed.getTime()) ? null : parsed;
    }
    if (!startTime && trimmed) {
        startTime = new Date();
        $startInput.val(startTime.toISOString());
    }

    const wordCount = countWords(trimmed);
    const endTime = new Date();
    const elapsedSeconds = startTime ? Math.max((endTime - startTime) / 1000, 0) : 0;
    const wpm = elapsedSeconds > 0 ? (wordCount / elapsedSeconds) * 60 : 0;

    const completed = Boolean(trimmed);

    $question.find(".o_wpm_word_count_input").val(wordCount);
    $question.find(".o_wpm_typed_text_input").val(rawText);

    if (completed) {
        $question.find(".o_wpm_completed").val("1");
        $question.find(".o_wpm_time_input").val(elapsedSeconds.toFixed(2));
        $question.find(".o_wpm_score_input").val(wpm.toFixed(2));
        $question.find(".o_wpm_end_timestamp").val(endTime.toISOString());
        $question.find(".o_wpm_answer_flag").val("1");
            console.debug("WPM typing calculado", {
                questionId: $question.data("question-id"),
                wordCount,
                elapsedSeconds,
                wpm,
            });
    } else {
        $question.find(".o_wpm_completed").val("0");
        $question.find(".o_wpm_time_input").val("");
        $question.find(".o_wpm_score_input").val("");
        $question.find(".o_wpm_end_timestamp").val("");
        $question.find(".o_wpm_answer_flag").val("");
        $question.find(".o_wpm_start_timestamp").val("");
    }

    return {
        completed,
        wordCount,
        elapsedSeconds,
        wpm,
        rawText,
    };
};

// Lectura -------------------------------------------------------------------

publicWidget.registry.SurveyWPMReading = publicWidget.Widget.extend({
    selector: ".o_survey_question_wpm_reading",

    start() {
        const result = this._super.apply(this, arguments);
        return Promise.resolve(result).then(() => {
            this.questionId = this.$el.data("question-id");
            this.wordCount = this.$el.data("word-count") || 0;
            ensureReadingQuestionStart(this.$el);
            const $wordInput = this.$(".o_wpm_word_count_input");
            if (!$wordInput.val()) {
                $wordInput.val(this.wordCount);
            }
            this.$(".o_wpm_completed").val("0");
            this.$(".o_wpm_answer_flag").val("");
        });
    },
});

// Escritura -----------------------------------------------------------------

publicWidget.registry.SurveyWPMTyping = publicWidget.Widget.extend({
    selector: ".o_survey_question_wpm_typing",

    events: {
        "input .o_wpm_typing_area": "_onTypingInput",
        "paste .o_wpm_typing_area": "_onPaste",
        "click .o_wpm_typing_finish_btn": "_onFinish",
    },

    start() {
        const result = this._super.apply(this, arguments);
        return Promise.resolve(result).then(() => {
            this.$textarea = this.$(".o_wpm_typing_area");
            this.$finishBtn = this.$(".o_wpm_typing_finish_btn");
            this.$timerDisplay = this.$(".o_wpm_timer_display");
            this.$wordCountDisplay = this.$(".o_wpm_word_count_display");
            this.$charCountDisplay = this.$(".o_wpm_char_count_display");
            this.$currentWpmDisplay = this.$(".o_wpm_current_wpm");
            this.$resultScreen = this.$(".o_wpm_result_screen");
            this.$finalScore = this.$(".o_wpm_final_score");
            this.$finalWords = this.$(".o_wpm_final_words");
            this.$classificationBadge = this.$(".o_wpm_classification_badge");

            this.showTimer = parseBoolean(this.$el.data("show-timer"));
            this.allowPaste = parseBoolean(this.$el.data("allow-paste"));
            this.thresholds = {
                slow: parseInt(this.$el.data("slow-threshold"), 10) || 0,
                average: parseInt(this.$el.data("average-threshold"), 10) || 0,
                fast: parseInt(this.$el.data("fast-threshold"), 10) || 0,
            };

            this.startTime = null;
            this.latestWordCount = 0;
            this.completed = false;
            this._timerHandle = null;

            this.$finishBtn.prop("disabled", true);
            this.$(".o_wpm_completed").val("0");
            this.$(".o_wpm_answer_flag").val("");

            const completed = this.$(".o_wpm_completed").val() === "1";
            if (completed) {
                this._restorePreviousResult();
            }
        });
    },

    destroy() {
        if (this._timerHandle) {
            clearInterval(this._timerHandle);
        }
        return this._super.apply(this, arguments);
    },

    _restorePreviousResult() {
        const wordCount = parseInt(this.$(".o_wpm_word_count_input").val(), 10) || 0;
        const elapsedSeconds = parseFloat(this.$(".o_wpm_time_input").val()) || 0;
    const parsedWpm = parseFloat(this.$(".o_wpm_score_input").val());
    const wpm = Number.isFinite(parsedWpm) ? parsedWpm : 0;
        const rawText = this.$(".o_wpm_typed_text_input").val() || "";

        this.$textarea.val(rawText);
        this.$wordCountDisplay.text(wordCount);
        this.$charCountDisplay.text(rawText.length);
        this.$currentWpmDisplay.text(wpm.toFixed(2));
        if (this.showTimer) {
            this.$timerDisplay.text(formatDuration(elapsedSeconds));
        }

        this._showResult({
            completed: true,
            wordCount,
            elapsedSeconds,
            wpm,
            rawText,
        });
        this.completed = true;
        this.$finishBtn.prop("disabled", false).removeClass("btn-success").addClass("btn-secondary");
    },

    _onPaste(ev) {
        if (!this.allowPaste) {
            ev.preventDefault();
            ev.stopPropagation();
        }
    },

    _onTypingInput() {
        const rawText = this.$textarea.val() || "";
        const trimmed = rawText.trim();

        if (this.completed) {
            this._resetMeasurementState();
        }

        if (!trimmed) {
            this.latestWordCount = 0;
            this.$wordCountDisplay.text("0");
            this.$charCountDisplay.text(rawText.length);
            this.$currentWpmDisplay.text("0");
            if (this.showTimer) {
                this.$timerDisplay.text("00:00");
            }
            this.$finishBtn.prop("disabled", true);
            this.$(".o_wpm_word_count_input").val(0);
            this.$(".o_wpm_typed_text_input").val("");
            return;
        }

        if (!this.startTime) {
            this.startTime = new Date();
            this.$(".o_wpm_start_timestamp").val(this.startTime.toISOString());
            this.$finishBtn.prop("disabled", false);
            this._startTimerTick();
        }

        const wordCount = countWords(trimmed);
        this.latestWordCount = wordCount;
        this.$wordCountDisplay.text(wordCount);
        this.$charCountDisplay.text(rawText.length);
        this.$(".o_wpm_word_count_input").val(wordCount);
        this.$(".o_wpm_typed_text_input").val(rawText);

        this._refreshRunningMetrics();
    },

    _startTimerTick() {
        if (this._timerHandle) {
            clearInterval(this._timerHandle);
        }
        if (!this.showTimer) {
            return;
        }
        this._timerHandle = setInterval(() => {
            this._refreshRunningMetrics();
        }, 300);
    },

    _refreshRunningMetrics() {
        if (!this.startTime) {
            return;
        }
        const seconds = Math.max((Date.now() - this.startTime.getTime()) / 1000, 0);
        if (this.showTimer) {
            this.$timerDisplay.text(formatDuration(seconds));
        }
        const wpm = seconds > 0 ? (this.latestWordCount / seconds) * 60 : 0;
        this.$currentWpmDisplay.text(wpm > 0 ? wpm.toFixed(2) : "0");
    },

    _resetMeasurementState() {
        this.completed = false;
        this.startTime = null;
        this.latestWordCount = 0;
        if (this._timerHandle) {
            clearInterval(this._timerHandle);
            this._timerHandle = null;
        }
        this.$(".o_wpm_completed").val("0");
        this.$(".o_wpm_time_input").val("");
        this.$(".o_wpm_score_input").val("");
        this.$(".o_wpm_end_timestamp").val("");
        this.$(".o_wpm_start_timestamp").val("");
        this.$(".o_wpm_answer_flag").val("");
        this.$(".o_wpm_typed_text_input").val("");
        this.$(".o_wpm_word_count_input").val(0);
        this.$resultScreen.hide();
        this.$finishBtn.prop("disabled", true)
            .removeClass("btn-secondary")
            .addClass("btn-success");
        this.$wordCountDisplay.text("0");
        this.$currentWpmDisplay.text("0");
        this.$charCountDisplay.text(this.$textarea.val().length);
        if (this.showTimer) {
            this.$timerDisplay.text("00:00");
        }
    },

    _onFinish(ev) {
        ev.preventDefault();
        const result = finalizeTypingQuestion(this.$el);
        if (!result || !result.completed) {
            return;
        }
            console.debug("WPM typing finalizado", {
                questionId: this.$el.data("question-id"),
                result,
            });
        if (this._timerHandle) {
            clearInterval(this._timerHandle);
            this._timerHandle = null;
        }
        this.completed = true;
        this.startTime = null;
        this.latestWordCount = result.wordCount;
        this._showResult(result);
        this.$finishBtn.prop("disabled", false).removeClass("btn-success").addClass("btn-secondary");
    },

    _showResult(result) {
        const { elapsedSeconds, wordCount } = result;
        const safeWpm = Number.isFinite(result.wpm) ? result.wpm : 0;
        this.$finalScore.text(safeWpm ? safeWpm.toFixed(2) : "0");
        this.$finalWords.text(wordCount);
        if (this.showTimer) {
            this.$timerDisplay.text(formatDuration(elapsedSeconds));
        }

        const classification = this._classifyWpm(safeWpm);
        this.$classificationBadge
            .text(classification.label)
            .removeClass("bg-danger bg-warning bg-info bg-success bg-secondary")
            .addClass(classification.badgeClass);

        this.$resultScreen.show();
    },

    _classifyWpm(wpm) {
        const labels = {
            slow: { label: _t("Lento"), badgeClass: "bg-danger" },
            average: { label: _t("Promedio"), badgeClass: "bg-warning" },
            fast: { label: _t("Rápido"), badgeClass: "bg-info" },
            exceptional: { label: _t("Excepcional"), badgeClass: "bg-success" },
        };

        if (!wpm || wpm <= 0) {
            return labels.slow;
        }
        if (this.thresholds.slow && wpm < this.thresholds.slow) {
            return labels.slow;
        }
        if (this.thresholds.average && wpm < this.thresholds.average) {
            return labels.average;
        }
        if (this.thresholds.fast && wpm < this.thresholds.fast) {
            return labels.fast;
        }
        return labels.exceptional;
    },
});

const SurveyFormWidget = publicWidget.registry.SurveyFormWidget;

if (SurveyFormWidget) {
    SurveyFormWidget.include({
        start() {
            const result = this._super.apply(this, arguments);
            return Promise.resolve(result).then(() => {
                this._initWpmQuestions();
            });
        },

        _onNextScreenDone() {
            const result = this._super.apply(this, arguments);
            this._initWpmQuestions();
            return result;
        },

        _onSubmit(ev) {
            this.$(".o_survey_question_wpm_reading:visible").each((idx, element) => {
                finalizeReadingQuestion($(element));
            });

            this.$(".o_survey_question_wpm_typing:visible").each((idx, element) => {
                finalizeTypingQuestion($(element));
            });

            return this._super.apply(this, arguments);
        },

        _prepareSubmitValues(formData, params) {
            this._super.apply(this, arguments);

            const grouped = {};
            formData.forEach((value, key) => {
                const match = key && key.match(/^([0-9]+)_wpm_(.+)$/);
                if (!match) {
                    return;
                }
                const questionId = match[1];
                const suffix = match[2];
                grouped[questionId] = grouped[questionId] || {};
                grouped[questionId][`wpm_${suffix}`] = value;
            });

            Object.entries(grouped).forEach(([questionId, data]) => {
                if (!Object.keys(data).length) {
                    return;
                }
                const existing = params[questionId];
                if (!existing) {
                    params[questionId] = data;
                } else if (Array.isArray(existing)) {
                    existing.push(data);
                } else if (typeof existing === "object") {
                    params[questionId] = Object.assign({}, existing, data);
                } else {
                    params[questionId] = [existing, data];
                }
            });
        },

        _initWpmQuestions() {
            this.$(".o_survey_question_wpm_reading").each((idx, element) => {
                const $question = $(element);
                const startDate = ensureReadingQuestionStart($question);
                if (!startDate) {
                    return;
                }
                const completed = $question.find(".o_wpm_completed").val() === "1";
                if (!completed) {
                    const wordCount = parseInt($question.data("word-count"), 10) || 0;
                    const $wordInput = $question.find(".o_wpm_word_count_input");
                    if (!$wordInput.val()) {
                        $wordInput.val(wordCount);
                    }
                    $question.find(".o_wpm_answer_flag").val("");
                    $question.find(".o_wpm_time_input").val("");
                    $question.find(".o_wpm_score_input").val("");
                    $question.find(".o_wpm_end_timestamp").val("");
                }
            });
        },
    });
}
