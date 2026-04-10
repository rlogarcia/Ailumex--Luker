# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartnerSisben(models.Model):

    _name = 'res.partner.sisben'
    _description = 'Clasificación SISBEN'
    _order = 'codigo'

    codigo = fields.Char('Código', required=True)
    grupo = fields.Char('Grupo', required=True)
    descripcion = fields.Char('Descripción', required=True)
    nivel_vulnerabilidad = fields.Selection([
        ('alto', 'Alto'),
        ('medio', 'Medio'),
        ('bajo', 'Bajo'),
    ], string='Nivel de Vulnerabilidad', required=True)
    aplica_subsidio = fields.Selection([
        ('si', 'Sí'),
        ('no', 'No'),
        ('depende', 'Depende'),
    ], string='Aplica Subsidio', required=True)
    name = fields.Char(
        string='Nombre',
        compute='_compute_name',
        store=True,
    )

    @api.depends('codigo', 'descripcion')
    def _compute_name(self):
        for rec in self:
            rec.name = (
                f"{rec.codigo} - {rec.descripcion}"
                if rec.codigo and rec.descripcion
                else rec.codigo or ''
            )
