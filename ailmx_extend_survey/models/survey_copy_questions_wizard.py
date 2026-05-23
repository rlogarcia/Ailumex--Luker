# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SurveyCopyQuestionsWizard(models.TransientModel):
    _name = 'survey.copy.questions.wizard'
    _description = 'Trasladar preguntas entre instrumentos'

    # ── Origen (readonly — viene del contexto) ─────────────────────────────
    survey_origen_id = fields.Many2one(
        'survey.survey',
        string='Instrumento origen',
        required=True,
        readonly=True,
    )

    # ── Destino ────────────────────────────────────────────────────────────
    survey_destino_id = fields.Many2one(
        'survey.survey',
        string='Instrumento destino',
        required=True,
        domain="[('id', '!=', survey_origen_id)]",
    )

    # ── Modo de traslado ───────────────────────────────────────────────────
    modo = fields.Selection([
        ('copiar', 'Copiar — quedan en origen Y van al destino'),
        ('mover',  'Mover  — se eliminan del origen'),
    ], string='Modo', default='copiar', required=True)

    # ── Opciones de qué incluir ────────────────────────────────────────────
    incluir_secciones = fields.Boolean(
        string='Incluir secciones',
        default=True,
        help='Crea la sección en el destino si no existe.',
    )
    incluir_opciones = fields.Boolean(
        string='Incluir opciones de respuesta',
        default=True,
        help='Copia las opciones (múltiple/única) con flg_is_correct y valor_puntaje.',
    )
    incluir_config_especial = fields.Boolean(
        string='Incluir configuración especial (GRID, audio, tiempo)',
        default=True,
        help='Copia la configuración de grids, audio automático y temporizador.',
    )

    # ── Preguntas seleccionadas ────────────────────────────────────────────
    pregunta_ids = fields.Many2many(
        'survey.question',
        'survey_copy_wiz_q_rel',
        'wizard_id',
        'question_id',
        string='Preguntas',
        domain="[('survey_id', '=', survey_origen_id), ('is_page', '=', False)]",
    )

    # ── Info ───────────────────────────────────────────────────────────────
    total_origen = fields.Integer(
        compute='_compute_info', store=False, string='Total en origen',
    )
    total_sel = fields.Integer(
        compute='_compute_info', store=False, string='Seleccionadas',
    )

    @api.depends('survey_origen_id', 'pregunta_ids')
    def _compute_info(self):
        for w in self:
            w.total_origen = len(
                w.survey_origen_id.question_and_page_ids.filtered(
                    lambda q: not q.is_page
                )
            ) if w.survey_origen_id else 0
            w.total_sel = len(w.pregunta_ids)

    # ── Acciones rápidas de selección ─────────────────────────────────────
    def action_sel_todas(self):
        self.ensure_one()
        qs = self.survey_origen_id.question_and_page_ids.filtered(
            lambda q: not q.is_page
        )
        self.pregunta_ids = [(6, 0, qs.ids)]
        return self._reopen()

    def action_sel_ninguna(self):
        self.ensure_one()
        self.pregunta_ids = [(5,)]
        return self._reopen()

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ── Ejecutar traslado ─────────────────────────────────────────────────
    def action_trasladar(self):
        self.ensure_one()

        if not self.pregunta_ids:
            raise ValidationError('Selecciona al menos una pregunta.')
        if not self.survey_destino_id:
            raise ValidationError('Selecciona el instrumento destino.')

        destino = self.survey_destino_id

        # Secuencia base al final del destino
        items_dst = destino.question_and_page_ids.sorted(
            key=lambda q: (q.sequence, q.id)
        )
        seq = (max(items_dst.mapped('sequence')) + 10) if items_dst else 10

        secciones_cache = {}  # titulo → id sección en destino

        preguntas_ordenadas = self.pregunta_ids.sorted(
            key=lambda q: (q.sequence, q.id)
        )

        for pregunta in preguntas_ordenadas:

            # ── Sección ─────────────────────────────────────────────────
            page_id = False
            if self.incluir_secciones and pregunta.page_id:
                titulo = (pregunta.page_id.title or '').strip()
                if titulo not in secciones_cache:
                    existente = destino.question_and_page_ids.filtered(
                        lambda q: q.is_page and (q.title or '').strip() == titulo
                    )
                    if existente:
                        secciones_cache[titulo] = existente[0].id
                    else:
                        nueva_sec = self.env['survey.question'].create({
                            'survey_id':     destino.id,
                            'title':         titulo,
                            'is_page':       True,
                            'question_type': 'text_box',
                            'sequence':      seq,
                        })
                        secciones_cache[titulo] = nueva_sec.id
                        seq += 10
                page_id = secciones_cache[titulo]

            # ── Campos base ─────────────────────────────────────────────
            vals = {
                'survey_id':    destino.id,
                'title':        pregunta.title,
                'question_type': pregunta.question_type or 'text_box',
                'is_page':      False,
                'sequence':     seq,
                'page_id':      page_id or False,
                # Nativo Odoo
                'description':            pregunta.description,
                'constr_mandatory':        pregunta.constr_mandatory,
                'constr_error_msg':        pregunta.constr_error_msg,
                'comments_allowed':        pregunta.comments_allowed,
                'comment_count_as_answer': pregunta.comment_count_as_answer,
                'save_as_email':           pregunta.save_as_email,
                'save_as_nickname':        pregunta.save_as_nickname,
                # Campos custom SISPAR
                'id_question_type':  pregunta.id_question_type.id if pregunta.id_question_type else False,
                'des_config_json':   pregunta.des_config_json,
                'flg_required':      pregunta.flg_required,
                'mostrar_info_seccion': pregunta.mostrar_info_seccion,
                'condiciones_fin_json': pregunta.condiciones_fin_json,
            }

            # ── Config especial ─────────────────────────────────────────
            if self.incluir_config_especial:
                vals.update({
                    'flg_time_limit':        pregunta.flg_time_limit,
                    'valor_limite_tiempo':   pregunta.valor_limite_tiempo,
                    'unidad_limite_tiempo':  pregunta.unidad_limite_tiempo,
                    'flg_auto_voice_record': pregunta.flg_auto_voice_record,
                    'modo_grabacion_voz':    pregunta.modo_grabacion_voz,
                    'flg_allow_image_attachment': pregunta.flg_allow_image_attachment,
                })

            nueva = self.env['survey.question'].create(vals)
            seq += 10

            # ── Opciones de respuesta ───────────────────────────────────
            if self.incluir_opciones and pregunta.suggested_answer_ids:
                for opt in pregunta.suggested_answer_ids.sorted('sequence'):
                    self.env['survey.question.answer'].create({
                        'question_id':    nueva.id,
                        'value':          opt.value,
                        'sequence':       opt.sequence,
                        'is_correct':     opt.is_correct,
                        'flg_is_correct': opt.flg_is_correct,
                        'valor_puntaje':  opt.valor_puntaje,
                    })

        # ── Si modo = mover, eliminar del origen ────────────────────────
        if self.modo == 'mover':
            self.pregunta_ids.unlink()

        n = len(preguntas_ordenadas)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title':   f'{"Copiadas" if self.modo == "copiar" else "Movidas"}: {n} preguntas',
                'message': f'Al instrumento "{destino.title}" — {self.modo}.',
                'type':    'success',
                'sticky':  False,
                'next': {
                    'type':      'ir.actions.act_window',
                    'res_model': 'survey.survey',
                    'res_id':    destino.id,
                    'view_mode': 'form',
                    'target':    'current',
                },
            },
        }
