# -*- coding: utf-8 -*-
# Entidades: ATR_Definicion + ATR_Opcion
from odoo import models, fields, api


class LukerAttributeDefinition(models.Model):
    _name        = 'luker.attribute.definition'
    _description = 'ATR_Definicion'
    _order       = 'orden, nom_atributo'

    # ── ATR_Definicion ────────────────────────────────────────
    cod_atributo     = fields.Char(string='Código', required=True, size=80, help='Cod_Atributo')
    nom_atributo     = fields.Char(string='Nombre', required=True, translate=True, help='Nom_Atributo')
    descripcion      = fields.Text(string='Descripción', help='Descripcion')
    alcance_entidad  = fields.Selection([
        ('participante', 'Participante'),
        ('sesion',       'Sesión'),
        ('institucion',  'Institución'),
    ], string='Alcance Entidad', default='participante', help='Alcance_Entidad')
    tipo_dato = fields.Selection([
        ('char',      'Texto corto'),
        ('text',      'Texto largo'),
        ('integer',   'Número entero'),
        ('float',     'Número decimal'),
        ('boolean',   'Sí / No'),
        ('date',      'Fecha'),
        ('selection', 'Lista de opciones (catálogo)'),
    ], string='Tipo de Dato', required=True, default='char', help='Tipo_Dato')
    es_requerido     = fields.Boolean(string='Es Requerido', default=False, help='Es_Requerido')
    es_catalogo      = fields.Boolean(
        string='Es Catálogo', compute='_compute_es_catalogo', store=True,
        help='Es_Catalogo — True cuando tipo_dato = selection')
    tiene_vigencia   = fields.Boolean(
        string='Con Vigencia', default=True,
        help='Si cada valor registrado lleva vigencia_desde / vigencia_hasta')
    responsable_gobierno = fields.Char(
        string='Responsable Gobernanza', help='Responsable_Gobierno')
    orden  = fields.Integer(string='Orden', default=10)
    activo = fields.Boolean(string='Activo', default=True)
    aplica_tipo_ids = fields.Many2many(
        'luker.participant.type', string='Aplica a tipos',
        help='Si está vacío, aplica a todos los tipos de participante.')
    opcion_ids = fields.One2many('luker.attribute.option', 'definicion_id', string='Opciones del catálogo')
    notas_gobierno = fields.Text(string='Notas de Gobernanza')

    _sql_constraints = [
        ('cod_unique', 'UNIQUE(cod_atributo)', 'El código del atributo debe ser único.'),
    ]

    @api.depends('tipo_dato')
    def _compute_es_catalogo(self):
        for rec in self:
            rec.es_catalogo = (rec.tipo_dato == 'selection')

    @api.onchange('tipo_dato')
    def _onchange_tipo_dato(self):
        if self.tipo_dato != 'selection':
            self.opcion_ids = [(5, 0, 0)]


class LukerAttributeOption(models.Model):
    _name        = 'luker.attribute.option'
    _description = 'ATR_Opcion'
    _order       = 'definicion_id, orden, nom_opcion'

    # ── ATR_Opcion ────────────────────────────────────────────
    definicion_id = fields.Many2one(
        'luker.attribute.definition', string='Atributo',
        required=True, ondelete='cascade', help='Id_ATR_Definicion')
    cod_opcion = fields.Char(string='Código de opción', required=True, help='Cod_Opcion')
    nom_opcion = fields.Char(string='Etiqueta', required=True, translate=True, help='Nom_Opcion')
    orden      = fields.Integer(string='Orden', default=10, help='Orden')
    activo     = fields.Boolean(string='Activo', default=True)
