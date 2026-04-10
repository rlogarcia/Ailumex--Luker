# -*- coding: utf-8 -*-
# Entidades: OPE_Carga_Poblacion + OPE_Carga_Poblacion_Detalle
from odoo import models, fields


class LukerParticipantImportLog(models.Model):
    _name        = 'luker.participant.import.log'
    _description = 'OPE_Carga_Poblacion'
    _order       = 'fecha_cargue desc'
    _inherit     = ['mail.thread']

    # ── OPE_Carga_Poblacion ───────────────────────────────────
    cod_carga = fields.Char(
        string='Código de carga', readonly=True, help='Cod_Carga')
    nom_carga = fields.Char(
        string='Nombre de la carga', required=True, tracking=True,
        help='Nombre descriptivo de esta carga masiva')
    nom_archivo_origen = fields.Char(
        string='Archivo de origen', readonly=True, help='Nom_Archivo_Origen')
    archivo_data = fields.Binary(
        string='Archivo cargado', readonly=True, attachment=True,
        help='Archivo Excel original — conservado para auditoría')
    fuente_formato = fields.Selection([
        ('simat',  'SIMAT — Anexo 6A'),
        ('manual', 'Plantilla manual Luker'),
        ('otro',   'Otro formato'),
        ('excel',  'Otro formato Excel (legacy)'),
    ], string='Formato de origen', default='simat', tracking=True,
       help='Fuente / Formato del archivo de origen')

    # ── Estado y contadores ───────────────────────────────────
    estado_carga = fields.Selection([
        ('borrador',  'Borrador'),
        ('completo',  'Completo'),
        ('parcial',   'Parcial (con errores)'),
        ('fallido',   'Fallido'),
    ], string='Estado', default='borrador', readonly=True, tracking=True,
       help='Estado_Carga')
    total_filas    = fields.Integer(string='Total filas', readonly=True, help='Total_Filas')
    filas_validas  = fields.Integer(string='Filas válidas (creadas + actualizadas)',
                                    readonly=True, help='Filas_Validas')
    filas_invalidas = fields.Integer(string='Filas inválidas (errores)',
                                     readonly=True, help='Filas_Invalidas')
    filas_omitidas  = fields.Integer(string='Filas omitidas', readonly=True)
    alertas_vacios  = fields.Integer(string='Alertas de datos vacíos', readonly=True)

    # ── Trazabilidad ──────────────────────────────────────────
    usuario_cargue_id = fields.Many2one(
        'res.users', string='Cargado por',
        default=lambda self: self.env.user, readonly=True, tracking=True,
        help='Id_SEG_Usuario_Cargue')
    fecha_cargue = fields.Datetime(
        string='Fecha de carga', default=fields.Datetime.now,
        readonly=True, tracking=True, help='Fecha_Cargue')

    # ── Configuración usada ───────────────────────────────────
    campo_conciliacion = fields.Char(
        string='Campo de conciliación usado', readonly=True,
        help='Campo que se usó para detectar duplicados (num_identidad)')
    accion_existente = fields.Selection([
        ('actualizar', 'Actualizar existente'),
        ('omitir',     'Omitir existente'),
        ('error',      'Marcar como error'),
    ], string='Acción si ya existe', readonly=True)

    # ── Mapeo guardado para auditoría ─────────────────────────
    mapeo_columnas_json  = fields.Text(
        string='Mapeo de columnas (JSON)', readonly=True,
        help='JSON {columna_excel: campo_destino} usado en esta carga')
    columnas_omitidas_json = fields.Text(
        string='Columnas omitidas (JSON)', readonly=True)

    # ── Detalle ───────────────────────────────────────────────
    detalle_ids = fields.One2many(
        'luker.participant.import.log.line', 'carga_id', string='Detalle por fila')
    notas = fields.Text(string='Notas del importador')

    def action_ver_creados(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Participantes creados en esta carga',
            'res_model': 'luker.participant',
            'view_mode': 'list,form',
            'domain': [('carga_origen_id', '=', self.id)],
        }

    def action_open_import_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Carga Masiva de Participantes',
            'res_model': 'luker.participant.import.wizard',
            'view_mode': 'form', 'target': 'new',
        }


class LukerParticipantImportLogLine(models.Model):
    _name        = 'luker.participant.import.log.line'
    _description = 'OPE_Carga_Poblacion_Detalle'
    _order       = 'carga_id, num_fila'

    # ── OPE_Carga_Poblacion_Detalle ───────────────────────────
    carga_id = fields.Many2one(
        'luker.participant.import.log', string='Carga',
        required=True, ondelete='cascade', help='Id_OPE_Carga_Poblacion')
    num_fila = fields.Integer(
        string='Fila #', readonly=True, help='Num_Fila')
    participante_id = fields.Many2one(
        'luker.participant', string='Participante',
        readonly=True, help='Id_PAR_Participante')
    cod_persona_externa = fields.Char(
        string='ID externo', readonly=True,
        help='Cod_Persona_Externa — número de documento u otro identificador externo')
    estado_registro = fields.Selection([
        ('creado',     'Creado'),
        ('actualizado','Actualizado'),
        ('omitido',    'Omitido (ya existe)'),
        ('advertencia','Advertencia (datos vacíos)'),
        ('error',      'Error'),
    ], string='Estado', readonly=True, help='Estado_Registro')
    mensaje_validacion = fields.Char(
        string='Mensaje / Detalle', readonly=True, help='Mensaje_Validacion')
    campos_vacios_json = fields.Char(
        string='Campos vacíos detectados', readonly=True,
        help='Lista de campos importantes que estaban vacíos en esta fila')
