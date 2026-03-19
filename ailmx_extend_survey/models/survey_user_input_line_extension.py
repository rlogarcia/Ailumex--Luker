# -*- coding: utf-8 -*-

from odoo import models, api

class SurveyUserInputLineExtension(models.Model):
    _inherit = 'survey.user_input.line' # Se hereda el modelo nativo de Odoo que guarda cada respuesta cuando el participante responde

    @api.model_create_multi # Es el decorador correcto para sobreescribir el método create
    def create(self, vals_list):

        # Super() guarda el método original sin modificación
        records = super().create(vals_list)

        # Por cada respuesta que Odoo guarda, se copia a survey_response_line
        for record in records:
            try:
                value = self._extract_value(record) # Se extrae el valor de la respuesta

                # Se valida el valor contra el esquema del tipo de pregunta
                # Si el valor no cumple las reglas, lanza un ValueError
                record.question_id.validate_response(value)

                # Se llama el metodo save_response que decide en que columna guardar
                self.env['survey.response.line'].save_response(
                    response_header_id=record.user_input_id.id,
                    question_id=record.question_id.id,
                    value=value
                )
            except Exception:
                # Si algo falla no se interrumpe la encuesta
                # El participante puede seguir respondiendo
                pass

        return records

    # METODO _extract_value
    # Este metodo identifica cual campo tiene valor y lo devuelve para pasarlo a save_response
    
    def _extract_value(self, record):

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