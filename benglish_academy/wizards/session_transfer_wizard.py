# -*- coding: utf-8 -*-

import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class SessionTransferWizard(models.TransientModel):
    _name = "benglish.session.transfer.wizard"
    _description = "Asistente de Traslado de Estudiantes"

    source_session_id = fields.Many2one(
        comodel_name="benglish.academic.session",
        string="Sesion Origen",
        required=True,
        readonly=True,
    )
    destination_session_id = fields.Many2one(
        comodel_name="benglish.academic.session",
        string="Sesion Destino",
        required=True,
    )
    destination_filter_campus_id = fields.Many2one(
        comodel_name="benglish.campus",
        string="Filtrar Sede",
    )
    destination_filter_teacher_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Filtrar Docente",
        domain="[('is_teacher', '=', True)]",
    )
    transfer_mode = fields.Selection(
        selection=[
            ("single", "Un estudiante"),
            ("all", "Todos los estudiantes"),
        ],
        string="Alcance",
        required=True,
        default="all",
    )
    student_id = fields.Many2one(
        comodel_name="benglish.student",
        string="Estudiante",
    )
    reason = fields.Text(string="Motivo (opcional)")

    validation_message = fields.Text(
        string="Validaciones",
        compute="_compute_validation_message",
        readonly=True,
    )
    can_transfer = fields.Boolean(
        compute="_compute_validation_message",
        readonly=True,
    )

    # Resumen de origen
    source_session_code = fields.Char(related="source_session_id.session_code", readonly=True)
    source_subject_id = fields.Many2one(related="source_session_id.subject_id", readonly=True)
    source_date = fields.Date(related="source_session_id.date", readonly=True)
    source_time_start_label = fields.Char(related="source_session_id.time_start_label", readonly=True)
    source_time_end_label = fields.Char(related="source_session_id.time_end_label", readonly=True)
    source_campus_id = fields.Many2one(related="source_session_id.campus_id", readonly=True)
    source_teacher_id = fields.Many2one(related="source_session_id.teacher_id", readonly=True)
    source_enrolled_count = fields.Integer(related="source_session_id.enrolled_count", readonly=True)

    # Resumen de destino
    destination_session_code = fields.Char(related="destination_session_id.session_code", readonly=True)
    destination_subject_id = fields.Many2one(related="destination_session_id.subject_id", readonly=True)
    destination_date = fields.Date(related="destination_session_id.date", readonly=True)
    destination_time_start_label = fields.Char(
        related="destination_session_id.time_start_label", readonly=True
    )
    destination_time_end_label = fields.Char(
        related="destination_session_id.time_end_label", readonly=True
    )
    destination_campus_id = fields.Many2one(related="destination_session_id.campus_id", readonly=True)
    destination_teacher_id = fields.Many2one(related="destination_session_id.teacher_id", readonly=True)
    destination_enrolled_count = fields.Integer(
        related="destination_session_id.enrolled_count", readonly=True
    )
    destination_available_spots = fields.Integer(
        related="destination_session_id.available_spots", readonly=True
    )
    destination_state = fields.Selection(related="destination_session_id.state", readonly=True)
    destination_is_published = fields.Boolean(related="destination_session_id.is_published", readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids") or []
        if not active_ids and self.env.context.get("active_id"):
            active_ids = [self.env.context.get("active_id")]
        if active_ids:
            if len(active_ids) > 1:
                raise UserError(_("Selecciona solo una sesion origen."))
            res["source_session_id"] = active_ids[0]
        return res

    @api.onchange("transfer_mode")
    def _onchange_transfer_mode(self):
        if self.transfer_mode != "single":
            self.student_id = False

    @api.onchange("source_session_id")
    def _onchange_source_session_id(self):
        domain = []
        if self.source_session_id:
            student_ids = self.source_session_id.enrollment_ids.mapped("student_id").ids
            domain = [("id", "in", student_ids)]
        return {"domain": {"student_id": domain}}

    @api.onchange("source_session_id")
    def _onchange_source_for_destination(self):
        """
        Configura dominio simple para sesión destino.
        Solo excluye la sesión origen y muestra todas las sesiones activas.
        El usuario puede elegir libremente cualquier sesión.
        """
        domain = [("active", "=", True)]
        source = self.source_session_id
        if source:
            domain.append(("id", "!=", source.id))
        return {"domain": {"destination_session_id": domain}}

    @api.depends("source_session_id", "destination_session_id", "transfer_mode", "student_id")
    def _compute_validation_message(self):
        for wizard in self:
            messages = []
            errors = []  # Errores que bloquean el traslado
            warnings = []  # Advertencias informativas
            
            if wizard.source_session_id and wizard.destination_session_id:
                # Verificar errores críticos
                if wizard.source_session_id.id == wizard.destination_session_id.id:
                    errors.append(_("❌ ERROR: El origen y el destino deben ser diferentes."))
                
                # Verificar origen
                source_errors = wizard._get_origin_errors(wizard.source_session_id)
                errors.extend(source_errors)
                
                # Generar advertencias (no bloquean)
                source = wizard.source_session_id
                dest = wizard.destination_session_id
                
                if source.subject_id != dest.subject_id:
                    warnings.append(
                        _("ℹ️ Asignaturas diferentes: %(src)s → %(dst)s")
                        % {"src": source.subject_id.name, "dst": dest.subject_id.name}
                    )
                
                if source.date != dest.date:
                    warnings.append(
                        _("ℹ️ Fechas diferentes: %(src)s → %(dst)s")
                        % {"src": source.date, "dst": dest.date}
                    )
                
                if not (
                    wizard._float_equal(source.time_start, dest.time_start)
                    and wizard._float_equal(source.time_end, dest.time_end)
                ):
                    warnings.append(
                        _("ℹ️ Horarios diferentes: %(src)s-%(end_src)s → %(dst)s-%(end_dst)s")
                        % {
                            "src": source.time_start_label,
                            "end_src": source.time_end_label,
                            "dst": dest.time_start_label,
                            "end_dst": dest.time_end_label,
                        }
                    )
                
                if source.campus_id != dest.campus_id:
                    warnings.append(
                        _("ℹ️ Sedes diferentes: %(src)s → %(dst)s")
                        % {"src": source.campus_id.name, "dst": dest.campus_id.name}
                    )
                
                if dest.available_spots <= 0:
                    warnings.append(
                        _("⚠️ ADVERTENCIA: La sesión destino no tiene cupos disponibles")
                    )
                
                if not dest.is_published:
                    warnings.append(_("⚠️ ADVERTENCIA: La sesión destino no está publicada"))
                
                if dest.state not in ("active", "with_enrollment", "draft"):
                    warnings.append(
                        _("⚠️ ADVERTENCIA: Estado de sesión destino: %(state)s")
                        % {"state": dict(dest._fields["state"].selection).get(dest.state)}
                    )
            
            if wizard.transfer_mode == "single" and not wizard.student_id:
                errors.append(_("❌ Selecciona un estudiante."))
            
            # Combinar mensajes: primero errores, luego advertencias
            messages = errors + warnings
            wizard.validation_message = "\n".join(messages) if messages else False
            wizard.can_transfer = not errors  # Solo errores bloquean, advertencias no

    def _float_equal(self, left, right, precision_digits=2):
        return float_compare(left or 0.0, right or 0.0, precision_digits=precision_digits) == 0

    def _get_equivalence_errors(self, source, destination):
        errors = []
        if not source or not destination:
            return errors
        if source.id == destination.id:
            errors.append(_("❌ ERROR: El origen y el destino deben ser diferentes."))
        # Advertencias (no bloquean el traslado)
        warnings = []
        if source.subject_id != destination.subject_id:
            warnings.append(
                _("⚠️ Advertencia: Asignaturas diferentes (Origen: %(src)s, Destino: %(dst)s)")
                % {"src": source.subject_id.name, "dst": destination.subject_id.name}
            )
        if source.date != destination.date:
            warnings.append(
                _("⚠️ Advertencia: Fechas diferentes (Origen: %(src)s, Destino: %(dst)s)")
                % {"src": source.date, "dst": destination.date}
            )
        if not (
            self._float_equal(source.time_start, destination.time_start)
            and self._float_equal(source.time_end, destination.time_end)
        ):
            warnings.append(
                _("⚠️ Advertencia: Horarios diferentes (Origen: %(src)s-%(src_end)s, Destino: %(dst)s-%(dst_end)s)")
                % {
                    "src": source.time_start_label,
                    "src_end": source.time_end_label,
                    "dst": destination.time_start_label,
                    "dst_end": destination.time_end_label,
                }
            )
        # Solo agregar advertencias como información, no como errores bloqueantes
        # errors.extend(warnings)  # Comentado para no bloquear
        return errors

    def _get_destination_errors(self, destination):
        errors = []
        if not destination:
            return errors
        if not destination.is_published:
            errors.append(_("La sesion destino debe estar publicada."))
        if destination.state not in ("active", "with_enrollment"):
            errors.append(_("La sesion destino no esta activa para recibir estudiantes."))
        if not destination.active:
            errors.append(_("La sesion destino esta inactiva."))
        return errors

    def _get_origin_errors(self, source):
        errors = []
        if not source:
            return errors
        if source.state in ("started", "done", "cancelled"):
            errors.append(_("La sesion origen no permite traslados en su estado actual."))
        return errors

    def _get_origin_enrollments(self, source, student=None):
        Enrollment = self.env["benglish.session.enrollment"]
        domain = [
            ("session_id", "=", source.id),
            ("state", "in", ["pending", "confirmed"]),
        ]
        if student:
            domain.append(("student_id", "=", student.id))
        return Enrollment.search(domain)

    def _get_destination_enrollment(self, destination, student):
        Enrollment = self.env["benglish.session.enrollment"]
        return Enrollment.search(
            [
                ("session_id", "=", destination.id),
                ("student_id", "=", student.id),
                ("state", "!=", "cancelled"),
            ],
            limit=1,
        )

    def _validate_capacity(self, destination, students_to_move):
        if not students_to_move:
            return
        available = destination.available_spots or 0
        if destination.is_full or available < len(students_to_move):
            raise UserError(
                _(
                    "La sesion destino no tiene cupos suficientes para el traslado.\n"
                    "Cupos disponibles: %(available)s\n"
                    "Estudiantes a mover: %(count)s\n\n"
                    "Ajusta la capacidad o elige otro destino."
                )
                % {"available": available, "count": len(students_to_move)}
            )

    def _update_portal_lines(self, student, source, destination):
        try:
            PlanLine = self.env["portal.student.weekly.plan.line"].sudo()
        except KeyError:
            return _("Portal no disponible.")
        origin_lines = PlanLine.search(
            [
                ("session_id", "=", source.id),
                ("plan_id.student_id", "=", student.id),
            ]
        )
        if not origin_lines:
            return _("Sin linea en agenda.")
        destination_lines = PlanLine.search(
            [
                ("session_id", "=", destination.id),
                ("plan_id.student_id", "=", student.id),
            ]
        )
        if destination_lines:
            origin_lines.unlink()
            return _("Agenda actualizada: origen eliminado.")
        origin_lines.with_context(skip_portal_plan_constraints=True).write(
            {"session_id": destination.id}
        )
        return _("Agenda actualizada al destino.")

    def _transfer_single_student(self, student, source, destination):
        origin_enrollment = self._get_origin_enrollments(source, student=student)[:1]
        if not origin_enrollment:
            return "skipped", _("No tiene inscripcion activa en el origen.")
        if origin_enrollment.state in ("attended", "absent"):
            return "failed", _(
                "No se puede trasladar porque ya tiene asistencia registrada."
            )

        destination_enrollment = self._get_destination_enrollment(destination, student)
        if destination_enrollment:
            origin_enrollment.action_cancel()
            portal_msg = self._update_portal_lines(student, source, destination)
            return "success", _(
                "Ya estaba en el destino. Origen cancelado. %(portal)s"
            ) % {"portal": portal_msg}

        effective_subject = destination.resolve_effective_subject(
            student,
            check_completed=False,
            raise_on_error=False,
            check_prereq=False,
        ) or destination.subject_id
        vals = {"session_id": destination.id}
        if effective_subject:
            vals.update(
                {
                    "effective_subject_id": effective_subject.id,
                    "effective_unit_number": effective_subject.unit_number
                    or effective_subject.unit_block_end
                    or 0,
                }
            )
        origin_enrollment.write(vals)
        portal_msg = self._update_portal_lines(student, source, destination)
        return "success", _(
            "Traslado completado. %(portal)s"
        ) % {"portal": portal_msg}

    def action_transfer(self):
        self.ensure_one()

        source = self.source_session_id
        destination = self.destination_session_id
        if not source or not destination:
            raise UserError(_("Debes seleccionar sesiones de origen y destino."))

        equivalence_errors = self._get_equivalence_errors(source, destination)
        destination_errors = self._get_destination_errors(destination)
        origin_errors = self._get_origin_errors(source)
        if equivalence_errors or destination_errors or origin_errors:
            raise UserError(
                "\n".join(equivalence_errors + destination_errors + origin_errors)
            )

        if self.transfer_mode == "single":
            if not self.student_id:
                raise UserError(_("Selecciona un estudiante para trasladar."))
            if not self._get_origin_enrollments(source, student=self.student_id):
                raise UserError(
                    _("El estudiante no esta inscrito en la sesion origen.")
                )
            students = self.student_id
        else:
            enrollments = self._get_origin_enrollments(source)
            if not enrollments:
                raise UserError(_("No hay estudiantes para trasladar en la sesion origen."))
            students = enrollments.mapped("student_id")

        dest_enrollments = self.env["benglish.session.enrollment"].search(
            [
                ("session_id", "=", destination.id),
                ("student_id", "in", students.ids),
                ("state", "!=", "cancelled"),
            ]
        )
        students_to_move = students - dest_enrollments.mapped("student_id")
        self._validate_capacity(destination, students_to_move)

        batch_id = uuid.uuid4().hex
        log_model = self.env["benglish.session.transfer.log"]
        results = {"success": 0, "skipped": 0, "failed": 0}

        for student in students:
            result = "failed"
            message = ""
            try:
                with self.env.cr.savepoint():
                    result, message = self._transfer_single_student(
                        student, source, destination
                    )
            except (UserError, ValidationError) as exc:
                message = self._get_error_message(exc)
            except Exception as exc:
                message = str(exc)
            results[result] = results.get(result, 0) + 1
            log_model.create(
                {
                    "batch_id": batch_id,
                    "source_session_id": source.id,
                    "destination_session_id": destination.id,
                    "source_session_code": source.session_code or source.name,
                    "destination_session_code": destination.session_code or destination.name,
                    "student_id": student.id,
                    "transfer_type": "single" if self.transfer_mode == "single" else "bulk",
                    "reason": self.reason,
                    "result": result,
                    "message": message,
                }
            )

        action = self.env.ref(
            "benglish_academy.action_session_transfer_log"
        ).read()[0]
        action["domain"] = [("batch_id", "=", batch_id)]
        action["context"] = dict(self.env.context, search_default_batch_id=batch_id)
        return action

    def _get_error_message(self, exc):
        msg = getattr(exc, "name", None) or ""
        if not msg and getattr(exc, "args", None):
            msg = exc.args[0]
        return msg or str(exc)
