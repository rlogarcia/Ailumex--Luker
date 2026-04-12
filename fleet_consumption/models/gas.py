from odoo import models, fields


class GasVehiculoGasto(models.Model):
    _name = 'gas.vehiculo.gasto'
    _description = 'GAS Vehículo Gasto'

    id_GAS_vehiculo_gasto = fields.Integer(string="ID GAS Vehículo Gasto", required=True)
    id_SEG_empresa = fields.Integer(string="ID SEG Empresa")
    id_FLO_vehiculo = fields.Integer(string="ID FLO Vehículo")
    id_RRHH_empleado_conductor = fields.Integer(string="ID RRHH Empleado Conductor")
    id_PRO_proveedor_perfil = fields.Integer(string="ID PRO Proveedor Perfil")
    id_CHK_lista_vehiculo = fields.Integer(string="ID CHK Lista Vehículo")
    id_MTO_vehiculo_evento = fields.Integer(string="ID MTO Vehículo Evento")
    uuid_local = fields.Char(string="UUID Local", required=True)
    fecha_hora_gasto = fields.Datetime(string="Fecha Hora Gasto", required=True)
    tipo_gasto = fields.Char(string="Tipo Gasto", required=True)
    categoria = fields.Char(string="Categoría")
    cantidad = fields.Float(string="Cantidad", digits=(14, 2))
    valor = fields.Float(string="Valor", digits=(14, 2), required=True)
    url_evidencia = fields.Char(string="URL Evidencia")
    estado_sincronizacion = fields.Char(string="Estado Sincronización", required=True)
    dispositivo_id = fields.Char(string="Dispositivo ID")
    enviado_offline = fields.Boolean(string="Enviado Offline")
    fecha_envio_dispositivo = fields.Datetime(string="Fecha Envío Dispositivo")
    fecha_recepcion_servidor = fields.Datetime(string="Fecha Recepción Servidor")
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")
