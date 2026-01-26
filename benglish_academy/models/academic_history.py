# -*- coding: utf-8 -*-
"""
Modelo de Bitácora Académica
Registra TODAS las clases dictadas con información de asistencia y novedades.
Es la fuente de verdad del historial académico del estudiante.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class AcademicHistory(models.Model):
    """
    Bitácora Académica: Registro inmutable de clases dictadas.

    Se crea automáticamente cuando una sesión pasa a estado 'done'.
    Registra la asistencia de cada estudiante inscrito y cualquier novedad.
    """

    _name = "benglish.academic.history"
    _description = "Bitácora Académica"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "session_date desc, session_time_start desc, id desc"
    _rec_name = "display_name"

    @api.model
    def _cron_alert_pending_lms(self):
        """
        Cron Job: Alertar Placement Tests pendientes de resultado LMS > 3 días
        Ejecuta diariamente
        """
        from datetime import timedelta

        threshold_date = fields.Date.today() - timedelta(days=3)

        # Search in placement test prospect model instead
        pending_lms = self.env["benglish.placement.test.prospect"].search(
            [
                ("oral_evaluation_score", ">", 0),
                ("lms_score", "=", 0),
                ("test_date", "<", threshold_date),
                ("placement_status", "in", ["pending_oral", "pending_lms"]),
            ]
        )

        if not pending_lms:
            return

        # Obtener coordinadores
        coordinator_group = self.env.ref(
            "benglish_academy.group_benglish_coordinator", raise_if_not_found=False
        )

        if not coordinator_group:
            _logger.warning("Grupo de coordinadores no encontrado")
            return

        for prospect in pending_lms:
            days_waiting = (fields.Date.today() - prospect.test_date).days

            # Crear actividad para cada coordinador
            for user in coordinator_group.users:
                self.env["mail.activity"].create(
                    {
                        "res_model_id": self.env.ref(
                            "benglish_academy.model_benglish_placement_test_prospect"
                        ).id,
                        "res_id": prospect.id,
                        "activity_type_id": self.env.ref(
                            "mail.mail_activity_data_warning"
                        ).id,
                        "summary": f"⚠️ LMS pendiente: {prospect.prospect_name}",
                        "note": f"""
                        <p>El Placement Test del prospecto <strong>{prospect.prospect_name}</strong> 
                        está esperando resultado del Campus Virtual desde hace <strong>{days_waiting} días</strong>.</p>
                        
                        <p><strong>Opciones:</strong></p>
                        <ul>
                            <li>Verificar logs de integración LMS</li>
                            <li>Contactar al equipo técnico del Campus Virtual</li>
                            <li>Usar el botón "Ingresar LMS Manualmente" en el registro</li>
                        </ul>
                    """,
                        "user_id": user.id,
                        "date_deadline": fields.Date.today(),
                    }
                )

            _logger.info(
                f"Alerta creada para Placement Test pendiente: {prospect.prospect_name} ({days_waiting} días)"
            )

        _logger.info(
            f"Cron ejecutado: {len(pending_lms)} Placement Tests pendientes de LMS"
        )

    # IDENTIFICACIÓN

    display_name = fields.Char(
        string="Nombre",
        compute="_compute_display_name",
        store=True,
        help="Nombre descriptivo del registro",
    )

    # RELACIONES PRINCIPALES

    student_id = fields.Many2one(
        comodel_name="benglish.student",
        string="Estudiante",
        required=False,  # MODIFICADO: Permitir registros sin estudiante (para documentación de materiales)
        ondelete="cascade",
        index=True,
        readonly=True,
        help="Estudiante que cursó la clase (opcional para registros de documentación sin asistencia)",
    )

    session_id = fields.Many2one(
        comodel_name="benglish.academic.session",
        string="Sesión",
        required=False,  # Opcional para permitir historial retroactivo sin sesión
        ondelete="restrict",
        index=True,
        readonly=True,
        help="Sesión de clase dictada (opcional para registros históricos retroactivos)",
    )

    enrollment_id = fields.Many2one(
        comodel_name="benglish.session.enrollment",
        string="Inscripción",
        ondelete="set null",
        readonly=True,
        help="Inscripción original del estudiante en la sesión",
    )

    # DATOS DE LA SESIÓN (DENORMALIZADOS PARA CONSULTAS RÁPIDAS)

    session_date = fields.Date(
        string="Fecha",
        required=True,
        index=True,
        readonly=True,
        help="Fecha en que se dictó la clase",
    )

    session_time_start = fields.Float(
        string="Hora Inicio", readonly=True, help="Hora de inicio de la clase"
    )

    session_time_end = fields.Float(
        string="Hora Fin", readonly=True, help="Hora de fin de la clase"
    )

    program_id = fields.Many2one(
        comodel_name="benglish.program",
        string="Programa",
        required=True,
        ondelete="restrict",
        index=True,
        readonly=True,
        help="Programa académico",
    )

    plan_id = fields.Many2one(
        comodel_name="benglish.plan",
        string="Plan",
        ondelete="restrict",
        readonly=True,
        help="Plan de estudio",
    )

    phase_id = fields.Many2one(
        comodel_name="benglish.phase",
        string="Fase",
        ondelete="restrict",
        index=True,
        readonly=True,
        help="Fase académica",
    )

    level_id = fields.Many2one(
        comodel_name="benglish.level",
        string="Nivel",
        ondelete="restrict",
        index=True,
        readonly=True,
        help="Nivel académico",
    )

    subject_id = fields.Many2one(
        comodel_name="benglish.subject",
        string="Asignatura",
        required=True,
        ondelete="cascade",
        index=True,
        readonly=True,
        help="Asignatura dictada",
    )

    campus_id = fields.Many2one(
        comodel_name="benglish.campus",
        string="Sede",
        ondelete="restrict",
        readonly=True,
        help="Sede donde se dictó la clase",
    )

    teacher_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Docente",
        ondelete="restrict",
        readonly=True,
        help="Docente que dictó la clase",
    )

    delivery_mode = fields.Selection(
        selection=[
            ("presential", "Presencial"),
            ("virtual", "Virtual"),
            ("hybrid", "Híbrida"),
        ],
        string="Modalidad",
        readonly=True,
        help="Modalidad en que se dictó la clase",
    )

    # ASISTENCIA

    attendance_status = fields.Selection(
        selection=[
            ("attended", "Asistió"),
            ("absent", "No asistió"),
            ("pending", "Sin registrar"),
        ],
        string="Asistencia",
        required=True,
        default="pending",
        index=True,
        help="Estado de asistencia del estudiante",
    )

    # Campo booleano para marcar asistencia (checkbox)
    attended = fields.Boolean(
        string="Asistió",
        compute="_compute_attended",
        inverse="_inverse_attended",
        store=True,
        help="Campo booleano que indica si el estudiante asistió (sincronizado con attendance_status)",
    )

    attendance_registered_at = fields.Datetime(
        string="Asistencia registrada",
        readonly=True,
        help="Fecha y hora en que se registró la asistencia",
    )

    attendance_registered_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Registrada por",
        readonly=True,
        help="Usuario que registró la asistencia",
    )

    # CALIFICACIÓN

    grade = fields.Float(
        string="Calificación",
        digits=(5, 2),
        help="Calificación numérica obtenida en la sesión (será digitada desde portal docente)",
    )

    grade_registered_at = fields.Datetime(
        string="Calificación registrada",
        readonly=True,
        help="Fecha y hora en que se registró la calificación",
    )

    grade_registered_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Calificación registrada por",
        readonly=True,
        help="Usuario que registró la calificación",
    )

    # CÓDIGO DE SESIÓN (para trazabilidad)

    session_code = fields.Char(
        string="Código Sesión",
        related="session_id.session_code",
        store=True,
        readonly=True,
        help="Código único de la sesión (desde el horario académico)",
    )


    # AUDITORÍA

    created_at = fields.Datetime(
        string="Creado",
        default=fields.Datetime.now,
        required=True,
        readonly=True,
        help="Fecha y hora de creación del registro",
    )

    created_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Creado por",
        default=lambda self: self.env.user,
        readonly=True,
        help="Usuario que creó el registro",
    )

    notes = fields.Text(string="Notas", help="Observaciones adicionales")

    # NOVEDAD (para bitácora académica)
    novedad = fields.Selection(
        selection=[
            ("normal", "Normal"),
            ("aplazada", "aplazada"),
            ("material", "material"),
            ("clase_no_dictada", "Clase no dictada"),
        ],
        string="Tipo Novedad",
        default="normal",
        help="Tipo de novedad reportada durante la clase",
    )

    # ARCHIVOS ADJUNTOS (materiales, evidencias, documentos)
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='benglish_academic_history_attachment_rel',
        column1='history_id',
        column2='attachment_id',
        string='Archivos Adjuntos',
        help='Materiales, documentos y evidencias adjuntas a este registro de bitácora',
    )

    attachment_count = fields.Integer(
        string='Cantidad de Adjuntos',
        compute='_compute_attachment_count',
        store=True,
        help='Número de archivos adjuntos',
    )

    # RESTRICCIONES SQL

    _sql_constraints = [
        (
            "unique_student_session",
            "UNIQUE(student_id, session_id)",
            "Ya existe un registro de historial para este estudiante en esta sesión.",
        ),
    ]

    # COMPUTED FIELDS

    @api.depends(
        "student_id.name", "session_id.display_name", "subject_id.name", "session_date"
    )
    def _compute_display_name(self):
        """Genera nombre descriptivo para el registro."""
        for record in self:
            parts = []
            if record.student_id:
                parts.append(record.student_id.name)
            if record.subject_id:
                parts.append(record.subject_id.code or record.subject_id.name)
            if record.session_date:
                parts.append(fields.Date.to_string(record.session_date))
            record.display_name = " - ".join(parts) if parts else "Historial Académico"

    @api.depends("attendance_status")
    def _compute_attended(self):
        """Calcula el campo booleano attended desde attendance_status."""
        for record in self:
            record.attended = record.attendance_status == "attended"
    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        """Calcula el número de archivos adjuntos."""
        for record in self:
            record.attachment_count = len(record.attachment_ids)
    def _inverse_attended(self):
        """Actualiza attendance_status cuando se modifica el checkbox attended."""
        for record in self:
            if record.attended:
                record.attendance_status = "attended"
            else:
                # Si se desmarca Y el estado actual no es 'absent', volver a pendiente
                # IMPORTANTE: Preservar 'absent' si ya está marcado como ausente
                if record.attendance_status != "absent":
                    record.attendance_status = "pending"

    # CRUD OVERRIDES

    @api.model_create_multi
    def create(self, vals_list):
        """
        Crea registros de historial.
        Valida que la sesión esté dictada o iniciada.

        ACTUALIZACIÓN: Permitimos crear registros cuando la sesión está 'started'
        para poder marcar asistencia mientras la clase está en curso.
        """
        for vals in vals_list:
            # Validar que la sesión exista y esté al menos iniciada
            session_id = vals.get("session_id")
            if session_id:
                session = self.env["benglish.academic.session"].browse(session_id)
                if session.state not in ["started", "done"]:
                    raise ValidationError(
                        _(
                            "Solo se pueden crear registros de historial para sesiones iniciadas o dictadas. "
                            "Estado actual: %(state)s"
                        )
                        % {"state": session.state}
                    )

        records = super(AcademicHistory, self).create(vals_list)

        # Log de creación
        for record in records:
            _logger.info(
                f"[ACADEMIC HISTORY] Created: Student={record.student_id.name}, "
                f"Subject={record.subject_id.name}, Date={record.session_date}, "
                f"Attendance={record.attendance_status}"
            )
        
        # ⭐ NUEVO: Forzar recálculo de KPIs del estudiante
        students = records.mapped('student_id')
        if students:
            # Forzar recálculo de campos computados
            students._compute_attendance_kpis()
            _logger.info(
                f"[ACADEMIC HISTORY] KPIs recalculados para {len(students)} estudiante(s) tras crear {len(records)} registro(s)"
            )

        return records

    def write(self, vals):
        """
        Permite actualizar SOLO el estado de asistencia y calificación.
        El resto de campos son inmutables.
        """
        # Si se actualiza 'attended' (campo booleano), sincronizar con 'attendance_status'
        if "attended" in vals:
            if vals["attended"]:
                vals["attendance_status"] = "attended"
            else:
                # Si se desmarca, marcar como ausente (no pendiente)
                vals["attendance_status"] = "absent"

        # Campos permitidos para actualización
        allowed_fields = {
            "attendance_status",
            "attended",  # Agregado para permitir edición directa del checkbox
            "attendance_registered_at",
            "attendance_registered_by_id",
            "grade",
            "grade_registered_at",
            "grade_registered_by_id",
            "notes",
        }

        # Verificar que solo se actualicen campos permitidos
        restricted_fields = set(vals.keys()) - allowed_fields
        if restricted_fields:
            raise UserError(
                _(
                    "No se pueden modificar estos campos del historial: %(fields)s\n\n"
                    "El historial académico es inmutable excepto para el registro de asistencia y calificación."
                )
                % {"fields": ", ".join(restricted_fields)}
            )

        # Si se actualiza asistencia, registrar quien y cuando
        if "attendance_status" in vals:
            vals["attendance_registered_at"] = fields.Datetime.now()
            vals["attendance_registered_by_id"] = self.env.user.id

        # Si se actualiza calificación, registrar quien y cuando
        if "grade" in vals:
            vals["grade_registered_at"] = fields.Datetime.now()
            vals["grade_registered_by_id"] = self.env.user.id

        result = super(AcademicHistory, self).write(vals)

        # Log de actualización
        for record in self:
            _logger.info(
                f"[ACADEMIC HISTORY] Updated: Student={record.student_id.name}, "
                f"Subject={record.subject_id.name}, Attendance={record.attendance_status}, "
                f"Grade={record.grade}"
            )
        
        # ⭐ NUEVO: Forzar recálculo de KPIs del estudiante
        if "attendance_status" in vals or "attended" in vals:
            students = self.mapped('student_id')
            if students:
                # Forzar recálculo de campos computados
                students._compute_attendance_kpis()
                _logger.info(
                    f"[ACADEMIC HISTORY] KPIs recalculados para {len(students)} estudiante(s)"
                )

        return result

    # NOTA: Eliminación permitida para correcciones administrativas
    # def unlink(self):
    #     """
    #     Previene eliminación de registros de historial.
    #     El historial es inmutable.
    #     """
    #     raise UserError(
    #         _(
    #             "No se pueden eliminar registros del historial académico.\n\n"
    #             "El historial es inmutable y debe mantenerse para auditoría."
    #         )
    #     )

    # MÉTODOS DE NEGOCIO

    def action_mark_attended(self):
        """Marca asistencia como 'Asistió'."""
        for record in self:
            if record.attendance_status == "attended":
                raise UserError(_("La asistencia ya está marcada como 'Asistió'."))

            record.write({"attendance_status": "attended"})

            record.student_id.message_post(
                body=_("Asistencia registrada: %(subject)s - %(date)s")
                % {
                    "subject": record.subject_id.name,
                    "date": fields.Date.to_string(record.session_date),
                },
                subject=_("Asistencia Registrada"),
            )

    def action_mark_absent(self):
        """Marca asistencia como 'No asistió'."""
        for record in self:
            if record.attendance_status == "absent":
                raise UserError(_("La asistencia ya está marcada como 'No asistió'."))

            record.write({"attendance_status": "absent"})

            record.student_id.message_post(
                body=_("Ausencia registrada: %(subject)s - %(date)s")
                % {
                    "subject": record.subject_id.name,
                    "date": fields.Date.to_string(record.session_date),
                },
                subject=_("Ausencia Registrada"),
            )

    @api.model
    def get_oral_test_min_grade(self):
        icp = self.env["ir.config_parameter"].sudo()
        value = icp.get_param("benglish.oral_test_min_grade", "70")
        try:
            return float(value)
        except (TypeError, ValueError):
            return 70.0

    @api.model
    def get_student_history(self, student_id, filters=None):
        """
        Obtiene el historial académico de un estudiante con filtros opcionales.

        Args:
            student_id: ID del estudiante
            filters: dict con filtros opcionales (program_id, subject_id, date_from, date_to, etc.)

        Returns:
            recordset de benglish.academic.history
        """
        domain = [("student_id", "=", student_id)]

        if filters:
            if filters.get("program_id"):
                domain.append(("program_id", "=", filters["program_id"]))
            if filters.get("subject_id"):
                domain.append(("subject_id", "=", filters["subject_id"]))
            if filters.get("attendance_status"):
                domain.append(("attendance_status", "=", filters["attendance_status"]))
            if filters.get("date_from"):
                domain.append(("session_date", ">=", filters["date_from"]))
            if filters.get("date_to"):
                domain.append(("session_date", "<=", filters["date_to"]))

        return self.search(domain, order="session_date desc, session_time_start desc")

    @api.model
    def get_attendance_summary(self, student_id, program_id=None):
        """
        Obtiene resumen de asistencia del estudiante.

        Returns:
            dict con estadísticas de asistencia
        """
        domain = [("student_id", "=", student_id)]
        if program_id:
            domain.append(("program_id", "=", program_id))

        history = self.search(domain)

        total = len(history)
        attended = len(history.filtered(lambda h: h.attendance_status == "attended"))
        absent = len(history.filtered(lambda h: h.attendance_status == "absent"))
        pending = len(history.filtered(lambda h: h.attendance_status == "pending"))

        attendance_rate = (attended / total * 100) if total > 0 else 0

        return {
            "total_classes": total,
            "attended": attended,
            "absent": absent,
            "pending": pending,
            "attendance_rate": round(attendance_rate, 2),
        }

    def action_download_bitacora(self):
        """
        Descarga la bitácora académica en formato Excel.
        """
        return {
            "type": "ir.actions.act_url",
            "url": "/benglish/bitacora/download?ids=%s" % ",".join(map(str, self.ids)),
            "target": "new",
        }
