# -*- coding: utf-8 -*-

from odoo import models, fields, api
import json

class SurveyQuestionExtension(models.Model):
    # _inherit le dice a odoo que no es una tabla nueva, sino que se agregan campos nuevos
    _inherit = 'survey.question'

    # Many2one signigica que muchas preguntas pueden tener el mismo tipo
    # Ejemplo: 100 preguntas pueden ser de tipo 'radio'
    Id_Question_Type = fields.Many2one(
        comodel_name='survey.question.type',
        string='Tipo de pregunta',
        help='Selecciona el tipo de este pregunta del catálogo'
    )

    # Se guarda la configuración específica de la pregunta en JSON
    # Ejemplo: number:   {"min": 0, "max": 100}, checkbox: {"opciones": ["Si", "No", "No aplica"]}
    Des_Config_JSON = fields.Json(
        string='Configuración JSON',
        help='Configuración específica de la pregunta en formato JSON'
    )

    # Indica si la pregunta es obligatoria o no
    Flg_Required = fields.Boolean(
        string='Es obligatoria',
        default=False,
        help='Si es True el usuario no puede dejar esta pregunta sin responder'
    )

    # Conecta esta pregunta con su elemento DAMA
    Id_Data_Element = fields.Many2one(
        comodel_name='data.element',
        string='Elemento de dato DAMA',
        help='Elemento del catálogo DAMA que define la gobernanza de este dato'
    )

    # MÉTODO API 3: create_question_with_type
    # Permite crear una pregunta completa desde código,
    # asignándole tipo y configuración en una sola operación.

    @api.model
    def create_question_with_type(self, survey_id, question_type_code, vals):

        # Verifica que el survey_id esté presente
        if not survey_id:
            raise ValueError('El campo survey_id es obligatorio.')

        # Verifica que el título de la pregunta esté presente
        if not vals.get('title'):
            raise ValueError('El campo title es obligatorio.')

        # Busca el tipo de pregunta por su código técnico
        # search() busca registros que cumplan una condición
        # El resultado es una lista de registros
        question_type = self.env['survey.question.type'].search([
            ('Cod_Question_Type', '=', question_type_code)
        ], limit=1)

        # Si no encuentra el tipo lanza un error
        if not question_type:
            raise ValueError(
                'No existe un tipo de pregunta con el código: %s' % question_type_code
            )

        # Agrega los campos necesarios al diccionario
        # de valores antes de crear la pregunta
        vals['survey_id'] = survey_id
        vals['Id_Question_Type'] = question_type.id

        # Crea la pregunta en la base de datos
        new_question = self.create(vals)

        return new_question

    # MÉTODO API 4: set_question_config
    # Permite actualizar la configuración JSON
    # de una pregunta existente desde código.

    def set_question_config(self, config):

        # Verifica que la configuración sea un diccionario
        if not isinstance(config, dict):
            raise ValueError('La configuración debe ser un diccionario JSON.')

        # Actualiza el campo Des_Config_JSON
        self.write({'Des_Config_JSON': config})

        return True

    # MÉTODO API 5: validate_response
    # Valida que una respuesta cumpla las reglas
    # definidas en Des_Validation_Schema del tipo.

    def validate_response(self, value):

        # Obtiene el tipo de pregunta asociado
        question_type = self.Id_Question_Type

        # Si no tiene tipo asignado no valida
        if not question_type:
            return True

        # Obtiene el esquema de validación del tipo
        schema = question_type.Des_Validation_Schema

        # Si no tiene esquema no valida
        #if not schema:
        #    return True
        
        # Se obtiene el esquema de validación del tipo
        # Es texto Char y se convierte a diccionario
        schema_raw = question_type.Des_Validation_Schema

        # Si no tiene esquema no valida
        if not schema_raw:
            return True

        # Convierte el texto JSON a diccionario Python
        # Si el texto no es JSON válido, no valida y sigue normal
        try:
            schema = json.loads(schema_raw)
        except (ValueError, TypeError):
            return True


        # Valida la regla 'required'
        # Si required es True y el valor está vacío
        # lanza un error
        if schema.get('required') and not value:
            raise ValueError(
                'La pregunta "%s" es obligatoria.' % self.title
            )

        # Valida la regla 'min' para valores numéricos
        # Si el valor es menor al mínimo lanza un error
        if schema.get('min') is not None:
            if isinstance(value, (int, float)) and value < schema['min']:
                raise ValueError(
                    'El valor %s es menor al mínimo permitido: %s'
                    % (value, schema['min'])
                )

        # Valida la regla 'max' para valores numéricos
        # Si el valor es mayor al máximo lanza un error
        if schema.get('max') is not None:
            if isinstance(value, (int, float)) and value > schema['max']:
                raise ValueError(
                    'El valor %s es mayor al máximo permitido: %s'
                    % (value, schema['max'])
                )

        return True