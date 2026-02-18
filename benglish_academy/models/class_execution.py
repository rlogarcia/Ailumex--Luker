# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ClassExecution(models.Model):
    """
    Clase Ejecutada.

    Registro de la ejecución real de una sesión académica.
    Se crea cuando un docente o gestor registra que la clase fue dictada,
    cancelada o que nadie llegó.

    Equivalencia con el modelo de datos:
    - Tabla: Clase_Ejecutada
    - Campos: Id_Clase (sesión), Fecha_Real, Estado_Ejecucion

    Reglas implementadas:
    - R19: Clase ejecutada por sesión y fecha
    - R20: Asistencia registrada contra clase ejecutada
    - R21: Bitácora ligada a clase ejecutada
    """

    _name = "benglish.class.execution"
    _description = "Clase Ejecutada"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "execution_date desc, session_id"
    _rec_name = "display_name"

    # ═══════════════════════════════════════════════════════════════════════════
    # IDENTIFICACIÓN
    # ═══════════════════════════════════════════════════════════════════════════

    display_name = fields.Char(
        string="Nombre",
        compute="_compute_display_name",
        store=True,
    )

    code = fields.Char(
        string="Código",
        copy=False,
        readonly=True,
        default="/",
        tracking=True,
        index=True,
        help="Código único generado automáticamente",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RELACIÓN CON SESIÓN
    # ═══════════════════════════════════════════════════════════════════════════

    session_id = fields.Many2one(
        comodel_name="benglish.academic.session",
        string="Sesión de Clase",
        required=True,
        ondelete="restrict",
        tracking=True,
        index=True,
        help="Sesión programada que fue ejecutada (o no)",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # FECHA Y HORA REAL DE EJECUCIÓN
    # ═══════════════════════════════════════════════════════════════════════════

    execution_date = fields.Date(
        string="Fecha de Ejecución",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        index=True,
        help="Fecha real en que se ejecutó (o debía ejecutarse) la clase",
    )

    time_start = fields.Float(
        string="Hora Inicio Real",
        help="Hora real de inicio de la clase",
    )

    time_end = fields.Float(
        string="Hora Fin Real",
        help="Hora real de fin de la clase",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # ESTADO DE EJECUCIÓN (R19)
    # ═══════════════════════════════════════════════════════════════════════════

    execution_state = fields.Selection(
        selection=[
            ("taught", "Dictada"),
            ("cancelled", "Cancelada"),
            ("no_show", "Nadie Llegó"),
        ],
        string="Estado de Ejecución",
        required=True,
        default="taught",
        tracking=True,
        help="taught: La clase fue dictada normalmente.\n"
             "cancelled: La clase fue cancelada por algún motivo.\n"
             "no_show: Nadie asistió a la clase.",
    )

    is_closed = fields.Boolean(
        string="Cerrada",
        default=False,
        tracking=True,
        help="Indica si la clase ejecutada ha sido cerrada y ya generó cumplimiento académico",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # INFORMACIÓN ACADÉMICA (denormalizada de la sesión)
    # ═══════════════════════════════════════════════════════════════════════════

    program_id = fields.Many2one(
        comodel_name="benglish.program",
        string="Programa",
        related="session_id.program_id",
        store=True,
        readonly=True,
    )

    subject_id = fields.Many2one(
        comodel_name="benglish.subject",
        string="Asignatura",
        related="session_id.subject_id",
        store=True,
        readonly=True,
    )

    campus_id = fields.Many2one(
        comodel_name="benglish.campus",
        string="Sede",
        related="session_id.campus_id",
        store=True,
        readonly=True,
    )

    teacher_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Docente",
        tracking=True,
        help="Docente que dictó la clase (puede diferir del asignado en la sesión)",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # ASISTENCIA (R20)
    # ═══════════════════════════════════════════════════════════════════════════

    attendance_ids = fields.One2many(
        comodel_name="benglish.class.execution.attendance",
        inverse_name="execution_id",
        string="Asistencia",
        help="Registros de asistencia de estudiantes",
    )

    total_students = fields.Integer(
        string="Total Estudiantes",
        compute="_compute_attendance_stats",
        store=True,
        help="Total de estudiantes registrados",
    )

    present_count = fields.Integer(
        string="Presentes",
        compute="_compute_attendance_stats",
        store=True,
        help="Cantidad de estudiantes presentes",
    )

    absent_count = fields.Integer(
        string="Ausentes",
        compute="_compute_attendance_stats",
        store=True,
        help="Cantidad de estudiantes ausentes",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # BITÁCORA (R21)
    # ═══════════════════════════════════════════════════════════════════════════

    incident_type = fields.Selection(
        selection=[
            ("none", "Sin Novedad"),
            ("cancelled_by_teacher", "Cancelada por Docente"),
            ("cancelled_by_admin", "Cancelada por Administración"),
            ("no_show", "Nadie Asistió"),
            ("late_start", "Inicio Tardío"),
            ("technical_issue", "Problema Técnico"),
            ("other", "Otra Novedad"),
        ],
        string="Tipo de Novedad",
        default="none",
        tracking=True,
        help="Tipo de novedad o incidente durante la clase",
    )

    incident_notes = fields.Text(
        string="Observaciones de Bitácora",
        tracking=True,
        help="Descripción detallada de la novedad o incidente (R21)",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # CUMPLIMIENTO
    # ═══════════════════════════════════════════════════════════════════════════

    compliance_ids = fields.One2many(
        comodel_name="benglish.student.compliance",
        inverse_name="class_execution_id",
        string="Cumplimientos Generados",
        readonly=True,
        help="Registros de cumplimiento académico generados al cerrar esta clase",
    )

    compliance_count = fields.Integer(
        string="Cumplimientos",
        compute="_compute_compliance_count",
        store=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RESTRICCIONES SQL (R19: no duplicar por sesión y fecha)
    # ═══════════════════════════════════════════════════════════════════════════

    _sql_constraints = [
        (
            "unique_session_date",
            "UNIQUE(session_id, execution_date)",
            "Ya existe una clase ejecutada para esta sesión en esta fecha. "
            "No se permite más de una clase ejecutada por sesión y fecha (R19).",
        ),
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # CAMPOS COMPUTADOS
    # ═══════════════════════════════════════════════════════════════════════════

    @api.depends("session_id", "execution_date", "execution_state")
    def _compute_display_name(self):
        state_labels = dict(self._fields["execution_state"].selection)
        for rec in self:
            parts = []
            if rec.code and rec.code != "/":
                parts.append(rec.code)
            if rec.session_id:
                parts.append(rec.session_id.display_name or str(rec.session_id.id))
            if rec.execution_date:
                parts.append(str(rec.execution_date))
            if rec.execution_state:
                parts.append(f"[{state_labels.get(rec.execution_state, '')}]")
            rec.display_name = " / ".join(parts) if parts else _("Clase Ejecutada")

    @api.depends("attendance_ids", "attendance_ids.attendance_state")
    def _compute_attendance_stats(self):
        for rec in self:
            attendances = rec.attendance_ids
            rec.total_students = len(attendances)
            rec.present_count = len(attendances.filtered(lambda a: a.attendance_state == "present"))
            rec.absent_count = len(attendances.filtered(lambda a: a.attendance_state == "absent"))

    @api.depends("compliance_ids")
    def _compute_compliance_count(self):
        for rec in self:
            rec.compliance_count = len(rec.compliance_ids)

    # ═══════════════════════════════════════════════════════════════════════════
    # CREACIÓN
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_next_reusable_execution_code(self):
        """
        Obtiene el próximo código de ejecución reutilizando huecos si existen.
        """
        import re
        prefix = "EXEC-"
        padding = 5
        
        existing = self.sudo().search([('code', '=like', f'{prefix}%')])
        used_numbers = set()
        
        for record in existing:
            if record.code:
                match = re.match(r'^EXEC-(\d+)$', record.code)
                if match:
                    used_numbers.add(int(match.group(1)))
        
        if used_numbers:
            for num in range(1, max(used_numbers) + 2):
                if num not in used_numbers:
                    return f"{prefix}{num:0{padding}d}"
        
        return f"{prefix}00001"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", "/") == "/":
                vals["code"] = self._get_next_reusable_execution_code()
        return super().create(vals_list)

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTODOS DE NEGOCIO
    # ═══════════════════════════════════════════════════════════════════════════

    def action_populate_attendance(self):
        """
        Crea registros de asistencia para todos los estudiantes
        inscritos en la sesión.
        """
        self.ensure_one()
        if not self.session_id:
            return

        Attendance = self.env["benglish.class.execution.attendance"]
        enrollments = self.env["benglish.session.enrollment"].search([
            ("session_id", "=", self.session_id.id),
            ("state", "in", ["pending", "confirmed"]),
        ])

        created = 0
        for enroll in enrollments:
            existing = Attendance.search([
                ("execution_id", "=", self.id),
                ("student_id", "=", enroll.student_id.id),
            ], limit=1)
            if not existing:
                Attendance.create({
                    "execution_id": self.id,
                    "student_id": enroll.student_id.id,
                    "session_enrollment_id": enroll.id,
                    "attendance_state": "present",
                })
                created += 1

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Asistencia Poblada"),
                "message": _("Se crearon %d registros de asistencia.") % created,
                "type": "success",
                "sticky": False,
            },
        }

    def action_close_execution(self):
        """
        Cierra la clase ejecutada y genera cumplimiento académico (R22-R24).
        Solo para clases dictadas con asistencia registrada.
        """
        self.ensure_one()
        if self.is_closed:
            return

        if self.execution_state != "taught":
            _logger.info(
                "Clase %s no fue dictada (estado: %s), no genera cumplimiento.",
                self.code,
                self.execution_state,
            )
            self.write({"is_closed": True})
            return

        # Generar cumplimiento para cada estudiante presente
        Compliance = self.env["benglish.student.compliance"]
        RequirementStatus = self.env["benglish.student.requirement.status"]

        present_attendances = self.attendance_ids.filtered(
            lambda a: a.attendance_state == "present"
        )

        for att in present_attendances:
            student = att.student_id
            # Buscar matrícula activa del estudiante
            enrollment = self.env["benglish.enrollment"].search([
                ("student_id", "=", student.id),
                ("state", "in", ["active", "enrolled", "in_progress"]),
            ], limit=1)

            if not enrollment:
                continue

            # Buscar estado de requisito que coincida con la asignatura de la sesión
            subject = self.subject_id
            if not subject:
                continue

            # Buscar requisitos pendientes que coincidan
            req_statuses = RequirementStatus.search([
                ("enrollment_id", "=", enrollment.id),
                ("state", "in", ["pending", "in_progress"]),
                "|",
                ("subject_id", "=", subject.id),
                "&",
                ("requirement_type", "=", "electives"),
                ("subject_id", "=", False),
            ])

            for req_status in req_statuses:
                try:
                    Compliance.register_compliance(
                        student=student,
                        enrollment=enrollment,
                        requirement_status=req_status,
                        subject=subject,
                        class_execution=self,
                        session=self.session_id,
                    )
                except Exception as e:
                    _logger.warning(
                        "Error registrando cumplimiento para %s: %s",
                        student.name,
                        str(e),
                    )

        self.write({"is_closed": True})
        self.message_post(
            body=_("Clase cerrada. Se generaron %d cumplimientos académicos.")
            % len(self.compliance_ids),
            subject=_("Clase Ejecutada Cerrada"),
        )

    def action_reopen(self):
        """Reabre una clase ejecutada (solo si no tiene cumplimientos)."""
        self.ensure_one()
        if self.compliance_ids:
            raise ValidationError(
                _("No se puede reabrir una clase que ya generó cumplimientos académicos.\n\n"
                  "Cumplimientos registrados: %d") % len(self.compliance_ids)
            )
        self.write({"is_closed": False})


class ClassExecutionAttendance(models.Model):
    """
    Asistencia en Clase Ejecutada.

    Registra la presencia/ausencia de cada estudiante en una clase ejecutada.

    Equivalencia con el modelo de datos:
    - Tabla: Asistencia
    - Campos: Id_Clase_Ejecutada, Id_Estudiante, Estado

    Regla implementada:
    - R20: Asistencia registrada contra clase ejecutada
    """

    _name = "benglish.class.execution.attendance"
    _description = "Asistencia en Clase Ejecutada"
    _order = "execution_id, student_id"
    _rec_name = "display_name"

    # ═══════════════════════════════════════════════════════════════════════════
    # RELACIONES
    # ═══════════════════════════════════════════════════════════════════════════

    execution_id = fields.Many2one(
        comodel_name="benglish.class.execution",
        string="Clase Ejecutada",
        required=True,
        ondelete="cascade",
        index=True,
    )

    student_id = fields.Many2one(
        comodel_name="benglish.student",
        string="Estudiante",
        required=True,
        ondelete="cascade",
        index=True,
    )

    session_enrollment_id = fields.Many2one(
        comodel_name="benglish.session.enrollment",
        string="Inscripción",
        ondelete="set null",
        help="Inscripción del estudiante en la sesión (referencia cruzada)",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # ESTADO DE ASISTENCIA
    # ═══════════════════════════════════════════════════════════════════════════

    attendance_state = fields.Selection(
        selection=[
            ("present", "Presente"),
            ("absent", "Ausente"),
        ],
        string="Asistencia",
        required=True,
        default="present",
        help="Indica si el estudiante asistió o no a la clase",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # INFORMACIÓN ADICIONAL
    # ═══════════════════════════════════════════════════════════════════════════

    notes = fields.Text(
        string="Observaciones",
        help="Notas sobre la asistencia del estudiante",
    )

    display_name = fields.Char(
        string="Nombre",
        compute="_compute_display_name",
        store=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RESTRICCIONES
    # ═══════════════════════════════════════════════════════════════════════════

    _sql_constraints = [
        (
            "unique_execution_student",
            "UNIQUE(execution_id, student_id)",
            "Solo puede existir un registro de asistencia por estudiante por clase ejecutada.",
        ),
    ]

    @api.depends("student_id", "attendance_state")
    def _compute_display_name(self):
        state_labels = dict(self._fields["attendance_state"].selection)
        for rec in self:
            if rec.student_id:
                rec.display_name = f"{rec.student_id.name} [{state_labels.get(rec.attendance_state, '')}]"
            else:
                rec.display_name = _("Asistencia")
