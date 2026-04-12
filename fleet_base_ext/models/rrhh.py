from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class RrhhEmpleado(models.Model):
    _name = 'rrhh.empleado'
    _description = 'RRHH Empleado'
    _rec_name = 'nom_RRHH_empleado'

    id_RRHH_empleado = fields.Integer(string="ID RRHH Empleado", required=True)
    id_SEG_empresa = fields.Many2one(
        comodel_name='seg.empresa',
        string="Empresa",
    )
    id_SEG_usuario = fields.Many2one(
        comodel_name='seg.usuario',
        string="Usuario",
    )
    foto_empleado = fields.Image(string="Foto")
    nom_RRHH_empleado = fields.Char(string="Nombre", required=True)
    num_identificacion = fields.Char(string="Cédula", required=True)
    telefono = fields.Char(string="Teléfono", required=True)
    correo = fields.Char(string="Correo")
    num_licencia = fields.Char(string="Licencia")
    categoria_licencia = fields.Selection([
        ('A1', 'A1'),
        ('A2', 'A2'),
        ('B1', 'B1'),
        ('B2', 'B2'),
        ('B3', 'B3'),
        ('C1', 'C1'),
        ('C2', 'C2'),
        ('C3', 'C3'),
    ], string="Categoría", required=True)
    fecha_vencimiento_licencia = fields.Date(string="Vencimiento Lic.", required=True)
    es_conductor = fields.Boolean(string="Es Conductor")
    activo = fields.Boolean(string="Activo")
    estado = fields.Selection([
        ('activo', 'Activo'),
        ('alerta', 'Alerta'),
        ('inactivo', 'Inactivo'),
    ], string="Estado", default='activo')
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")

    # Computed fields
    vehiculo_asignado = fields.Char(
        string="Vehículo Asignado",
        compute='_compute_vehiculo_asignado',
        store=False,
    )
    checklists_mes = fields.Integer(
        string="Checklists (Mes)",
        compute='_compute_checklists_mes',
        store=False,
    )

    @api.depends_context('uid')
    def _compute_vehiculo_asignado(self):
        for rec in self:
            asignacion = self.env['flo.vehiculo.conductor'].search([
                ('id_RRHH_empleado', '=', rec.id),
                ('estado', '=', 'activo'),
            ], limit=1)
            if asignacion and asignacion.id_FLO_vehiculo:
                rec.vehiculo_asignado = asignacion.id_FLO_vehiculo.placa
            else:
                rec.vehiculo_asignado = False

    @api.depends_context('uid')
    def _compute_checklists_mes(self):
        if 'chk.lista.vehiculo' not in self.env:
            for rec in self:
                rec.checklists_mes = 0
            return
        today = fields.Date.context_today(self)
        first_day = today.replace(day=1)
        last_day = (first_day + relativedelta(months=1)) - relativedelta(days=1)
        for rec in self:
            count = self.env['chk.lista.vehiculo'].search_count([
                ('id_RRHH_empleado_conductor', '=', rec.id_RRHH_empleado),
                ('fecha_hora_checklist', '>=', fields.Datetime.to_string(first_day)),
                ('fecha_hora_checklist', '<=', fields.Datetime.to_string(last_day)),
            ])
            rec.checklists_mes = count
