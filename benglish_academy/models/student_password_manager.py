# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class StudentPasswordManager(models.Model):
    """
    Modelo para gestionar las contraseñas de los estudiantes desde configuración.
    Permite visualizar y cambiar las contraseñas de acceso al portal de estudiantes.
    """

    _name = "benglish.student.password.manager"
    _description = "Gestión de Contraseñas de Estudiantes"
    _order = "student_name"

    # Campo para búsqueda y selección del estudiante
    student_id = fields.Many2one(
        comodel_name="benglish.student",
        string="Estudiante",
        required=True,
        ondelete="cascade",
        help="Estudiante al que pertenece esta contraseña",
    )

    # Campos relacionados para información del estudiante
    student_name = fields.Char(
        string="Nombre",
        related="student_id.name",
        store=True,
        readonly=True,
    )
    student_code = fields.Char(
        string="Código",
        related="student_id.code",
        store=True,
        readonly=True,
    )
    student_email = fields.Char(
        string="Email",
        related="student_id.email",
        readonly=True,
    )
    student_documento = fields.Char(
        string="Documento",
        related="student_id.student_id_number",
        readonly=True,
    )

    # Usuario portal relacionado
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Usuario Portal",
        related="student_id.user_id",
        readonly=True,
        help="Usuario de portal asociado al estudiante",
    )
    
    portal_login = fields.Char(
        string="Login Portal",
        related="user_id.login",
        readonly=True,
        help="Login del usuario portal",
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
        help="Ingrese la nueva contraseña para el estudiante",
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
        help="Indica si el estudiante tiene usuario portal creado",
    )

    @api.depends("user_id")
    def _compute_has_portal_user(self):
        """Verifica si el estudiante tiene usuario portal"""
        for record in self:
            record.has_portal_user = bool(record.user_id)

    @api.depends("user_id")
    def _compute_current_password(self):
        """
        Muestra la contraseña actual si está almacenada.
        Nota: Odoo solo almacena hashes, así que solo se puede mostrar
        si se ha guardado temporalmente en un campo custom.
        """
        for record in self:
            # Por seguridad, no mostramos la contraseña real
            # Solo indicamos si existe usuario
            if record.user_id:
                record.current_password = "••••••••"
            else:
                record.current_password = "Sin usuario portal"

    def action_change_password(self):
        """
        Cambia la contraseña del usuario portal del estudiante.
        """
        self.ensure_one()
        
        if not self.user_id:
            raise UserError(_("Este estudiante no tiene usuario portal creado.\n"
                            "Por favor, cree el usuario portal primero desde el formulario del estudiante."))
        
        if not self.new_password:
            raise ValidationError(_("Debe ingresar una nueva contraseña."))
        
        if len(self.new_password) < 4:
            raise ValidationError(_("La contraseña debe tener al menos 4 caracteres."))

        try:
            # Cambiar la contraseña del usuario
            self.user_id.sudo().write({
                'password': self.new_password,
            })
            
            # Limpiar el campo de nueva contraseña
            self.write({'new_password': False})
            
            _logger.info(f"Contraseña actualizada para estudiante {self.student_name} (Usuario: {self.user_id.login})")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Contraseña Actualizada'),
                    'message': _('La contraseña del estudiante %s ha sido actualizada correctamente.') % self.student_name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Error al cambiar contraseña para {self.student_name}: {str(e)}")
            raise UserError(_("Error al cambiar la contraseña: %s") % str(e))

    def action_create_portal_user(self):
        """
        Crea el usuario portal para el estudiante si no existe.
        """
        self.ensure_one()
        
        if self.user_id:
            raise UserError(_("Este estudiante ya tiene un usuario portal creado."))
        
        try:
            result = self.student_id._create_single_portal_user()
            
            if result.get('success'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Usuario Portal Creado'),
                        'message': _('El usuario portal para %s ha sido creado exitosamente.') % self.student_name,
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(result.get('message', 'Error desconocido al crear usuario portal'))
                
        except Exception as e:
            _logger.error(f"Error al crear usuario portal para {self.student_name}: {str(e)}")
            raise UserError(_("Error al crear usuario portal: %s") % str(e))

    def action_reset_password_to_document(self):
        """
        Restablece la contraseña del estudiante a su número de documento.
        """
        self.ensure_one()
        
        if not self.user_id:
            raise UserError(_("Este estudiante no tiene usuario portal creado."))
        
        if not self.student_documento:
            raise UserError(_("El estudiante no tiene documento registrado."))
        
        try:
            # Normalizar el documento para usar como contraseña
            normalized_doc = self.student_id._normalize_portal_document(self.student_documento)
            
            if not normalized_doc:
                raise UserError(_("No se pudo normalizar el documento para usar como contraseña."))
            
            # Establecer el documento como contraseña
            self.user_id.sudo().write({
                'password': normalized_doc,
            })
            
            _logger.info(f"Contraseña restablecida a documento para {self.student_name}")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Contraseña Restablecida'),
                    'message': _('La contraseña de %s ha sido restablecida a su número de documento.') % self.student_name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Error al restablecer contraseña para {self.student_name}: {str(e)}")
            raise UserError(_("Error al restablecer contraseña: %s") % str(e))

    @api.model
    def action_open_password_manager(self):
        """
        Acción para abrir el gestor de contraseñas.
        """
        return {
            'name': _('Gestión de Contraseñas de Estudiantes'),
            'type': 'ir.actions.act_window',
            'res_model': 'benglish.student.password.manager',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    @api.model
    def create(self, vals):
        """
        Sobrescribe create para evitar duplicados.
        Si ya existe un registro para el estudiante, lo retorna.
        """
        if 'student_id' in vals:
            existing = self.search([('student_id', '=', vals['student_id'])], limit=1)
            if existing:
                return existing
        return super().create(vals)

    @api.model
    def get_or_create_for_student(self, student_id):
        """
        Obtiene o crea un registro de gestión de contraseña para un estudiante.
        """
        record = self.search([('student_id', '=', student_id)], limit=1)
        if not record:
            record = self.create({'student_id': student_id})
        return record
