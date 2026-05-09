# -*- coding: utf-8 -*-
# OPE_Ejecutor — Extiende hr.employee para roles operativos SISPAR
# Los datos del ejecutor vienen del módulo de Empleados.
# Aquí solo se agregan el rol, instituciones y estadísticas SISPAR.
# Los datos personales (nombre, correo, doc, teléfono) los gestiona RRHH.
from odoo import models, fields, api


class LukerOperationExecutor(models.Model):
    _name        = 'luker.operation.executor'
    _description = 'Ejecutor SISPAR (Aplicador / Supervisor / Coordinador)'
    _order       = 'employee_id'
    _rec_name    = 'nom_ejecutor'

    # ── Vínculo con Empleados ─────────────────────────────────────────────────
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
        ondelete='restrict',
        index=True,
        help='Empleado del módulo RRHH vinculado a este ejecutor SISPAR.',
    )

    # ── Datos traídos del empleado (readonly) ─────────────────────────────────
    nom_ejecutor = fields.Char(
        string='Nombre',
        related='employee_id.name',
        store=True, readonly=True,
    )
    work_email = fields.Char(
        string='Correo laboral',
        related='employee_id.work_email',
        store=True, readonly=True,
    )
    work_phone = fields.Char(
        string='Teléfono laboral',
        related='employee_id.work_phone',
        store=True, readonly=True,
    )
    mobile_phone = fields.Char(
        string='Móvil',
        related='employee_id.mobile_phone',
        store=True, readonly=True,
    )
    job_title = fields.Char(
        string='Cargo',
        related='employee_id.job_title',
        store=True, readonly=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Departamento',
        related='employee_id.department_id',
        store=True, readonly=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Usuario Odoo',
        related='employee_id.user_id',
        store=True, readonly=True,
    )
    image_128 = fields.Image(
        string='Foto',
        related='employee_id.image_128',
        readonly=True,
    )

    # ── Datos del contacto personal ───────────────────────────────────────────
    num_identificacion = fields.Char(
        string='Número de identificación',
        related='employee_id.identification_id',
        store=True, readonly=True,
    )

    # ── Rol SISPAR ────────────────────────────────────────────────────────────
    rol = fields.Selection([
        ('aplicador',   'Aplicador'),
        ('supervisor',  'Supervisor'),
        ('coordinador', 'Coordinador'),
        ('logistico',   'Logístico'),
    ], string='Rol SISPAR', required=True, default='aplicador')

    cod_ejecutor = fields.Char(
        string='Código ejecutor',
        readonly=True, copy=False, index=True,
        default='Nuevo',
    )
    activo = fields.Boolean(string='Activo', default=True)

    # ── Cobertura operativa ───────────────────────────────────────────────────
    institucion_ids = fields.Many2many(
        'luker.organization',
        'luker_executor_organizacion_rel',
        'executor_id', 'organizacion_id',
        string='Instituciones asignadas',
    )

    # ── Estadísticas ──────────────────────────────────────────────────────────
    tarea_count = fields.Integer(
        string='Tareas',
        compute='_compute_tarea_count',
        store=False,
    )
    tarea_completada_count = fields.Integer(
        string='Completadas',
        compute='_compute_tarea_count',
        store=False,
    )

    @api.depends()
    def _compute_tarea_count(self):
        Task = self.env['luker.operation.task']
        for ex in self:
            tareas = Task.search([('executor_id', '=', ex.id)])
            ex.tarea_count = len(tareas)
            ex.tarea_completada_count = len(
                tareas.filtered(lambda t: t.estado == 'completado')
            )

    # ── Constraint: un empleado = un ejecutor ─────────────────────────────────
    _sql_constraints = [
        ('employee_unique', 'UNIQUE(employee_id)',
         'Este empleado ya está registrado como ejecutor SISPAR.'),
    ]

    # ── ORM ───────────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('cod_ejecutor') or vals['cod_ejecutor'] == 'Nuevo':
                vals['cod_ejecutor'] = self.env['ir.sequence'].next_by_code(
                    'luker.operation.executor'
                ) or 'EJE-0001'
        return super().create(vals_list)

    def action_ver_tareas(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Tareas — {self.nom_ejecutor}',
            'res_model': 'luker.operation.task',
            'view_mode': 'list,form',
            'domain': [('executor_id', '=', self.id)],
            'context': {'default_executor_id': self.id},
        }

    def action_abrir_empleado(self):
        """Navega al formulario del empleado en RRHH."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'form',
            'res_id': self.employee_id.id,
            'target': 'current',
        }


class HrEmployeeExecutorExtend(models.Model):
    """Agrega vínculo inverso en hr.employee → ejecutor SISPAR."""
    _inherit = 'hr.employee'

    executor_sispar_id = fields.One2many(
        'luker.operation.executor',
        'employee_id',
        string='Ejecutor SISPAR',
    )
    es_ejecutor_sispar = fields.Boolean(
        string='Es ejecutor SISPAR',
        compute='_compute_es_ejecutor',
        store=True,
    )

    @api.depends('executor_sispar_id')
    def _compute_es_ejecutor(self):
        for emp in self:
            emp.es_ejecutor_sispar = bool(emp.executor_sispar_id)

    def action_registrar_como_ejecutor(self):
        """Botón en el empleado para registrarlo como ejecutor SISPAR."""
        self.ensure_one()
        if self.executor_sispar_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'luker.operation.executor',
                'view_mode': 'form',
                'res_id': self.executor_sispar_id[0].id,
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Registrar como ejecutor SISPAR',
            'res_model': 'luker.operation.executor',
            'view_mode': 'form',
            'context': {'default_employee_id': self.id},
            'target': 'new',
        }
