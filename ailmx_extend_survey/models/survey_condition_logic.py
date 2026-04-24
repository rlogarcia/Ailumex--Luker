# -*- coding: utf-8 -*-

from odoo import models
import logging

_logger = logging.getLogger(__name__)


class SurveySurvey(models.Model):
    _inherit = 'survey.survey'

    def _get_question_answer_value(self, user_input, question):
        """
        Obtiene el valor de respuesta guardado para una pregunta específica.
        Siempre devuelve texto para facilitar comparaciones.
        """
        if not question:
            return ""

        answer_lines = user_input.user_input_line_ids.filtered(
            lambda l: l.question_id.id == question.id
        )

        if not answer_lines:
            _logger.warning(
                "[COND_RULES] No se encontraron líneas de respuesta para la pregunta %s (%s)",
                question.id, question.display_name
            )
            return ""

        values = []

        for line in answer_lines:
            value = ""

            if getattr(line, 'suggested_answer_id', False):
                value = line.suggested_answer_id.value or line.suggested_answer_id.display_name or ""

            elif getattr(line, 'value_char_box', False):
                value = line.value_char_box or ""

            elif getattr(line, 'value_text_box', False):
                value = line.value_text_box or ""

            elif getattr(line, 'value_numerical_box', False) not in (False, None):
                value = str(line.value_numerical_box)

            elif getattr(line, 'value_date', False):
                value = str(line.value_date)

            elif getattr(line, 'value_datetime', False):
                value = str(line.value_datetime)

            elif getattr(line, 'value_free_text', False):
                value = line.value_free_text or ""

            value = (value or "").strip()

            if value:
                values.append(value)

        final_value = ", ".join(values).strip()

        _logger.warning(
            "[COND_RULES] Pregunta %s (%s) -> valor leído: %s",
            question.id, question.display_name, final_value
        )

        return final_value

    def _normalize_rule_value(self, value):
        """
        Normaliza un valor para comparaciones de reglas.

        - Convierte None a cadena vacía
        - Quita espacios
        - Si parece número, lo devuelve como float
        - Si no, lo devuelve como texto en minúscula
        """
        value = (value or "").strip()

        if value == "":
            return ""

        try:
            return float(value)
        except Exception:
            return value.lower()

    def _evaluate_rule_operator(self, actual_value, operator, expected_value):
        """
        Evalúa una comparación simple entre valor real y valor esperado.

        Mejoras:
        - texto sin sensibilidad a mayúsculas/minúsculas
        - números comparados como números reales
        - 20 y 20.0 se consideran iguales
        """
        actual_raw = (actual_value or "").strip()
        expected_raw = (expected_value or "").strip()

        actual = self._normalize_rule_value(actual_raw)
        expected = self._normalize_rule_value(expected_raw)

        result = False

        if operator == "eq":
            result = actual == expected

        elif operator == "neq":
            result = actual != expected

        elif operator == "contains":
            result = str(expected).lower() in str(actual).lower()

        elif operator == "not_contains":
            result = str(expected).lower() not in str(actual).lower()

        elif operator == "gt":
            try:
                result = float(actual) > float(expected)
            except Exception:
                result = False

        elif operator == "lt":
            try:
                result = float(actual) < float(expected)
            except Exception:
                result = False

        _logger.warning(
            "[COND_RULES] Comparación -> actual_raw='%s' | expected_raw='%s' | actual='%s' | expected='%s' | operador='%s' | resultado=%s",
            actual_raw, expected_raw, actual, expected, operator, result
        )

        return result

    def _evaluate_finish_condition_rule(self, user_input, current_question, rule):
        """
        Evalúa una regla completa.

        Soporta:
        - source_type = current / other
        - logic = and / or
        - operadores eq / neq / contains / not_contains / gt / lt
        """
        if not rule:
            return False

        # ---------------------------------------------------------
        # Regla por tiempo
        # ---------------------------------------------------------
        if (rule.get("trigger_type") or "answer") == "time":
            try:
                from odoo.http import request
                return str(request.params.get("ailmx_time_rule_triggered")) == "1"
            except Exception:
                return False

        conditions = rule.get("conditions", [])
        logic = (rule.get("logic") or "and").lower()

        if not conditions:
            _logger.warning("[COND_RULES] Regla sin condiciones")
            return False

        results = []

        _logger.warning(
            "[COND_RULES] Evaluando regla en pregunta actual %s (%s) | logic=%s | action=%s",
            current_question.id,
            current_question.display_name,
            logic,
            rule.get("action")
        )

        for index, cond in enumerate(conditions, start=1):
            source_type = (cond.get("source_type") or "current").strip()
            operator = (cond.get("operator") or "eq").strip()
            expected_value = (cond.get("value") or "").strip()

            compare_question = self.env['survey.question']

            if source_type == "current":
                compare_question = current_question

            elif source_type == "other":
                compare_question_id = cond.get("compare_question_id")
                if compare_question_id:
                    compare_question = self.env['survey.question'].browse(int(compare_question_id))

            if not compare_question:
                _logger.warning(
                    "[COND_RULES] Condición %s -> no se encontró pregunta a comparar",
                    index
                )
                results.append(False)
                continue

            actual_value = self._get_question_answer_value(user_input, compare_question)

            result = self._evaluate_rule_operator(
                actual_value=actual_value,
                operator=operator,
                expected_value=expected_value,
            )

            _logger.warning(
                "[COND_RULES] Condición %s -> source_type=%s | pregunta=%s (%s) | esperado='%s' | resultado=%s",
                index,
                source_type,
                compare_question.id,
                compare_question.display_name,
                expected_value,
                result
            )

            results.append(result)

        final_result = any(results) if logic == "or" else all(results)

        _logger.warning(
            "[COND_RULES] Resultado final regla -> results=%s | logic=%s | final=%s",
            results,
            logic,
            final_result
        )

        return final_result

    def _get_last_question_for_conditional_navigation(self, user_input):
        """
        Devuelve la última pregunta real de la encuesta para navegación condicional.
        """
        self.ensure_one()

        questions = self.question_ids.sorted(key=lambda q: (q.sequence, q.id))

        if not questions:
            return self.env['survey.question']

        return questions[-1]

    def _get_next_page_or_question(self, user_input, current_page_or_question_id, go_back=False):
        """
        Lógica personalizada de navegación de encuesta.
        Permite saltar, finalizar, ir a última pregunta o bloquear avance
        según condiciones definidas.
        """
        next_page = super()._get_next_page_or_question(
            user_input,
            current_page_or_question_id,
            go_back=go_back
        )

        if go_back:
            return next_page

        current_question = self.env['survey.question'].browse(current_page_or_question_id)

        if not current_question or not current_question.finish_conditions_json:
            user_input.conditional_block_message = False
            return next_page

        rules = current_question.finish_conditions_json or []

        _logger.warning(
            "[COND_RULES] Revisando reglas en pregunta %s (%s). Total reglas: %s",
            current_question.id,
            current_question.display_name,
            len(rules)
        )

        for rule in rules:
            rule_matches = self._evaluate_finish_condition_rule(
                user_input=user_input,
                current_question=current_question,
                rule=rule,
            )

            if not rule_matches:
                continue

            action = (rule.get("action") or "").strip()

            # Acción: ir a una pregunta específica
            if action == "go_to_question":
                user_input.conditional_block_message = False

                target_id = rule.get("target_question_id")
                if target_id:
                    target_question = self.env['survey.question'].browse(int(target_id))
                    if target_question:
                        return target_question

            # Acción: finalizar encuesta inmediatamente
            if action == "finish":
                user_input.conditional_block_message = False
                user_input._mark_done()
                return self.env['survey.question']

            # Acción: ir a la última pregunta del instrumento
            if action == "end_page":
                user_input.conditional_block_message = False

                last_question = self._get_last_question_for_conditional_navigation(user_input)
                if last_question:
                    if current_question.id == last_question.id:
                        user_input._mark_done()
                        return self.env['survey.question']

                    return last_question

            # Acción: bloquear avance y mostrar mensaje
            if action == "block":
                user_input.conditional_block_message = (
                    rule.get("block_message")
                    or "No puedes continuar con esta respuesta."
                )
                return current_question

        # Si ninguna regla aplica, limpiar mensaje y seguir normal
        user_input.conditional_block_message = False
        return next_page