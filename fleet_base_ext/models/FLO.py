from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class FloVehiculo(models.Model):
    _name = 'flo.vehiculo'
    _description = 'FLO Vehículo'
    _rec_name = 'placa'

    id_FLO_vehiculo = fields.Integer(string="ID FLO Vehículo", required=True)
    id_SEG_empresa = fields.Many2one(
        comodel_name='seg.empresa',
        string="Empresa",
        required=True,
    )
    id_FLO_sede_operativa = fields.Many2one(
        comodel_name='flo.sede.operativa',
        string="Sede Operativa",
    )
    id_FLO_centro_costo = fields.Many2one(
        comodel_name='flo.centro.costo',
        string="Centro de Costo",
    )
    foto_vehiculo = fields.Image(string="Foto Vehículo")
    placa = fields.Char(string="Placa", required=True)
    num_interno = fields.Char(string="Número Interno", required=True)
    tipo_vinculacion = fields.Char(string="Tipo Vinculación", required=True)
    tipo_vehiculo = fields.Selection([
        # Transporte de pasajeros
        ('bus_intermunicipal',  'Bus Intermunicipal'),
        ('bus_urbano',          'Bus Urbano'),
        ('buseta',              'Buseta'),
        ('microbus',            'Microbús'),
        ('minivan_pasajeros',   'Minivan de Pasajeros'),
        ('taxi',                'Taxi'),
        ('escolar',             'Transporte Escolar'),
        ('especial',            'Servicio Especial'),
        # Transporte de carga
        ('camion_rigido',       'Camión Rígido'),
        ('tractocamion',        'Tractocamión'),
        ('furgon',              'Furgón'),
        ('volqueta',            'Volqueta'),
        ('cama_baja',           'Cama Baja'),
        ('cisterna',            'Cisterna'),
        ('refrigerado',         'Refrigerado'),
        # Vehículos livianos / administrativos
        ('automovil',           'Automóvil'),
        ('camioneta',           'Camioneta'),
        ('van_carga',           'Van de Carga'),
        ('pick_up',             'Pick-Up'),
        # Maquinaria
        ('maquinaria',          'Maquinaria y Equipo'),
        # Otro
        ('otro',                'Otro'),
    ], string="Tipo Vehículo", required=True)
    marca = fields.Selection([
        # Automóviles / Camionetas
        ('chevrolet',       'Chevrolet'),
        ('ford',            'Ford'),
        ('toyota',          'Toyota'),
        ('nissan',          'Nissan'),
        ('hyundai',         'Hyundai'),
        ('kia',             'Kia'),
        ('renault',         'Renault'),
        ('volkswagen',      'Volkswagen'),
        ('mazda',           'Mazda'),
        ('honda',           'Honda'),
        ('suzuki',          'Suzuki'),
        ('mitsubishi',      'Mitsubishi'),
        ('jeep',            'Jeep'),
        ('dodge',           'Dodge'),
        ('ram',             'RAM'),
        # Buses / Busetas
        ('mercedes_benz',   'Mercedes-Benz'),
        ('volvo_bus',       'Volvo Bus'),
        ('scania',          'Scania'),
        ('marcopolo',       'Marcopolo'),
        ('comil',           'Comil'),
        ('busscar',         'Busscar'),
        ('irizar',          'Irizar'),
        ('superpolo',       'Superpolo'),
        ('modasa',          'Modasa'),
        ('ayco',            'Ayco'),
        ('king_long',       'King Long'),
        ('yutong',          'Yutong'),
        ('higer',           'Higer'),
        # Camiones / Tractocamiones
        ('international',   'International'),
        ('kenworth',        'Kenworth'),
        ('freightliner',    'Freightliner'),
        ('mack',            'Mack'),
        ('volvo_truck',     'Volvo Truck'),
        ('man',             'MAN'),
        ('iveco',           'Iveco'),
        # Otro
        ('otro',            'Otro'),
    ], string="Marca")
    linea = fields.Char(string="Línea")
    modelo_anio = fields.Integer(string="Modelo Año")
    vin = fields.Char(string="VIN")
    num_motor = fields.Char(string="Número Motor")
    num_chasis = fields.Char(string="Número Chasis")
    tipo_combustible = fields.Selection([
        ('gasolina',        'Gasolina'),
        ('diesel',          'Diésel'),
        ('gnv',             'Gas Natural Vehicular (GNV)'),
        ('glp',             'Gas Licuado de Petróleo (GLP)'),
        ('hibrido',         'Híbrido (Gasolina + Eléctrico)'),
        ('hibrido_diesel',  'Híbrido (Diésel + Eléctrico)'),
        ('electrico',       'Eléctrico'),
        ('hidrogeno',       'Hidrógeno'),
        ('otro',            'Otro'),
    ], string="Tipo Combustible")
    odometro_actual = fields.Float(string="Odómetro Actual", digits=(14, 2))
    estado_operativo = fields.Char(string="Estado Operativo", required=True)
    requiere_checklist = fields.Boolean(string="Requiere Checklist")
    aplica_regulacion = fields.Boolean(string="Aplica Regulación")
    fecha_ultimo_checklist = fields.Date(string="Fecha Último Checklist")
    fecha_ultimo_preventivo = fields.Date(string="Fecha Último Preventivo")
    fecha_proximo_preventivo = fields.Date(string="Fecha Próximo Preventivo")
    fotos_vehiculo = fields.One2many(
        comodel_name='flo.vehiculo.foto',
        inverse_name='id_FLO_vehiculo',
        string="Galería de Fotos",
    )
    documentos = fields.One2many(
        comodel_name='flo.documento',
        inverse_name='id_FLO_vehiculo',
        string="Documentos",
    )
    activo = fields.Boolean(string="Activo" , default=True)
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")


