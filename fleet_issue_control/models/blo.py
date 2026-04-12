from odoo import models, fields, api


class BloVehiculoBloqueo(models.Model):
    _name = 'blo.vehiculo.bloqueo'
    _description = 'BLO Vehículo Bloqueo'
    _rec_name = 'id_FLO_vehiculo'
    _order = 'fecha_hora_inicio desc'

    id_BLO_vehiculo_bloqueo = fields.Char(string="ID BLO Vehículo Bloqueo", copy=False, readonly=True, default='Nuevo')
    id_SEG_empresa = fields.Many2one(comodel_name='seg.empresa', string="Empresa", ondelete='restrict')
    id_FLO_vehiculo = fields.Many2one(comodel_name='flo.vehiculo', string="Vehículo", ondelete='restrict')
    id_CHK_lista_vehiculo = fields.Many2one(comodel_name='chk.lista.vehiculo', string="Checklist Origen", ondelete='set null')
    id_SEG_supervisor = fields.Many2one(comodel_name='seg.usuario', string="Supervisor", ondelete='set null')
    id_SEG_usuario_liberador = fields.Many2one(comodel_name='seg.usuario', string="Usuario Liberador", ondelete='set null')
    id_NOV_vehiculo_novedad = fields.Many2one(comodel_name='nov.vehiculo.novedad', string="Novedad Origen", ondelete='set null')
    modelo_origen = fields.Char(string="Modelo Origen")
    id_origen = fields.Many2one(comodel_name='chk.lista.vehiculo', string="ID Origen")
    item_causante = fields.Many2one(comodel_name='chk.item', string="Ítem Causante")
    motivo = fields.Text(string="Causa", required=True)
    severidad = fields.Selection([
        ('Critica', 'Crítica'),
        ('Alta', 'Alta'),
        ('Media', 'Media'),
        ('Baja', 'Baja'),
    ], string="Severidad", required=True)
    fecha_hora_inicio = fields.Datetime(string="Bloqueado En", required=True)
    fecha_hora_fin = fields.Datetime(string="Liberado En")
    estado = fields.Selection([
        ('activo', 'Activo'),
        ('historico', 'Histórico'),
        ('liberado', 'Liberado'),
    ], string="Estado", required=True, default='activo')
    notas_liberacion = fields.Text(string="Notas Liberación")
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")

    def action_liberar(self):
        for rec in self:
            rec.estado = 'liberado'
            rec.fecha_hora_fin = fields.Datetime.now()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('id_BLO_vehiculo_bloqueo') or vals['id_BLO_vehiculo_bloqueo'] == 'Nuevo':
                vals['id_BLO_vehiculo_bloqueo'] = self.env['ir.sequence'].next_by_code('blo.vehiculo.bloqueo') or 'Nuevo'
        return super().create(vals_list)

