# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import json


class SurveyQuestionExtension(models.Model):
    _inherit = 'survey.question'

    Id_Question_Type = fields.Many2one(
        comodel_name='survey.question.type',
        string='Tipo de pregunta',
        help='Selecciona el tipo de este pregunta del catálogo'
    )

    Des_Config_JSON = fields.Json(
        string='Configuración JSON',
        help='Configuración específica de la pregunta en formato JSON'
    )

    Flg_Required = fields.Boolean(
        string='Es obligatoria',
        default=False,
        help='Si es True el usuario no puede dejar esta pregunta sin responder'
    )

    Id_Data_Element = fields.Many2one(
        comodel_name='data.element',
        string='Elemento de dato DAMA',
        help='Elemento del catálogo DAMA que define la gobernanza de este dato'
    )

    # =========================================================
    # TEMPORIZADOR
    # =========================================================
    has_time_limit = fields.Boolean(
        string='¿Tiene límite de tiempo?',
        default=False,
        help='Si está marcada, el usuario tendrá un tiempo limitado para responder a esta pregunta.'
    )

    time_limit_unit = fields.Selection([
        ('seconds', 'Segundos'),
        ('minutes', 'Minutos')
    ], string='Unidad de tiempo', default='seconds')

    time_limit_value = fields.Integer(
        string='Valor del tiempo',
        default=0,
        help='Tiempo permitido para esta pregunta'
    )

    # =========================================================
    # IMÁGENES DE LA PREGUNTA
    # =========================================================
    Flg_Allow_Image_Attachment = fields.Boolean(
        string='¿Permitir adjuntar imagen?',
        default=False,
        help='Si está activado, esta pregunta podrá mostrar imágenes cargadas desde backend.'
    )

    Img_Question_Attachment = fields.Image(
        string='Imagen de la pregunta',
        max_width=1920,
        max_height=1920,
        help='Imagen única de compatibilidad. Puede retirarse más adelante.'
    )

    Question_Image_Attachment_Ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='survey_question_image_attachment_rel',
        column1='question_id',
        column2='attachment_id',
        string='Imágenes de la pregunta',
        domain="[('mimetype', 'ilike', 'image/')]",
        help='Permite cargar una o varias imágenes para mostrar en la pregunta.'
    )

    # =========================================================
    # GRABACIÓN AUTOMÁTICA DE VOZ
    # =========================================================
    Flg_Auto_Voice_Record = fields.Boolean(
        string='¿Grabar voz automáticamente?',
        default=False,
        help='Si está activado, al abrir esta pregunta se iniciará automáticamente la grabación de voz.'
    )

    @api.model
    def create_question_with_type(self, survey_id, question_type_code, vals):
        if not survey_id:
            raise ValueError('El campo survey_id es obligatorio.')

        if not vals.get('title'):
            raise ValueError('El campo title es obligatorio.')

        question_type = self.env['survey.question.type'].search([
            ('Cod_Question_Type', '=', question_type_code)
        ], limit=1)

        if not question_type:
            raise ValueError(
                'No existe un tipo de pregunta con el código: %s' % question_type_code
            )

        vals['survey_id'] = survey_id
        vals['Id_Question_Type'] = question_type.id

        new_question = self.create(vals)
        return new_question

    def set_question_config(self, config):
        if not isinstance(config, dict):
            raise ValueError('La configuración debe ser un diccionario JSON.')

        self.write({'Des_Config_JSON': config})
        return True

    @api.constrains('Id_Data_Element')
    def _check_data_element(self):
        for record in self:
            if record.Id_Question_Type and not record.Id_Data_Element:
                raise ValidationError(
                    'La pregunta "%s" debe tener un Elemento de dato DAMA asignado.'
                    % record.title
                )

    @api.constrains('question_type', 'suggested_answer_ids', 'suggested_answer_ids.Flg_Is_Correct')
    def _check_correct_answers_for_choice_questions(self):
        """
        Regla final deseada:
        - Selección única: puede tener 0 o 1 correcta. Nunca más de 1.
        - Selección múltiple: puede tener 0, 1 o varias correctas.
        - Es opcional marcar respuestas correctas.
        """
        for record in self:
            if record.question_type not in ('simple_choice', 'multiple_choice'):
                continue

            correct_answers = record.suggested_answer_ids.filtered('Flg_Is_Correct')
            correct_count = len(correct_answers)

            if record.question_type == 'simple_choice' and correct_count > 1:
                raise ValidationError(
                    'La pregunta "%s" es de selección única y no puede tener más de una opción correcta.'
                    % record.title
                )

    def validate_response(self, value):
        question_type = self.Id_Question_Type

        if not question_type:
            return True

        schema_raw = question_type.Des_Validation_Schema
        if not schema_raw:
            return True

        try:
            schema = json.loads(schema_raw)
        except (ValueError, TypeError):
            return True

        if schema.get('required') and not value:
            raise ValueError(
                'La pregunta "%s" es obligatoria.' % self.title
            )

        if schema.get('min') is not None:
            if isinstance(value, (int, float)) and value < schema['min']:
                raise ValueError(
                    'El valor %s es menor al mínimo permitido: %s'
                    % (value, schema['min'])
                )

        if schema.get('max') is not None:
            if isinstance(value, (int, float)) and value > schema['max']:
                raise ValueError(
                    'El valor %s es mayor al máximo permitido: %s'
                    % (value, schema['max'])
                )

        return True