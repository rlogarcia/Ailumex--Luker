# -*- coding: utf-8 -*-

import json
from odoo import models, api


class SurveyUserInputLineExtension(models.Model):
    _inherit = 'survey.user_input.line'  # Se hereda el modelo nativo de Odoo que guarda cada respuesta cuando el participante responde

    @api.model_create_multi  # Es el decorador correcto para sobreescribir el método create
    def create(self, vals_list):

        # Super() guarda el método original sin modificación
        records = super().create(vals_list)

        # Por cada respuesta que Odoo guarda, se copia a survey_response_line
        for record in records:
            try:
                # =====================================================
                # CASO ESPECIAL: GRID LECTURA
                # =====================================================
                # NO lo copiamos aquí porque reading_grid ya se guarda
                # directamente desde survey_user_input_custom_save.py
                # =====================================================
                if record.question_id.question_type == 'reading_grid':
                    continue

                value = self._extract_value(record)  # Se extrae el valor de la respuesta

                # Se valida el valor contra el esquema del tipo de pregunta
                record.question_id.validate_response(value)

                # Se llama el metodo save_response que decide en que columna guardar
                self.env['survey.response.line'].save_response(
                    response_header_id=record.user_input_id.id,
                    question_id=record.question_id.id,
                    value=value
                )

            except Exception as error:
                print("ERROR copiando a survey.response.line:", error)

        return records

    # METODO _extract_value
    # Este metodo identifica cual campo tiene valor y lo devuelve para pasarlo a save_response
    def _extract_value(self, record):

        # =========================================================
        # CASO ESPECIAL: GRID LECTURA
        # =========================================================
        # La respuesta viene serializada en JSON dentro de value_text_box.
        # La convertimos a estructura Python para que save_response
        # la guarde como Val_JSON.
        # =========================================================
        if record.question_id.question_type == 'reading_grid' and record.value_text_box:
            try:
                return json.loads(record.value_text_box)
            except (json.JSONDecodeError, TypeError):
                return record.value_text_box

        # Texto de una línea — preguntas tipo cuadro de texto de una línea
        if record.value_char_box:
            return record.value_char_box

        # Texto largo — preguntas de tipo text_box
        elif record.value_text_box:
            return record.value_text_box

        # Opción seleccionada — preguntas radio o checkbox
        elif record.suggested_answer_id:
            return record.suggested_answer_id.value

        # Valor numérico — preguntas number
        elif record.value_numerical_box is not None and record.value_numerical_box != 0:
            return record.value_numerical_box

        # Valor escala — preguntas scale
        elif record.value_scale is not None and record.value_scale != 0:
            return record.value_scale

        # Fecha — preguntas de tipo date
        elif record.value_date:
            return record.value_date

        # Fecha y hora — preguntas de tipo datetime
        elif record.value_datetime:
            return record.value_datetime

        # Si ningún campo tiene valor devuelve vacío
        else:
            return ''