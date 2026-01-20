# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
import re

_logger = logging.getLogger(__name__)


class TeacherPasswordManager(models.Model):
    """
    Modelo para gestionar las contraseñas de los docentes desde configuración.
    Permite visualizar y cambiar las contraseñas de acceso al portal de docentes/coaches.
    """

    _name = "benglish.teacher.password.manager"
    _description = "Gestión de Contraseñas de Docentes"
    _order = "teacher_name"

    # Campo para búsqueda y selección del empleado/docente
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Docente/Empleado",
        required=True,
        ondelete="cascade",
        domain=[("is_teacher", "=", True)],
        help="Docente/empleado al que pertenece esta contraseña",
    )

    # Campos relacionados para información del empleado
    teacher_name = fields.Char(
        string="Nombre",
        related="employee_id.name",
        store=True,
        readonly=True,
    )
    teacher_email = fields.Char(
        string="Email",
        related="employee_id.work_email",
        readonly=True,
    )

    # Partner relacionado
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contacto",
        compute="_compute_partner_id",
        store=True,
        readonly=True,
        help="Contacto asociado al empleado",
    )

    partner_vat = fields.Char(
        string="Número de Identificación",
        related="partner_id.vat",
        readonly=True,
        help="Número de identificación del contacto (usado como login)",
    )

    # Usuario portal relacionado
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Usuario Portal",
        related="employee_id.user_id",
        readonly=True,
        help="Usuario de portal asociado al docente",
    )
    
    portal_login = fields.Char(
        string="Login Portal",
        related="user_id.login",
        readonly=True,
        help="Login del usuario portal (número de identificación)",
    )

    # Campo para mostrar la contraseña actual (solo lectura)
    current_password = fields.Char(
        string="Contraseña Actual",
        compute="_compute_current_password",
        help="Contraseña actual del usuario (solo visible si fue establecida manualmente)",
    )

    # Campo para establecer nueva contraseña
    new_password = fields.Char(
        string="Nueva Contraseña",
        help="Ingrese la nueva contraseña para el docente",
    )

    # Estado del usuario
    user_active = fields.Boolean(
        string="Usuario Activo",
        related="user_id.active",
        readonly=True,
    )

    has_portal_user = fields.Boolean(
        string="Tiene Usuario Portal",
        compute="_compute_has_portal_user",
        store=True,
        help="Indica si el docente tiene usuario portal creado",
    )

    @api.depends("user_id")
    def _compute_has_portal_user(self):
        """Verifica si el docente tiene usuario portal"""
        for record in self:
            record.has_portal_user = bool(record.user_id)

    @api.depends("employee_id", "employee_id.work_email")
    def _compute_partner_id(self):
        """Busca el partner asociado al empleado"""
        for record in self:
            if record.employee_id and record.employee_id.work_email:
                partner = self.env["res.partner"].sudo().search([
                    "|",
                    ("email", "=", record.employee_id.work_email),
                    ("name", "=", record.employee_id.name)
                ], limit=1)
                record.partner_id = partner
            else:
                record.partner_id = False

    @api.depends("user_id")
    def _compute_current_password(self):
        """
        Intenta mostrar la contraseña actual.
        Por seguridad, Odoo no permite leer contraseñas hasheadas,
        así que este campo solo mostrará información si se guardó manualmente.
        """
        for record in self:
            if record.user_id:
                # Por seguridad, no se puede recuperar la contraseña real
                # Solo mostramos un mensaje indicativo
                record.current_password = "********"
            else:
                record.current_password = "Sin usuario portal"

    def action_change_password(self):
        """
        Cambia la contraseña del usuario portal del docente.
        """
        self.ensure_one()

        if not self.user_id:
            raise UserError(
                _("Este docente no tiene usuario portal creado.\n"
                  "Active el checkbox 'Acceso Al Portal Docente' en el empleado primero.")
            )

        if not self.new_password:
            raise ValidationError(_("Debe ingresar una nueva contraseña"))

        if len(self.new_password) < 4:
            raise ValidationError(
                _("La contraseña debe tener al menos 4 caracteres")
            )

        try:
            # Cambiar la contraseña
            self.user_id.sudo().write({"password": self.new_password})

            # Limpiar el campo de nueva contraseña
            self.new_password = False

            # Notificar al empleado
            self.employee_id.message_post(
                body=f"""<p>✅ <strong>Contraseña del Portal Actualizada</strong></p>
                <ul>
                    <li><strong>Usuario:</strong> {self.portal_login}</li>
                    <li><strong>Email:</strong> {self.teacher_email}</li>
                    <li><strong>Nueva contraseña:</strong> [Actualizada exitosamente]</li>
                </ul>
                <p><em>La contraseña fue cambiada por un administrador.</em></p>""",
                subject="Contraseña del Portal Actualizada",
            )

            _logger.info(
                f"✅ Contraseña actualizada para docente {self.teacher_name} (User ID: {self.user_id.id})"
            )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Contraseña actualizada"),
                    "message": _("La contraseña del docente %s fue actualizada exitosamente")
                    % self.teacher_name,
                    "type": "success",
                    "sticky": False,
                },
            }

        except Exception as e:
            _logger.error(
                f"❌ Error al cambiar contraseña de {self.teacher_name}: {str(e)}"
            )
            raise ValidationError(
                _("Error al cambiar la contraseña: %s") % str(e)
            )

    def action_reset_to_document(self):
        """
        Restablece la contraseña al número de identificación (comportamiento por defecto).
        """
        self.ensure_one()

        if not self.user_id:
            raise UserError(
                _("Este docente no tiene usuario portal creado.\n"
                  "Active el checkbox 'Acceso Al Portal Docente' en el empleado primero.")
            )

        if not self.partner_vat:
            raise ValidationError(
                _("El contacto asociado no tiene número de identificación.\n"
                  "Configure el número de identificación en el contacto primero.")
            )

        # Normalizar el número de identificación
        normalized_document = re.sub(r"[^0-9a-zA-Z]", "", self.partner_vat or "")
        if not normalized_document:
            raise ValidationError(
                _("El número de identificación no es válido.")
            )

        try:
            # Cambiar la contraseña al número de identificación
            self.user_id.sudo().write({"password": normalized_document})

            # Notificar al empleado
            self.employee_id.message_post(
                body=f"""<p>✅ <strong>Contraseña Restablecida</strong></p>
                <ul>
                    <li><strong>Usuario:</strong> {self.portal_login}</li>
                    <li><strong>Contraseña:</strong> {normalized_document}</li>
                    <li><strong>Email:</strong> {self.teacher_email}</li>
                </ul>
                <p><em>La contraseña fue restablecida al número de identificación.</em></p>""",
                subject="Contraseña Restablecida",
            )

            _logger.info(
                f"✅ Contraseña restablecida al documento para {self.teacher_name} (User ID: {self.user_id.id})"
            )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Contraseña restablecida"),
                    "message": _("La contraseña del docente %s fue restablecida al número de identificación: %s")
                    % (self.teacher_name, normalized_document),
                    "type": "success",
                    "sticky": True,
                },
            }

        except Exception as e:
            _logger.error(
                f"❌ Error al restablecer contraseña de {self.teacher_name}: {str(e)}"
            )
            raise ValidationError(
                _("Error al restablecer la contraseña: %s") % str(e)
            )

    def action_toggle_user_active(self):
        """
        Activa o desactiva el usuario portal del docente.
        """
        self.ensure_one()

        if not self.user_id:
            raise UserError(
                _("Este docente no tiene usuario portal creado.")
            )

        new_state = not self.user_id.active
        self.user_id.sudo().write({"active": new_state})

        status_text = "activado" if new_state else "desactivado"
        _logger.info(
            f"✅ Usuario portal {status_text} para {self.teacher_name}"
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Usuario %s") % status_text,
                "message": _("El usuario portal del docente %s fue %s")
                % (self.teacher_name, status_text),
                "type": "info",
            },
        }
