from odoo import models, fields, api


class NovVehiculoNovedad(models.Model):
    _name = 'nov.vehiculo.novedad'
    _description = 'NOV Vehículo Novedad'
    _rec_name = 'nom_novedad'

    id_NOV_vehiculo_novedad = fields.Char(string="ID NOV Vehículo Novedad", required=True, copy=False, readonly=True, default='Nuevo')
    id_SEG_empresa = fields.Many2one(comodel_name='seg.empresa', string="Empresa", ondelete='restrict')
    id_FLO_vehiculo = fields.Many2one(comodel_name='flo.vehiculo', string="Vehículo", ondelete='restrict')
    id_CHK_lista_vehiculo = fields.Many2one(comodel_name='chk.lista.vehiculo', string="Checklist Origen", ondelete='set null')
    id_RRHH_empleado_conductor = fields.Many2one(comodel_name='rrhh.empleado', string="Conductor", ondelete='restrict')
    id_SEG_usuario_asignado = fields.Many2one(comodel_name='seg.usuario', string="Usuario Asignado", ondelete='set null')
    id_MTO_vehiculo_evento = fields.Integer(string="ID MTO Vehículo Evento")
    nom_novedad = fields.Char(string="Nombre Novedad", required=True)
    fuente = fields.Char(string="Fuente", required=True)
    tipo_novedad = fields.Char(string="Tipo Novedad", required=True)
    severidad = fields.Selection([
        ('Critica', 'Crítica'),
        ('Alta', 'Alta'),
        ('Media', 'Media'),
        ('Baja', 'Baja'),
    ], string="Severidad", required=True)
    descripcion = fields.Text(string="Descripción", required=True)
    url_evidencia = fields.Char(string="URL Evidencia")
    estado = fields.Selection([
        ('Nueva', 'Nueva'),
        ('En Revisión', 'En Revisión'),
        ('Programada', 'Programada'),
        ('Resuelta', 'Resuelta'),
    ], string="Estado", required=True, default='Nueva', group_expand='_group_expand_estado')

    @api.model
    def _group_expand_estado(self, states, domain):
        return [s[0] for s in self._fields['estado'].selection]
    notas_resolucion = fields.Text(string="Notas Resolución")
    fecha_reporte = fields.Datetime(string="Fecha Reporte", required=True)
    fecha_cierre = fields.Datetime(string="Fecha Cierre")
    uuid_local = fields.Char(string="UUID Local")
    estado_sincronizacion = fields.Char(string="Estado Sincronización")
    dispositivo_id = fields.Char(string="Dispositivo ID")
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")
    bloqueo_ids = fields.One2many(comodel_name='blo.vehiculo.bloqueo', inverse_name='id_NOV_vehiculo_novedad', string="Bloqueos Generados")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('id_NOV_vehiculo_novedad') or vals['id_NOV_vehiculo_novedad'] == 'Nuevo':
                vals['id_NOV_vehiculo_novedad'] = self.env['ir.sequence'].next_by_code('nov.vehiculo.novedad') or 'Nuevo'
        return super().create(vals_list)