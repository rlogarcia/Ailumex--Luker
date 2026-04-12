from odoo import models, fields


class SegEmpresa(models.Model):
    _name = 'seg.empresa'
    _description = 'SEG Empresa'

    name = fields.Char(string="Nombre Empresa", required=True)
    activo = fields.Boolean(string="Activo", default=True)
    fecha_creacion = fields.Datetime(string="Fecha Creación", default=fields.Datetime.now)
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")

    usuario_ids = fields.One2many(
        comodel_name='seg.usuario',
        inverse_name='empresa_id',
        string="Usuarios de la Empresa"
    )


class SegUsuario(models.Model):
    _name = 'seg.usuario'
    _description = 'SEG Usuario'

    name = fields.Char(string="Nombre Usuario", required=True)
    login = fields.Char(string="Login", required=True)
    activo = fields.Boolean(string="Activo", default=True)
    fecha_creacion = fields.Datetime(string="Fecha Creación", default=fields.Datetime.now)
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")

    empresa_id = fields.Many2one(
        comodel_name='seg.empresa',
        string="Empresa",
        required=True,
        ondelete='restrict'
    )
