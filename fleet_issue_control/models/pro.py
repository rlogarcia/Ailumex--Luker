from odoo import models, fields


class ProProveedorPerfil(models.Model):
    _name = 'pro.proveedor.perfil'
    _description = 'PRO Proveedor Perfil'

    id_PRO_proveedor_perfil = fields.Many2one(string="ID PRO Proveedor Perfil", required=True)
    id_SEG_empresa = fields.Many2one(string="ID SEG Empresa")
    id_TERC_partner = fields.Many2one(string="ID TERC Partner")
    cod_proveedor = fields.Char(string="Código Proveedor", required=True)
    es_proveedor_flota = fields.Boolean(string="Es Proveedor Flota")
    disponible_24_7 = fields.Boolean(string="Disponible 24/7")
    modalidad_servicio = fields.Char(string="Modalidad Servicio")
    estado_aprobacion = fields.Char(string="Estado Aprobación", required=True)
    rating = fields.Float(string="Rating", digits=(5, 2))
    estado_contrato = fields.Char(string="Estado Contrato")
    fecha_inicio = fields.Date(string="Fecha Inicio")
    fecha_fin = fields.Date(string="Fecha Fin")
    documentos_completos = fields.Boolean(string="Documentos Completos")
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")


class ProProveedorPerfilTipo(models.Model):
    _name = 'pro.proveedor.perfil.tipo'
    _description = 'PRO Proveedor Perfil Tipo'

    id_PRO_proveedor_perfil_tipo = fields.Integer(string="ID PRO Proveedor Perfil Tipo", required=True)
    id_PRO_proveedor_perfil = fields.Integer(string="ID PRO Proveedor Perfil")
    id_PRO_tipo_proveedor = fields.Integer(string="ID PRO Tipo Proveedor")


class ProEspecialidadProveedor(models.Model):
    _name = 'pro.especialidad.proveedor'
    _description = 'PRO Especialidad Proveedor'

    id_PRO_especialidad_proveedor = fields.Integer(string="ID PRO Especialidad Proveedor", required=True)
    id_SEG_empresa = fields.Integer(string="ID SEG Empresa")
    id_PRO_tipo_proveedor = fields.Integer(string="ID PRO Tipo Proveedor")
    nom_especialidad_proveedor = fields.Char(string="Nombre Especialidad Proveedor", required=True)
    activo = fields.Boolean(string="Activo")
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")


class ProProveedorDocumento(models.Model):
    _name = 'pro.proveedor.documento'
    _description = 'PRO Proveedor Documento'

    id_PRO_proveedor_documento = fields.Integer(string="ID PRO Proveedor Documento", required=True)
    id_PRO_proveedor_perfil = fields.Integer(string="ID PRO Proveedor Perfil")
    tipo_documento = fields.Char(string="Tipo Documento", required=True)
    num_documento = fields.Char(string="Número Documento")
    fecha_emision = fields.Date(string="Fecha Emisión")
    fecha_vencimiento = fields.Date(string="Fecha Vencimiento")
    url_archivo = fields.Char(string="URL Archivo")
    estado = fields.Char(string="Estado", required=True)
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")


class ProTipoProveedor(models.Model):
    _name = 'pro.tipo.proveedor'
    _description = 'PRO Tipo Proveedor'

    id_PRO_tipo_proveedor = fields.Integer(string="ID PRO Tipo Proveedor", required=True)
    id_SEG_empresa = fields.Integer(string="ID SEG Empresa")
    cod_tipo_proveedor = fields.Char(string="Código Tipo Proveedor", required=True)
    nom_tipo_proveedor = fields.Char(string="Nombre Tipo Proveedor", required=True)
    activo = fields.Boolean(string="Activo")
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")


class ProProveedorPerfilEspecialidad(models.Model):
    _name = 'pro.proveedor.perfil.especialidad'
    _description = 'PRO Proveedor Perfil Especialidad'

    id_PRO_proveedor_perfil_especialidad = fields.Integer(string="ID PRO Proveedor Perfil Especialidad", required=True)
    id_PRO_proveedor_perfil = fields.Integer(string="ID PRO Proveedor Perfil")
    id_PRO_especialidad_proveedor = fields.Integer(string="ID PRO Especialidad Proveedor")


class ProProveedorEvaluacion(models.Model):
    _name = 'pro.proveedor.evaluacion'
    _description = 'PRO Proveedor Evaluación'

    id_PRO_proveedor_evaluacion = fields.Integer(string="ID PRO Proveedor Evaluación", required=True)
    id_PRO_proveedor_perfil = fields.Integer(string="ID PRO Proveedor Perfil")
    id_SEG_usuario_evaluador = fields.Integer(string="ID SEG Usuario Evaluador")
    fecha_evaluacion = fields.Date(string="Fecha Evaluación", required=True)
    puntaje_calidad = fields.Float(string="Puntaje Calidad", digits=(5, 2))
    puntaje_servicio = fields.Float(string="Puntaje Servicio", digits=(5, 2))
    puntaje_tiempo_respuesta = fields.Float(string="Puntaje Tiempo Respuesta", digits=(5, 2))
    puntaje_costo = fields.Float(string="Puntaje Costo", digits=(5, 2))
    puntaje_cumplimiento = fields.Float(string="Puntaje Cumplimiento", digits=(5, 2))
    puntaje_final = fields.Float(string="Puntaje Final", digits=(5, 2))
    resultado = fields.Char(string="Resultado", required=True)
    notas = fields.Text(string="Notas")
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")
