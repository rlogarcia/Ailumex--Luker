# -*- coding: utf-8 -*-
# Entidades: CTX_Unidad_Organizacional (Institución, Sede, Unidad)
from odoo import models, fields, api


class LukerOrganization(models.Model):
    """
    Representa la Institución (nivel 1 de CTX_Unidad_Organizacional).
    Vinculada a res.partner (empresa) para reutilizar datos ya registrados.
    """
    _name        = 'luker.organization'
    _description = 'CTX_Unidad_Organizacional — Institución'
    _order       = 'nom_unidad'
    _inherit     = ['mail.thread', 'mail.activity.mixin']

    # ── Vínculo con Empresas ──────────────────────────────────
    partner_id = fields.Many2one(
        'res.partner', string='Empresa / Institución', required=True,
        ondelete='cascade', domain=[('is_company', '=', True)], tracking=True)

    # ── Campos desde partner ──────────────────────────────────
    nom_unidad = fields.Char(
        related='partner_id.name', string='Nombre', store=True, readonly=True,
        help='Nom_Unidad')
    cod_territorio = fields.Char(
        related='partner_id.city', string='Municipio', store=True, readonly=True,
        help='Cod_Territorio — Ciudad/Municipio')
    telefono = fields.Char(related='partner_id.phone', readonly=True)
    email    = fields.Char(related='partner_id.email',  readonly=True)
    image_128 = fields.Image(related='partner_id.image_128', readonly=True)

    # ── Campos propios CTX ────────────────────────────────────
    cod_unidad = fields.Char(
        string='Código interno', size=30, tracking=True, help='Cod_Unidad')
    tipo_dominio = fields.Selection([
        ('educacion_formal', 'Educación Formal'),
        ('educacion_rural',  'Educación Rural'),
        ('corporativo',      'Corporativo'),
        ('comunitario',      'Comunitario'),
        ('otro',             'Otro'),
    ], string='Tipo / Dominio', required=True, default='educacion_formal', tracking=True)
    estado = fields.Selection([
        ('activo',   'Activo'),
        ('inactivo', 'Inactivo'),
    ], string='Estado', default='activo', tracking=True, help='Estado')
    activo = fields.Boolean(string='Activo', default=True, tracking=True)
    notas  = fields.Text(string='Observaciones')

    # ── Relaciones ────────────────────────────────────────────
    sede_ids           = fields.One2many('luker.organization.branch', 'institucion_id', string='Sedes')
    sede_count         = fields.Integer(compute='_compute_counts', string='Sedes')
    participante_count = fields.Integer(compute='_compute_counts', string='Participantes activos')

    _sql_constraints = [
        ('partner_unique', 'UNIQUE(partner_id)', 'Esta empresa ya está registrada como institución.'),
    ]

    @api.depends('sede_ids')
    def _compute_counts(self):
        for org in self:
            org.sede_count = len(org.sede_ids)
            org.participante_count = self.env['luker.participant.assignment'].search_count([
                ('institucion_id', '=', org.id), ('vigencia_hasta', '=', False)])

    def action_abrir_empresa(self):
        return {'type': 'ir.actions.act_window', 'name': 'Empresa — %s' % self.nom_unidad,
                'res_model': 'res.partner', 'res_id': self.partner_id.id, 'view_mode': 'form'}


class LukerOrganizationBranch(models.Model):
    """Sede — nivel 2 de CTX_Unidad_Organizacional."""
    _name        = 'luker.organization.branch'
    _description = 'CTX_Unidad_Organizacional — Sede'
    _order       = 'institucion_id, nom_sede'

    institucion_id = fields.Many2one(
        'luker.organization', string='Institución', required=True, ondelete='cascade',
        help='Id_CTX_Unidad_Organizacional_Padre')
    nom_sede = fields.Char(string='Nombre de la Sede', required=True, help='Nom_Unidad')
    cod_sede = fields.Char(string='Código', size=20, help='Cod_Unidad')
    activo   = fields.Boolean(string='Activo', default=True)
    unidad_ids = fields.One2many('luker.organization.unit', 'sede_id', string='Unidades')


class LukerOrganizationUnit(models.Model):
    """
    Unidad organizacional — nivel 3 de CTX_Unidad_Organizacional.
    Representa Grado + Grupo + Jornada para educación,
    o Área + Cargo para corporativo.
    """
    _name        = 'luker.organization.unit'
    _description = 'CTX_Unidad_Organizacional — Grado/Grupo/Área'
    _order       = 'sede_id, nom_grado, nom_grupo'
    _rec_name    = 'nom_grado'

    sede_id = fields.Many2one(
        'luker.organization.branch', string='Sede', required=True, ondelete='cascade',
        help='Id_CTX_Unidad_Organizacional_Padre')
    institucion_id = fields.Many2one(
        related='sede_id.institucion_id', string='Institución', store=True,
        help='Institución raíz')

    # Educación formal
    nom_grado  = fields.Char(string='Grado',  help='Ej: 9°, 2°, Preescolar')
    nom_grupo  = fields.Char(string='Grupo',  help='Ej: A, B, 801')
    jornada    = fields.Selection([
        ('manana', 'Mañana'), ('tarde', 'Tarde'),
        ('noche',  'Noche'),  ('unica', 'Única'),
    ], string='Jornada')

    # Corporativo
    area     = fields.Char(string='Área / Departamento')
    position = fields.Char(string='Cargo / Rol')

    activo            = fields.Boolean(string='Activo', default=True)
    participante_count = fields.Integer(compute='_compute_participante_count')

    def _compute_participante_count(self):
        for u in self:
            u.participante_count = self.env['luker.participant.assignment'].search_count([
                ('unidad_id', '=', u.id), ('vigencia_hasta', '=', False)])

    def name_get(self):
        jornadas = dict(self._fields['jornada'].selection)
        result   = []
        for u in self:
            parts = []
            if u.nom_grado:  parts.append(str(u.nom_grado))
            if u.nom_grupo:  parts.append(f'Gr.{u.nom_grupo}')
            if u.jornada:    parts.append(jornadas.get(u.jornada, ''))
            if u.area:       parts.append(str(u.area))
            name = ' · '.join(filter(None, parts)) or f'Unidad {u.id}'
            result.append((u.id, name))
        return result
