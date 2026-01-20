# -*- coding: utf-8 -*-
from odoo import models

class BenglishStudent(models.Model):
    _inherit = "benglish.student"

    def action_create_portal_user(self):
        """Crea usuario portal y marca cambio de contraseña obligatorio."""
        res = super().action_create_portal_user()
        if self.user_id:
            self.user_id.sudo().write(
                {
                    "portal_must_change_password": True,
                    "portal_password_changed_at": False,
                }
            )
        return res

    def portal_get_access_rules(self):
        """Reglas de acceso del portal basadas en configuración académica."""
        self.ensure_one()
        return super().portal_get_access_rules()
