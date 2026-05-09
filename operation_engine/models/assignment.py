# -*- coding: utf-8 -*-
# OPE_Asignacion — Asignación de participante a campaña
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LukerOperationAssignment(models.Model):
    _name        = 'luker.operation.assignment'
    _description = 'Asignación Operativa SISPAR'
    _order       = 'campana_id, participante_id'
    _rec_name    = 'display_name'

    # ── Vínculos principales ──────────────────────────────────────────────────
    campana_id = fields.Many2one(
        'luker.operation.campaign',
        string='Campaña',
        required=True, ondelete='cascade', index=True,
    )
    participante_id = fields.Many2one(
        'luker.participant',
        string='Participante',
        required=True, ondelete='restrict', index=True,
    )
    executor_id = fields.Many2one(
        'luker.operation.executor',
        string='Aplicador asignado',
        domain="[('rol', 'in', ('aplicador', 'supervisor'))]",
        tracking=True,
    )

    # ── Estado ───────────────────────────────────────────────────────────────
    estado = fields.Selection([
        ('pendiente',    'Pendiente'),
        ('asignado',     'Asignado'),
        ('completado',   'Completado'),
        ('no_aplico',    'No aplicó'),
        ('cancelado',    'Cancelado'),
    ], string='Estado', default='pendiente', index=True)

    # ── Contexto de la asignación ────────────────────────────────────────────
    institucion_id = fields.Many2one(
        'luker.organization',
        string='Institución',
        related='participante_id.institucion_actual_id',
        store=True, readonly=True,
    )
    notas = fields.Text(string='Notas')
    fecha_asignacion = fields.Datetime(
        string='Fecha asignación',
        default=fields.Datetime.now,
        readonly=True,
    )

    # ── Nombre visible ────────────────────────────────────────────────────────
    display_name = fields.Char(
        compute='_compute_display_name',
        store=False,
    )

    @api.depends('campana_id', 'participante_id')
    def _compute_display_name(self):
        for a in self:
            camp = a.campana_id.nom_campana or ''
            part = a.participante_id.nom_completo or ''
            a.display_name = f'{camp} / {part}'

    # ── Constraint: sin duplicados por campaña ────────────────────────────────
    _sql_constraints = [
        ('unique_campana_participante',
         'UNIQUE(campana_id, participante_id)',
         'Este participante ya está asignado a esta campaña.'),
    ]

    @api.onchange('executor_id')
    def _onchange_executor(self):
        if self.executor_id:
            self.estado = 'asignado'
