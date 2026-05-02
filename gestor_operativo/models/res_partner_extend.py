# -*- coding: utf-8 -*-
# Extensión de res.partner para integración con Gestor Operativo Luker
# SOLO agrega campos y métodos — no modifica nada existente en res.partner
from odoo import models, fields, api


class ResPartnerLukerExtend(models.Model):
    _inherit = 'res.partner'

    # ── Vínculo inverso: participantes Luker asociados a este contacto ──────
    luker_participant_ids = fields.One2many(
        'luker.participant',
        'partner_id',
        string='Participantes Luker',
        readonly=True,
    )

    luker_participant_count = fields.Integer(
        string='Participantes',
        compute='_compute_luker_counts',
        store=False,
    )

    luker_sesion_count = fields.Integer(
        string='Sesiones',
        compute='_compute_luker_counts',
        store=False,
    )

    # ── Cómputo ─────────────────────────────────────────────────────────────
    @api.depends('luker_participant_ids', 'luker_participant_ids.sesion_count')
    def _compute_luker_counts(self):
        for partner in self:
            participantes = partner.luker_participant_ids
            partner.luker_participant_count = len(participantes)
            partner.luker_sesion_count = sum(
                p.sesion_count for p in participantes
            )

    # ── Acciones de los smart buttons ───────────────────────────────────────
    def action_ver_participantes_luker(self):
        """Abre la lista de participantes Luker vinculados a este contacto."""
        self.ensure_one()
        participantes = self.luker_participant_ids
        if len(participantes) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'luker.participant',
                'view_mode': 'form',
                'res_id': participantes.id,
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Participantes Luker',
            'res_model': 'luker.participant',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
            'target': 'current',
        }

    def action_ver_sesiones_luker(self):
        """Abre todas las sesiones de aplicación de los participantes de este contacto."""
        self.ensure_one()
        participante_ids = self.luker_participant_ids.ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sesiones Luker',
            'res_model': 'luker.application.result',
            'view_mode': 'list,form',
            'domain': [('participante_id', 'in', participante_ids)],
            'target': 'current',
        }
