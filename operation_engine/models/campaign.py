# -*- coding: utf-8 -*-
# OPE_Campaña — Campaña operativa SISPAR
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LukerOperationCampaign(models.Model):
    _name        = 'luker.operation.campaign'
    _description = 'Campaña Operativa SISPAR'
    _order       = 'fecha_inicio desc'
    _rec_name    = 'nom_campana'
    _inherit     = ['mail.thread', 'mail.activity.mixin']

    # ── Identificación ───────────────────────────────────────────────────────
    cod_campana = fields.Char(
        string='Código',
        readonly=True, copy=False, index=True,
        default='Nuevo',
        tracking=True,
    )
    nom_campana = fields.Char(
        string='Nombre de campaña',
        required=True,
        tracking=True,
    )
    descripcion = fields.Text(string='Descripción')

    # ── Instrumento vinculado ─────────────────────────────────────────────────
    survey_id = fields.Many2one(
        'survey.survey',
        string='Instrumento',
        required=True,
        tracking=True,
    )
    version_instrumento_id = fields.Many2one(
        'luker.instrument.version',
        string='Versión del instrumento',
        domain="[('survey_id', '=', survey_id), ('estado', '=', 'publicada')]",
        tracking=True,
    )
    cod_instrumento = fields.Char(
        string='Código instrumento',
        compute='_compute_cod_instrumento', store=True, readonly=True,
    )

    # ── Fechas ────────────────────────────────────────────────────────────────
    fecha_inicio = fields.Date(string='Fecha inicio', required=True, tracking=True)
    fecha_fin    = fields.Date(string='Fecha fin',    required=True, tracking=True)
    anio         = fields.Integer(
        string='Año',
        compute='_compute_anio', store=True,
    )

    # ── Estado ───────────────────────────────────────────────────────────────
    estado = fields.Selection([
        ('borrador',  'Borrador'),
        ('activa',    'Activa'),
        ('cerrada',   'Cerrada'),
        ('cancelada', 'Cancelada'),
    ], string='Estado', default='borrador', tracking=True, readonly=True)

    # ── Metas operativas ──────────────────────────────────────────────────────
    meta_participantes = fields.Integer(
        string='Meta de participantes',
        default=0,
    )
    institucion_ids = fields.Many2many(
        'luker.organization',
        'luker_campaign_organizacion_rel',
        'campaign_id', 'organizacion_id',
        string='Instituciones / Sedes',
    )
    responsable_id = fields.Many2one(
        'luker.operation.executor',
        string='Coordinador responsable',
        tracking=True,
    )
    notas = fields.Text(string='Notas operativas')

    # ── Estadísticas ──────────────────────────────────────────────────────────
    asignacion_count = fields.Integer(
        string='Asignaciones',
        compute='_compute_stats', store=False,
    )
    asignacion_ids = fields.One2many(
        'luker.operation.assignment',
        'campana_id',
        string='Asignaciones',
    )
    tarea_count = fields.Integer(
        string='Tareas',
        compute='_compute_stats', store=False,
    )
    tarea_completada_count = fields.Integer(
        string='Completadas',
        compute='_compute_stats', store=False,
    )
    pct_avance = fields.Float(
        string='Avance %',
        compute='_compute_stats', store=False,
        digits=(5, 1),
    )

    # ── Cómputos ─────────────────────────────────────────────────────────────
    @api.depends('survey_id')
    def _compute_cod_instrumento(self):
        for rec in self:
            rec.cod_instrumento = rec.survey_id.name[:30] if rec.survey_id else ''


    @api.depends('fecha_inicio')
    def _compute_anio(self):
        for c in self:
            c.anio = c.fecha_inicio.year if c.fecha_inicio else 0

    @api.depends()
    def _compute_stats(self):
        Assignment = self.env['luker.operation.assignment']
        Task = self.env['luker.operation.task']
        for c in self:
            asigs = Assignment.search([('campana_id', '=', c.id)])
            tareas = Task.search([('campana_id', '=', c.id)])
            completadas = tareas.filtered(lambda t: t.estado == 'completado')
            c.asignacion_count = len(asigs)
            c.tarea_count = len(tareas)
            c.tarea_completada_count = len(completadas)
            c.pct_avance = (
                len(completadas) / len(tareas) * 100
                if tareas else 0.0
            )

    # ── Constraints ──────────────────────────────────────────────────────────
    @api.constrains('fecha_inicio', 'fecha_fin')
    def _check_fechas(self):
        for c in self:
            if c.fecha_inicio and c.fecha_fin and c.fecha_fin < c.fecha_inicio:
                raise ValidationError(
                    'La fecha de fin debe ser posterior a la fecha de inicio.'
                )

    # ── ORM ───────────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('cod_campana') or vals['cod_campana'] == 'Nuevo':
                vals['cod_campana'] = self.env['ir.sequence'].next_by_code(
                    'luker.operation.campaign'
                ) or 'CAM-0001'
        return super().create(vals_list)

    # ── Acciones de estado ────────────────────────────────────────────────────
    def action_activar(self):
        for c in self:
            if not c.survey_id:
                raise ValidationError('La campaña debe tener un instrumento asignado.')
            if not c.fecha_inicio or not c.fecha_fin:
                raise ValidationError('La campaña debe tener fechas definidas.')
            c.write({'estado': 'activa'})

    def action_asignar_por_institucion(self):
        """Asigna masivamente todos los participantes de las instituciones seleccionadas."""
        self.ensure_one()
        if not self.institucion_ids:
            raise ValidationError(
                'Selecciona al menos una institución en la pestaña de Asignaciones.'
            )
        Participante = self.env['luker.participant']
        Assignment = self.env['luker.operation.assignment']
        creados = 0
        for institucion in self.institucion_ids:
            participantes = Participante.search([
                ('institucion_actual_id', '=', institucion.id),
                ('estado', '=', 'activo'),
            ])
            for p in participantes:
                existe = Assignment.search([
                    ('campana_id', '=', self.id),
                    ('participante_id', '=', p.id),
                ], limit=1)
                if not existe:
                    Assignment.create({
                        'campana_id':      self.id,
                        'participante_id': p.id,
                    })
                    creados += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Asignación masiva completada',
                'message': f'Se crearon {creados} asignaciones nuevas.',
                'type': 'success',
            }
        }

    def action_cerrar(self):
        self.write({'estado': 'cerrada'})

    def action_cancelar(self):
        self.write({'estado': 'cancelada'})

    def action_borrador(self):
        self.write({'estado': 'borrador'})

    def action_ver_tareas(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Tareas — {self.nom_campana}',
            'res_model': 'luker.operation.task',
            'view_mode': 'list,form',
            'domain': [('campana_id', '=', self.id)],
            'context': {'default_campana_id': self.id},
        }
