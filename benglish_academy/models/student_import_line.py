# -*- coding: utf-8 -*-

import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import email_normalize


class StudentImportLine(models.Model):
    _name = "benglish.student.import.line"
    _description = "Línea de staging para importación de estudiantes"
    _order = "row_number, id"

    batch_id = fields.Many2one(
        "benglish.student.import.batch",
        string="Batch",
        required=True,
        ondelete="cascade",
        index=True,
    )
    row_number = fields.Integer(string="Fila")
    source = fields.Selection(
        [("xlsx", "XLSX"), ("manual", "Manual")],
        string="Origen",
        default="xlsx",
        required=True,
    )
    raw_values = fields.Json(string="Datos crudos")

    # Nombres desagregados
    first_name = fields.Char(string="Primer Nombre")
    second_name = fields.Char(string="Segundo Nombre")
    first_last_name = fields.Char(string="Primer Apellido")
    second_last_name = fields.Char(string="Segundo Apellido")
    name = fields.Char(string="Nombre completo")

    # Identificación
    student_id_number = fields.Char(string="Documento de identidad")
    identity_key = fields.Char(
        string="Clave identidad",
        compute="_compute_identity_key",
        store=True,
        index=True,
    )

    # Contacto
    email = fields.Char(string="Correo")
    phone = fields.Char(string="Teléfono")
    mobile = fields.Char(string="Celular")

    # Datos personales
    birth_date = fields.Date(string="Fecha de nacimiento")
    birth_date_parse_error = fields.Boolean(string="Error fecha", default=False)
    gender = fields.Selection(
        [("male", "Masculino"), ("female", "Femenino"), ("other", "Otro")],
        string="Género",
    )
    gender_parse_error = fields.Boolean(string="Error género", default=False)
    code = fields.Char(string="Código")

    # Dirección
    address = fields.Text(string="Dirección")
    city = fields.Char(string="Ciudad")
    country_id = fields.Many2one("res.country", string="País")
    country_match_error = fields.Boolean(string="Error país", default=False)

    # Académico
    program_id = fields.Many2one("benglish.program", string="Programa")
    program_match_error = fields.Boolean(string="Error programa", default=False)
    plan_id = fields.Many2one("benglish.plan", string="Plan")
    plan_match_error = fields.Boolean(string="Error plan", default=False)
    phase_id = fields.Many2one("benglish.phase", string="Fase")
    phase_match_error = fields.Boolean(string="Error fase", default=False)
    level_id = fields.Many2one("benglish.level", string="Nivel")
    level_match_error = fields.Boolean(string="Error nivel", default=False)
    preferred_campus_id = fields.Many2one("benglish.campus", string="Sede")
    campus_match_error = fields.Boolean(string="Error sede", default=False)
    preferred_delivery_mode = fields.Selection(
        [
            ("presential", "Presencial"),
            ("virtual", "Virtual"),
            ("hybrid", "Híbrido"),
        ],
        string="Modalidad preferida",
    )
    delivery_mode_parse_error = fields.Boolean(string="Error modalidad", default=False)

    # Datos del contrato académico (matrícula)
    categoria = fields.Char(string="Categoría")
    course_start_date = fields.Date(string="Fecha Inicio Curso")
    course_start_date_parse_error = fields.Boolean(
        string="Error fecha inicio", default=False
    )
    course_end_date = fields.Date(string="Fecha Fin Curso")
    course_end_date_parse_error = fields.Boolean(
        string="Error fecha fin", default=False
    )
    max_freeze_date = fields.Date(string="Fecha Máxima Congelamiento")
    max_freeze_date_parse_error = fields.Boolean(
        string="Error fecha congelamiento", default=False
    )
    course_days = fields.Integer(string="Días del Curso")

    # Estado académico
    estado_academico = fields.Selection(
        [
            ("prospect", "Prospecto"),
            ("enrolled", "Matriculado"),
            ("active", "Activo"),
            ("inactive", "Inactivo"),
            ("graduated", "Graduado"),
            ("withdrawn", "Retirado"),
        ],
        string="Estado Académico",
    )
    estado_parse_error = fields.Boolean(string="Error estado", default=False)

    # Titular/Responsable
    responsible_name = fields.Char(string="Contacto Titular")

    duplicate_in_batch = fields.Boolean(string="Duplicado en batch", default=False)
    duplicate_line_numbers = fields.Char(string="Filas duplicadas")
    existing_student_id = fields.Many2one(
        "benglish.student", string="Estudiante existente"
    )
    duplicate_scope = fields.Selection(
        [
            ("none", "Sin duplicados"),
            ("batch", "Duplicado en batch"),
            ("existing", "Duplicado en base"),
            ("both", "Duplicado en batch y base"),
        ],
        compute="_compute_duplicate_scope",
        store=True,
        string="Tipo de duplicado",
    )

    action_decision = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("create", "Crear"),
            ("update", "Actualizar"),
            ("ignore", "Ignorar"),
        ],
        string="Decisión",
        default="pending",
        required=True,
    )
    target_student_id = fields.Many2one(
        "benglish.student", string="Estudiante objetivo"
    )

    decision_conflict = fields.Boolean(string="Conflicto de decision", default=False)
    decision_conflict_message = fields.Char(string="Detalle conflicto")

    validation_state = fields.Selection(
        [
            ("error", "Error"),
            ("warning", "Advertencia"),
            ("ok", "Valido"),
        ],
        compute="_compute_validation",
        store=True,
        string="Estado de validación",
    )
    error_messages = fields.Text(
        string="Errores", compute="_compute_validation", store=True
    )
    warning_messages = fields.Text(
        string="Advertencias", compute="_compute_validation", store=True
    )

    result_state = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("created", "Creado"),
            ("updated", "Actualizado"),
            ("ignored", "Ignorado"),
            ("error", "Error"),
        ],
        string="Resultado",
        default="pending",
    )
    result_message = fields.Text(string="Detalle del resultado")
    processed_at = fields.Datetime(string="Procesado el")
    processed_by = fields.Many2one("res.users", string="Procesado por")

    is_empty = fields.Boolean(string="Fila vacía", default=False)

    @api.depends("student_id_number")
    def _compute_identity_key(self):
        for line in self:
            if line.student_id_number:
                key = re.sub(r"\s+", "", line.student_id_number.strip().upper())
                line.identity_key = key
            else:
                line.identity_key = False

    @api.depends("duplicate_in_batch", "existing_student_id")
    def _compute_duplicate_scope(self):
        for line in self:
            if line.duplicate_in_batch and line.existing_student_id:
                line.duplicate_scope = "both"
            elif line.duplicate_in_batch:
                line.duplicate_scope = "batch"
            elif line.existing_student_id:
                line.duplicate_scope = "existing"
            else:
                line.duplicate_scope = "none"

    @api.depends(
        "is_empty",
        "student_id_number",
        "first_name",
        "first_last_name",
        "email",
        "phone",
        "birth_date_parse_error",
        "gender_parse_error",
        "delivery_mode_parse_error",
        "program_match_error",
        "plan_match_error",
        "phase_match_error",
        "level_match_error",
        "campus_match_error",
        "country_match_error",
        "course_start_date_parse_error",
        "course_end_date_parse_error",
        "max_freeze_date_parse_error",
        "estado_parse_error",
        "duplicate_scope",
        "action_decision",
        "target_student_id",
        "decision_conflict",
    )
    def _compute_validation(self):
        for line in self:
            errors = []
            warnings = []

            if line.is_empty:
                errors.append(_("Fila vacía."))

            if not line.student_id_number:
                errors.append(_("Documento de identidad requerido."))
            if not line.first_name:
                errors.append(_("Primer nombre requerido."))
            if not line.first_last_name:
                errors.append(_("Primer apellido requerido."))
            if not line.email:
                errors.append(_("Correo requerido."))
            elif not email_normalize(line.email):
                errors.append(_("Correo inválido."))
            if not line.phone:
                errors.append(_("Teléfono requerido."))

            if line.birth_date_parse_error:
                errors.append(_("Fecha de nacimiento inválida."))
            if line.gender_parse_error:
                errors.append(_("Género inválido."))
            if line.delivery_mode_parse_error:
                errors.append(_("Modalidad inválida."))
            if line.course_start_date_parse_error:
                warnings.append(_("Fecha de inicio del curso inválida."))
            if line.course_end_date_parse_error:
                warnings.append(_("Fecha de fin del curso inválida."))
            if line.max_freeze_date_parse_error:
                warnings.append(_("Fecha máxima de congelamiento inválida."))
            if line.estado_parse_error:
                warnings.append(_("Estado académico inválido."))

            if line.program_match_error:
                warnings.append(_("Programa no encontrado o ambíguo."))
            if line.plan_match_error:
                warnings.append(_("Plan no encontrado o ambíguo."))
            if line.phase_match_error:
                warnings.append(_("Fase no encontrada o ambigua."))
            if line.level_match_error:
                warnings.append(_("Nivel no encontrado o ambíguo."))
            if line.campus_match_error:
                warnings.append(_("Sede no encontrada o ambigua."))
            if line.country_match_error:
                warnings.append(_("País no encontrado o ambíguo."))

            if line.duplicate_scope in ("batch", "existing", "both"):
                if line.action_decision == "pending":
                    errors.append(_("Duplicado detectado, requiere decisión."))
                else:
                    warnings.append(_("Duplicado detectado."))

            if line.action_decision == "update" and not line.target_student_id:
                errors.append(
                    _("Debe seleccionar el estudiante objetivo para actualizar.")
                )

            if line.decision_conflict:
                errors.append(
                    line.decision_conflict_message or _("Conflicto de decisión.")
                )

            if line.action_decision == "ignore" and errors:
                warnings.extend(errors)
                errors = []

            if errors:
                line.validation_state = "error"
            elif warnings:
                line.validation_state = "warning"
            else:
                line.validation_state = "ok"

            line.error_messages = "\n".join(errors) if errors else False
            line.warning_messages = "\n".join(warnings) if warnings else False

    @api.onchange("first_name", "second_name", "first_last_name", "second_last_name")
    def _onchange_name_parts(self):
        for line in self:
            if line.first_name or line.first_last_name:
                parts = [
                    line.first_name,
                    line.second_name,
                    line.first_last_name,
                    line.second_last_name,
                ]
                line.name = " ".join(part for part in parts if part).strip()

    @api.onchange("email")
    def _onchange_email(self):
        for line in self:
            if line.email:
                line.email = line.email.strip().lower()

    @api.onchange("student_id_number")
    def _onchange_student_id_number(self):
        for line in self:
            if line.student_id_number:
                line.student_id_number = re.sub(
                    r"\s+", "", line.student_id_number.strip()
                )

    @api.onchange("phone")
    def _onchange_phone(self):
        for line in self:
            if line.phone:
                line.phone = re.sub(r"[^\d+]", "", line.phone)

    @api.onchange("mobile")
    def _onchange_mobile(self):
        for line in self:
            if line.mobile:
                line.mobile = re.sub(r"[^\d+]", "", line.mobile)

    @api.onchange("birth_date")
    def _onchange_birth_date(self):
        for line in self:
            if line.birth_date:
                line.birth_date_parse_error = False

    @api.onchange("gender")
    def _onchange_gender(self):
        for line in self:
            if line.gender:
                line.gender_parse_error = False

    @api.onchange("preferred_delivery_mode")
    def _onchange_delivery_mode(self):
        for line in self:
            if line.preferred_delivery_mode:
                line.delivery_mode_parse_error = False

    @api.onchange("program_id")
    def _onchange_program_id(self):
        for line in self:
            if line.program_id:
                line.program_match_error = False

    @api.onchange("plan_id")
    def _onchange_plan_id(self):
        for line in self:
            if line.plan_id:
                line.plan_match_error = False

    @api.onchange("preferred_campus_id")
    def _onchange_preferred_campus_id(self):
        for line in self:
            if line.preferred_campus_id:
                line.campus_match_error = False

    @api.onchange("country_id")
    def _onchange_country_id(self):
        for line in self:
            if line.country_id:
                line.country_match_error = False

    @api.onchange(
        "student_id_number",
        "first_name",
        "last_name",
        "email",
        "phone",
        "mobile",
        "birth_date",
        "gender",
    )
    def _onchange_clear_empty_flag(self):
        for line in self:
            if any(
                [
                    line.student_id_number,
                    line.first_name,
                    line.last_name,
                    line.email,
                    line.phone,
                    line.mobile,
                    line.birth_date,
                    line.gender,
                ]
            ):
                line.is_empty = False

    @api.onchange("action_decision")
    def _onchange_action_decision(self):
        for line in self:
            if line.action_decision == "update":
                if line.existing_student_id and not line.target_student_id:
                    line.target_student_id = line.existing_student_id
            else:
                line.target_student_id = False

    @api.onchange("existing_student_id")
    def _onchange_existing_student(self):
        for line in self:
            if (
                line.action_decision == "update"
                and line.existing_student_id
                and not line.target_student_id
            ):
                line.target_student_id = line.existing_student_id

    @api.constrains("action_decision", "target_student_id")
    def _check_action_target(self):
        for line in self:
            if line.action_decision == "update" and not line.target_student_id:
                raise ValidationError(
                    _("Debe seleccionar un estudiante objetivo para actualizar.")
                )
            if line.action_decision in ("create", "ignore") and line.target_student_id:
                raise ValidationError(
                    _("No se permite seleccionar estudiante objetivo si no actualiza.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if not self.env.context.get("skip_import_recompute"):
            batches = lines.mapped("batch_id")
            keys = set(lines.mapped("identity_key"))
            for batch in batches:
                batch.with_context(
                    skip_import_recompute=True
                )._recompute_duplicates_for_keys(keys)
                batch.with_context(
                    skip_import_recompute=True
                )._recompute_decision_conflicts(keys)
                batch.with_context(skip_import_recompute=True)._suggest_actions()
        return lines

    def write(self, vals):
        if self.env.context.get("skip_import_recompute"):
            return super().write(vals)

        old_keys = set(self.mapped("identity_key"))
        res = super().write(vals)
        new_keys = set(self.mapped("identity_key"))
        keys = (old_keys | new_keys) - {False}

        if keys:
            batches = self.mapped("batch_id")
            for batch in batches:
                batch.with_context(
                    skip_import_recompute=True
                )._recompute_duplicates_for_keys(keys)
                batch.with_context(
                    skip_import_recompute=True
                )._recompute_decision_conflicts(keys)
                batch.with_context(skip_import_recompute=True)._suggest_actions()

        return res
