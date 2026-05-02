# -*- coding: utf-8 -*-
# Integración ox_res_partner_ext_co → luker.participant
# Expone los campos colombianos del contacto como campos relacionados
# del participante. Solo lectura — la fuente es siempre res.partner.
# Prefijo co_ para evitar colisiones con campos existentes.
from odoo import models, fields


class LukerParticipantCo(models.Model):
    _inherit = 'luker.participant'

    # ── Información personal Colombia ────────────────────────────────────────
    co_sexo_biologico = fields.Selection(
        related='partner_id.sexo_biologico',
        string='Sexo Biológico',
        readonly=True, store=False,
    )
    co_sexo_identificacion = fields.Selection(
        related='partner_id.sexo_identificacion',
        string='Sexo de Identificación',
        readonly=True, store=False,
    )
    co_estado_civil = fields.Selection(
        related='partner_id.estado_civil',
        string='Estado Civil',
        readonly=True, store=False,
    )
    co_zona = fields.Selection(
        related='partner_id.zona',
        string='Zona',
        readonly=True, store=False,
    )
    co_barrio_ciudad = fields.Char(
        related='partner_id.barrio_ciudad',
        string='Barrio / Ciudad',
        readonly=True, store=False,
    )
    co_direccion_residencia = fields.Char(
        related='partner_id.direccion_residencia',
        string='Dirección de Residencia',
        readonly=True, store=False,
    )

    # ── SISBEN ───────────────────────────────────────────────────────────────
    co_tiene_sisben = fields.Boolean(
        related='partner_id.tiene_sisben',
        string='Tiene SISBEN',
        readonly=True, store=False,
    )
    co_sisben_id = fields.Many2one(
        related='partner_id.sisben_id',
        string='Clasificación SISBEN',
        readonly=True, store=False,
    )

    # ── Estrato socioeconómico ───────────────────────────────────────────────
    co_estrato_id = fields.Many2one(
        related='partner_id.estrato_id',
        string='Estrato Socioeconómico',
        readonly=True, store=False,
    )

    # ── Discapacidad ─────────────────────────────────────────────────────────
    co_tiene_discapacidad = fields.Boolean(
        related='partner_id.tiene_discapacidad',
        string='Tiene Discapacidad',
        readonly=True, store=False,
    )
    co_discapacidad_id = fields.Many2one(
        related='partner_id.discapacidad_id',
        string='Tipo de Discapacidad',
        readonly=True, store=False,
    )

    # ── Víctima del conflicto ────────────────────────────────────────────────
    co_es_victima_conflicto = fields.Boolean(
        related='partner_id.es_victima_conflicto',
        string='Víctima del Conflicto Armado',
        readonly=True, store=False,
    )
    co_tipo_victima_id = fields.Many2one(
        related='partner_id.tipo_victima_id',
        string='Tipo de Víctima',
        readonly=True, store=False,
    )

    # ── Salud ────────────────────────────────────────────────────────────────
    co_ips_cotizante = fields.Selection(
        related='partner_id.ips_cotizante',
        string='IPS Cotizante',
        readonly=True, store=False,
    )