class FloDocumento(models.Model):
    _name = 'flo.documento'
    _description = 'Documentos del Vehículo'
    _rec_name = 'descripcion'

    id_FLO_vehiculo = fields.Many2one(
        comodel_name='flo.vehiculo',
        string="Vehículo",
        required=True,
        ondelete='cascade',
    )
    tipo_documento = fields.Selection([
        ('soat', 'SOAT'),
        ('tecnomecanica', 'Tecnomecánica'),
        ('licencia_transito', 'Licencia de Tránsito'),
    ], string="Tipo Documento", required=True)
    documento = fields.Binary(string="Documento", required=True)
    descripcion = fields.Char(string="Descripción")
    fecha_expiracion = fields.Date(string="Fecha Expiración")
    estado = fields.Selection([
        ('vigente', 'Vigente'),
        ('proximo_vencer', 'Próximo a Vencer'),
        ('vencido', 'Vencido'),
    ], string="Estado", compute='_compute_estado', store=True)
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")

    @api.depends('fecha_expiracion')
    def _compute_estado(self):
        hoy = fields.Date.today()
        un_mes = hoy + relativedelta(months=1)
        for rec in self:
            if not rec.fecha_expiracion:
                rec.estado = 'vigente'
            elif rec.fecha_expiracion < hoy:
                rec.estado = 'vencido'
            elif rec.fecha_expiracion <= un_mes:
                rec.estado = 'proximo_vencer'
            else:
                rec.estado = 'vigente'


class FloVehiculoFoto(models.Model):
    _name = 'flo.vehiculo.foto'
    _description = 'Galería de Fotos del Vehículo'
    _rec_name = 'descripcion'
    _order = 'sequence, id'

    id_FLO_vehiculo = fields.Many2one(
        comodel_name='flo.vehiculo',
        string="Vehículo",
        required=True,
        ondelete='cascade',
    )
    foto = fields.Image(string="Foto", required=True)
    descripcion = fields.Char(string="Descripción")
    sequence = fields.Integer(string="Orden", default=10)


class FloSedeOperativa(models.Model):
    _name = 'flo.sede.operativa'
    _description = 'FLO Sede Operativa'
    _rec_name = 'nom_sede_operativa'

    id_FLO_sede_operativa = fields.Integer(string="ID FLO Sede Operativa", required=True)
    id_SEG_empresa = fields.Integer(string="ID SEG Empresa", required=True)
    nom_sede_operativa = fields.Char(string="Nombre Sede Operativa", required=True)
    cod_sede_operativa = fields.Char(string="Código Sede Operativa")
    ciudad = fields.Char(string="Ciudad")
    departamento = fields.Char(string="Departamento")
    activo = fields.Boolean(string="Activo")
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")


class FloCentroCosto(models.Model):
    _name = 'flo.centro.costo'
    _description = 'FLO Centro Costo'
    _rec_name = 'nom_centro_costo'

    id_FLO_centro_costo = fields.Integer(string="ID FLO Centro Costo", required=True)
    id_SEG_empresa = fields.Integer(string="ID SEG Empresa", required=True)
    nom_centro_costo = fields.Char(string="Nombre Centro Costo", required=True)
    cod_centro_costo = fields.Char(string="Código Centro Costo")
    activo = fields.Boolean(string="Activo")
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")


class FloVehiculoConductor(models.Model):
    _name = 'flo.vehiculo.conductor'
    _description = 'Asignaciones'

    id_FLO_vehiculo_conductor = fields.Integer(string="ID FLO Vehículo Conductor", required=True)
    id_SEG_empresa = fields.Many2one(
        comodel_name='seg.empresa',
        string="Empresa",
        required=True,
    )
    id_FLO_vehiculo = fields.Many2one(
        comodel_name='flo.vehiculo',
        string="Vehículo",
        required=True,
        ondelete='restrict',
    )
    id_RRHH_empleado = fields.Many2one(
        comodel_name='rrhh.empleado',
        string="Conductor",
        required=True,
        ondelete='restrict',
    )
    tipo_conductor = fields.Selection([
        ('titular', 'Principal'),
        ('suplente', 'Suplente'),
    ], string="Tipo", required=True)
    es_principal = fields.Boolean(string="Es Principal")
    fecha_inicio = fields.Date(string="Desde", required=True)
    fecha_fin = fields.Date(string="Hasta")
    estado = fields.Selection([
        ('activo', 'Activa'),
        ('restringida', 'Restringida'),
        ('suspendido', 'Suspendida'),
        ('finalizado', 'Finalizada'),
    ], string="Estado", required=True, default='activo')
    observacion = fields.Text(string="Observación")
    activo = fields.Boolean(string="Activo")
    fecha_creacion = fields.Datetime(string="Fecha Creación")
    fecha_actualizacion = fields.Datetime(string="Fecha Actualización")

    sede_nombre = fields.Char(
        string="Sede",
        related='id_FLO_vehiculo.id_FLO_sede_operativa.nom_sede_operativa',
        store=False,
        readonly=True,
    )
