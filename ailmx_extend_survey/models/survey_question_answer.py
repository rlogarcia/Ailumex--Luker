# -*- coding: utf-8 -*-

# Este archivo extiende el modelo nativo:
# survey.question.answer
# que es donde Odoo guarda cada opción de respuesta.

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SurveyQuestionAnswer(models.Model):
    _inherit = 'survey.question.answer'

    # =========================================================
    # CAMPO: Flg_Is_Correct
    # =========================================================
    # Este campo indica si una opción es correcta o no.
    #
    # Casos de uso:
    # - Selección única (radio): solo una opción puede ser correcta
    # - Selección múltiple (checkbox): varias opciones pueden ser correctas
    # =========================================================
    Flg_Is_Correct = fields.Boolean(
        string='Es correcta',
        default=False,
        help='Marca esta opción si debe considerarse una respuesta correcta.'
    )

    # =========================================================
    # VALIDACIÓN DE INTEGRIDAD
    # =========================================================
    # Si la pregunta es de selección única,
    # no se permite más de una opción correcta.
    #
    # NOTA:
    # El nombre técnico del campo nativo de Odoo es question_id.
    # Desde ahí accedemos al tipo de pregunta.
    # =========================================================
    @api.constrains('Flg_Is_Correct', 'question_id')
    def _check_single_choice_only_one_correct(self):
        for record in self:
            # Si no hay pregunta asociada, no validamos
            if not record.question_id:
                continue

            question = record.question_id

            # Solo nos interesa validar preguntas de selección única
            # En Odoo Survey el campo técnico usual es question_type.
            # Dependiendo de la versión, los valores más comunes son:
            # - simple_choice
            # - multiple_choice
            #
            # Aquí validamos solo cuando sea selección única.
            if question.question_type == 'simple_choice':
                correct_answers = question.suggested_answer_ids.filtered('Flg_Is_Correct')

                if len(correct_answers) > 1:
                    raise ValidationError(
                        'La pregunta "%s" es de selección única y solo puede tener una opción correcta.'
                        % question.title
                    )