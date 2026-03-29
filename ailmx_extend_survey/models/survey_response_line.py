# -*- coding: utf-8 -*-

# Importamos los módulos base de Odoo
from odoo import models, fields


class SurveyResponseLine(models.Model):
    """
    Modelo extensible para almacenar respuestas de encuesta
    en una estructura propia del módulo.
    """
    _name = "survey.response.line"
    _description = "Línea de respuesta extensible"

    # =========================================================
    # IDENTIFICADOR
    # =========================================================

    Id_Response_Line = fields.Integer(
        string='ID Línea Respuesta',
        readonly=True
    )
    # Identificador interno de la línea de respuesta.
    # En este caso está declarado como campo adicional informativo.

    # =========================================================
    # RELACIONES PRINCIPALES
    # =========================================================

    Id_Response_Header = fields.Many2one(
        comodel_name='survey.user_input',
        string='Encabezado de respuesta',
        required=True,
        ondelete='cascade',
        help='Respuesta general a la que pertenece esta línea'
    )
    # Encabezado general de respuesta.
    # survey.user_input es el registro principal de una encuesta respondida.

    Id_Instrument = fields.Many2one(
        comodel_name='survey.survey',
        string='Instrumento',
        help='Encuesta a la que pertenece esta respuesta'
    )
    # Encuesta o instrumento al que pertenece la respuesta.

    Id_Question = fields.Many2one(
        comodel_name='survey.question',
        string='Pregunta',
        required=True,
        help='Pregunta específica que se está respondiendo'
    )
    # Pregunta específica respondida.

    Id_Section = fields.Many2one(
        comodel_name='survey.question',
        string='Sección',
        help='Sección a la que pertenece esta pregunta'
    )
    # En Odoo, las secciones también se modelan como survey.question.

    # =========================================================
    # TIPO Y OPCIÓN DE RESPUESTA
    # =========================================================

    Typ_Response = fields.Char(
        string='Tipo de respuesta',
        help='Indica el tipo de dato guardado: text, number, date, boolean, json'
    )
    # Guarda el tipo lógico de la respuesta.
    # Ejemplos:
    # - text_short
    # - text_long
    # - number
    # - scale
    # - date
    # - datetime
    # - checkbox
    # - matrix
    # - reading_grid

    Id_Question_Option = fields.Many2one(
        comodel_name='survey.question.answer',
        string='Opción seleccionada',
        help='Opción seleccionada por el usuario en preguntas de tipo radio o checkbox'
    )
    # Se usa cuando una respuesta corresponde a una opción específica.

    # =========================================================
    # VALORES SEGÚN TIPO
    # =========================================================

    Val_Text = fields.Text(
        string='Valor texto',
        help='Para respuestas de tipo texto corto o largo'
    )
    # Para text_short / text_long / fallback de seguridad.

    Val_Number = fields.Float(
        string='Valor numérico',
        help='Para respuestas de tipo número o escala'
    )
    # Para preguntas number o scale.

    Val_Date = fields.Date(
        string='Valor fecha',
        help='Para respuestas de tipo fecha'
    )
    # Para preguntas date.

    Val_Datetime = fields.Datetime(
        string='Valor fecha y hora',
        help='Para respuestas de tipo fecha y hora'
    )
    # Para preguntas datetime.

    Val_JSON = fields.Json(
        string='Valor JSON',
        help='Para respuestas de tipo checkbox, matriz, GRID lectura o datos complejos'
    )
    # Este campo es el importante para estructuras complejas:
    # - checkbox
    # - matrix
    # - reading_grid
    # - futuros grids complejos

    # =========================================================
    # RESULTADO / METADATOS
    # =========================================================

    Flg_Omitted = fields.Boolean(
        string='Fue omitida',
        default=False,
        help='True si el usuario dejó esta pregunta sin responder'
    )
    # Marca si la respuesta fue omitida.

    Num_Score = fields.Float(
        string='Puntaje',
        default=0.0,
        help='Puntaje obtenido en esta respuesta'
    )
    # Puntaje asociado a la respuesta.

    # =========================================================
    # AUDITORÍA
    # =========================================================

    Dat_Created_At = fields.Datetime(
        string='Fecha de creación',
        default=fields.Datetime.now,
        readonly=True
    )
    # Fecha de creación del registro.

    Nam_User = fields.Char(
        string='Usuario',
        readonly=True
    )
    # Nombre del participante o usuario.
    # Si es anónimo, puede quedar como "Anónimo".

    Nam_Device = fields.Char(
        string='Dispositivo',
        readonly=True
    )
    # Referencia del dispositivo / token / acceso desde donde respondió.

    # =========================================================
    # MÉTODO: save_response
    # =========================================================

    def save_response(self, response_header_id, question_id, value):
        """
        Guarda una respuesta en la tabla extensible survey.response.line.

        Parámetros:
        - response_header_id: ID del survey.user_input
        - question_id: ID de la pregunta respondida
        - value: valor de la respuesta ya extraído / interpretado

        Este método decide en qué columna persistir el valor
        según el tipo de pregunta.
        """

        # =====================================================
        # VALIDAR ENCABEZADO DE RESPUESTA
        # =====================================================

        response_header = self.env['survey.user_input'].browse(response_header_id)
        if not response_header.exists():
            raise ValueError(
                'No existe un encabezado de respuesta con ID: %s'
                % response_header_id
            )

        # =====================================================
        # VALIDAR PREGUNTA
        # =====================================================

        question = self.env['survey.question'].browse(question_id)
        if not question.exists():
            raise ValueError(
                'No existe una pregunta con ID: %s' % question_id
            )

        # =====================================================
        # OBTENER TIPO DE PREGUNTA DESDE EL CATÁLOGO
        # =====================================================

        question_type = question.Id_Question_Type

        # Si la pregunta no tiene tipo asignado en el catálogo,
        # se guarda por defecto como texto.
        if not question_type:
            return self.create({
                'Id_Response_Header': response_header_id,
                'Id_Instrument': response_header.survey_id.id,
                'Id_Question': question_id,
                'Typ_Response': 'text',
                'Val_Text': str(value) if value else False,
            })

        # Código técnico del tipo de pregunta
        type_code = question_type.Cod_Question_Type

        # =====================================================
        # DICCIONARIO BASE DE VALORES
        # =====================================================

        vals = {
            'Id_Response_Header': response_header_id,
            'Id_Instrument': response_header.survey_id.id,
            'Id_Question': question_id,
            'Typ_Response': type_code,
            'Nam_User': response_header.partner_id.name or 'Anónimo',
            'Nam_Device': response_header.access_token or 'Desconocido',
        }

        # =====================================================
        # LÓGICA DE PERSISTENCIA SEGÚN EL TIPO
        # =====================================================

        if type_code in ('text_short', 'text_long'):
            # Texto corto y largo se guardan en Val_Text
            vals['Val_Text'] = str(value) if value else False

        elif type_code in ('number', 'scale'):
            # Números y escalas se guardan en Val_Number
            # Si no puede convertirse a float, se guarda como texto
            try:
                vals['Val_Number'] = float(value)
            except (ValueError, TypeError):
                vals['Val_Text'] = str(value) if value else False

        elif type_code == 'date':
            # Fechas se guardan en Val_Date
            vals['Val_Date'] = value

        elif type_code == 'datetime':
            # Fecha y hora se guarda en Val_Datetime
            vals['Val_Datetime'] = value

        elif type_code == 'radio':
            # Opción única
            vals['Val_Text'] = str(value) if value else False

            # Si el valor es un ID de opción, se guarda también la relación
            if isinstance(value, int):
                vals['Id_Question_Option'] = value

        elif type_code in ('checkbox', 'matrix', 'reading_grid'):
            # =================================================
            # RESPUESTAS COMPLEJAS EN JSON
            # =================================================
            # Aquí ahora también soportamos:
            # - reading_grid
            #
            # Si el valor es lista o diccionario, se guarda en Val_JSON.
            # Si viene en otro formato, por seguridad lo guardamos como texto.
            if isinstance(value, (list, dict)):
                vals['Val_JSON'] = value
            else:
                vals['Val_Text'] = str(value) if value else False

        else:
            # Cualquier tipo desconocido se guarda como texto por seguridad
            vals['Val_Text'] = str(value) if value else False

        # =====================================================
        # CREAR REGISTRO EN BASE DE DATOS
        # =====================================================

        return self.create(vals)

    # =========================================================
    # MÉTODO: get_typed_value
    # =========================================================

    def get_typed_value(self):
        """
        Devuelve el valor correcto según el tipo de respuesta.
        Sirve para reportes, lógica o cálculos posteriores.
        """
        if self.Typ_Response in ('text_short', 'text_long'):
            return self.Val_Text

        elif self.Typ_Response in ('number', 'scale'):
            return self.Val_Number

        elif self.Typ_Response == 'date':
            return self.Val_Date

        elif self.Typ_Response == 'datetime':
            return self.Val_Datetime

        elif self.Typ_Response in ('checkbox', 'matrix', 'reading_grid'):
            # También incluimos reading_grid como JSON
            return self.Val_JSON

        elif self.Typ_Response == 'radio':
            return self.Val_Text

        else:
            # Si no reconoce el tipo, devuelve texto por seguridad
            return self.Val_Text