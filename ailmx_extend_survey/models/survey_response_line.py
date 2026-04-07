# -*- coding: utf-8 -*-

# Importamos los módulos base de Odoo
from odoo import models, fields, api


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

    Val_Number = fields.Float(
        string='Valor numérico',
        help='Para respuestas de tipo número o escala'
    )

    Val_Date = fields.Date(
        string='Valor fecha',
        help='Para respuestas de tipo fecha'
    )

    Val_Datetime = fields.Datetime(
        string='Valor fecha y hora',
        help='Para respuestas de tipo fecha y hora'
    )

    Val_JSON = fields.Json(
        string='Valor JSON',
        help='Para respuestas de tipo checkbox, matriz, GRID lectura o datos complejos'
    )

    # =========================================================
    # RESULTADO / METADATOS
    # =========================================================

    Flg_Omitted = fields.Boolean(
        string='Fue omitida',
        default=False,
        help='True si el usuario dejó esta pregunta sin responder'
    )

    Num_Score = fields.Float(
        string='Puntaje',
        default=0.0,
        help='Puntaje obtenido en esta respuesta'
    )

    # =========================================================
    # AUDITORÍA
    # =========================================================

    Dat_Created_At = fields.Datetime(
        string='Fecha de creación',
        default=fields.Datetime.now,
        readonly=True
    )

    Nam_User = fields.Char(
        string='Usuario',
        readonly=True
    )

    Nam_Device = fields.Char(
        string='Dispositivo',
        readonly=True
    )

    # =========================================================
    # 🔴 NUEVO CAMPO FUNCIONAL
    # =========================================================
    # Este campo sirve para mostrar la respuesta capturada
    # de una forma legible dentro del detalle de la aplicación.
    # Así evitamos que el usuario tenga que mirar varias columnas
    # técnicas (Val_Text, Val_Number, Val_Date, etc.).
    # =========================================================
    Nam_Response_Display = fields.Char(
        string='Respuesta capturada',
        compute='_compute_response_display',
        store=False
    )

    @api.depends(
        'Typ_Response',
        'Val_Text',
        'Val_Number',
        'Val_Date',
        'Val_Datetime',
        'Val_JSON',
        'Id_Question_Option'
    )
    def _compute_response_display(self):
        """
        Construye un valor legible de la respuesta capturada.
        """
        for record in self:
            display_value = ''

            # Si hay opción seleccionada, es lo primero que intentamos mostrar
            if record.Id_Question_Option:
                # Mostramos el campo "value" de la opción si existe
                # y si no, usamos display_name como respaldo.
                display_value = (
                    record.Id_Question_Option.value
                    or record.Id_Question_Option.display_name
                    or ''
                )

            elif record.Val_Text:
                display_value = record.Val_Text

            elif record.Val_Number not in (False, None):
                display_value = str(record.Val_Number)

            elif record.Val_Date:
                display_value = str(record.Val_Date)

            elif record.Val_Datetime:
                display_value = str(record.Val_Datetime)

            elif record.Val_JSON:
                display_value = str(record.Val_JSON)

            elif record.Flg_Omitted:
                display_value = 'Omitida'

            record.Nam_Response_Display = display_value

    # =========================================================
    # MÉTODO: save_response
    # =========================================================

    def save_response(self, response_header_id, question_id, value):
        """
        Guarda una respuesta en la tabla extensible survey.response.line.
        """

        # VALIDAR ENCABEZADO DE RESPUESTA
        response_header = self.env['survey.user_input'].browse(response_header_id)
        if not response_header.exists():
            raise ValueError(
                'No existe un encabezado de respuesta con ID: %s'
                % response_header_id
            )

        # VALIDAR PREGUNTA
        question = self.env['survey.question'].browse(question_id)
        if not question.exists():
            raise ValueError(
                'No existe una pregunta con ID: %s' % question_id
            )

        # OBTENER TIPO DE PREGUNTA DESDE EL CATÁLOGO
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

        # DICCIONARIO BASE DE VALORES
        vals = {
            'Id_Response_Header': response_header_id,
            'Id_Instrument': response_header.survey_id.id,
            'Id_Question': question_id,
            'Typ_Response': type_code,
            'Nam_User': response_header.partner_id.name or 'Anónimo',
            'Nam_Device': response_header.access_token or 'Desconocido',
        }

        # LÓGICA DE PERSISTENCIA SEGÚN EL TIPO
        if type_code in ('text_short', 'text_long'):
            vals['Val_Text'] = str(value) if value else False

        elif type_code in ('number', 'scale'):
            try:
                vals['Val_Number'] = float(value)
            except (ValueError, TypeError):
                vals['Val_Text'] = str(value) if value else False

        elif type_code == 'date':
            vals['Val_Date'] = value

        elif type_code == 'datetime':
            vals['Val_Datetime'] = value

        elif type_code == 'radio':
            vals['Val_Text'] = str(value) if value else False

            if isinstance(value, int):
                vals['Id_Question_Option'] = value

        elif type_code in ('checkbox', 'matrix', 'reading_grid'):
            if isinstance(value, (list, dict)):
                vals['Val_JSON'] = value
            else:
                vals['Val_Text'] = str(value) if value else False

        else:
            vals['Val_Text'] = str(value) if value else False

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
            return self.Val_JSON

        elif self.Typ_Response == 'radio':
            return self.Val_Text

        else:
            return self.Val_Text