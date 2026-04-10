# -*- coding: utf-8 -*-
# Entidad: PAR_Tipo_Participante
from odoo import models, fields, api


class LukerParticipantType(models.Model):
    _name        = 'luker.participant.type'
    _description = 'PAR_Tipo_Participante'
    _order       = 'orden, nom_tipo_participante'
    _rec_name    = 'nom_tipo_participante'

    cod_tipo_participante = fields.Char(string='Código', required=True, size=50)
    nom_tipo_participante = fields.Char(string='Nombre', required=True, translate=True)
    descripcion           = fields.Text(string='Descripción')
    orden                 = fields.Integer(string='Orden', default=10)
    activo                = fields.Boolean(string='Activo', default=True)

    participante_count = fields.Integer(
        string='Participantes', compute='_compute_participante_count')

    _sql_constraints = [
        ('cod_unique', 'UNIQUE(cod_tipo_participante)',
         'El código del tipo de participante debe ser único.'),
    ]

    def _compute_participante_count(self):
        for rec in self:
            rec.participante_count = self.env['luker.participant'].search_count([
                ('tipo_participante_id', '=', rec.id)])

    def action_ver_participantes(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Participantes — {self.nom_tipo_participante}',
            'res_model': 'luker.participant',
            'view_mode': 'list,form,kanban',
            'domain': [('tipo_participante_id', '=', self.id)],
            'context': {'default_tipo_participante_id': self.id},
        }
