from odoo import models, fields, api


class ChkPlantilla(models.Model):
    _name = 'chk.plantilla'
    _description = 'CHK Plantilla'
    _rec_name = 'nom_CHK_plantilla'
    _order = 'id desc'

    id_CHK_plantilla = fields.Integer(string="ID CHK Plantilla")
    id_SEG_empresa = fields.Integer(string="ID SEG Empresa")
    cod_CHK_plantilla = fields.Char(string="Código", readonly=True, default='Nuevo', copy=False)
    nom_CHK_plantilla = fields.Char(string="Nombre de Plantilla", required=True)
    tipo_vehiculo = fields.Char(string="Tipo Vehículo", required=True)
    version = fields.Char(string="Versión", required=True, default='1.0')
    es_activa = fields.Boolean(string="Activa", default=True)
    fecha_vigencia = fields.Date(string="Fecha Vigencia")
    linea_ids = fields.One2many('chk.plantilla.linea', 'plantilla_id', string="Ítems de la Plantilla")
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('cod_CHK_plantilla', 'Nuevo') == 'Nuevo':
                vals['cod_CHK_plantilla'] = self.env['ir.sequence'].next_by_code('chk.plantilla')
        return super().create(vals_list)


class ChkPlantillaLinea(models.Model):
    _name = 'chk.plantilla.linea'
    _description = 'CHK Plantilla Línea'
    _order = 'secuencia, id'

    id_CHK_plantilla_linea = fields.Integer(string="ID CHK Plantilla Línea")
    plantilla_id = fields.Many2one('chk.plantilla', string="Plantilla", ondelete='cascade')
    item_id = fields.Many2one('chk.item', string="Ítem", ondelete='restrict', required=True)
    requerido = fields.Boolean(string="Requerido", default=True)
    secuencia = fields.Integer(string="Secuencia", default=10)
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")


class ChkItem(models.Model):
    _name = 'chk.item'
    _rec_name = 'nom_CHK_item'
    _description = 'CHK Item'

    id_CHK_item = fields.Integer(string="ID CHK Item")
    id_SEG_empresa = fields.Integer(string="ID SEG Empresa")
    id_CHK_categoria = fields.Many2one('chk.categoria', string="Categoría", ondelete='set null')
    cod_CHK_item = fields.Char(string="Código CHK Item", readonly=True, default='Nuevo')
    nom_CHK_item = fields.Char(string="Nombre CHK Item", required=True)
    criticidad = fields.Selection([
        ('critico', 'Crítico'),
        ('alto',    'Alto'),
        ('medio',   'Medio'),
        ('bajo',    'Bajo'),
    ], string="Criticidad", required=True)
    requiere_evidencia_si_falla = fields.Boolean(string="Requiere Evidencia Si Falla")
    requiere_observacion_si_falla = fields.Boolean(string="Requiere Observación Si Falla")
    crear_novedad_si_falla = fields.Boolean(string="Crear Novedad Si Falla")
    bloquear_operacion_si_falla = fields.Boolean(string="Bloquear Operación Si Falla")
    activo = fields.Boolean(string="Activo")
    secuencia = fields.Integer(string="Secuencia")
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('cod_CHK_item', 'Nuevo') == 'Nuevo':
                vals['cod_CHK_item'] = self.env['ir.sequence'].next_by_code('chk.item')
        return super().create(vals_list)


class ChkCategoria(models.Model):
    _name = 'chk.categoria'
    _description = 'CHK Categoría'
    _rec_name = 'nom_categoria'
    _order = 'secuencia, id'

    id_CHK_categoria = fields.Integer(string="ID CHK Categoría")
    id_SEG_empresa = fields.Integer(string="ID SEG Empresa")
    nom_categoria = fields.Char(string="Nombre Categoría", required=True)
    secuencia = fields.Integer(string="Secuencia")
    activo = fields.Boolean(string="Activo")
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")


