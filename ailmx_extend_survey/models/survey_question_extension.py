# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import json


class SurveyQuestionExtension(models.Model):
    _inherit = 'survey.question'

    id_question_type = fields.Many2one(
        comodel_name='survey.question.type',
        string='Tipo de pregunta',
        help='Selecciona el tipo de este pregunta del catálogo'
    )

    des_config_json = fields.Json(
        string='Configuración JSON',
        help='Configuración específica de la pregunta en formato JSON'
    )

    flg_required = fields.Boolean(
        string='Es obligatoria',
        default=False,
        help='Si es True el usuario no puede dejar esta pregunta sin responder'
    )

    id_luker_data_element = fields.Many2one(
        comodel_name='luker.data.element',
        string='Elemento de dato DAMA',
        help='Elemento del catálogo DAMA que define la gobernanza de este dato'
    )

    # =========================================================
    # TEMPORIZADOR
    # =========================================================
    flg_time_limit = fields.Boolean(
        string='¿Tiene límite de tiempo?',
        default=False,
        help='Si está marcada, el usuario tendrá un tiempo limitado para responder a esta pregunta.'
    )

    unidad_limite_tiempo = fields.Selection([
        ('seconds', 'Segundos'),
        ('minutes', 'Minutos')
    ], string='Unidad de tiempo', default='seconds')

    valor_limite_tiempo = fields.Integer(
        string='Valor del tiempo',
        default=0,
        help='Tiempo permitido para esta pregunta'
    )

    # =========================================================
    # IMÁGENES DE LA PREGUNTA
    # =========================================================
    flg_allow_image_attachment = fields.Boolean(
        string='¿Permitir adjuntar imagen?',
        default=False,
        help='Si está activado, esta pregunta podrá mostrar imágenes cargadas desde backend.'
    )

    img_question_attachment = fields.Image(
        string='Imagen de la pregunta',
        max_width=1920,
        max_height=1920,
        help='Imagen única de compatibilidad. Puede retirarse más adelante.'
    )

    question_image_attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='survey_question_image_attachment_rel',
        column1='id_question_audio',
        column2='id_adjunto',
        string='Imágenes de la pregunta',
        domain="[('mimetype', 'ilike', 'image/')]",
        help='Permite cargar una o varias imágenes para mostrar en la pregunta.'
    )

    # =========================================================
    # GRABACIÓN DE VOZ
    # =========================================================
    flg_auto_voice_record = fields.Boolean(
        string='¿Grabar voz?',
        default=False,
        help='Si está activado, la pregunta permitirá grabar voz.'
    )

    modo_grabacion_voz = fields.Selection([
        ('auto', 'Automática'),
        ('manual', 'Manual'),
    ], string='Modo de grabación', default='auto',
        help='Automática: inicia sola al entrar a la pregunta. Manual: el usuario decide cuándo iniciar.')

    # ---------------------------------------------------------
    # CONDICIONES DE FINALIZACIÓN
    # ---------------------------------------------------------
    condiciones_fin_json = fields.Json(
        string='Condiciones de finalización JSON',
        default=list,
        help='Configuración de condiciones de finalización en formato JSON.'
    )

    # =========================================================
    # OPCIONES DISPONIBLES PARA CONDICIONES DE FINALIZACIÓN
    # =========================================================
    condiciones_fin_opciones = fields.Json(
        string='Opciones de preguntas para condiciones',
        compute='_compute_finish_condition_question_options',
        store=False
    )

    # =========================================================
    # TEXTO JSON PARA FRONTEND
    # =========================================================
    condiciones_fin_texto = fields.Text(
        string='Condiciones de finalización (texto JSON)',
        compute='_compute_finish_conditions_json_text',
        store=False
    )

    # =========================================================
    # INDICADOR DE SECCIÓN
    # =========================================================
    indice_seccion = fields.Integer(
        string='Número de sección',
        compute='_compute_section_position',
        store=False
    )

    total_secciones = fields.Integer(
        string='Total de secciones',
        compute='_compute_section_position',
        store=False
    )

    mostrar_info_seccion = fields.Boolean(
        string='Mostrar información de la sección en sus preguntas',
        default=True,
        help='Si está activo, el título y la descripción de esta sección se mostrarán encima de cada pregunta del bloque.'
    )

    @api.depends('condiciones_fin_json')
    def _compute_finish_conditions_json_text(self):
        for rec in self:
            rec.condiciones_fin_texto = json.dumps(
                rec.condiciones_fin_json or [],
                ensure_ascii=False
            )

    @api.depends(
        'survey_id',
        'page_id',
        'survey_id.question_and_page_ids',
        'survey_id.question_and_page_ids.is_page',
        'survey_id.question_and_page_ids.sequence',
    )
    def _compute_section_position(self):
        """
        Calcula la posición de la sección actual.

        Ejemplo:
        - Si la pregunta pertenece a la segunda sección de cinco,
          devuelve:
          indice_seccion = 2
          total_secciones = 5

        Si la pregunta no pertenece a sección:
          indice_seccion = 0
          total_secciones = 0
        """
        for rec in self:
            rec.indice_seccion = 0
            rec.total_secciones = 0

            if not rec.survey_id or not rec.page_id:
                continue

            sections = rec.survey_id.question_and_page_ids.filtered(
                lambda item: item.is_page
            ).sorted(key=lambda item: (item.sequence, item.id))

            rec.total_secciones = len(sections)

            for index, section in enumerate(sections, start=1):
                if section.id == rec.page_id.id:
                    rec.indice_seccion = index
                    break

    def _compute_finish_condition_question_options(self):
        """
        Devuelve las otras preguntas de la misma encuesta para
        poblar el selector del widget custom.

        IMPORTANTE:
        - Ignora registros temporales NewId que todavía no existen
          realmente en base de datos.
        - Excluye la pregunta actual.
        - Excluye páginas / secciones.
        """
        for rec in self:
            options = []

            if rec.survey_id and rec.survey_id.question_and_page_ids:
                for question in rec.survey_id.question_and_page_ids:
                    # -------------------------------------------------
                    # Obtener un ID persistido y seguro para JSON
                    # -------------------------------------------------
                    question_real_id = question._origin.id or question.id

                    # Si no hay ID real todavía, no lo incluimos
                    if not isinstance(question_real_id, int):
                        continue

                    # Excluir la pregunta actual
                    rec_real_id = rec._origin.id or rec.id
                    if isinstance(rec_real_id, int) and question_real_id == rec_real_id:
                        continue

                    # Excluir páginas / secciones
                    if getattr(question, 'is_page', False):
                        continue

                    title = question.title or f'Pregunta #{question_real_id}'

                    options.append({
                        'id': question_real_id,
                        'title': title,
                    })

            rec.condiciones_fin_opciones = options

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('question_type') and not vals.get('is_page', False):
                vals['question_type'] = 'text_box'
        return super().create(vals_list)

    @api.model
    def create_question_with_type(self, survey_id, question_type_code, vals):
        if not survey_id:
            raise ValueError('El campo survey_id es obligatorio.')

        if not vals.get('title'):
            raise ValueError('El campo title es obligatorio.')

        question_type = self.env['survey.question.type'].search([
            ('cod_question_type', '=', question_type_code)
        ], limit=1)

        if not question_type:
            raise ValueError(
                'No existe un tipo de pregunta con el código: %s' % question_type_code
            )

        vals['survey_id'] = survey_id
        vals['id_question_type'] = question_type.id

        new_question = self.create(vals)
        return new_question

    def set_question_config(self, config):
        if not isinstance(config, dict):
            raise ValueError('La configuración debe ser un diccionario JSON.')

        self.write({'des_config_json': config})
        return True

    @api.constrains('id_luker_data_element')
    def _check_luker_data_element(self):
        # Validación desactivada — el elemento DAMA es opcional
        pass

    @api.constrains('question_type', 'suggested_answer_ids', 'suggested_answer_ids.flg_is_correct')
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

            correct_answers = record.suggested_answer_ids.filtered('flg_is_correct')
            correct_count = len(correct_answers)

            if record.question_type == 'simple_choice' and correct_count > 1:
                raise ValidationError(
                    'La pregunta "%s" es de selección única y no puede tener más de una opción correcta.'
                    % record.title
                )

    def validate_response(self, value):
        question_type = self.id_question_type

        if not question_type:
            return True

        schema_raw = question_type.des_validation_schema
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
    
    def action_edit_section_popup(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Editar sección',
            'res_model': 'survey.question',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context),
        }