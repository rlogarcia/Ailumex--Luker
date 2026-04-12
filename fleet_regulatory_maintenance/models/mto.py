from odoo import models, fields, api


class MtoVehiculoEvidencia(models.Model):
    _name = 'mto.vehiculo.evidencia'
    _description = 'MTO Vehículo Evidencia'

    id_MTO_vehiculo_evidencia = fields.Integer(string="ID MTO Vehículo Evidencia", required=True)
    id_MTO_vehiculo_evento = fields.Integer(string="ID MTO Vehículo Evento")
    nom_archivo = fields.Char(string="Nombre Archivo")
    url_archivo = fields.Char(string="URL Archivo")
    id_SEG_usuario_cargue = fields.Integer(string="ID SEG Usuario Cargue")
    fecha_cargue = fields.Datetime(string="Fecha Cargue")


class MtoVehiculoPlan(models.Model):
    _name = 'mto.vehiculo.plan'
    _description = 'MTO Vehículo Plan'

    id_MTO_vehiculo_plan = fields.Integer(string="ID MTO Vehículo Plan", required=True)
    id_SEG_empresa = fields.Integer(string="ID SEG Empresa")
    id_FLO_vehiculo = fields.Many2one('flo.vehiculo', string="ID FLO Vehículo")
    esquema_regulatorio = fields.Char(string="Esquema Regulatorio", required=True)
    unidad_frecuencia_preventiva = fields.Char(string="Unidad Frecuencia Preventiva", required=True)
    valor_frecuencia_preventiva = fields.Integer(string="Valor Frecuencia Preventiva", required=True)
    fecha_ultimo_preventivo = fields.Date(string="Fecha Último Preventivo")
    fecha_proximo_preventivo = fields.Date(string="Fecha Próximo Preventivo", required=True)
    estado_cumplimiento = fields.Char(string="Estado Cumplimiento", required=True)
    es_bimestral_regulado = fields.Boolean(string="Es Bimestral Regulado")
    requiere_aprobacion_empresa = fields.Boolean(string="Requiere Aprobación Empresa")
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")


class MtoVehiculoEvento(models.Model):
    _name = 'mto.vehiculo.evento'
    _description = 'MTO Vehículo Evento'

    id_MTO_vehiculo_evento = fields.Integer(string="ID MTO Vehículo Evento", required=True)
    id_SEG_empresa = fields.Integer(string="ID SEG Empresa")
    id_FLO_vehiculo = fields.Integer(string="ID FLO Vehículo")
    id_MTO_vehiculo_plan = fields.Integer(string="ID MTO Vehículo Plan")
    id_PRO_proveedor_perfil = fields.Integer(string="ID PRO Proveedor Perfil")
    id_SEG_usuario_aprobador = fields.Integer(string="ID SEG Usuario Aprobador")
    tipo_mantenimiento = fields.Char(string="Tipo Mantenimiento",selection=[('preventivo','Preventivo'),('correctivo','Correctivo')], required=True)
    origen_regulatorio = fields.Char(string="Origen Regulatorio")
    fecha_ejecucion = fields.Date(string="Fecha Ejecución", required=True)
    nom_centro_especializado = fields.Char(string="Nombre Centro Especializado", required=True)
    nom_ingeniero_mecanico = fields.Char(string="Nombre Ingeniero Mecánico")
    nom_tecnico = fields.Char(string="Nombre Técnico")
    detalle_actividades = fields.Text(string="Detalle Actividades", required=True)
    hallazgos = fields.Text(string="Hallazgos")
    recomendaciones = fields.Text(string="Recomendaciones")
    aprobado_por_empresa = fields.Boolean(string="Aprobado Por Empresa")
    fecha_aprobacion = fields.Datetime(string="Fecha Aprobación")
    odometro = fields.Float(string="Odómetro", digits=(14, 2))
    costo_total = fields.Float(string="Costo Total", digits=(14, 2))
    estado = fields.Char(string="Estado", required=True)
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")


class MtoFichaRegulatoria(models.Model):
    _name = 'mto.ficha.regulatoria'
    _description = 'MTO Ficha Regulatoria'
    _rec_name = 'nom_ficha'
    _order = 'fecha_ejecucion desc'

    nom_ficha = fields.Char(string="No. Ficha", readonly=True, copy=False, default='Nuevo')
    id_FLO_vehiculo = fields.Many2one('flo.vehiculo', string="Vehículo", ondelete='restrict')
    id_MTO_vehiculo_evento = fields.Many2one('mto.vehiculo.evento', string="Evento de Mantenimiento", ondelete='restrict')
    tipo_mantenimiento = fields.Selection([
        ('preventivo', 'Preventivo'),
        ('correctivo', 'Correctivo'),
    ], string="Tipo", required=True)
    fecha_ejecucion = fields.Date(string="Fecha", required=True)
    nom_centro_especializado = fields.Char(string="Proveedor / Centro")
    nom_ingeniero_mecanico = fields.Char(string="Ingeniero Mecánico")
    id_SEG_usuario_aprobador = fields.Many2one('res.users', string="Aprobado Por", ondelete='set null')
    estado = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    ], string="Estado", required=True, default='pendiente')
    detalle_actividades = fields.Text(string="Detalle Actividades")
    hallazgos = fields.Text(string="Hallazgos")
    recomendaciones = fields.Text(string="Recomendaciones")
    fecha_creacion_ficha = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion_ficha = fields.Datetime(string="Fecha Actualización")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('nom_ficha') or vals['nom_ficha'] == 'Nuevo':
                vals['nom_ficha'] = self.env['ir.sequence'].next_by_code('mto.ficha.regulatoria') or 'Nuevo'
        return super().create(vals_list)
