# -*- coding: utf-8 -*-
# Sprint 2 — Logística de campo SISPAR
# Modelos: equipo logístico, agenda, incidentes, progreso
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import uuid as _uuid


# ── Equipo Logístico ──────────────────────────────────────────────────────────

class LukerOperationLogisticTeam(models.Model):
    _name        = 'luker.operation.logistic.team'
    _description = 'Equipo Logístico SISPAR'
    _order       = 'nom_equipo'
    _rec_name    = 'nom_equipo'

    nom_equipo   = fields.Char(string='Nombre del equipo', required=True)
    campana_id   = fields.Many2one(
        'luker.operation.campaign',
        string='Campaña', required=True, ondelete='cascade', index=True,
    )
    responsable_id = fields.Many2one(
        'luker.operation.executor',
        string='Responsable del equipo',
    )
    capacidad    = fields.Integer(string='Capacidad (participantes/día)', default=0)
    activo       = fields.Boolean(string='Activo', default=True)
    notas        = fields.Text(string='Notas')

    member_ids   = fields.One2many(
        'luker.operation.team.member', 'team_id', string='Miembros',
    )
    member_count = fields.Integer(
        string='Miembros', compute='_compute_member_count', store=False,
    )

    @api.depends('member_ids')
    def _compute_member_count(self):
        for t in self:
            t.member_count = len(t.member_ids)


class LukerOperationTeamMember(models.Model):
    _name        = 'luker.operation.team.member'
    _description = 'Miembro de Equipo Logístico'
    _rec_name    = 'executor_id'

    team_id     = fields.Many2one(
        'luker.operation.logistic.team',
        string='Equipo', required=True, ondelete='cascade',
    )
    executor_id = fields.Many2one(
        'luker.operation.executor',
        string='Ejecutor', required=True, ondelete='restrict',
    )
    fecha_inicio = fields.Date(string='Desde')
    fecha_fin    = fields.Date(string='Hasta')
    activo       = fields.Boolean(string='Activo', default=True)
    notas        = fields.Text(string='Notas')

    _sql_constraints = [
        ('unique_team_executor',
         'UNIQUE(team_id, executor_id)',
         'Este ejecutor ya hace parte de este equipo.'),
    ]


# ── Agenda y Logística ────────────────────────────────────────────────────────

class LukerOperationAgenda(models.Model):
    _name        = 'luker.operation.agenda'
    _description = 'Agenda Operativa SISPAR'
    _order       = 'fecha desc'
    _rec_name    = 'display_name'
    _inherit     = ['mail.thread']

    campana_id  = fields.Many2one(
        'luker.operation.campaign',
        string='Campaña', required=True, ondelete='cascade', index=True,
    )
    team_id     = fields.Many2one(
        'luker.operation.logistic.team',
        string='Equipo',
        domain="[('campana_id', '=', campana_id)]",
    )
    fecha       = fields.Date(string='Fecha', required=True, tracking=True)
    sede_id     = fields.Many2one(
        'luker.organization',
        string='Sede / Institución',
    )
    estado      = fields.Selection([
        ('planeada',   'Planeada'),
        ('en_curso',   'En curso'),
        ('completada', 'Completada'),
        ('cancelada',  'Cancelada'),
    ], string='Estado', default='planeada', tracking=True)

    item_ids    = fields.One2many(
        'luker.operation.agenda.item', 'agenda_id', string='Ítems',
    )
    total_items       = fields.Integer(compute='_compute_stats', store=False)
    items_completados = fields.Integer(compute='_compute_stats', store=False)
    notas       = fields.Text(string='Notas')

    display_name = fields.Char(compute='_compute_display_name', store=False)

    @api.depends('campana_id', 'fecha')
    def _compute_display_name(self):
        for a in self:
            camp = a.campana_id.nom_campana or ''
            fecha = str(a.fecha) if a.fecha else ''
            a.display_name = f'{camp} — {fecha}'

    @api.depends('item_ids', 'item_ids.estado')
    def _compute_stats(self):
        for a in self:
            a.total_items = len(a.item_ids)
            a.items_completados = len(
                a.item_ids.filtered(lambda i: i.estado == 'completado')
            )


class LukerOperationAgendaItem(models.Model):
    _name        = 'luker.operation.agenda.item'
    _description = 'Ítem de Agenda SISPAR'
    _order       = 'hora_inicio'

    agenda_id    = fields.Many2one(
        'luker.operation.agenda',
        string='Agenda', required=True, ondelete='cascade',
    )
    task_id      = fields.Many2one(
        'luker.operation.task',
        string='Tarea',
        domain="[('campana_id', '=', agenda_id.campana_id)]",
    )
    participante_id = fields.Many2one(
        'luker.participant',
        string='Participante',
        related='task_id.participante_id',
        store=True, readonly=True,
    )
    executor_id  = fields.Many2one(
        'luker.operation.executor',
        string='Aplicador',
        related='task_id.executor_id',
        store=True, readonly=True,
    )
    hora_inicio  = fields.Float(string='Hora inicio', digits=(4, 2))
    hora_fin     = fields.Float(string='Hora fin',    digits=(4, 2))
    estado       = fields.Selection([
        ('pendiente',  'Pendiente'),
        ('completado', 'Completado'),
        ('cancelado',  'Cancelado'),
    ], string='Estado', default='pendiente')
    notas        = fields.Text(string='Notas')


# ── Incidentes de campo ───────────────────────────────────────────────────────

