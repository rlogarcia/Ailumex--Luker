# -*- coding: utf-8 -*-
# Entidad: PAR_Valor_Dinamico
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LukerParticipantAttributeValue(models.Model):
    _name        = 'luker.participant.attribute.value'
    _description = 'PAR_Valor_Dinamico'
    _order       = 'participante_id, definicion_id, vigencia_desde desc'

    # ── PAR_Valor_Dinamico ────────────────────────────────────
    participante_id = fields.Many2one(
        'luker.participant', string='Participante',
        required=True, ondelete='cascade', help='Id_PAR_Participante')
    definicion_id = fields.Many2one(
        'luker.attribute.definition', string='Atributo',
        required=True, ondelete='restrict', help='Id_ATR_Definicion')
    tipo_dato = fields.Selection(
        related='definicion_id.tipo_dato', string='Tipo', readonly=True)

    # Valores tipados — uno aplica según tipo_dato
    valor_texto      = fields.Text(string='Valor texto', help='Valor_Texto')
    valor_numero     = fields.Float(string='Valor número', digits=(18, 4), help='Valor_Numero')
    valor_fecha      = fields.Date(string='Valor fecha', help='Valor_Fecha')
    valor_booleano   = fields.Boolean(string='Valor booleano', help='Valor_Booleano')
    opcion_id        = fields.Many2one(
        'luker.attribute.option', string='Opción del catálogo',
        domain="[('definicion_id', '=', definicion_id)]",
        ondelete='restrict', help='Id_ATR_Opcion')
    valor_json       = fields.Text(string='Valor JSON', help='Valor_JSON')
    valor_display    = fields.Char(
        string='Valor', compute='_compute_valor_display', store=True)

    vigencia_desde = fields.Date(
        string='Vigencia Desde', required=True, default=fields.Date.today,
        help='Vigencia_Desde')
    vigencia_hasta = fields.Date(
        string='Vigencia Hasta', help='Vigencia_Hasta')
    es_vigente = fields.Boolean(
        string='Vigente', compute='_compute_es_vigente', store=True)
    fuente = fields.Selection([
        ('manual',       'Manual'),
        ('carga_masiva', 'Carga masiva'),
        ('api',          'API'),
        ('calculo',      'Cálculo automático'),
    ], string='Fuente', default='manual', help='Fuente')
    activo = fields.Boolean(string='Activo', default=True)

    @api.depends(
        'tipo_dato', 'valor_texto', 'valor_numero',
        'valor_fecha', 'valor_booleano', 'opcion_id',
    )
    def _compute_valor_display(self):
        for rec in self:
            dt = rec.tipo_dato
            if dt in ('char', 'text'):
                rec.valor_display = (rec.valor_texto or '')[:80]
            elif dt in ('integer', 'float'):
                rec.valor_display = str(rec.valor_numero)
            elif dt == 'boolean':
                rec.valor_display = _('Sí') if rec.valor_booleano else _('No')
            elif dt == 'date':
                rec.valor_display = str(rec.valor_fecha) if rec.valor_fecha else ''
            elif dt == 'selection':
                rec.valor_display = rec.opcion_id.nom_opcion or ''
            else:
                rec.valor_display = ''

    @api.depends('vigencia_hasta')
    def _compute_es_vigente(self):
        today = fields.Date.today()
        for rec in self:
            rec.es_vigente = not rec.vigencia_hasta or rec.vigencia_hasta >= today

    @api.constrains('vigencia_desde', 'vigencia_hasta')
    def _check_fechas(self):
        for rec in self:
            if rec.vigencia_hasta and rec.vigencia_hasta < rec.vigencia_desde:
                raise ValidationError(_('Vigencia_Hasta no puede ser anterior a Vigencia_Desde.'))
