# -*- coding: utf-8 -*-
# Entidad: PAR_Identidad
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LukerParticipantIdentity(models.Model):
    _name        = 'luker.participant.identity'
    _description = 'PAR_Identidad'
    _order       = 'es_principal desc, vigencia_desde desc'

    # ── PAR_Identidad ─────────────────────────────────────────
    participante_id = fields.Many2one(
        'luker.participant', string='Participante',
        required=True, ondelete='cascade', help='Id_PAR_Participante')
    tipo_identidad_id = fields.Many2one(
        'l10n_latam.identification.type', string='Tipo de Identidad',
        required=True, ondelete='restrict', help='Id_PAR_Tipo_Identidad')
    num_identidad = fields.Char(
        string='Número / Código', required=True, help='Num_Identidad')
    es_principal = fields.Boolean(
        string='Es Principal', default=False, help='Es_Principal')
    vigencia_desde = fields.Date(
        string='Vigencia Desde', required=True, default=fields.Date.today,
        help='Vigencia_Desde')
    vigencia_hasta = fields.Date(
        string='Vigencia Hasta', help='Vigencia_Hasta')
    estado = fields.Selection([
        ('activa',    'Activa'),
        ('vencida',   'Vencida'),
        ('cancelada', 'Cancelada'),
    ], string='Estado', default='activa', required=True, help='Estado')
    activo = fields.Boolean(string='Activo', default=True)
    notas  = fields.Char(string='Observaciones')

    @api.constrains('es_principal', 'estado', 'participante_id')
    def _check_una_principal(self):
        for rec in self:
            if rec.es_principal and rec.estado == 'activa':
                otros = self.search([
                    ('participante_id', '=', rec.participante_id.id),
                    ('es_principal', '=', True),
                    ('estado', '=', 'activa'),
                    ('id', '!=', rec.id),
                ])
                if otros:
                    raise ValidationError(_(
                        'Ya existe una identidad principal activa para "%s".',
                        rec.participante_id.nom_completo,
                    ))

    @api.constrains('vigencia_desde', 'vigencia_hasta')
    def _check_fechas(self):
        for rec in self:
            if rec.vigencia_hasta and rec.vigencia_hasta < rec.vigencia_desde:
                raise ValidationError(_('Vigencia_Hasta no puede ser anterior a Vigencia_Desde.'))