class LukerOperationIncidentType(models.Model):
    _name        = 'luker.operation.incident.type'
    _description = 'Tipo de Novedad de Campo'
    _order       = 'sequence, nom_tipo'
    _rec_name    = 'nom_tipo'

    nom_tipo    = fields.Char(string='Nombre', required=True)
    cod_tipo    = fields.Char(string='Código', required=True)
    sequence    = fields.Integer(string='Secuencia', default=10)
    activo      = fields.Boolean(string='Activo', default=True)
    impacto     = fields.Selection([
        ('bajo',   'Bajo'),
        ('medio',  'Medio'),
        ('alto',   'Alto'),
        ('critico','Crítico'),
    ], string='Impacto', default='bajo')
    requiere_reprogramacion = fields.Boolean(
        string='Requiere reprogramación', default=False,
    )

    _sql_constraints = [
        ('cod_tipo_unique', 'UNIQUE(cod_tipo)', 'El código debe ser único.'),
    ]


class LukerOperationIncident(models.Model):
    _name        = 'luker.operation.incident'
    _description = 'Novedad de Campo SISPAR'
    _order       = 'fecha_incidente desc'
    _rec_name    = 'cod_incidente'
    _inherit     = ['mail.thread']

    cod_incidente  = fields.Char(
        string='Código', readonly=True, copy=False, index=True, default='Nuevo',
    )
    uuid_local     = fields.Char(
        string='UUID local', readonly=True, copy=False, index=True,
        help='UUID generado en el dispositivo. Garantiza idempotencia offline.',
    )

    # Vínculos operativos
    campana_id     = fields.Many2one(
        'luker.operation.campaign', string='Campaña',
        required=True, ondelete='restrict', index=True,
    )
    task_id        = fields.Many2one(
        'luker.operation.task', string='Tarea afectada',
        domain="[('campana_id', '=', campana_id)]",
    )
    executor_id    = fields.Many2one(
        'luker.operation.executor', string='Reportó',
    )
    tipo_id        = fields.Many2one(
        'luker.operation.incident.type', string='Tipo de novedad', required=True,
    )

    # Detalle
    descripcion    = fields.Text(string='Descripción', required=True)
    fecha_incidente = fields.Datetime(
        string='Fecha y hora', default=fields.Datetime.now, tracking=True,
    )
    estado         = fields.Selection([
        ('abierto',   'Abierto'),
        ('en_gestion','En gestión'),
        ('resuelto',  'Resuelto'),
        ('cerrado',   'Cerrado'),
    ], string='Estado', default='abierto', tracking=True)
    impacto        = fields.Selection(
        related='tipo_id.impacto', store=True, readonly=True,
    )
    enviado_offline = fields.Boolean(string='Capturado offline', default=False)
    resolucion      = fields.Text(string='Resolución')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('cod_incidente') or vals['cod_incidente'] == 'Nuevo':
                vals['cod_incidente'] = self.env['ir.sequence'].next_by_code(
                    'luker.operation.incident'
                ) or 'INC-00001'
            if not vals.get('uuid_local'):
                vals['uuid_local'] = str(_uuid.uuid4())
        return super().create(vals_list)

    def action_resolver(self):
        self.write({'estado': 'resuelto'})

    def action_cerrar(self):
        self.write({'estado': 'cerrado'})


# ── Monitoreo de Progreso ─────────────────────────────────────────────────────

class LukerOperationProgress(models.Model):
    _name        = 'luker.operation.progress'
    _description = 'Progreso de Campaña SISPAR'
    _order       = 'fecha_snapshot desc'
    _rec_name    = 'campana_id'

    campana_id         = fields.Many2one(
        'luker.operation.campaign', string='Campaña',
        required=True, ondelete='cascade', index=True,
    )
    fecha_snapshot     = fields.Datetime(
        string='Fecha del snapshot', default=fields.Datetime.now, readonly=True,
    )
    # Métricas
    total_asignaciones = fields.Integer(string='Total asignaciones')
    completadas        = fields.Integer(string='Completadas')
    pendientes         = fields.Integer(string='Pendientes')
    fallidas           = fields.Integer(string='Fallidas')
    incidentes_abiertos = fields.Integer(string='Incidentes abiertos')
    pct_avance         = fields.Float(string='Avance %', digits=(5, 1))

    @api.model
    def generar_snapshot(self, campana_id):
        """Genera un snapshot de progreso para la campaña indicada."""
        campana = self.env['luker.operation.campaign'].browse(campana_id)
        if not campana.exists():
            return

        Task = self.env['luker.operation.task']
        Incident = self.env['luker.operation.incident']

        tareas = Task.search([('campana_id', '=', campana_id)])
        incidentes = Incident.search([
            ('campana_id', '=', campana_id),
            ('estado', 'in', ('abierto', 'en_gestion')),
        ])

        completadas = len(tareas.filtered(lambda t: t.estado == 'completado'))
        total = len(tareas)

        self.create({
            'campana_id':          campana_id,
            'total_asignaciones':  campana.asignacion_count,
            'completadas':         completadas,
            'pendientes':          len(tareas.filtered(
                lambda t: t.estado in ('pendiente', 'programado')
            )),
            'fallidas':            len(tareas.filtered(lambda t: t.estado == 'fallido')),
            'incidentes_abiertos': len(incidentes),
            'pct_avance':          (completadas / total * 100) if total else 0.0,
        })
