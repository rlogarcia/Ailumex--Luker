# -*- coding: utf-8 -*-
import uuid
import logging
from datetime import timedelta
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

EXPIRACION_DIAS = 30


class LukerApiToken(models.Model):
    _name        = 'luker.api.token'
    _description = 'Token de autenticación PWA por dispositivo'
    _order       = 'fecha_creacion desc'
    _rec_name    = 'dispositivo_id'

    # ── Identificación ───────────────────────────────────────────────────────
    token        = fields.Char(
        string='Token', readonly=True, copy=False, index=True,
        help='UUID generado al autenticarse. Se envía en el header Authorization.',
    )
    dispositivo_id = fields.Char(
        string='ID Dispositivo', required=True, index=True,
        help='Identificador único del dispositivo físico (tablet/móvil).',
    )

    # ── Vínculo con participante ─────────────────────────────────────────────
    participante_id = fields.Many2one(
        'luker.participant',
        string='Participante',
        ondelete='cascade',
    )

    # ── Vigencia ────────────────────────────────────────────────────────────
    fecha_creacion   = fields.Datetime(string='Creado', default=fields.Datetime.now, readonly=True)
    fecha_expiracion = fields.Datetime(string='Expira',  readonly=True)
    activo           = fields.Boolean(string='Activo', default=True)

    # ── Trazabilidad ────────────────────────────────────────────────────────
    ultima_actividad = fields.Datetime(string='Último uso')
    ip_origen        = fields.Char(string='IP de origen')

    # ── ORM ─────────────────────────────────────────────────────────────────
    @api.model
    def generar_token(self, participante_id, dispositivo_id, ip=None):
        """
        Crea o renueva el token para un par (participante, dispositivo).
        Invalida tokens anteriores del mismo dispositivo.
        Devuelve el string del token.
        """
        # Invalidar tokens anteriores del mismo dispositivo
        self.search([
            ('dispositivo_id', '=', dispositivo_id),
            ('activo', '=', True),
        ]).write({'activo': False})

        ahora = fields.Datetime.now()
        token_str = str(uuid.uuid4())

        self.create({
            'token':            token_str,
            'dispositivo_id':   dispositivo_id,
            'participante_id':  participante_id,
            'fecha_creacion':   ahora,
            'fecha_expiracion': ahora + timedelta(days=EXPIRACION_DIAS),
            'activo':           True,
            'ip_origen':        ip,
        })
        _logger.info(
            'Token generado para participante=%s dispositivo=%s',
            participante_id, dispositivo_id,
        )
        return token_str

    @api.model
    def validar_token(self, token_str):
        """
        Valida el token y retorna el registro si es válido y no expiró.
        Actualiza última_actividad.
        """
        ahora = fields.Datetime.now()
        rec = self.search([
            ('token', '=', token_str),
            ('activo', '=', True),
            ('fecha_expiracion', '>', ahora),
        ], limit=1)

        if rec:
            rec.ultima_actividad = ahora
        return rec
