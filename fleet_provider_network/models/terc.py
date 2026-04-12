from odoo import models, fields


class TercPartner(models.Model):
    _name = 'terc.partner'
    _description = 'TERC Partner'

    id_TERC_partner = fields.Integer(string="ID TERC Partner", required=True)
    id_SEG_empresa = fields.Integer(string="ID SEG Empresa")
    nom_TERC_partner = fields.Char(string="Nombre TERC Partner", required=True)
    nit = fields.Char(string="NIT")
    correo = fields.Char(string="Correo")
    telefono = fields.Char(string="Teléfono")
    celular = fields.Char(string="Celular")
    direccion = fields.Char(string="Dirección")
    ciudad = fields.Char(string="Ciudad")
    departamento = fields.Char(string="Departamento")
    pais = fields.Char(string="País")
    activo = fields.Boolean(string="Activo")
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")
