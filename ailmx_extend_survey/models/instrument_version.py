# -*- coding: utf-8 -*-
# Versionamiento formal de instrumentos (survey.survey)
# Permite crear snapshots de un instrumento en un momento dado,
# seleccionar qué preguntas incluir, nombrar la versión y hacer seguimiento.
import hashlib
import json
import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class LukerInstrumentVersion(models.Model):
    _name        = 'luker.instrument.version'
    _description = 'Versión de instrumento SISPAR'
    _order       = 'fecha_creacion desc, id desc'
    _rec_name    = 'cod_version'

    # ── Identificación ───────────────────────────────────────────────────────
    cod_version = fields.Char(
        string='Código de versión',
        readonly=True, copy=False, index=True,
        help='Generado automáticamente. Ej: INS-001-V2026-001',
    )
    nom_version = fields.Char(
        string='Nombre de versión',
        required=True,
        help='Nombre descriptivo. Ej: "SISPAR 2026 — Primera aplicación"',
    )
    anio = fields.Integer(
        string='Año',
        required=True,
        default=lambda self: fields.Date.today().year,
        help='Año al que corresponde esta versión del instrumento.',
    )
    num_version = fields.Integer(
        string='Número de versión',
        readonly=True,
        help='Número secuencial dentro del mismo instrumento y año.',
    )

    # ── Instrumento padre ────────────────────────────────────────────────────
    survey_id = fields.Many2one(
        'survey.survey',
        string='Instrumento',
        required=True,
        ondelete='cascade',
        index=True,
    )

    # ── Estado ───────────────────────────────────────────────────────────────
    estado = fields.Selection([
        ('borrador',   'Borrador'),
        ('publicada',  'Publicada'),
        ('deprecada',  'Deprecada'),
    ], string='Estado', default='borrador', readonly=True, copy=False)

    # ── Preguntas incluidas ──────────────────────────────────────────────────
    question_ids = fields.Many2many(
        'survey.question',
        'luker_instrument_version_question_rel',
        'version_id',
        'question_id',
        string='Preguntas incluidas',
        domain="[('survey_id', '=', survey_id), ('is_page', '=', False)]",
        help='Preguntas del instrumento que forman parte de esta versión.',
    )
    num_preguntas = fields.Integer(
        string='Preguntas',
        compute='_compute_estadisticas',
        store=True,
    )

    # ── Trazabilidad ─────────────────────────────────────────────────────────
    fecha_creacion  = fields.Datetime(
        string='Creada',
        default=fields.Datetime.now,
        readonly=True,
    )
    usuario_creacion_id = fields.Many2one(
        'res.users',
        string='Creada por',
        default=lambda self: self.env.user,
        readonly=True,
    )
    fecha_publicacion = fields.Datetime(
        string='Publicada',
        readonly=True,
    )
    usuario_publicacion_id = fields.Many2one(
        'res.users',
        string='Publicada por',
        readonly=True,
    )
    fecha_deprecacion = fields.Datetime(
        string='Deprecada',
        readonly=True,
    )

    # ── Versión anterior ─────────────────────────────────────────────────────
    version_anterior_id = fields.Many2one(
        'luker.instrument.version',
        string='Versión anterior',
        readonly=True,
        help='Versión de la que deriva esta. Trazabilidad del linaje.',
    )
    version_siguiente_id = fields.Many2one(
        'luker.instrument.version',
        string='Versión siguiente',
        readonly=True,
        compute='_compute_version_siguiente',
        store=False,
    )

    # ── Notas ────────────────────────────────────────────────────────────────
    descripcion_cambios = fields.Text(
        string='Cambios respecto a versión anterior',
        help='Descripción de qué cambió en esta versión.',
    )
    notas = fields.Text(string='Notas internas')

    # ── Hash de contenido ────────────────────────────────────────────────────
    hash_contenido = fields.Char(
        string='Hash de contenido',
        readonly=True,
        help='Huella digital del contenido — garantiza que no fue alterado.',
    )

    # ── Cómputos ─────────────────────────────────────────────────────────────
    @api.depends('question_ids')
    def _compute_estadisticas(self):
        for v in self:
            v.num_preguntas = len(v.question_ids)

    def _compute_version_siguiente(self):
        for v in self:
            siguiente = self.search([
                ('version_anterior_id', '=', v.id)
            ], limit=1, order='fecha_creacion asc')
            v.version_siguiente_id = siguiente

    # ── Constraints ──────────────────────────────────────────────────────────
    _sql_constraints = [
        ('cod_version_unique', 'UNIQUE(cod_version)',
         'El código de versión debe ser único.'),
    ]

    # ── Onchange: precargar preguntas del instrumento ─────────────────────────
    @api.onchange('survey_id')
    def _onchange_survey_id(self):
        if self.survey_id:
            preguntas = self.survey_id.question_and_page_ids.filtered(
                lambda q: not q.is_page
            )
            self.question_ids = preguntas

    # ── ORM ──────────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            survey_id = vals.get('survey_id')
            anio = vals.get('anio', fields.Date.today().year)

            # Calcular número secuencial por instrumento + año
            ultimo = self.search([
                ('survey_id', '=', survey_id),
                ('anio', '=', anio),
            ], order='num_version desc', limit=1)
            num = (ultimo.num_version + 1) if ultimo else 1
            vals['num_version'] = num

            # Obtener código del instrumento
            survey = self.env['survey.survey'].browse(survey_id)
            cod_ins = getattr(survey, 'cod_instrument', 'INS') or 'INS'
            vals['cod_version'] = f'{cod_ins}-V{anio}-{num:03d}'

        records = super().create(vals_list)

        # Calcular hash de contenido inicial
        for rec in records:
            rec._calcular_hash()

        return records

    # ── Acciones de flujo ─────────────────────────────────────────────────────
    def action_publicar(self):
        for rec in self:
            if rec.estado != 'borrador':
                raise ValidationError(
                    'Solo se puede publicar una versión en estado Borrador.'
                )
            if not rec.question_ids:
                raise ValidationError(
                    'La versión debe tener al menos una pregunta antes de publicarse.'
                )
            rec._calcular_hash()
            rec.write({
                'estado': 'publicada',
                'fecha_publicacion': fields.Datetime.now(),
                'usuario_publicacion_id': self.env.user.id,
            })

    def action_deprecar(self):
        for rec in self:
            if rec.estado != 'publicada':
                raise ValidationError(
                    'Solo se puede deprecar una versión publicada.'
                )
            rec.write({
                'estado': 'deprecada',
                'fecha_deprecacion': fields.Datetime.now(),
            })

    def action_nueva_version(self):
        """Crea una nueva versión a partir de esta, copiando sus preguntas."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nueva versión del instrumento',
            'res_model': 'luker.instrument.version',
            'view_mode': 'form',
            'context': {
                'default_survey_id':          self.survey_id.id,
                'default_version_anterior_id': self.id,
                'default_anio':               fields.Date.today().year,
                'default_question_ids':       self.question_ids.ids,
                'default_descripcion_cambios': '',
            },
            'target': 'new',
        }

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _calcular_hash(self):
        """Genera un hash SHA-256 del contenido del instrumento."""
        self.ensure_one()
        contenido = {
            'survey_id': self.survey_id.id,
            'anio': self.anio,
            'preguntas': sorted(self.question_ids.ids),
        }
        raw = json.dumps(contenido, sort_keys=True).encode('utf-8')
        self.hash_contenido = hashlib.sha256(raw).hexdigest()[:16].upper()


class SurveySurveyVersionExtend(models.Model):
    """Agrega el vínculo inverso y el botón de versionar al survey.survey."""
    _inherit = 'survey.survey'

    version_ids = fields.One2many(
        'luker.instrument.version',
        'survey_id',
        string='Versiones',
    )
    num_versiones = fields.Integer(
        string='Versiones',
        compute='_compute_num_versiones',
        store=False,
    )
    ultima_version_id = fields.Many2one(
        'luker.instrument.version',
        string='Última versión',
        compute='_compute_ultima_version',
        store=False,
    )

    @api.depends('version_ids')
    def _compute_num_versiones(self):
        for s in self:
            s.num_versiones = len(s.version_ids)

    def _compute_ultima_version(self):
        Version = self.env['luker.instrument.version']
        for s in self:
            v = Version.search([
                ('survey_id', '=', s.id),
                ('estado', '=', 'publicada'),
            ], order='fecha_creacion desc', limit=1)
            s.ultima_version_id = v

    def action_crear_version(self):
        """Botón 'Versionar' en el formulario del instrumento."""
        self.ensure_one()
        # Buscar la última versión publicada para usar como base
        ultima = self.env['luker.instrument.version'].search([
            ('survey_id', '=', self.id),
        ], order='fecha_creacion desc', limit=1)

        preguntas = self.question_and_page_ids.filtered(
            lambda q: not q.is_page
        )

        ctx = {
            'default_survey_id': self.id,
            'default_anio': fields.Date.today().year,
            'default_question_ids': preguntas.ids,
        }
        if ultima:
            ctx['default_version_anterior_id'] = ultima.id

        return {
            'type': 'ir.actions.act_window',
            'name': f'Nueva versión — {self.title}',
            'res_model': 'luker.instrument.version',
            'view_mode': 'form',
            'view_id': self.env.ref(
                'ailmx_extend_survey.view_luker_instrument_version_form'
            ).id,
            'context': ctx,
            'target': 'new',
        }

    def action_ver_versiones(self):
        """Smart button para ver todas las versiones."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Versiones — {self.title}',
            'res_model': 'luker.instrument.version',
            'view_mode': 'list,form',
            'domain': [('survey_id', '=', self.id)],
            'context': {'default_survey_id': self.id},
        }
