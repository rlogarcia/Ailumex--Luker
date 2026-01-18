# -*- coding: utf-8 -*-
"""Modelo para rastrear notificaciones vistas por estudiantes."""

from odoo import api, fields, models


class PortalNotificationView(models.Model):
    """Registra qué notificaciones ha visto cada estudiante."""
    
    _name = "portal.notification.view"
    _description = "Notificaciones vistas por estudiantes"
    _rec_name = "user_id"

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Usuario",
        required=True,
        ondelete="cascade",
        index=True
    )
    session_id = fields.Many2one(
        comodel_name="benglish.academic.session",
        string="Sesión académica",
        required=True,
        ondelete="cascade",
        index=True
    )
    viewed_at = fields.Datetime(
        string="Visto en",
        default=fields.Datetime.now,
        required=True
    )

    _sql_constraints = [
        (
            "unique_user_session",
            "unique(user_id, session_id)",
            "Esta notificación ya fue marcada como vista por este usuario."
        )
    ]
