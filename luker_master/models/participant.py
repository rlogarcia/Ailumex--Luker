# -*- coding: utf-8 -*-
# Entidad: PAR_Participante
import uuid
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LukerParticipant(models.Model):
    _name        = 'luker.participant'
    _description = 'PAR_Participante'
    _order       = 'nom_completo'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _rec_name    = 'nom_completo'

    # ── Identificación interna ─────────────────────────────────
    cod_participante = fields.Char(
        string='Código Participante', readonly=True, copy=False, default='/',
        tracking=True, help='Cod_Participante')
    uuid_local = fields.Char(
        string='UUID Local', readonly=True, copy=False,
        help='Identificador único para sincronización offline-first')

    # ── Vínculo con Contactos (res.partner) ───────────────────
    partner_id = fields.Many2one(
        'res.partner', string='Contacto vinculado', required=True,
        ondelete='cascade', tracking=True,
        domain=[('is_company', '=', False)],
        help='Contacto de Odoo asociado a este participante')

    # ── Campos traídos del contacto ───────────────────────────
    nom_completo = fields.Char(
        related='partner_id.name', string='Nombre Completo',
        store=True, readonly=True, help='Nom_Completo')
    email = fields.Char(
        related='partner_id.email', string='Correo', store=True, readonly=True)
    telefono = fields.Char(
        related='partner_id.phone', string='Teléfono', store=True, readonly=True)
    image_128 = fields.Image(
        related='partner_id.image_128', readonly=True)

    # ── Datos propios del participante (PAR_Participante) ──────
    tipo_participante_id = fields.Many2one(
        'luker.participant.type', string='Tipo de Participante',
        required=True, tracking=True, ondelete='restrict',
        help='Id_PAR_Tipo_Participante')
    estado = fields.Selection([
        ('borrador',  'Borrador'),
        ('activo',    'Activo'),
        ('inactivo',  'Inactivo'),
        ('archivado', 'Archivado'),
    ], string='Estado', default='activo', required=True, tracking=True,
       help='Estado')
    fecha_nacimiento = fields.Date(
        string='Fecha de Nacimiento', tracking=True, help='Fecha_Nacimiento')
    edad = fields.Integer(
        string='Edad', compute='_compute_edad', store=False)
    sexo = fields.Selection([
        ('masculino',  'Masculino'),
        ('femenino',   'Femenino'),
        ('no_binario', 'No binario'),
        ('no_informa', 'Prefiero no informar'),
    ], string='Sexo', tracking=True, help='Sexo')
    fuente_creacion = fields.Selection([
        ('manual',   'Manual'),
        ('carga_masiva', 'Carga masiva'),
        ('api',      'API'),
        ('offline',  'Dispositivo offline'),
    ], string='Fuente de Creación', default='manual',
       help='Fuente_Creacion')
    activo = fields.Boolean(
        string='Activo', default=True, help='Activo')

    # ── Sincronización offline-first ──────────────────────────
    estado_sync = fields.Selection([
        ('sincronizado', 'Sincronizado'),
        ('borrador_local', 'Borrador local'),
        ('en_cola', 'En cola'),
        ('error_sync', 'Error de sync'),
        ('conflicto', 'Conflicto'),
    ], string='Estado Sync', default='sincronizado', tracking=True)
    dispositivo_id = fields.Char(string='Dispositivo origen')
    fecha_ultima_sync = fields.Datetime(string='Última sincronización')

    # ── Contexto actual (desnormalizado para consulta rápida) ──
    institucion_actual_id = fields.Many2one(
        'luker.organization', string='Organización actual',
        compute='_compute_contexto_actual', store=True)
    unidad_actual_id = fields.Many2one(
        'luker.organization.unit', string='Unidad actual',
        compute='_compute_contexto_actual', store=True)

    # ── Relaciones ────────────────────────────────────────────
    identidad_ids = fields.One2many(
        'luker.participant.identity', 'participante_id', string='Identidades')
    identidad_principal_display = fields.Char(
        string='Identificación principal',
        compute='_compute_identidad_principal', store=True)
    asignacion_contexto_ids = fields.One2many(
        'luker.participant.assignment', 'participante_id',
        string='Asignaciones de Contexto')
    valor_dinamico_ids = fields.One2many(
        'luker.participant.attribute.value', 'participante_id',
        string='Caracterización Dinámica')
    sesion_ids = fields.One2many(
        'luker.application.result', 'participante_id',
        string='Sesiones / Aplicaciones')

    # ── Trazabilidad de carga ─────────────────────────────────
    carga_origen_id = fields.Many2one(
        'luker.participant.import.log', string='Carga masiva origen',
        readonly=True, help='Id_OPE_Carga_Poblacion — origen de la carga')

    # ── Contadores ────────────────────────────────────────────
    sesion_count = fields.Integer(
        string='Aplicaciones', compute='_compute_sesion_count')
    identidad_count = fields.Integer(
        string='Identidades', compute='_compute_identidad_count')

    notas = fields.Html(string='Notas')

    _sql_constraints = [
        ('partner_unique', 'UNIQUE(partner_id)',
         'Este contacto ya tiene un participante registrado.'),
    ]

    # ─────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('cod_participante', '/') == '/':
                vals['cod_participante'] = (
                    self.env['ir.sequence'].next_by_code('luker.participant') or '/')
            if not vals.get('uuid_local'):
                vals['uuid_local'] = str(uuid.uuid4())[:12]
        return super().create(vals_list)

    @api.depends('fecha_nacimiento')
    def _compute_edad(self):
        today = fields.Date.today()
        for p in self:
            if p.fecha_nacimiento:
                p.edad = (today - p.fecha_nacimiento).days // 365
            else:
                p.edad = 0

    @api.depends('identidad_ids', 'identidad_ids.es_principal', 'identidad_ids.estado')
    def _compute_identidad_principal(self):
        for p in self:
            principal = p.identidad_ids.filtered(
                lambda i: i.es_principal and i.estado == 'activa')[:1]
            if principal:
                nombre_tipo = (principal.tipo_identidad_id.name
                               if principal.tipo_identidad_id else '')
                p.identidad_principal_display = f'{nombre_tipo}: {principal.num_identidad}'
            else:
                p.identidad_principal_display = False

    @api.depends('asignacion_contexto_ids', 'asignacion_contexto_ids.vigencia_hasta')
    def _compute_contexto_actual(self):
        for p in self:
            actual = p.asignacion_contexto_ids.filtered(
                lambda a: not a.vigencia_hasta
            ).sorted('vigencia_desde', reverse=True)[:1]
            p.institucion_actual_id = actual.institucion_id if actual else False
            p.unidad_actual_id      = actual.unidad_id      if actual else False

    def _compute_sesion_count(self):
        for p in self:
            p.sesion_count = len(p.sesion_ids)

    def _compute_identidad_count(self):
        for p in self:
            p.identidad_count = len(p.identidad_ids)

    # ── Actions ───────────────────────────────────────────────
    def action_set_activo(self):
        self.write({'estado': 'activo'})

    def action_set_inactivo(self):
        self.write({'estado': 'inactivo'})

    def action_ver_sesiones(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Aplicaciones — %s') % self.nom_completo,
            'res_model': 'luker.application.result',
            'view_mode': 'list,form',
            'domain': [('participante_id', '=', self.id)],
        }

    def action_abrir_contacto(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Contacto — %s') % self.nom_completo,
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'view_mode': 'form',
        }

    def action_open_import_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Carga Masiva de Participantes',
            'res_model': 'luker.participant.import.wizard',
            'view_mode': 'form', 'target': 'new',
        }