class ChkListaVehiculoLinea(models.Model):
    _name = 'chk.lista.vehiculo.linea'
    _description = 'CHK Lista Vehículo Línea'
    _order = 'id_CHK_categoria, id_CHK_item'

    id_CHK_lista_vehiculo_linea = fields.Integer(string="ID CHK Lista Vehículo Línea")
    id_CHK_lista_vehiculo = fields.Integer(string="ID CHK Lista Vehículo")
    checklist_id = fields.Many2one('chk.lista.vehiculo', string="Checklist", ondelete='cascade')
    item_id = fields.Many2one('chk.item', string="Ítem", ondelete='restrict',
                              domain=[('activo', '=', True)])
    categoria_id = fields.Many2one('chk.categoria', string="Categoría", ondelete='set null')
    id_CHK_item = fields.Integer(string="ID CHK Item")
    id_CHK_categoria = fields.Integer(string="ID CHK Categoría")
    nom_categoria = fields.Char(string="Categoría (texto)")
    uuid_local = fields.Char(string="UUID Local")
    cod_item = fields.Char(string="Código Item")
    nom_item = fields.Char(string="Nombre Item")
    respuesta = fields.Selection([
        ('bien',        'Bien'),
        ('observacion', 'Observación'),
        ('malo',        'Malo'),
    ], string="Respuesta", default='bien')
    puntaje = fields.Float(string="Puntaje", digits=(10, 2))
    criticidad = fields.Selection([
        ('critico', 'Crítico'),
        ('alto',    'Alto'),
        ('medio',   'Medio'),
        ('bajo',    'Bajo'),
    ], string="Criticidad")
    requiere_evidencia = fields.Boolean(string="Requiere Evidencia")
    url_evidencia = fields.Char(string="URL Evidencia")
    observacion = fields.Text(string="Observación")
    bloquear_operacion = fields.Boolean(string="Bloquear Operación")
    crear_novedad = fields.Boolean(string="Crear Novedad")
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")

    @api.onchange('item_id')
    def _onchange_item_id(self):
        if self.item_id:
            self.cod_item = self.item_id.cod_CHK_item
            self.nom_item = self.item_id.nom_CHK_item
            self.criticidad = self.item_id.criticidad
            self.categoria_id = self.item_id.id_CHK_categoria
            self.crear_novedad = self.item_id.crear_novedad_si_falla


class ChkListaVehiculo(models.Model):
    _name = 'chk.lista.vehiculo'
    _description = 'CHK Lista Vehículo'
    _rec_name = 'nom_checklist'

    id_CHK_lista_vehiculo = fields.Integer(string="ID CHK Lista Vehículo")
    id_SEG_empresa = fields.Integer(string="ID SEG Empresa")
    id_FLO_vehiculo = fields.Many2one('flo.vehiculo', string="Vehículo", domain=[('activo', '=', True)])
    id_RRHH_empleado_conductor = fields.Many2one('rrhh.empleado', string="Conductor")
    id_CHK_plantilla = fields.Integer(string="ID CHK Plantilla")
    plantilla_id = fields.Many2one('chk.plantilla', string="Plantilla Aplicada",
                                   domain=[('es_activa', '=', True)])
    id_SEG_usuario_revisor = fields.Integer(string="ID SEG Usuario Revisor")
    nom_checklist = fields.Char(string="Nombre Checklist")
    uuid_local = fields.Char(string="UUID Local")
    identificacion_conductor = fields.Char(string="Identificación Conductor")
    fecha_hora_checklist = fields.Datetime(string="Fecha Hora Checklist", required=True)
    odometro = fields.Float(string="Odómetro", digits=(14, 2), required=True)
    estado_nivel_combustible = fields.Char(string="Estado Nivel Combustible")
    url_evidencia_general = fields.Char(string="URL Evidencia General")
    notas_evidencia_general = fields.Text(string="Notas Evidencia General")
    resultado = fields.Char(string="Resultado")
    puntaje = fields.Float(string="Puntaje", digits=(10, 2))
    cantidad_ok = fields.Integer(string="Ítems OK")
    cantidad_fallas_criticas = fields.Integer(string="Cantidad Fallas Críticas")
    cantidad_alertas = fields.Integer(string="Cantidad Alertas")
    notas = fields.Text(string="Notas")
    estado = fields.Char(string="Estado")
    estado_sincronizacion = fields.Char(string="Estado Sincronización")
    dispositivo_id = fields.Char(string="Dispositivo ID")
    enviado_offline = fields.Boolean(string="Enviado Offline")
    fecha_envio_dispositivo = fields.Datetime(string="Fecha Envío Dispositivo")
    fecha_recepcion_servidor = fields.Datetime(string="Fecha Recepción Servidor")
    mensaje_sincronizacion = fields.Text(string="Mensaje Sincronización")
    fecha_revision = fields.Datetime(string="Fecha Revisión")
    linea_ids = fields.One2many('chk.lista.vehiculo.linea', 'checklist_id', string="Líneas del Checklist")
    origen = fields.Char(string="Origen", compute='_compute_origen', store=False)
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")

    @api.depends('enviado_offline')
    def _compute_origen(self):
        for rec in self:
            rec.origen = 'PWA Sync' if rec.enviado_offline else 'Backend'