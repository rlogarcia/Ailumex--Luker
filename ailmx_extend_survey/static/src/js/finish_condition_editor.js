/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

export class FinishConditionEditor extends Component {
    static template = "ailmx_extend_survey.FinishConditionEditor";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.notification = useService("notification");
        this._uidCounter = 1;

        this.addRule = this.addRule.bind(this);
        this.removeRule = this.removeRule.bind(this);
        this.addSubCondition = this.addSubCondition.bind(this);
        this.removeSubCondition = this.removeSubCondition.bind(this);
        this.onRuleFieldChange = this.onRuleFieldChange.bind(this);
        this.onConditionFieldChange = this.onConditionFieldChange.bind(this);
        this.getRuleLabel = this.getRuleLabel.bind(this);
        this.getConditionLabel = this.getConditionLabel.bind(this);
        this.requiresTargetQuestion = this.requiresTargetQuestion.bind(this);
        this.usesOtherQuestion = this.usesOtherQuestion.bind(this);
        this.isAnswerRule = this.isAnswerRule.bind(this);
        this.isTimeRule = this.isTimeRule.bind(this);

        this.state = useState({
            rules: this._normalizeRules(this.props.record.data[this.props.name]),
            availableQuestions: this._buildAvailableQuestions(),
        });
    }

    _generateUid(prefix = "uid") {
        const uid = `${prefix}_${Date.now()}_${this._uidCounter}`;
        this._uidCounter += 1;
        return uid;
    }

    _buildAvailableQuestions() {
        return this.props.record.data.finish_condition_question_options || [];
    }

    _normalizeRules(rawValue) {
        if (!rawValue || !Array.isArray(rawValue)) {
            return [];
        }

        const looksLikeOldFormat = rawValue.length > 0 && !rawValue[0].conditions && !rawValue[0].trigger_type;

        if (looksLikeOldFormat) {
            return rawValue.map((item) => ({
                _uid: this._generateUid("rule"),
                trigger_type: "answer",
                logic: "and",
                action: item.action || "finish",
                target_question_id: item.target_question_id || false,
                time_value: 1,
                time_unit: "minutes",
                conditions: [
                    {
                        _uid: this._generateUid("cond"),
                        source_type: item.compare_question_id ? "other" : "current",
                        compare_question_id: item.compare_question_id || false,
                        operator: item.operator || "eq",
                        value: item.value || "",
                    },
                ],
            }));
        }

        return rawValue.map((rule) => ({
            _uid: this._generateUid("rule"),
            trigger_type: rule.trigger_type || "answer",
            logic: rule.logic || "and",
            action: rule.action || "finish",
            target_question_id: rule.target_question_id || false,
            time_value: rule.time_value || 1,
            time_unit: rule.time_unit || "minutes",
            conditions: Array.isArray(rule.conditions)
                ? rule.conditions.map((condition) => ({
                    _uid: this._generateUid("cond"),
                    source_type: condition.source_type || "current",
                    compare_question_id: condition.compare_question_id || false,
                    operator: condition.operator || "eq",
                    value: condition.value || "",
                }))
                : [],
        }));
    }

    _getSanitizedRules() {
        return this.state.rules.map((rule) => ({
            trigger_type: rule.trigger_type || "answer",
            logic: rule.logic || "and",
            action: rule.action || "finish",
            target_question_id: rule.target_question_id || false,
            time_value: rule.time_value || 1,
            time_unit: rule.time_unit || "minutes",
            conditions:
                (rule.trigger_type || "answer") === "answer"
                    ? (rule.conditions || []).map((condition) => ({
                        source_type: condition.source_type || "current",
                        compare_question_id:
                            (condition.source_type || "current") === "other"
                                ? (condition.compare_question_id || false)
                                : false,
                        operator: condition.operator || "eq",
                        value: condition.value || "",
                    }))
                    : [],
        }));
    }

    async _saveRules() {
        try {
            await this.props.record.update({
                [this.props.name]: this._getSanitizedRules(),
            });
        } catch (error) {
            this.notification.add(
                "No se pudieron guardar las reglas.",
                { type: "danger" }
            );
            console.error("Error guardando finish_conditions_json:", error);
        }
    }

    async addRule() {
        this.state.rules.push({
            _uid: this._generateUid("rule"),
            trigger_type: "answer",
            logic: "and",
            action: "finish",
            target_question_id: false,
            time_value: 1,
            time_unit: "minutes",
            conditions: [
                {
                    _uid: this._generateUid("cond"),
                    source_type: "current",
                    compare_question_id: false,
                    operator: "eq",
                    value: "",
                },
            ],
        });

        await this._saveRules();
    }

    async removeRule(ev) {
        const ruleIndex = parseInt(ev.currentTarget.dataset.ruleIndex, 10);

        if (Number.isNaN(ruleIndex)) {
            return;
        }

        if (ruleIndex < 0 || ruleIndex >= this.state.rules.length) {
            return;
        }

        this.state.rules.splice(ruleIndex, 1);
        await this._saveRules();
    }

    async addSubCondition(ev) {
        const ruleIndex = parseInt(ev.currentTarget.dataset.ruleIndex, 10);

        if (Number.isNaN(ruleIndex) || !this.state.rules[ruleIndex]) {
            return;
        }

        this.state.rules[ruleIndex].conditions.push({
            _uid: this._generateUid("cond"),
            source_type: "current",
            compare_question_id: false,
            operator: "eq",
            value: "",
        });

        await this._saveRules();
    }

    async removeSubCondition(ev) {
        const ruleIndex = parseInt(ev.currentTarget.dataset.ruleIndex, 10);
        const conditionIndex = parseInt(ev.currentTarget.dataset.conditionIndex, 10);

        if (
            Number.isNaN(ruleIndex) ||
            Number.isNaN(conditionIndex) ||
            !this.state.rules[ruleIndex] ||
            !this.state.rules[ruleIndex].conditions[conditionIndex]
        ) {
            return;
        }

        this.state.rules[ruleIndex].conditions.splice(conditionIndex, 1);

        if (this.state.rules[ruleIndex].conditions.length === 0) {
            this.state.rules[ruleIndex].conditions.push({
                _uid: this._generateUid("cond"),
                source_type: "current",
                compare_question_id: false,
                operator: "eq",
                value: "",
            });
        }

        await this._saveRules();
    }

    async onRuleFieldChange(ev) {
        const ruleIndex = parseInt(ev.currentTarget.dataset.ruleIndex, 10);
        const fieldName = ev.currentTarget.dataset.field;

        if (Number.isNaN(ruleIndex) || !fieldName || !this.state.rules[ruleIndex]) {
            return;
        }

        let value = ev.currentTarget.value;

        if (fieldName === "target_question_id") {
            value = value ? parseInt(value, 10) : false;
        }

        if (fieldName === "time_value") {
            value = parseInt(value || 1, 10);
            if (!value || value < 1) {
                value = 1;
            }
        }

        this.state.rules[ruleIndex][fieldName] = value;

        if (fieldName === "action" && value !== "go_to_question") {
            this.state.rules[ruleIndex].target_question_id = false;
        }

        if (fieldName === "trigger_type" && value === "time") {
            this.state.rules[ruleIndex].conditions = [];
            this.state.rules[ruleIndex].logic = "and";
        }

        if (fieldName === "trigger_type" && value === "answer" && this.state.rules[ruleIndex].conditions.length === 0) {
            this.state.rules[ruleIndex].conditions.push({
                _uid: this._generateUid("cond"),
                source_type: "current",
                compare_question_id: false,
                operator: "eq",
                value: "",
            });
        }

        await this._saveRules();
    }

    async onConditionFieldChange(ev) {
        const ruleIndex = parseInt(ev.currentTarget.dataset.ruleIndex, 10);
        const conditionIndex = parseInt(ev.currentTarget.dataset.conditionIndex, 10);
        const fieldName = ev.currentTarget.dataset.field;

        if (
            Number.isNaN(ruleIndex) ||
            Number.isNaN(conditionIndex) ||
            !fieldName ||
            !this.state.rules[ruleIndex] ||
            !this.state.rules[ruleIndex].conditions[conditionIndex]
        ) {
            return;
        }

        let value = ev.currentTarget.value;

        if (fieldName === "compare_question_id") {
            value = value ? parseInt(value, 10) : false;
        }

        this.state.rules[ruleIndex].conditions[conditionIndex][fieldName] = value;

        if (fieldName === "source_type" && value === "current") {
            this.state.rules[ruleIndex].conditions[conditionIndex].compare_question_id = false;
        }

        await this._saveRules();
    }

    getRuleLabel(index) {
        return `REGLA ${index + 1}`;
    }

    getConditionLabel(index) {
        return `CONDICIÓN ${index + 1}`;
    }

    requiresTargetQuestion(action) {
        return action === "go_to_question";
    }

    usesOtherQuestion(sourceType) {
        return sourceType === "other";
    }

    isAnswerRule(triggerType) {
        return triggerType === "answer";
    }

    isTimeRule(triggerType) {
        return triggerType === "time";
    }
}

export const finishConditionEditorField = {
    component: FinishConditionEditor,
    displayName: "Finish Condition Editor",
    supportedTypes: ["json"],
};

registry.category("fields").add("finish_condition_editor", finishConditionEditorField);