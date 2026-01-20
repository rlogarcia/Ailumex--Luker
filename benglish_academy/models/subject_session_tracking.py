# -*- coding: utf-8 -*-
"""
Modelo de Tracking de Asistencia por Sesión
Registra la asistencia y calificaciones de cada sesión del estudiante
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SubjectSessionTracking(models.Model):
    """
    Tracking de asistencia y notas por sesión del estudiante.

    CONCEPTO:
    - Se crea automáticamente una fila por cada asignatura del plan del estudiante
    - El docente desde el portal registra: asistencia, calificación y observaciones
    - Permite trazabilidad de qué sesión tomó el estudiante
    """

    _name = "benglish.subject.session.tracking"
    _description = "Tracking de Asistencia y Notas"
    _order = "student_id, phase_id, subject_id"
    _rec_name = "display_name"

    display_name = fields.Char(
        string="Nombre",
        compute="_compute_display_name",
        store=True,
    )

    # RELACIONES PRINCIPALES
    student_id = fields.Many2one(
        comodel_name="benglish.student",
        string="Estudiante",
        required=True,
        ondelete="cascade",
        index=True,
    )

    subject_id = fields.Many2one(
        comodel_name="benglish.subject",
        string="Asignatura",
        required=True,
        ondelete="restrict",
        index=True,
    )

    # JERARQUÍA ACADÉMICA (para filtrar por fase)
    phase_id = fields.Many2one(
        comodel_name="benglish.phase",
        string="Fase",
        compute="_compute_hierarchy",
        store=True,
        index=True,
        readonly=False,
    )

    level_id = fields.Many2one(
        comodel_name="benglish.level",
        string="Nivel",
        compute="_compute_hierarchy",
        store=True,
        readonly=False,
    )

    # INFORMACIÓN DE LA SESIÓN TOMADA
    session_id = fields.Many2one(
        comodel_name="benglish.academic.session",
        string="Sesión",
        help="Sesión específica a la que asistió el estudiante",
        ondelete="set null",
    )

    session_code = fields.Char(
        string="Código Sesión",
        related="session_id.session_code",
        store=True,
        readonly=True,
        help="Identificador único de la sesión tomada desde el horario",
    )

    # ESTADO Y ASISTENCIA
    state = fields.Selection(
        selection=[
            ("pending", "Pendiente"),
            ("registered", "Registrado"),
        ],
        string="Estado",
        default="pending",
        required=True,
        help="Pendiente: No se ha registrado asistencia | Registrado: Ya tiene datos",
    )

    attended = fields.Boolean(
        string="Asistió",
        default=False,
        help="Indica si el estudiante asistió a la sesión",
    )

    # CALIFICACIÓN Y DOCENTE
    grade = fields.Float(
        string="Calificación",
        digits=(5, 2),
        help="Calificación obtenida en la sesión (0-100)",
    )

    teacher_id = fields.Many2one(
        comodel_name="benglish.coach",
        string="Docente",
        help="Docente que impartió la sesión",
        ondelete="set null",
    )

    # OBSERVACIONES
    notes = fields.Text(
        string="Observaciones",
        help="Anotaciones del docente sobre la sesión",
    )

    _sql_constraints = [
        (
            "unique_student_subject",
            "UNIQUE(student_id, subject_id)",
            "Ya existe un registro de tracking para esta asignatura y estudiante.",
        ),
    ]

    @api.depends("student_id", "subject_id")
    def _compute_display_name(self):
        for record in self:
            if record.student_id and record.subject_id:
                record.display_name = (
                    f"{record.student_id.name} - {record.subject_id.name}"
                )
            else:
                record.display_name = "Tracking de Sesión"

    @api.depends("subject_id", "subject_id.phase_id", "subject_id.level_id")
    def _compute_hierarchy(self):
        """Computa la jerarquía académica desde la asignatura"""
        for record in self:
            record.phase_id = (
                record.subject_id.phase_id.id if record.subject_id else False
            )
            record.level_id = (
                record.subject_id.level_id.id if record.subject_id else False
            )

    @api.onchange("attended", "grade", "teacher_id", "notes", "session_id")
    def _onchange_session_data(self):
        """Cuando se registra algún dato, cambiar estado a 'registered'"""
        for record in self:
            if (
                record.attended
                or record.grade
                or record.teacher_id
                or record.notes
                or record.session_id
            ):
                record.state = "registered"

    def write(self, vals):
        """
        Override write para sincronizar con historial académico.
        Cuando se actualiza attended, grade o notes, se sincroniza con academic_history.
        """
        result = super(SubjectSessionTracking, self).write(vals)

        # Si se actualizó asistencia, nota o observaciones, sincronizar con historial
        # PERO solo si no viene del contexto de enrollment (evitar sobrescribir)
        if any(key in vals for key in ["attended", "grade", "notes", "session_id"]):
            if not self.env.context.get('skip_history_sync'):
                for record in self:
                    record._sync_to_academic_history()

        return result

    def _sync_to_academic_history(self):
        """
        Sincroniza datos de tracking con el historial académico.

        FLUJO:
        1. El docente marca asistencia/nota/observaciones en subject.session.tracking
        2. Se sincroniza automáticamente con academic.history
        3. El historial académico queda actualizado para el portal del estudiante
        """
        self.ensure_one()

        import logging

        _logger = logging.getLogger(__name__)

        # Solo sincronizar si hay una sesión asociada
        if not self.session_id:
            _logger.info(
                f"[TRACKING→HISTORY] No hay sesión asociada para tracking {self.id}, no se sincroniza"
            )
            return False

        session = self.session_id
        student = self.student_id

        # Verificar que la sesión esté al menos iniciada
        if session.state not in ["started", "done"]:
            _logger.warning(
                f"[TRACKING→HISTORY] Sesión {session.id} en estado '{session.state}', "
                f"no se puede sincronizar (debe estar 'started' o 'done')"
            )
            return False

        History = self.env["benglish.academic.history"].sudo()

        # Buscar historial existente para esta sesión y estudiante
        existing_history = History.search(
            [
                ("student_id", "=", student.id),
                ("session_id", "=", session.id),
            ],
            limit=1,
        )

        # Determinar estado de asistencia
        attendance_status = "attended" if self.attended else "pending"

        if existing_history:
            # Actualizar historial existente
            update_vals = {
                "grade": self.grade if self.grade else 0.0,
                "notes": self.notes or "",
            }
            
            # IMPORTANTE: Solo actualizar attendance_status si NO está ya marcada como attended/absent
            # Esto permite que el sistema de Portal Coach tenga prioridad
            if existing_history.attendance_status == 'pending':
                update_vals["attendance_status"] = attendance_status

            # Solo actualizar si cambió algo
            should_update = False
            if existing_history.attendance_status == 'pending' and existing_history.attendance_status != attendance_status:
                should_update = True
            if existing_history.grade != (self.grade or 0.0):
                should_update = True
            if existing_history.notes != (self.notes or ""):
                should_update = True
                
            if should_update:
                existing_history.write(update_vals)
                _logger.info(
                    f"✅ [TRACKING→HISTORY] Historial ID {existing_history.id} actualizado - "
                    f"Estudiante: {student.name}, Sesión: {session.id}, "
                    f"Attended: {self.attended}, Grade: {self.grade}"
                )
        else:
            # Crear nuevo registro de historial
            history_vals = {
                "student_id": student.id,
                "session_id": session.id,
                "session_date": session.date,
                "session_time_start": session.time_start,
                "session_time_end": session.time_end,
                "program_id": session.program_id.id,
                "plan_id": student.plan_id.id if student.plan_id else False,
                "phase_id": self.phase_id.id if self.phase_id else False,
                "level_id": self.level_id.id if self.level_id else False,
                "subject_id": self.subject_id.id,
                "campus_id": session.campus_id.id if session.campus_id else False,
                "teacher_id": session.teacher_id.id if session.teacher_id else False,
                "delivery_mode": session.delivery_mode,
                "attendance_status": attendance_status,
                "grade": self.grade if self.grade else 0.0,
                "notes": self.notes or "",
                "attendance_registered_at": fields.Datetime.now(),
                "attendance_registered_by_id": self.env.user.id,
            }

            try:
                new_history = History.create(history_vals)
                _logger.info(
                    f"✅ [TRACKING→HISTORY] Historial ID {new_history.id} creado - "
                    f"Estudiante: {student.name}, Sesión: {session.id}, "
                    f"Attended: {self.attended}, Grade: {self.grade}"
                )
            except Exception as e:
                _logger.error(
                    f"❌ [TRACKING→HISTORY] Error creando historial: {str(e)} - "
                    f"Tracking {self.id}, Session {session.id}, Student {student.id}"
                )
                return False

        return True

    @api.model
    def create_tracking_for_student(self, student_id):
        """
        Crea registros de tracking para las asignaturas del plan del estudiante.
        Usa student.subject_ids que ya filtra por programa/plan/fases.
        """
        student = self.env["benglish.student"].browse(student_id)
        if not student.plan_id:
            return self.browse()

        # Usar subject_ids del estudiante (ya filtrado por programa/plan)
        subjects = student.subject_ids

        tracking_records = self.browse()
        for subject in subjects:
            # Verificar si ya existe
            existing = self.search(
                [
                    ("student_id", "=", student.id),
                    ("subject_id", "=", subject.id),
                ],
                limit=1,
            )

            if not existing:
                tracking_records |= self.create(
                    {
                        "student_id": student.id,
                        "subject_id": subject.id,
                        "phase_id": subject.phase_id.id,
                        "level_id": subject.level_id.id,
                        "state": "pending",
                    }
                )

        return tracking_records
