# -*- coding: utf-8 -*-
# Snapshot de contexto del participante — IMMUTABLE
# Se crea automáticamente al iniciar una sesión de aplicación.
# Nunca se modifica. Es la fotografía del participante en ese momento.
import json
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class LukerParticipantSnapshot(models.Model):
    _name        = 'luker.participant.snapshot'
    _description = 'Snapshot de contexto del participante SISPAR'
    _order       = 'fecha_snapshot desc'
    _rec_name    = 'display_name'

    # ── Vínculos ──────────────────────────────────────────────────────────────
    participante_id = fields.Many2one(
        'luker.participant',
        string='Participante',
        required=True, ondelete='restrict', index=True,
    )
    sesion_id = fields.Many2one(
        'luker.application.result',
        string='Sesión de aplicación',
        readonly=True, ondelete='set null',
    )
    campana_id = fields.Many2one(
        'luker.operation.campaign',
        string='Campaña',
        readonly=True,
    )

    # ── Momento del snapshot ──────────────────────────────────────────────────
    fecha_snapshot = fields.Datetime(
        string='Fecha del snapshot',
        default=fields.Datetime.now,
        readonly=True,
    )

    # ── Datos congelados del participante ─────────────────────────────────────
    # Campos clave copiados en el momento (no relacionados — son copias reales)
    nom_completo       = fields.Char(string='Nombre completo', readonly=True)
    cod_participante   = fields.Char(string='Código participante', readonly=True)
    tipo_participante  = fields.Char(string='Tipo de participante', readonly=True)
    institucion        = fields.Char(string='Institución', readonly=True)
    estado_participante = fields.Char(string='Estado', readonly=True)

    # JSON con todos los atributos dinámicos vigentes en el momento
    contexto_json = fields.Text(
        string='Contexto completo (JSON)',
        readonly=True,
        help='Serialización completa del contexto del participante. '
             'Este campo nunca se modifica después de creado.',
    )

    display_name = fields.Char(
        compute='_compute_display_name', store=False,
    )

    @api.depends('participante_id', 'fecha_snapshot')
    def _compute_display_name(self):
        for s in self:
            nom = s.participante_id.nom_completo or ''
            fecha = str(s.fecha_snapshot)[:10] if s.fecha_snapshot else ''
            s.display_name = f'Snapshot — {nom} ({fecha})'

    # ── ORM: congelar contexto al crear ───────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            participante_id = vals.get('participante_id')
            if participante_id:
                participante = self.env['luker.participant'].browse(participante_id)
                if participante.exists():
                    vals.update(self._extraer_contexto(participante))
        return super().create(vals_list)

    def _extraer_contexto(self, participante):
        """Extrae y serializa el contexto completo del participante."""
        try:
            # Atributos dinámicos vigentes
            atributos = {}
            for attr in participante.attribute_value_ids.filtered(
                lambda a: a.es_vigente
            ):
                atributos[attr.attribute_id.name] = str(attr.val_value or '')

            contexto = {
                'cod_participante':  participante.cod_participante or '',
                'nom_completo':      participante.nom_completo or '',
                'tipo':              participante.tipo_participante_id.nom_tipo_participante
                                     if participante.tipo_participante_id else '',
                'institucion':       participante.institucion_actual_id.nom_unidad
                                     if participante.institucion_actual_id else '',
                'estado':            participante.estado or '',
                'email':             participante.email or '',
                'atributos_dinamicos': atributos,
                'fecha_snapshot':    str(fields.Datetime.now()),
            }
            return {
                'nom_completo':        contexto['nom_completo'],
                'cod_participante':    contexto['cod_participante'],
                'tipo_participante':   contexto['tipo'],
                'institucion':         contexto['institucion'],
                'estado_participante': contexto['estado'],
                'contexto_json':       json.dumps(contexto, ensure_ascii=False, default=str),
            }
        except Exception as exc:
            _logger.error('Error extrayendo contexto del participante %s: %s',
                          participante.id, exc)
            return {'contexto_json': '{}'}
