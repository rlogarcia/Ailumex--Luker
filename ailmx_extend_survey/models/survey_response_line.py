# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SurveyResponseLine(models.Model):
    # Odoo va a crear la tabla survey_response_line en PostgreSQL
    _name = "survey.response.line"
    _description = "Línea de respuesta extensible"

    Id_Response_Line = fields.Integer( # Identificador único
        string='ID Línea Respuesta',
        readonly=True
    )

    # survey.user_input es la tabla de Odoo que guarda al usuario que respondió la encuesta
    Id_Response_Header = fields.Many2one(
        comodel_name='survey.user_input',
        string='Encabezado de respuesta',
        required=True,
        ondelete='cascade',
        help='Respuesta general a la que pertenece esta línea'
    )    

    # survey.survey es la tabla de Odoo que guarda la encuesta
    Id_Instrument = fields.Many2one(
        comodel_name='survey.survey',
        string='Instrumento',
        help='Encuesta a la que pertenece esta respuesta'
    )

    # fk a la pregunta que se está respondiendo
    Id_Question = fields.Many2one(
        comodel_name='survey.question',
        string='Pregunta',
        required=True,
        help='Pregunta específica que se está respondiendo'
    )

    # En Odoo las secciones también son survey.question
    Id_Section = fields.Many2one(
        comodel_name='survey.question',
        string='Sección',
        help='Sección a la que pertenece esta pregunta'
    )

    # Tipo de respuesta guardada - text, number, date, boolean, json
    Typ_Response = fields.Char(
        string='Tipo de respuesta',
        help='Indica el tipo de dato guardado: text, number, date, boolean, json'
    )

    # Se usa cuando la pregunta es de tipo radio o checkbox y el usuario selecciona una opción
    Id_Question_Option = fields.Many2one(
        comodel_name='survey.question.answer',
        string='Opción seleccionada',
        help='Opción seleccionada por el usuario en preguntas de tipo radio o checkbox'
    )

    # Se usa para preguntas text_short y text_long
    Val_Text = fields.Text(
        string='Valor texto',
        help='Para respuestas de tipo texto corto o largo'
    )

    # Guarda respuestas de tipo numérico (number, scale)
    Val_Number = fields.Float(
        string='Valor numérico',
        help='Para respuestas de tipo número o escala'
    )

    # Guarda respuestas de tipo fecha (date)
    Val_Date = fields.Date(
        string='Valor fecha',
        help='Para respuestas de tipo fecha'
    )

    # Guarda respuestas de tipo fecha y hora (datetime)
    Val_Datetime = fields.Datetime(
        string='Valor fecha y hora',
        help='Para respuestas de tipo fecha y hora'
    )

    # Guarda respuestas en formato JSON (checkbox, matriz, GPS)
    Val_JSON = fields.Json(
        string='Valor JSON',
        help='Para respuestas de tipo checkbox, matriz o datos complejos'
    )

    # Indica si la respuesta fue omitida por el usuario
    Flg_Omitted = fields.Boolean(
        string='Fue omitida',
        default=False,
        help='True si el usuario dejó esta pregunta sin responder'
    )

    # Puntaje obtenido en esta respuesta, según la opción seleccionada
    Num_Score = fields.Float(
        string='Puntaje',
        default=0.0,
        help='Puntaje obtenido en esta respuesta'
    )

    # Campos de auditoría
    # FECHA
    Dat_Created_At = fields.Datetime(
        string='Fecha de creación',
        default=fields.Datetime.now,
        readonly=True
    )

    # PARTICIPANTE
    # Vacío si el participante respondió de forma anónima
    Nam_User = fields.Char(
        string='Usuario', 
        readonly=True
    )

    # DISPOSITIVO
    # lA IP del dispositivo desde donde se respondió Sirve como referencia del dispositivo
    Nam_Device = fields.Char(
        string='Dispositivo', 
        readonly=True
    )

    # MÉTODO save_response
    # Recibe una pregunta y un valor, identifica el tipo de dato correcto y guarda la respuesta
    # en la columna adecuada de esta tabla.
    
    # @api.model # significa que opera sobre el modelo completo, no sobre un registro.
    def save_response(self, response_header_id, question_id, value):

        # Busca el encabezado de la respuesta
        response_header = self.env['survey.user_input'].browse(
            response_header_id
        )
        if not response_header.exists():
            raise ValueError(
                'No existe un encabezado de respuesta con ID: %s'
                % response_header_id
            )

        # Busca la pregunta
        question = self.env['survey.question'].browse(question_id)
        if not question.exists():
            raise ValueError(
                'No existe una pregunta con ID: %s' % question_id
            )

        # Obtiene el tipo de pregunta del catálogo
        question_type = question.Id_Question_Type

        # Si la pregunta no tiene tipo asignado se guarda como texto por defecto
        if not question_type:
            return self.create({
                'Id_Response_Header': response_header_id,
                'Id_Instrument': response_header.survey_id.id,
                'Id_Question': question_id,
                'Typ_Response': 'text',
                'Val_Text': str(value) if value else False,
            })

        # Obtiene el código del tipo de pregunta para decidir en qué columna guardar
        type_code = question_type.Cod_Question_Type

        # Diccionario base con campos comunes a todas las respuestas
        vals = {
            'Id_Response_Header': response_header_id,
            'Id_Instrument': response_header.survey_id.id,
            'Id_Question': question_id,
            'Typ_Response': type_code,
            'Nam_User': response_header.partner_id.name or 'Anónimo',
            'Nam_Device': response_header.access_token or 'Desconocido',
        }

        # LÓGICA DE PERSISTENCIA
        # Según el tipo de pregunta se llena la columna correcta

        if type_code in ('text_short', 'text_long'):
            # Texto corto y largo van a Val_Text
            vals['Val_Text'] = str(value) if value else False

        elif type_code in ('number', 'scale'):
            # Números y escalas van a Val_Number
            # Se intenta convertir a float, Si falla se guarda en Val_Text
            try:
                vals['Val_Number'] = float(value)
            except (ValueError, TypeError):
                vals['Val_Text'] = str(value) if value else False

        elif type_code == 'date':
            # Fechas van a Val_Date
            vals['Val_Date'] = value

        elif type_code == 'datetime':
            # Fecha y hora van a Val_Datetime
            vals['Val_Datetime'] = value

        elif type_code == 'radio':
            # Opción única guarda el texto y la opción seleccionada si existe
            vals['Val_Text'] = str(value) if value else False
            # Si el valor es el ID de una opción se guarda en Id_Question_Option
            if isinstance(value, int):
                vals['Id_Question_Option'] = value

        elif type_code in ('checkbox', 'matrix'):
            # Opciones múltiples y matrices
            # se guardan como JSON porque tienen múltiples valores
            if isinstance(value, (list, dict)):
                vals['Val_JSON'] = value
            else:
                vals['Val_Text'] = str(value) if value else False

        else:
            # Cualquier tipo desconocido se guarda como texto por seguridad
            vals['Val_Text'] = str(value) if value else False

        # Crea el registro en la base de datos
        return self.create(vals)

    # MÉTODO: get_typed_value
    # Devuelve el valor correcto de una línea de respuesta según su tipo.
    # Sirve para reportes y cálculos.

    def get_typed_value(self):
        # Según el tipo de respuesta devuelve el valor de la columna correcta
        if self.Typ_Response in ('text_short', 'text_long'):
            return self.Val_Text

        elif self.Typ_Response in ('number', 'scale'):
            return self.Val_Number

        elif self.Typ_Response == 'date':
            return self.Val_Date

        elif self.Typ_Response == 'datetime':
            return self.Val_Datetime

        elif self.Typ_Response in ('checkbox', 'matrix'):
            return self.Val_JSON

        elif self.Typ_Response == 'radio':
            return self.Val_Text

        else:
            # Si no reconoce el tipo devuelve Val_Text
            return self.Val_Text