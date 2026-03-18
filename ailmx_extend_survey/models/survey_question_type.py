# -*- coding: utf-8 -*-

# Se importa 'models' y 'fields' de odoo
# 'models' permite crear tablas en la BD
# 'fields' permite definir los campos (columnas) de la tabla
from odoo import models, fields, api

class SurveyQuestionsType(models.Model):
    _name = 'survey.question.type' # Nombre técnico del modelo en Odoo
    _description = 'Catálogo de tipos de pregunta' # Descrición legible del modelo que aparece en la interfaz técnica de Odoo
    _order = 'Nam_Question_Type asc' # Define como se ordenan los registros por defecto
    _rec_name = 'Nam_Question_Type' # Campo que se muestra en la interfaz de Odoo

    Id_Survey_Question_Type = fields.Integer( # Identificador único del tipo de pregunta
        string = 'ID Tipo Pregunta',
        readonly = True
    )

    Cod_Question_Type = fields.Char(
        string = 'Código técnico', 
        required = True, # True significa que no puede quedar vacío
        help = 'Identificador único del tipo (Radio, number, date ...)'
    )

    Nam_Question_Type = fields.Char(
        string = 'Nombre',
        required = True,
        help = 'Nombre legible del tipo. (Opción única, opción múltiple)'
    )

    Typ_Data = fields.Char ( # Degine que clase de dato produce la respuesta
        string = 'Tipo de dato',
        help = 'Clase de dato que produce la respuesta (string, number, json ...)'
    )

    Nam_UI_Component = fields.Char ( # Nombre del componente visual que debe mostrarse en pantalla para el tipo de pregunta
        string = 'Componente UI',
        help = 'Nombre del componente visual que renderiza la pregunta'
    )

    Flg_Supports_Multiple = fields.Boolean ( # Indica si el tipo de pregunta soporta múltiples respuestas
        string = 'Permite múltiples respuestas',
        default = False # Por defecto es no
    )

    Flg_Supports_Media = fields.Boolean ( # Indica si este tipo permite adjuntar archivos
        string = 'Admite evidencia o foto',
        default = False
    )

    Flg_Supports_GPS = fields.Boolean ( # Indica si este tipo captura automáticamente la ubicación GPS del dispositivo al responder
        string = 'Admite GPS',
        default = False
    )

    Flg_Supports_Score = fields.Boolean ( # Indica si las opciones tienen un puntaje numérico asociado
        string = 'Admite puntuación',
        default = False
    )

    Flg_Supports_Offline = fields.Boolean ( # Indica si el tipo de pregunta se puede usar sin conexión
        string = 'Admite offline',
        default = True # True porque la mayoría si lo soporta
    )

    Des_Validation_Schema = fields.Char ( # Guarda las reglas de validación en formato JSON
        string = 'Esquema de validación',
        help = 'Reglas de validación en formato JSON'
    )

    active = fields.Boolean ( # Nativo de Odoo, 
        string = 'Activo',
        default = True # Todo registro nuevo queda activo por defecto
    )

    #Restricción SQL
    _sql_constraints = [
        (
            'cod_question_type_unique', # Nombre interno de la restricción
            'unique(Cod_Question_Type)', # Garantiza que no pueden existir dos registros con el mismo código en la BD
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
        if not vals.get('Cod_Question_Type'):
            raise ValueError('El campo Cod_Question_Type es obligatorio.')
        if not vals.get('Nam_Question_Type'):
            raise ValueError('El campo Nam_Question_Type es obligatorio.')

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

        # Actualiza el campo Des_Validation_Schema
        # con el esquema recibido
        self.write({'Des_Validation_Schema': schema})

        return True