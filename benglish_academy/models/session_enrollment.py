# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class SessionEnrollment(models.Model):
    """
    Modelo para gestionar la inscripción de estudiantes en sesiones académicas.
    Representa la relación Many2many entre sesiones y estudiantes.
    """

    _name = "benglish.session.enrollment"
    _description = "Inscripción de Estudiante en Sesión"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "session_id, enrollment_date desc, student_id"
    _rec_name = "display_name"

    # RELACIONES PRINCIPALES

    session_id = fields.Many2one(
        comodel_name="benglish.academic.session",
        string="Sesión",
        required=True,
        ondelete="cascade",
        tracking=True,
        index=True,
        help="Sesión de clase a la que se inscribe el estudiante",
    )

    student_id = fields.Many2one(
        comodel_name="benglish.student",
        string="Estudiante",
        required=True,
        ondelete="cascade",
        tracking=True,
        index=True,
        help="Estudiante inscrito en la sesión",
    )

    # INFORMACIÓN DE INSCRIPCIÓN

    enrollment_date = fields.Datetime(
        string="Fecha de Inscripción",
        default=fields.Datetime.now,
        required=True,
        readonly=True,
        tracking=True,
        help="Fecha y hora en que se realizó la inscripción",
    )

    enrolled_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Inscrito por",
        default=lambda self: self.env.user,
        readonly=True,
        help="Usuario que realizó la inscripción",
    )

    state = fields.Selection(
        selection=[
            ("pending", "Pendiente"),
            ("confirmed", "Confirmada"),
            ("attended", "Asistió"),
            ("absent", "Ausente"),
            ("cancelled", "Cancelada"),
        ],
        string="Estado",
        default="pending",
        required=True,
        tracking=True,
        help="Estado de la inscripción",
    )

    notes = fields.Text(
        string="Notas",
        help="Observaciones sobre la inscripción",
    )

    # Modalidad del estudiante (para sesiones híbridas)
    student_delivery_mode = fields.Selection(
        selection=[
            ("presential", "Presencial"),
            ("virtual", "Virtual"),
        ],
        string="Modalidad del Estudiante",
        help="Modalidad elegida por el estudiante en sesiones híbridas (presencial o virtual)",
    )

    # CAMPOS RELACIONADOS (PARA BÚSQUEDAS)

    # Datos de la sesión
    session_date = fields.Date(
        string="Fecha de Sesión",
        related="session_id.date",
        store=True,
        readonly=True,
    )

    session_time_start = fields.Float(
        string="Hora de Inicio",
        related="session_id.time_start",
        store=True,
        readonly=True,
    )

    session_state = fields.Selection(
        string="Estado de Sesión",
        related="session_id.state",
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

    effective_subject_id = fields.Many2one(
        comodel_name="benglish.subject",
        string="Asignatura Efectiva",
        ondelete="cascade",
        help="Asignatura real contabilizada para este estudiante en esta sesión.",
    )

    effective_unit_number = fields.Integer(
        string="Unidad Efectiva",
        help="Unidad efectiva asignada para auditoría.",
    )

    program_id = fields.Many2one(
        comodel_name="benglish.program",
        string="Programa",
        related="session_id.program_id",
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

    # Datos del estudiante
    student_name = fields.Char(
        string="Nombre Estudiante",
        related="student_id.name",
        store=True,
        readonly=True,
    )

    student_email = fields.Char(
        string="Email Estudiante",
        related="student_id.email",
        store=True,
        readonly=True,
    )

    student_alias = fields.Char(
        string="Alias Estudiante",
        related="session_id.student_alias",
        store=True,
        readonly=True,
        help="Alias visible para el estudiante.",
    )

    # CAMPOS COMPUTADOS

    display_name = fields.Char(
        string="Nombre a Mostrar",
        compute="_compute_display_name",
        store=True,
        help="Nombre completo para visualización",
    )

    can_confirm = fields.Boolean(
        string="Puede Confirmar",
        compute="_compute_can_actions",
        help="Indica si se puede confirmar la inscripción",
    )

    can_cancel = fields.Boolean(
        string="Puede Cancelar",
        compute="_compute_can_actions",
        help="Indica si se puede cancelar la inscripción",
    )

    # RESTRICCIONES SQL

    _sql_constraints = [
        (
            "unique_enrollment",
            "UNIQUE(session_id, student_id) WHERE state != 'cancelled'",
            "El estudiante ya está inscrito en esta sesión.",
        ),
    ]

    # COMPUTED FIELDS

    @api.depends("student_id.name", "session_id.display_name", "state")
    def _compute_display_name(self):
        """Genera nombre para visualización."""
        for record in self:
            if record.student_id and record.session_id:
                state_label = dict(record._fields["state"].selection).get(
                    record.state, ""
                )
                record.display_name = (
                    f"{record.student_id.name} → "
                    f"{record.session_id.subject_id.code if record.session_id.subject_id else 'Sesión'} "
                    f"[{state_label}]"
                )
            else:
                record.display_name = "Nueva Inscripción"

    @api.depends("state", "session_id.state")
    def _compute_can_actions(self):
        """Determina qué acciones están disponibles."""
        for record in self:
            # Puede confirmar si está pendiente y la sesión está publicada/activa
            record.can_confirm = (
                record.state == "pending"
                and record.session_id.state in ["active", "with_enrollment"]
            )

            # Puede cancelar si NO está cancelada ni ha asistido
            record.can_cancel = record.state not in ["cancelled", "attended"]

    # VALIDACIONES

    @api.constrains("session_id", "student_id")
    def _check_unique_enrollment(self):
        """Valida que no exista inscripción duplicada activa."""
        for record in self:
            if record.state != "cancelled":
                existing = self.search(
                    [
                        ("id", "!=", record.id),
                        ("session_id", "=", record.session_id.id),
                        ("student_id", "=", record.student_id.id),
                        ("state", "!=", "cancelled"),
                    ]
                )
                if existing:
                    raise ValidationError(
                        _(
                            "El estudiante '%(student)s' ya está inscrito en esta sesión."
                        )
                        % {"student": record.student_id.name}
                    )

    @api.constrains("session_id")
    def _check_session_capacity(self):
        """Valida que la sesión tenga capacidad disponible."""
        for record in self:
            if record.state == "confirmed":
                session = record.session_id

                # Contar inscripciones confirmadas (excluyendo la actual si ya está confirmada)
                confirmed_count = self.search_count(
                    [
                        ("session_id", "=", session.id),
                        ("state", "=", "confirmed"),
                        ("id", "!=", record.id),
                    ]
                )

                if confirmed_count >= session.max_capacity:
                    raise ValidationError(
                        _(
                            "No hay cupos disponibles en esta sesión.\n"
                            "Capacidad: %(capacity)s\n"
                            "Inscritos: %(enrolled)s"
                        )
                        % {
                            "capacity": session.max_capacity,
                            "enrolled": confirmed_count,
                        }
                    )

    @api.constrains("session_id")
    def _check_session_state(self):
        """Valida que la sesión esté en estado válido para inscripciones."""
        for record in self:
            if record.state in ["pending", "confirmed"]:
                if record.session_id.state not in [
                    "draft",
                    "active",
                    "with_enrollment",
                ]:
                    raise ValidationError(
                        _(
                            "No se pueden crear inscripciones en sesiones en estado '%(state)s'."
                        )
                        % {
                            "state": dict(
                                record.session_id._fields["state"].selection
                            ).get(record.session_id.state)
                        }
                    )

    # CRUD OVERRIDES

    @api.model_create_multi
    def create(self, vals_list):
        """
        Validaciones al crear inscripción.
        
        NUEVO: Maneja pools de electivas - asigna automáticamente la asignatura efectiva
        desde el pool según las unidades de audiencia de la sesión.
        """
        import logging
        _logger = logging.getLogger(__name__)
        
        # Preprocesar vals_list para asignar effective_subject_id en sesiones con pool de electivas
        for vals in vals_list:
            session_id = vals.get('session_id')
            if session_id:
                session = self.env['benglish.academic.session'].browse(session_id)
                
                # Si la sesión tiene pool de electivas configurado
                if session.elective_pool_id and session.elective_pool_id.subject_ids:
                    _logger.info(
                        f"🟢 [ELECTIVE-POOL] Sesión {session.id} tiene pool de electivas: "
                        f"{session.elective_pool_id.name} con {len(session.elective_pool_id.subject_ids)} asignaturas"
                    )
                    
                    # Obtener el estudiante para determinar su nivel actual
                    student_id = vals.get('student_id')
                    student = self.env['benglish.student'].browse(student_id) if student_id else None
                    
                    # Obtener el rango de unidades de audiencia de la sesión
                    unit_from = session.audience_unit_from or 0
                    unit_to = session.audience_unit_to or 0
                    
                    _logger.info(
                        f"📊 [ELECTIVE-POOL] Rango de unidades: {unit_from} - {unit_to}, "
                        f"Estudiante: {student.name if student else 'N/A'}"
                    )
                    
                    # Asignar asignatura efectiva basada en el nivel del estudiante
                    if not vals.get('effective_subject_id'):
                        effective_subject = None
                        
                        # OPCIÓN 1: Si el estudiante tiene nivel actual definido
                        if student and student.current_level_id:
                            # Filtrar asignaturas del pool que son del nivel del estudiante
                            pool_subjects_same_level = session.elective_pool_id.subject_ids.filtered(
                                lambda s: s.level_id == student.current_level_id
                            )
                            
                            _logger.info(
                                f"📚 [ELECTIVE-POOL] Asignaturas del pool para nivel {student.current_level_id.name}: "
                                f"{[(s.code, s.name) for s in pool_subjects_same_level]}"
                            )
                            
                            if pool_subjects_same_level:
                                # Buscar cuáles YA completó el estudiante
                                History = self.env['benglish.academic.history'].sudo()
                                completed_subject_ids = History.search([
                                    ('student_id', '=', student.id),
                                    ('subject_id', 'in', pool_subjects_same_level.ids),
                                    ('attendance_status', '=', 'attended')
                                ]).mapped('subject_id').ids
                                
                                _logger.info(
                                    f"✅ [ELECTIVE-POOL] Asignaturas del pool ya completadas: {completed_subject_ids}"
                                )
                                
                                # Filtrar asignaturas NO completadas del pool
                                pending_pool_subjects = pool_subjects_same_level.filtered(
                                    lambda s: s.id not in completed_subject_ids
                                )
                                
                                if pending_pool_subjects:
                                    # Ordenar por secuencia/código y tomar la primera pendiente
                                    effective_subject = pending_pool_subjects.sorted(
                                        key=lambda s: (s.sequence or 0, s.code or '')
                                    )[0]
                                    _logger.info(
                                        f"🎯 [ELECTIVE-POOL] Asignatura pendiente asignada: "
                                        f"{effective_subject.code} - {effective_subject.name} (ID: {effective_subject.id})"
                                    )
                                else:
                                    # Todas completadas, usar la primera como fallback
                                    effective_subject = pool_subjects_same_level.sorted(
                                        key=lambda s: (s.sequence or 0, s.code or '')
                                    )[0]
                                    _logger.warning(
                                        f"⚠️ [ELECTIVE-POOL] Todas las asignaturas del nivel completadas. "
                                        f"Usando primera como fallback: {effective_subject.name}"
                                    )
                        
                        # OPCIÓN 2: Si no se encontró por nivel, usar la primera del pool
                        if not effective_subject and session.elective_pool_id.subject_ids:
                            effective_subject = session.elective_pool_id.subject_ids[0]
                            _logger.warning(
                                f"⚠️ [ELECTIVE-POOL] No se encontró asignatura para el nivel del estudiante. "
                                f"Usando primera del pool: {effective_subject.name}"
                            )
                        
                        if effective_subject:
                            vals['effective_subject_id'] = effective_subject.id
                            vals['effective_unit_number'] = unit_to  # Usar la unidad final como referencia
                            
                            _logger.info(
                                f"✅ [ELECTIVE-POOL] Asignada asignatura efectiva: {effective_subject.name} "
                                f"(ID: {effective_subject.id}) para unidad {unit_to}"
                            )
                else:
                    # Si NO tiene pool de electivas, la asignatura efectiva es la misma de la sesión
                    if not vals.get('effective_subject_id') and session.subject_id:
                        vals['effective_subject_id'] = session.subject_id.id
                        _logger.info(
                            f"📝 [STANDARD-SESSION] Asignada asignatura efectiva desde sesión: "
                            f"{session.subject_id.name} (ID: {session.subject_id.id})"
                        )
        
        enrollments = super(SessionEnrollment, self).create(vals_list)

        for enrollment in enrollments:
            # Registrar en el chatter de la sesión
            subject_info = ""
            if enrollment.effective_subject_id and enrollment.effective_subject_id != enrollment.subject_id:
                subject_info = f" (Asignatura efectiva: {enrollment.effective_subject_id.name})"
            
            enrollment.session_id.message_post(
                body=_("Estudiante inscrito: %(student)s [%(state)s]%(subject)s")
                % {
                    "student": enrollment.student_id.name,
                    "state": dict(enrollment._fields["state"].selection).get(
                        enrollment.state
                    ),
                    "subject": subject_info,
                },
                subject=_("Nueva Inscripción"),
            )

        return enrollments

    def write(self, vals):
        """
        Notifica cambios importantes.
        
        NUEVO: Sincroniza automáticamente con el historial académico
        cuando se marca asistencia (attended/absent).
        """
        import logging
        _logger = logging.getLogger(__name__)
        
        result = super(SessionEnrollment, self).write(vals)

        if "state" in vals:
            for record in self:
                state_label = dict(record._fields["state"].selection).get(record.state)
                record.session_id.message_post(
                    body=_("Estado de inscripción actualizado: %(student)s → %(state)s")
                    % {
                        "student": record.student_id.name,
                        "state": state_label,
                    },
                )
                
                # ⭐ NUEVO: Sincronización automática con historial académico
                # Solo si el estado cambia a 'attended' o 'absent'
                if vals['state'] in ['attended', 'absent']:
                    _logger.info(
                        f"🔵 [SYNC-DEBUG] Enrollment {record.id}: Detectado cambio a '{vals['state']}'. "
                        f"Estudiante: {record.student_id.name}, Sesión: {record.session_id.id}, "
                        f"Estado sesión: {record.session_id.state}"
                    )
                    # Verificar que la sesión esté en estado válido
                    if record.session_id.state in ['active', 'started', 'done']:
                        _logger.info(
                            f"🟢 [SYNC-START] Iniciando sincronización: Enrollment {record.id}"
                        )
                        try:
                            record._sync_to_academic_history()
                            _logger.info(
                                f"✅ [SYNC-SUCCESS] Sincronización completada: Enrollment {record.id}"
                            )
                        except Exception as e:
                            _logger.error(
                                f"❌ [SYNC-ERROR] Error sincronizando enrollment {record.id}: {str(e)}",
                                exc_info=True
                            )
                            # No lanzar excepción para no bloquear el flujo principal
                    else:
                        _logger.warning(
                            f"⚠️ [SYNC-SKIP] No se sincroniza enrollment {record.id}: "
                            f"sesión {record.session_id.id} en estado '{record.session_id.state}' "
                            f"(debe estar 'active', 'started' o 'done')"
                        )

        return result

    def unlink(self):
        """Registra eliminación en el chatter."""
        for record in self:
            session = record.session_id
            student_name = record.student_id.name

            result = super(SessionEnrollment, record).unlink()

            if session.exists():
                session.message_post(
                    body=_("Inscripción eliminada: %(student)s")
                    % {"student": student_name},
                    subject=_("Inscripción Eliminada"),
                )

        return True

    # TRANSICIONES DE ESTADO

    def _ensure_effective_subject(self, raise_on_error=True):
        self.ensure_one()
        if self.effective_subject_id:
            return self.effective_subject_id
        subject = self.session_id.resolve_effective_subject(
            self.student_id,
            check_completed=False,
            raise_on_error=raise_on_error,
        ) or self.session_id.subject_id
        if subject:
            unit_number = subject.unit_number or subject.unit_block_end or 0
            self.write(
                {
                    "effective_subject_id": subject.id,
                    "effective_unit_number": unit_number,
                }
            )
        return subject

    def action_confirm(self):
        """Confirma la inscripción."""
        for record in self:
            if record.state != "pending":
                raise UserError(_("Solo se pueden confirmar inscripciones pendientes."))

            if not record.session_id.can_enroll_student():
                raise UserError(
                    _("No se puede confirmar: la sesión no acepta más inscripciones.")
                )

            effective_subject = record.session_id.resolve_effective_subject(
                record.student_id,
                check_completed=True,
                raise_on_error=True,
            ) or record.session_id.subject_id

            if effective_subject:
                record.write(
                    {
                        "effective_subject_id": effective_subject.id,
                        "effective_unit_number": effective_subject.unit_number
                        or effective_subject.unit_block_end
                        or 0,
                    }
                )

            # Validar que el estudiante NO haya completado ya esta asignatura efectiva
            History = self.env["benglish.academic.history"].sudo()
            already_completed = History.search_count(
                [
                    ("student_id", "=", record.student_id.id),
                    ("subject_id", "=", effective_subject.id if effective_subject else record.session_id.subject_id.id),
                    ("attendance_status", "=", "attended"),
                ]
            )

            if already_completed > 0:
                raise UserError(
                    _(
                        "❌ No se puede confirmar la inscripción.\n\n"
                        "El estudiante %(student)s ya completó la asignatura '%(subject)s' anteriormente.\n\n"
                        "Un estudiante no puede ver la misma clase dos veces. "
                        "Verifica el historial académico del estudiante."
                    )
                    % {
                        "student": record.student_id.name,
                        "subject": (effective_subject.name if effective_subject else record.session_id.subject_id.name),
                    }
                )

            record.write({"state": "confirmed"})
            # Forzar persistencia inmediata en base de datos
            record.flush_recordset()
            record.message_post(
                body=_("Inscripción confirmada."),
                subject=_("Inscripción Confirmada"),
            )

            # Si la inscripción fue realizada desde el portal, y la sesión está publicada
            # en estado 'active', marcar la sesión como 'with_enrollment'
            try:
                if record.enrolled_by_id and record.enrolled_by_id.share:
                    session = record.session_id
                    if session.state == "active":
                        session.write({"state": "with_enrollment"})
                        session.message_post(
                            body=_(
                                "La sesión pasó a 'En horario' porque hay inscripciones desde el portal."
                            ),
                            subject=_("En horario"),
                        )
            except Exception:
                # No queremos romper la confirmación de la inscripción por un fallo en el cambio de estado
                pass

    def action_mark_attended(self):
        """
        Marca asistencia del estudiante.
        Automáticamente crea/actualiza registro en Historial Académico.
        """
        for record in self:
            if record.state not in ["confirmed"]:
                raise UserError(
                    _("Solo se puede marcar asistencia de inscripciones confirmadas.")
                )

            if record.session_id.state not in ["started", "done"]:
                raise UserError(
                    _(
                        "Solo se puede marcar asistencia en sesiones iniciadas o finalizadas."
                    )
                )

            record.write({"state": "attended"})
            # Forzar persistencia inmediata en base de datos
            record.flush_recordset()
            record.message_post(
                body=_("Asistencia registrada."),
                subject=_("Asistió"),
            )

            # Crear/actualizar historial académico automáticamente
            record._sync_to_academic_history()

    def action_mark_absent(self):
        """
        Marca ausencia del estudiante.
        Automáticamente crea/actualiza registro en Historial Académico.
        """
        for record in self:
            if record.state not in ["confirmed"]:
                raise UserError(
                    _("Solo se puede marcar ausencia de inscripciones confirmadas.")
                )

            if record.session_id.state not in ["started", "done"]:
                raise UserError(
                    _(
                        "Solo se puede marcar ausencia en sesiones iniciadas o finalizadas."
                    )
                )

            record.write({"state": "absent"})
            # Forzar persistencia inmediata en base de datos
            record.flush_recordset()
            record.message_post(
                body=_("Ausencia registrada."),
                subject=_("Ausente"),
            )

            # Crear/actualizar historial académico automáticamente
            record._sync_to_academic_history()

    def action_cancel(self):
        """Cancela la inscripción."""
        for record in self:
            if record.state in ["cancelled"]:
                raise UserError(_("La inscripción ya está cancelada."))

            if record.state == "attended":
                raise UserError(
                    _(
                        "No se puede cancelar una inscripción donde el estudiante ya asistió."
                    )
                )

            record.write({"state": "cancelled"})
            # Forzar persistencia inmediata en base de datos
            record.flush_recordset()
            record.message_post(
                body=_("Inscripción cancelada."),
                subject=_("Inscripción Cancelada"),
            )

    def action_reopen(self):
        """Reactiva una inscripción cancelada."""
        for record in self:
            if record.state != "cancelled":
                raise UserError(_("Solo se pueden reabrir inscripciones canceladas."))

            if not record.session_id.can_enroll_student():
                raise UserError(
                    _("No se puede reabrir: la sesión no acepta más inscripciones.")
                )

            record.write({"state": "pending"})
            # Forzar persistencia inmediata en base de datos
            record.flush_recordset()
            record.message_post(
                body=_("Inscripción reabierta."),
                subject=_("Inscripción Reabierta"),
            )

    # MÉTODOS DE VISTA

    def action_view_session(self):
        """Navega a la sesión."""
        self.ensure_one()
        return {
            "name": _("Sesión"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.academic.session",
            "res_id": self.session_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_student(self):
        """Navega al estudiante."""
        self.ensure_one()
        return {
            "name": _("Estudiante"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.student",
            "res_id": self.student_id.id,
            "view_mode": "form",
            "target": "current",
        }

    # ==========================================
    # SINCRONIZACIÓN CON HISTORIAL ACADÉMICO
    # ==========================================

    def _sync_to_academic_history(self):
        """
        Crea o actualiza el registro en el Historial Académico.
        Se ejecuta automáticamente cuando se marca asistencia/ausencia.

        IMPORTANTE: Solo se puede crear historial si la sesión está en estado 'done' (dictada)
        o si se está marcando asistencia/ausencia en sesiones iniciadas.
        """
        self.ensure_one()

        import logging

        _logger = logging.getLogger(__name__)

        History = self.env["benglish.academic.history"].sudo()
        session = self.session_id
        student = self.student_id
        effective_subject = self.effective_subject_id or self._ensure_effective_subject(
            raise_on_error=False
        )
        if not effective_subject:
            effective_subject = session.subject_id

        _logger.info(
            f"🔍 [SYNC-DETAIL] _sync_to_academic_history llamado: "
            f"Enrollment {self.id}, Student {student.name}, Session {session.id}, "
            f"State enrollment: {self.state}, State session: {session.state}"
        )

        # Verificar que la sesión tenga los datos necesarios
        if not session.date or not session.subject_id:
            _logger.error(
                f"❌ [SYNC-FAIL] No se puede crear historial para enrollment {self.id}: "
                f"sesión {session.id} sin fecha o asignatura. "
                f"Date: {session.date}, Subject: {session.subject_id}"
            )
            return False

        # VALIDACIÓN CRÍTICA: Solo crear historial si la sesión está iniciada o dictada
        if session.state not in ["active", "started", "done"]:
            _logger.error(
                f"❌ [SYNC-FAIL] No se puede crear historial para enrollment {self.id}: "
                f"sesión {session.id} en estado '{session.state}' (debe estar 'active', 'started' o 'done')"
            )
            return False

        # Buscar si ya existe un registro de historial para esta combinación
        existing_history = History.search(
            [
                ("student_id", "=", student.id),
                ("session_id", "=", session.id),
            ],
            limit=1,
        )

        if existing_history:
            _logger.info(
                f"🔄 [SYNC-UPDATE] Historial existente encontrado ID {existing_history.id}. Actualizando..."
            )
            # Si ya existe, solo actualizar campos de asistencia (permitidos)
            # Mapear el estado del enrollment al attendance_status del historial
            attendance_status_map = {
                "attended": "attended",
                "absent": "absent",
                "confirmed": "pending",
                "pending": "pending",
            }

            new_attendance_status = attendance_status_map.get(self.state, "pending")

            attendance_vals = {
                "attendance_status": new_attendance_status,
                "attended": (new_attendance_status == "attended"),  # ⭐ CRÍTICO: Sincronizar campo booleano
                "attendance_registered_at": fields.Datetime.now(),
                "attendance_registered_by_id": self.env.user.id,
                # ⭐ NO incluir 'grade' aquí - solo se agregará si existe en tracking
            }
            
            _logger.info(
                f"📝 [SYNC-VALUES] Valores de asistencia a actualizar: {attendance_vals}"
            )
            
            # ⭐ Sincronizar nota (grade) si existe en tracking
            # IMPORTANTE: El checklist de asistencia se marca SIEMPRE (arriba)
            # La nota es OPCIONAL y solo se sincroniza si existe
            Tracking = self.env['benglish.subject.session.tracking'].sudo()
            tracking = Tracking.search([
                ('student_id', '=', student.id),
                ('subject_id', '=', effective_subject.id if effective_subject else session.subject_id.id),
            ], limit=1)
            
            _logger.info(
                f"📊 [SYNC-TRACKING] Tracking encontrado: {tracking.id if tracking else 'No'}, "
                f"Tiene nota: {'Sí (' + str(tracking.grade) + ')' if tracking and tracking.grade else 'No'}"
            )
            
            if tracking and tracking.grade:
                attendance_vals['grade'] = tracking.grade
                attendance_vals['grade_registered_at'] = fields.Datetime.now()
                attendance_vals['grade_registered_by_id'] = self.env.user.id
                _logger.info(
                    f"📝 [SYNC-GRADE] Sincronizando nota al historial: Estudiante {student.name}, "
                    f"Asignatura {effective_subject.name if effective_subject else session.subject_id.name}, Nota: {tracking.grade}"
                )
            
            _logger.info(
                f"📦 [SYNC-FINAL-VALUES] Valores finales a escribir en historial: {attendance_vals}"
            )
            
            existing_history.write(attendance_vals)
            _logger.info(
                f"✅ Historial actualizado: Estudiante {student.name} (ID: {student.id}) "
                f"- Sesión {session.id} - Estado: {self.state} → Asistencia: {new_attendance_status} "
                f"- Nota: {attendance_vals.get('grade', 'Sin nota')}"
            )
        else:
            _logger.info(
                f"➕ [SYNC-CREATE] No existe historial. Creando nuevo registro..."
            )
            # Si no existe, crear nuevo registro con todos los datos
            # Mapear el estado del enrollment al attendance_status del historial
            attendance_status_map = {
                "attended": "attended",
                "absent": "absent",
                "confirmed": "pending",
                "pending": "pending",
            }

            new_attendance_status = attendance_status_map.get(self.state, "pending")

            history_vals = {
                "student_id": student.id,
                "session_id": session.id,
                "enrollment_id": self.id,
                "session_date": session.date,
                "session_time_start": session.time_start,
                "session_time_end": session.time_end,
                "program_id": session.program_id.id,
                "plan_id": student.plan_id.id if student.plan_id else False,
                "phase_id": (
                    student.current_phase_id.id if student.current_phase_id else False
                ),
                "level_id": (
                    student.current_level_id.id if student.current_level_id else False
                ),
                "subject_id": effective_subject.id if effective_subject else session.subject_id.id,
                "campus_id": session.campus_id.id if session.campus_id else False,
                "teacher_id": session.teacher_id.id if session.teacher_id else False,
                "delivery_mode": session.delivery_mode,
                "attendance_status": new_attendance_status,
                "attended": (new_attendance_status == "attended"),  # ⭐ CRÍTICO: Sincronizar campo booleano
                "attendance_registered_at": fields.Datetime.now(),
                "attendance_registered_by_id": self.env.user.id,
                # ⭐ NO incluir 'grade' aquí - solo se agregará si existe en tracking
            }
            
            _logger.info(
                f"📝 [SYNC-VALUES-NEW] Valores base para nuevo historial: attended={history_vals['attended']}, "
                f"attendance_status={history_vals['attendance_status']}"
            )
            
            # ⭐ Sincronizar nota (grade) si existe en tracking
            # IMPORTANTE: El historial se crea SIEMPRE (arriba con attended=True/False)
            # La nota es OPCIONAL y solo se agrega si existe
            Tracking = self.env['benglish.subject.session.tracking'].sudo()
            tracking = Tracking.search([
                ('student_id', '=', student.id),
                ('subject_id', '=', effective_subject.id if effective_subject else session.subject_id.id),
            ], limit=1)
            
            _logger.info(
                f"📊 [SYNC-TRACKING-NEW] Tracking encontrado: {tracking.id if tracking else 'No'}, "
                f"Tiene nota: {'Sí (' + str(tracking.grade) + ')' if tracking and tracking.grade else 'No'}"
            )
            
            if tracking and tracking.grade:
                history_vals['grade'] = tracking.grade
                history_vals['grade_registered_at'] = fields.Datetime.now()
                history_vals['grade_registered_by_id'] = self.env.user.id
                _logger.info(
                    f"📝 [SYNC-GRADE-NEW] Nueva nota en historial: Estudiante {student.name}, "
                    f"Asignatura {effective_subject.name if effective_subject else session.subject_id.name}, Nota: {tracking.grade}"
                )
            
            _logger.info(
                f"📦 [SYNC-FINAL-VALUES-NEW] Valores finales para crear historial: "
                f"attended={history_vals['attended']}, grade={history_vals.get('grade', 'Sin nota')}"
            )

            try:
                new_history = History.create(history_vals)
                _logger.info(
                    f"✅ [SYNC-CREATED] Historial creado exitosamente: ID {new_history.id} - "
                    f"Estudiante {student.name} (ID: {student.id}) - Sesión {session.id} - "
                    f"Attended: {new_history.attended}, Grade: {new_history.grade or 'Sin nota'}"
                )
            except Exception as e:
                _logger.error(
                    f"❌ Error creando historial: {str(e)} - "
                    f"Enrollment {self.id}, Session {session.id}, Student {student.id}"
                )
                return False

        # SINCRONIZAR TAMBIÉN CON SUBJECT SESSION TRACKING
        # ⭐ BUGFIX: Buscar por subject_id en lugar de session_id
        # El tracking se crea con subject_id, no con session_id asignado inicialmente
        Tracking = self.env['benglish.subject.session.tracking'].sudo()
        tracking = Tracking.search([
            ('student_id', '=', student.id),
            ('subject_id', '=', effective_subject.id if effective_subject else session.subject_id.id),
        ], limit=1)
        
        if tracking:
            # Actualizar el campo 'attended' basado en el estado del enrollment
            attended_value = (self.state == 'attended')
            
            # ⭐ TAMBIÉN actualizar session_id, state y otros datos relevantes
            update_vals = {
                'attended': attended_value,
                'state': 'registered',  # Cambiar a 'registered' cuando se marca asistencia
            }
            
            # Si no tiene session_id asignado, asignarlo ahora
            if not tracking.session_id:
                update_vals['session_id'] = session.id
            
            # Sincronizar nota si existe en historial (buscar el historial recién creado/actualizado)
            history = self.env['benglish.academic.history'].sudo().search([
                ('student_id', '=', student.id),
                ('session_id', '=', session.id),
            ], limit=1)
            if history and history.grade:
                update_vals['grade'] = history.grade
            
            # Usar sudo y context para evitar recursión infinita
            tracking.with_context(skip_history_sync=True).write(update_vals)
            _logger.info(
                f"✅ [TRACKING-SYNC] Tracking actualizado: ID {tracking.id} - "
                f"Estudiante {student.name} - attended={attended_value} - "
                f"session_id={session.id} - state=registered - grade={update_vals.get('grade', 'Sin nota')}"
            )
        else:
            _logger.warning(
                f"⚠️ [TRACKING-SYNC] No se encontró tracking para Estudiante {student.name} "
                f"y Asignatura {effective_subject.name if effective_subject else session.subject_id.name} "
                f"(ID: {(effective_subject.id if effective_subject else session.subject_id.id)})"
            )

        return True
