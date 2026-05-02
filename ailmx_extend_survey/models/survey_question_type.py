# -*- coding: utf-8 -*-

# Se importa 'models' y 'fields' de odoo
# 'models' permite crear tablas en la BD
# 'fields' permite definir los campos (columnas) de la tabla
from odoo import models, fields, api

class SurveyQuestionsType(models.Model):
    _name = 'survey.question.type' # Nombre técnico del modelo en Odoo
    _description = 'Catálogo de tipos de pregunta' # Descrición legible del modelo que aparece en la interfaz técnica de Odoo
    _order = 'nam_question_type asc' # Define como se ordenan los registros por defecto
    _rec_name = 'nam_question_type' # Campo que se muestra en la interfaz de Odoo

    cod_question_type = fields.Char(
        string = 'Código técnico', 
        required = True, # True significa que no puede quedar vacío
        help = 'Identificador único del tipo (Radio, number, date ...)'
    )

    nam_question_type = fields.Char(
        string = 'Nombre',
        required = True,
        help = 'Nombre legible del tipo. (Opción única, opción múltiple)'
    )

    typ_data = fields.Char ( # Degine que clase de dato produce la respuesta
        string = 'Tipo de dato',
        help = 'Clase de dato que produce la respuesta (string, number, json ...)'
    )

    nam_ui_component = fields.Char ( # Nombre del componente visual que debe mostrarse en pantalla para el tipo de pregunta
        string = 'Componente UI',
        help = 'Nombre del componente visual que renderiza la pregunta'
    )

    flg_supports_multiple = fields.Boolean ( # Indica si el tipo de pregunta soporta múltiples respuestas
        string = 'Permite múltiples respuestas',
        default = False # Por defecto es no
    )

    flg_supports_media = fields.Boolean ( # Indica si este tipo permite adjuntar archivos
        string = 'Admite evidencia o foto',
        default = False
    )

    flg_supports_gps = fields.Boolean ( # Indica si este tipo captura automáticamente la ubicación GPS del dispositivo al responder
        string = 'Admite GPS',
        default = False
    )

    flg_supports_score = fields.Boolean ( # Indica si las opciones tienen un puntaje numérico asociado
        string = 'Admite puntuación',
        default = False
    )

    flg_supports_offline = fields.Boolean ( # Indica si el tipo de pregunta se puede usar sin conexión
        string = 'Admite offline',
        default = True # True porque la mayoría si lo soporta
    )

    des_validation_schema = fields.Char ( # Guarda las reglas de validación en formato JSON
        string = 'Esquema de validación',
        help = 'Reglas de validación en formato JSON'
    )

    activo = fields.Boolean ( # Nativo de Odoo, 
        string = 'Activo',
        default = True # Todo registro nuevo queda activo por defecto
    )

    #Restricción SQL
    _sql_constraints = [
        (
            'cod_question_type_unique', # Nombre interno de la restricción
            'unique(cod_question_type)', # Garantiza que no pueden existir dos registros con el mismo código en la BD
            'Ya existe un tipo de pregunta con ese código técnico.' # Mensaje de error que va a ver el usuario
        )
    ]

    # MÉTODO API 1: create_question_type
    # Recibe un diccionario con los datos del tipo.
    # Devuelve el registro creado.

    @api.model
    def create_question_type(self, vals):
        # Verifica que los campos obligatorios estén presentes
        # antes de intentar crear el registro
        if not vals.get('cod_question_type'):
            raise ValueError('El campo cod_question_type es obligatorio.')
        if not vals.get('nam_question_type'):
            raise ValueError('El campo nam_question_type es obligatorio.')

        # Crea el registro en la base de datos
        new_type = self.create(vals) # self.create() es el método nativo de Odoo para crear registros

        return new_type

    # MÉTODO API 2: set_validation_schema
    # Permite configurar las reglas de validación
    # de un tipo de pregunta existente desde código.
    
    def set_validation_schema(self, schema):
        # Verifica que el esquema sea un diccionario
        if not isinstance(schema, dict):
            raise ValueError('El esquema de validación debe ser un diccionario JSON.')

        # Actualiza el campo des_validation_schema
        # con el esquema recibido
        self.write({'des_validation_schema': schema})

        return True