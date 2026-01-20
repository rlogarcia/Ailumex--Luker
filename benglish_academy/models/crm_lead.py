# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class CrmLeadInherit(models.Model):
    """
    Extensión de crm.lead para integración con HR y validaciones comerciales.

    ARQUITECTURA:
    - Solo empleados con is_sales=True pueden ser asignados como responsables de leads
    - La validación se ejecuta en create y write
    - El campo source_id tiene protección especial contra modificaciones no autorizadas
    """

    _inherit = "crm.lead"

    # CAMPOS ADICIONALES (Equivalencia Excel)


    # Campos básicos de contacto extendidos
    external_id = fields.Char(
        string="ID Externo",
        help="Identificador del lead en sistema externo (CRM anterior, Excel, etc.)",
        index=True,
    )

    referral_source = fields.Char(
        string="Fuente de Referido",
        help="Persona o entidad que refirió al prospecto",
    )

    preferred_contact_time = fields.Selection(
        selection=[
            ("morning", "Mañana (8:00 - 12:00)"),
            ("afternoon", "Tarde (12:00 - 18:00)"),
            ("evening", "Noche (18:00 - 21:00)"),
        ],
        string="Horario Preferido de Contacto",
        help="Horario en que el prospecto prefiere ser contactado",
    )

    # Información académica del prospecto
    english_level = fields.Selection(
        selection=[
            ("beginner", "Principiante (A1)"),
            ("elementary", "Elemental (A2)"),
            ("intermediate", "Intermedio (B1)"),
            ("upper_intermediate", "Intermedio Alto (B2)"),
            ("advanced", "Avanzado (C1)"),
            ("proficient", "Experto (C2)"),
        ],
        string="Nivel de Inglés",
        help="Nivel estimado o declarado de inglés del prospecto",
    )

    learning_objective = fields.Selection(
        selection=[
            ("work", "Trabajo/Carrera Profesional"),
            ("travel", "Viajes"),
            ("study", "Estudios/Certificaciones"),
            ("personal", "Desarrollo Personal"),
            ("business", "Negocios Internacionales"),
        ],
        string="Objetivo de Aprendizaje",
        help="Motivación principal para aprender inglés",
    )

    preferred_schedule = fields.Selection(
        selection=[
            ("weekday_morning", "Entre semana - Mañana"),
            ("weekday_afternoon", "Entre semana - Tarde"),
            ("weekday_evening", "Entre semana - Noche"),
            ("weekend", "Fines de semana"),
            ("flexible", "Horario Flexible"),
        ],
        string="Horario Preferido",
        help="Disponibilidad horaria del prospecto para clases",
    )

    delivery_mode_preference = fields.Selection(
        selection=[
            ("presential", "Presencial"),
            ("virtual", "Virtual"),
            ("hybrid", "Híbrido"),
            ("no_preference", "Sin Preferencia"),
        ],
        string="Modalidad Preferida",
        help="Preferencia de modalidad de clases",
        default="no_preference",
    )

    # Campos de seguimiento comercial
    evaluation_date = fields.Datetime(
        string="Fecha de Evaluación",
        help="Fecha programada para evaluación de nivel",
    )

    evaluation_completed = fields.Boolean(
        string="Evaluación Completada",
        default=False,
        tracking=True,
    )

    evaluation_result = fields.Text(
        string="Resultado de Evaluación",
        help="Observaciones y resultados de la evaluación de nivel",
    )

    # Información de conversión
    converted_student_id = fields.Many2one(
        comodel_name="benglish.student",
        string="Estudiante Convertido",
        help="Estudiante creado al convertir este lead",
        readonly=True,
        ondelete="set null",
    )

    # VALIDACIONES


    @api.constrains("user_id")
    def _check_user_is_sales_employee(self):
        """
        Valida que el usuario asignado sea un empleado con perfil comercial.
        CRÍTICO: Solo empleados comerciales pueden recibir leads.
        """
        for lead in self:
            if lead.user_id:
                # Buscar empleado asociado al usuario
                employee = self.env["hr.employee"].search(
                    [("user_id", "=", lead.user_id.id)], limit=1
                )

                if not employee:
                    raise ValidationError(
                        _(
                            "El usuario %(user)s no tiene un empleado asociado.\n"
                            "Solo se pueden asignar leads a usuarios con perfil de empleado."
                        )
                        % {"user": lead.user_id.name}
                    )

                if not employee.is_sales:
                    raise ValidationError(
                        _(
                            "El empleado %(employee)s no está marcado como vendedor.\n"
                            "Solo empleados con el campo 'Es Vendedor/Comercial' "
                            "activado pueden recibir leads.\n\n"
                            "Por favor, active este campo en el perfil del empleado "
                            "o asigne el lead a otro usuario."
                        )
                        % {"employee": employee.name}
                    )

    @api.constrains("user_id")
    def _check_user_active(self):
        """
        Valida que el responsable asignado esté activo.
        CRÍTICO: Previene asignación a usuarios inactivos.
        """
        for lead in self:
            if lead.user_id and not lead.user_id.active:
                raise ValidationError(
                    _(
                        "No se puede asignar el lead a un usuario inactivo.\n"
                        "Usuario: %(user)s\n\n"
                        "Por favor, asigne el lead a un usuario activo."
                    )
                    % {"user": lead.user_id.name}
                )

    # OVERRIDE DE MÉTODOS


    @api.model_create_multi
    def create(self, vals_list):
        """Override create para registrar en chatter la asignación inicial."""
        leads = super().create(vals_list)

        for lead in leads:
            if lead.user_id:
                employee = self.env["hr.employee"].search(
                    [("user_id", "=", lead.user_id.id)], limit=1
                )

                lead.message_post(
                    body=_("Lead asignado a %(employee)s (Vendedor)")
                    % {"employee": employee.name if employee else lead.user_id.name},
                    subject=_("Asignación Inicial"),
                    message_type="notification",
                )

        return leads

    def write(self, vals):
        """Override write para auditar cambios de responsable y fuente."""
        # Auditar cambio de fuente (source_id o campaign_id)
        if "source_id" in vals or "campaign_id" in vals:
            for lead in self:
                # Verificar si el usuario tiene permiso para cambiar fuente
                if not self.env.user.has_group("sales_team.group_sale_manager"):
                    # Si no es manager, bloquear el cambio
                    old_source = lead.source_id.name if lead.source_id else "Sin fuente"
                    new_source_id = vals.get("source_id", lead.source_id.id)
                    new_source = (
                        self.env["utm.source"].browse(new_source_id).name
                        if new_source_id
                        else "Sin fuente"
                    )

                    # Registrar intento en chatter
                    lead.message_post(
                        body=_(
                            "⚠️ INTENTO DE MODIFICACIÓN BLOQUEADO<br/>"
                            "<b>Usuario:</b> %(user)s<br/>"
                            "<b>Campo:</b> Fuente del Lead<br/>"
                            "<b>Valor anterior:</b> %(old)s<br/>"
                            "<b>Valor intentado:</b> %(new)s<br/>"
                            "<b>Motivo:</b> Solo los gestores pueden modificar la fuente del lead"
                        )
                        % {
                            "user": self.env.user.name,
                            "old": old_source,
                            "new": new_source,
                        },
                        subject=_("Intento de Modificación Bloqueado"),
                        message_type="notification",
                        subtype_id=self.env.ref("mail.mt_note").id,
                    )

                    raise UserError(
                        _(
                            "❌ Acceso Denegado\n\n"
                            "No tiene permisos para modificar la fuente del lead.\n"
                            "Solo los gestores comerciales pueden realizar esta acción.\n\n"
                            "Este intento ha sido registrado en el historial del lead."
                        )
                    )
                else:
                    # Si es manager, registrar el cambio autorizado
                    old_source = lead.source_id.name if lead.source_id else "Sin fuente"
                    new_source_id = vals.get("source_id", lead.source_id.id)
                    new_source = (
                        self.env["utm.source"].browse(new_source_id).name
                        if new_source_id
                        else "Sin fuente"
                    )

                    if old_source != new_source:
                        lead.message_post(
                            body=_(
                                "✅ Fuente del lead modificada<br/>"
                                "<b>Usuario:</b> %(user)s<br/>"
                                "<b>Valor anterior:</b> %(old)s<br/>"
                                "<b>Nuevo valor:</b> %(new)s"
                            )
                            % {
                                "user": self.env.user.name,
                                "old": old_source,
                                "new": new_source,
                            },
                            subject=_("Fuente Modificada"),
                            message_type="notification",
                        )

        # Auditar cambio de responsable
        if "user_id" in vals:
            for lead in self:
                old_user = lead.user_id
                new_user = (
                    self.env["res.users"].browse(vals["user_id"])
                    if vals["user_id"]
                    else False
                )

                if old_user != new_user:
                    old_name = old_user.name if old_user else "Sin asignar"
                    new_name = new_user.name if new_user else "Sin asignar"

                    lead.message_post(
                        body=_("Responsable cambiado de %(old)s a %(new)s")
                        % {"old": old_name, "new": new_name},
                        subject=_("Cambio de Responsable"),
                        message_type="notification",
                    )

        return super().write(vals)

    # MÉTODOS PÚBLICOS


    def action_convert_to_student(self):
        """
        Convierte el lead en un estudiante de Benglish.
        Crea un registro en benglish.student con la información del lead.
        """
        self.ensure_one()

        if self.converted_student_id:
            raise UserError(
                _("Este lead ya fue convertido al estudiante: %s")
                % self.converted_student_id.name
            )

        # Crear estudiante
        student_vals = {
            "name": self.contact_name or self.name,
            "email": self.email_from,
            "phone": self.phone,
            "mobile": self.mobile,
            # Mapear campos adicionales según necesidad
        }

        student = self.env["benglish.student"].create(student_vals)

        # Registrar conversión
        self.write(
            {
                "converted_student_id": student.id,
            }
        )

        self.message_post(
            body=_("Lead convertido exitosamente a estudiante: %s") % student.name,
            subject=_("Conversión a Estudiante"),
            message_type="notification",
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "benglish.student",
            "res_id": student.id,
            "view_mode": "form",
            "target": "current",
        }
