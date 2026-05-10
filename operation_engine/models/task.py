# -*- coding: utf-8 -*-
# OPE_Tarea — Tarea ejecutable SISPAR
# Unidad mínima de trabajo: un aplicador aplica un instrumento a un participante.
import uuid as _uuid
from odoo import models, fields, api
from odoo.exceptions import ValidationError


ESTADOS_TAREA = [
    ('pendiente',    'Pendiente'),
    ('programado',   'Programado'),
    ('en_progreso',  'En progreso'),
    ('completado',   'Completado'),
    ('fallido',      'Fallido'),
    ('reprogramado', 'Reprogramado'),
    ('cancelado',    'Cancelado'),
]


class LukerOperationTask(models.Model):
    _name        = 'luker.operation.task'
    _description = 'Tarea Operativa SISPAR'
    _order       = 'fecha_programada, estado'
    _rec_name    = 'cod_tarea'
    _inherit     = ['mail.thread']

    # ── Identificación ───────────────────────────────────────────────────────
    cod_tarea = fields.Char(
        string='Código tarea',
        readonly=True, copy=False, index=True,
        default='Nuevo',
    )
    uuid_local = fields.Char(
        string='UUID local',
        readonly=True, copy=False, index=True,
        help='UUID generado al crear la tarea. Garantiza idempotencia offline.',
    )

    # ── Vínculos operativos ───────────────────────────────────────────────────
    campana_id = fields.Many2one(
        'luker.operation.campaign',
        string='Campaña',
        required=True, ondelete='restrict', index=True,
        tracking=True,
    )
    asignacion_id = fields.Many2one(
        'luker.operation.assignment',
        string='Asignación',
        ondelete='restrict',
        domain="[('campana_id', '=', campana_id)]",
    )
    participante_id = fields.Many2one(
        'luker.participant',
        string='Participante',
        required=True, ondelete='restrict',
        related='asignacion_id.participante_id',
        store=True, readonly=False,
    )
    executor_id = fields.Many2one(
        'luker.operation.executor',
        string='Aplicador',
        required=True, ondelete='restrict',
        domain="[('activo', '=', True)]",
        tracking=True,
    )
    survey_id = fields.Many2one(
        'survey.survey',
        string='Instrumento',
        related='campana_id.survey_id',
        store=True, readonly=True,
    )

    # ── Estado y fechas ───────────────────────────────────────────────────────
    estado = fields.Selection(
        ESTADOS_TAREA,
        string='Estado',
        default='pendiente',
        index=True, tracking=True,
    )
    fecha_programada = fields.Datetime(
        string='Fecha programada',
        tracking=True,
    )
    fecha_inicio_real = fields.Datetime(
        string='Inicio real',
        readonly=True,
    )
    fecha_fin_real = fields.Datetime(
        string='Fin real',
        readonly=True,
    )
    duracion_minutos = fields.Integer(
        string='Duración (min)',
        compute='_compute_duracion',
        store=True,
    )

    # ── Resultado vinculado ───────────────────────────────────────────────────
    resultado_id = fields.Many2one(
        'luker.application.result',
        string='Sesión de aplicación',
        readonly=True, copy=False,
    )
    survey_input_id = fields.Many2one(
        'survey.user_input',
        string='Respuesta encuesta',
        related='resultado_id.survey_input_id',
        store=True, readonly=True,
    )

    # ── Sync offline ──────────────────────────────────────────────────────────
    enviado_offline = fields.Boolean(string='Capturado offline', default=False)
    estado_sync = fields.Selection([
        ('pendiente', 'Pendiente sync'),
        ('synced',    'Sincronizado'),
        ('error',     'Error de sync'),
        ('conflict',  'Conflicto'),
    ], string='Estado sync', default='pendiente')

    notas = fields.Text(string='Observaciones')

    # ── Cómputos ─────────────────────────────────────────────────────────────
    @api.depends('fecha_inicio_real', 'fecha_fin_real')
    def _compute_duracion(self):
        for t in self:
            if t.fecha_inicio_real and t.fecha_fin_real:
                delta = t.fecha_fin_real - t.fecha_inicio_real
                t.duracion_minutos = int(delta.total_seconds() / 60)
            else:
                t.duracion_minutos = 0

    # ── ORM ───────────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('cod_tarea') or vals['cod_tarea'] == 'Nuevo':
                vals['cod_tarea'] = self.env['ir.sequence'].next_by_code(
                    'luker.operation.task'
                ) or 'TAR-0001'
            if not vals.get('uuid_local'):
                vals['uuid_local'] = str(_uuid.uuid4())
        return super().create(vals_list)

    # ── Transiciones de estado ────────────────────────────────────────────────
    def action_iniciar(self):
        for t in self:
            if t.estado not in ('pendiente', 'programado', 'reprogramado'):
                raise ValidationError('Solo se pueden iniciar tareas pendientes o programadas.')
            t.write({
                'estado': 'en_progreso',
                'fecha_inicio_real': fields.Datetime.now(),
            })

    def action_completar(self):
        for t in self:
            if t.estado != 'en_progreso':
                raise ValidationError('Solo se pueden completar tareas en progreso.')
            t.write({
                'estado': 'completado',
                'fecha_fin_real': fields.Datetime.now(),
            })

    def action_reprogramar(self):
        self.write({'estado': 'reprogramado'})

    def action_cancelar(self):
        self.write({'estado': 'cancelado'})

    def action_marcar_fallido(self):
        self.write({
            'estado': 'fallido',
            'fecha_fin_real': fields.Datetime.now(),
        })
