# -*- coding: utf-8 -*-
# Catálogos: Programa y Línea de Intervención
# Se usan para clasificar los instrumentos SISPAR
from odoo import models, fields, api


class LukerPrograma(models.Model):
    _name        = 'luker.programa'
    _description = 'Programa — catálogo SISPAR'
    _order       = 'nom_programa'
    _rec_name    = 'nom_programa'

    cod_programa = fields.Char(
        string='Código', size=40, required=True, index=True,
    )
    nom_programa = fields.Char(
        string='Nombre del programa', size=220, required=True,
    )
    descripcion  = fields.Text(string='Descripción')
    activo       = fields.Boolean(string='Activo', default=True)

    linea_ids = fields.One2many(
        'luker.linea.intervencion', 'programa_id',
        string='Líneas de intervención',
    )
    num_lineas = fields.Integer(
        compute='_compute_num_lineas', string='Líneas', store=False,
    )

    @api.depends('linea_ids')
    def _compute_num_lineas(self):
        for p in self:
            p.num_lineas = len(p.linea_ids)

    _sql_constraints = [
        ('cod_programa_unique', 'UNIQUE(cod_programa)',
         'El código de programa ya existe.'),
    ]


class LukerLineaIntervencion(models.Model):
    _name        = 'luker.linea.intervencion'
    _description = 'Línea de Intervención — catálogo SISPAR'
    _order       = 'programa_id, nom_linea'
    _rec_name    = 'nom_linea'

    programa_id = fields.Many2one(
        'luker.programa',
        string='Programa', required=True, ondelete='cascade', index=True,
    )
    cod_linea = fields.Char(
        string='Código', size=40, required=True, index=True,
    )
    nom_linea = fields.Char(
        string='Nombre de la línea', size=220, required=True,
    )
    descripcion = fields.Text(string='Descripción')
    activo      = fields.Boolean(string='Activa', default=True)

    display_name_completo = fields.Char(
        compute='_compute_display', store=False,
    )

    @api.depends('programa_id', 'nom_linea')
    def _compute_display(self):
        for l in self:
            prog = l.programa_id.cod_programa or ''
            l.display_name_completo = f'[{prog}] {l.nom_linea}' if prog else l.nom_linea

    _sql_constraints = [
        ('cod_linea_unique', 'UNIQUE(programa_id, cod_linea)',
         'El código de línea ya existe en este programa.'),
    ]
