# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class EnrollmentWizard(models.TransientModel):
    """
    Wizard para matricular estudiantes a un PLAN COMERCIAL.

    ╔═══════════════════════════════════════════════════════════════════════════════╗
    ║  CONCEPTO REFACTORIZADO (Feb 2026)                                            ║
    ║  ═══════════════════════════════════════════════════════════════════════════  ║
    ║  ✅ CORRECTO: Matrícula al PLAN COMERCIAL                                     ║
    ║  ❌ DEPRECADO: benglish.plan (Plan de Estudios Legacy)                        ║
    ║                                                                               ║
    ║  El wizard permite seleccionar el Plan Comercial que define las cantidades    ║
    ║  de asignaturas por tipo que el estudiante debe cursar.                       ║
    ╚═══════════════════════════════════════════════════════════════════════════════╝

    FLUJO DEL WIZARD:
    =================
    1. Selección de estudiante
    2. Selección de programa y PLAN COMERCIAL
    3. [OPCIONAL] Selección de asignatura inicial
    4. Configuración de modalidad de asistencia
    5. Confirmación y creación de matrícula

    CREACIÓN DE MATRÍCULA:
    ======================
    - Se crea UNA matrícula con el Plan Comercial
    - Se auto-genera el Progreso Comercial (por nivel)
    - La asignatura seleccionada se marca como "current_subject_id"
    """

    _name = "benglish.enrollment.wizard"
    _description = "Asistente de Matrícula de Estudiantes"

    # PASO 1: ESTUDIANTE

    student_id = fields.Many2one(
        comodel_name="benglish.student",
        string="Estudiante",
        required=True,
        help="Estudiante a matricular",
    )
    student_code = fields.Char(
        string="Código", related="student_id.code", readonly=True
    )
    student_email = fields.Char(
        string="Email", related="student_id.email", readonly=True
    )
    student_program_id = fields.Many2one(
        comodel_name="benglish.program",
        related="student_id.program_id",
        readonly=True,
        string="Programa del Estudiante",
    )
    student_commercial_plan_id = fields.Many2one(
        comodel_name="benglish.commercial.plan",
        related="student_id.commercial_plan_id",
        readonly=True,
        string="Plan Comercial del Estudiante",
    )
    # Legacy - mantener para compatibilidad
    student_plan_id = fields.Many2one(
        comodel_name="benglish.plan",
        related="student_id.plan_id",
        readonly=True,
        string="Plan Legacy del Estudiante",
    )

    # PASO 2: PLAN COMERCIAL (OBLIGATORIO)

    program_id = fields.Many2one(
        comodel_name="benglish.program",
        string="Programa",
        required=True,
        help="Programa académico",
    )
    commercial_plan_id = fields.Many2one(
        comodel_name="benglish.commercial.plan",
        string="Plan Comercial",
        domain="[('program_id', '=', program_id), ('state', '=', 'active')]",
        required=True,
        help="Plan comercial que define las cantidades de asignaturas por tipo. "
        "Ejemplos: Plan Plus (78 asig.), Plan Gold (126 asig.), Módulo (42 asig.)",
    )
    # Legacy - mantener para compatibilidad con matrículas antiguas
    plan_id = fields.Many2one(
        comodel_name="benglish.plan",
        string="Plan de Estudios (Legacy)",
        domain="[('program_id', '=', program_id)]",
        required=False,
        help="[DEPRECADO] Solo para compatibilidad con datos antiguos.",
    )

    # PASO 3: ASIGNATURA INICIAL (OPCIONAL - COMPATIBILIDAD)
    # La asignatura seleccionada se usará como punto de inicio (current_subject_id)
    # NO se crea matrícula a la asignatura, sino que se marca como "actual"

    subject_id = fields.Many2one(
        comodel_name="benglish.subject",
        string="Asignatura Inicial",
        domain="[('program_id', '=', program_id)]",
        required=False,
        help="[OPCIONAL] Asignatura con la que el estudiante iniciará el plan. "
        "Si no se selecciona, se asignará automáticamente la primera asignatura del plan. "
        "NOTA: Esto NO crea una matrícula a la asignatura, solo marca el punto de inicio.",
    )
    level_id = fields.Many2one(
        comodel_name="benglish.level",
        string="Nivel",
        related="subject_id.level_id",
        readonly=True,
        store=True,
    )
    phase_id = fields.Many2one(
        comodel_name="benglish.phase",
        string="Fase",
        related="subject_id.phase_id",
        readonly=True,
        store=True,
    )

    # Prerrequisitos
    prerequisite_ids = fields.Many2many(
        comodel_name="benglish.subject",
        string="Prerrequisitos",
        related="subject_id.prerequisite_ids",
        readonly=True,
    )
    prerequisites_met = fields.Boolean(
        string="Cumple Prerrequisitos",
        compute="_compute_prerequisites_met",
        help="Indica si el estudiante cumple con los prerrequisitos",
    )
    missing_prerequisites = fields.Char(
        string="Prerrequisitos Faltantes",
        compute="_compute_prerequisites_met",
        help="Lista de prerrequisitos que faltan",
    )
    can_override_prerequisites = fields.Boolean(
        string="Puede Autorizar Excepción",
        compute="_compute_can_override_prerequisites",
        help="Usuario tiene permisos para autorizar excepción de prerrequisitos",
    )
    prerequisite_override = fields.Boolean(
        string="Autorizar Excepción de Prerrequisitos",
        default=False,
        help="Permite matricular aunque no se cumplan prerrequisitos",
    )
    override_reason = fields.Text(
        string="Justificación de Excepción",
        help="Razón por la cual se autoriza la excepción",
    )

    # PASO 3 ELIMINADO: YA NO SE SOLICITA GRUPO

    # PASO 4: MODALIDAD

    delivery_mode = fields.Selection(
        selection=[
            ("presential", "Presencial"),
            ("virtual", "Virtual"),
            ("hybrid", "Híbrido"),
        ],
        string="Modalidad de Asistencia",
        compute="_compute_delivery_mode",
        store=True,
        readonly=False,
        help="Modalidad en la que el estudiante tomará las clases",
    )
    attendance_type = fields.Selection(
        selection=[
            ("presential", "Presencial"),
            ("virtual", "Virtual (Remoto)"),
        ],
        string="Tipo de Asistencia",
        help="Para modalidad híbrida: elegir si asiste presencial o remoto",
    )

    #  FECHAS Y OBSERVACIONES

    enrollment_date = fields.Date(
        string="Fecha de Matrícula", default=fields.Date.context_today, required=True
    )
    notes = fields.Text(
        string="Observaciones", help="Notas adicionales sobre esta matrícula"
    )

    # VALIDACIONES Y WARNINGS

    has_capacity_warning = fields.Boolean(
        string="Advertencia de Cupos", compute="_compute_warnings"
    )
    capacity_warning_message = fields.Char(
        string="Mensaje de Capacidad", compute="_compute_warnings"
    )
    has_prerequisite_warning = fields.Boolean(
        string="Advertencia de Prerrequisitos", compute="_compute_warnings"
    )
    prerequisite_warning_message = fields.Text(
        string="Mensaje de Prerrequisitos", compute="_compute_warnings"
    )

    # MÉTODOS COMPUTADOS

    @api.depends("student_id", "subject_id", "subject_id.prerequisite_ids")
    def _compute_prerequisites_met(self):
        """Valida si el estudiante cumple con los prerrequisitos"""
        for wizard in self:
            if not wizard.student_id or not wizard.subject_id:
                wizard.prerequisites_met = True
                wizard.missing_prerequisites = ""
                continue

            result = wizard.subject_id.check_prerequisites_completed(wizard.student_id)
            wizard.prerequisites_met = result["completed"]
            if result["missing_prerequisites"]:
                wizard.missing_prerequisites = ", ".join(
                    result["missing_prerequisites"].mapped("name")
                )
            else:
                wizard.missing_prerequisites = ""

    @api.depends("student_id")
    def _compute_can_override_prerequisites(self):
        """Verifica si el usuario puede autorizar excepción de prerrequisitos"""
        for wizard in self:
            wizard.can_override_prerequisites = self.env.user.has_group(
                "benglish_academy.group_academic_coordinator"
            ) or self.env.user.has_group("benglish_academy.group_academic_manager")

    @api.depends("delivery_mode")
    def _compute_delivery_mode(self):
        """Fija modalidad por defecto si no hay grupo"""
        for wizard in self:
            if not wizard.delivery_mode:
                wizard.delivery_mode = "presential"

    @api.depends("prerequisites_met", "subject_id")
    def _compute_warnings(self):
        """Calcula advertencias solo de prerrequisitos"""
        for wizard in self:
            if wizard.subject_id and wizard.subject_id.prerequisite_ids:
                if not wizard.prerequisites_met and not wizard.prerequisite_override:
                    wizard.has_prerequisite_warning = True
                    wizard.prerequisite_warning_message = _(
                        "El estudiante NO cumple con los prerrequisitos.\n"
                        "Prerrequisitos faltantes: %s\n\n"
                        "%s"
                    ) % (
                        wizard.missing_prerequisites,
                        (
                            "Puede autorizar una excepción si tiene permisos."
                            if wizard.can_override_prerequisites
                            else "Contacte al coordinador para autorizar una excepción."
                        ),
                    )
                else:
                    wizard.has_prerequisite_warning = False
                    wizard.prerequisite_warning_message = ""
            else:
                wizard.has_prerequisite_warning = False
                wizard.prerequisite_warning_message = ""
            wizard.has_capacity_warning = False
            wizard.capacity_warning_message = ""

    # ONCHANGES

    @api.onchange("student_id")
    def _onchange_student_id(self):
        """Carga el programa y plan del estudiante si existen"""
        if self.student_id:
            # Cargar programa y plan si el estudiante ya los tiene
            # (pueden ser False si es un estudiante nuevo sin matrículas previas)
            if self.student_id.program_id:
                self.program_id = self.student_id.program_id
            if self.student_id.commercial_plan_id:
                self.commercial_plan_id = self.student_id.commercial_plan_id
            # Legacy
            if self.student_id.plan_id:
                self.plan_id = self.student_id.plan_id

            # Intentar asignar asignatura por defecto
            self._assign_default_subject()

            # Tomar modalidad preferida del estudiante
            self.delivery_mode = self.student_id.preferred_delivery_mode or "presential"

            # Ajustar tipo de asistencia según modalidad
            self._onchange_delivery_mode()

    @api.onchange("program_id")
    def _onchange_program_id(self):
        """Limpia planes y asignatura al cambiar programa"""
        if self.commercial_plan_id and self.commercial_plan_id.program_id != self.program_id:
            self.commercial_plan_id = False
        if self.plan_id and self.plan_id.program_id != self.program_id:
            self.plan_id = False
        if not self.commercial_plan_id:
            self.subject_id = False

    @api.onchange("commercial_plan_id")
    def _onchange_commercial_plan_id(self):
        """Selecciona automáticamente la asignatura al cambiar plan comercial"""
        if self.commercial_plan_id and self.commercial_plan_id.program_id:
            # Asignar primera asignatura del programa
            subject = self._get_default_subject_by_program(self.commercial_plan_id.program_id.id)
            if subject:
                self.subject_id = subject

    @api.onchange("plan_id")
    def _onchange_plan_id(self):
        """Selecciona automáticamente la asignatura del plan (legacy)"""
        self._assign_default_subject()

    @api.onchange("delivery_mode")
    def _onchange_delivery_mode(self):
        """Configura attendance_type según modalidad"""
        if self.delivery_mode == "presential":
            self.attendance_type = "presential"
        elif self.delivery_mode == "virtual":
            self.attendance_type = "virtual"
        elif self.delivery_mode == "hybrid":
            if not self.attendance_type:
                self.attendance_type = "presential"

    # MÉTODOS DE NEGOCIO

    def action_create_enrollment(self):
        """
        Crea la matrícula con el PLAN COMERCIAL.

        CAMBIO CONCEPTUAL (Feb 2026):
        =============================
        - La matrícula usa el Plan Comercial que define cantidades por tipo
        - subject_id se usa solo como "current_subject_id" (punto de inicio)
        - Se auto-genera el Progreso Comercial por nivel
        """
        self.ensure_one()

        # Validar que hay plan comercial seleccionado (OBLIGATORIO)
        if not self.commercial_plan_id:
            raise ValidationError(
                _(
                    "Debe seleccionar un Plan Comercial para la matrícula.\n\n"
                    "💡 El Plan Comercial define cuántas asignaturas de cada tipo debe cursar el estudiante."
                )
            )

        # Si no hay asignatura inicial, asignar la primera del programa automáticamente
        if not self.subject_id:
            first_subject = self.env["benglish.subject"].search(
                [("program_id", "=", self.program_id.id)],
                order="level_id, sequence",
                limit=1,
            )
            if first_subject:
                self.subject_id = first_subject
            else:
                raise ValidationError(
                    _(
                        "No se encontraron asignaturas en el programa '%s'.\n\n"
                        "💡 Debe configurar al menos una asignatura en el programa antes de matricular."
                    )
                    % self.program_id.name
                )

        # Validar consistencia académica
        if self.subject_id.program_id != self.commercial_plan_id.program_id:
            raise ValidationError(
                _(
                    'ERROR DE CONSISTENCIA: La asignatura "%s" pertenece al programa "%s", '
                    'pero está intentando matricular en el plan "%s" del programa "%s".\n\n'
                    "Por favor, seleccione una asignatura del mismo programa."
                )
                % (
                    self.subject_id.name,
                    self.subject_id.program_id.name,
                    self.commercial_plan_id.name,
                    self.commercial_plan_id.program_id.name,
                )
            )

        # Validación de prerrequisitos (solo informativo para asignatura inicial)
        if not self.prerequisites_met and not self.prerequisite_override:
            raise ValidationError(
                _(
                    'El estudiante no cumple con los prerrequisitos para iniciar en la asignatura "%s".\n\n'
                    "Prerrequisitos faltantes: %s\n\n"
                    "Debe aprobar estas asignaturas antes de iniciar en este punto del plan."
                )
                % (self.subject_id.name, self.missing_prerequisites)
            )

        # Validar justificación de excepción si aplica
        if self.prerequisite_override and not self.override_reason:
            raise ValidationError(
                _(
                    "Debe proporcionar una justificación para autorizar la excepción de prerrequisitos."
                )
            )

        # ═══════════════════════════════════════════════════════════════════════
        # CREAR MATRÍCULA CON PLAN COMERCIAL
        # ═══════════════════════════════════════════════════════════════════════

        enrollment_vals = {
            # Estudiante
            "student_id": self.student_id.id,
            # PLAN COMERCIAL (obligatorio - elemento principal)
            "program_id": self.program_id.id,
            "commercial_plan_id": self.commercial_plan_id.id,
            # Legacy: plan_id si se seleccionó
            "plan_id": self.plan_id.id if self.plan_id else False,
            # Progresión actual (punto de inicio)
            "current_phase_id": (
                self.subject_id.phase_id.id if self.subject_id else False
            ),
            "current_level_id": (
                self.subject_id.level_id.id if self.subject_id else False
            ),
            "current_subject_id": self.subject_id.id if self.subject_id else False,
            # Modalidad
            "delivery_mode": self.delivery_mode,
            "attendance_type": (
                self.attendance_type if self.delivery_mode == "hybrid" else False
            ),
            # Fechas y notas
            "enrollment_date": self.enrollment_date,
            "notes": self.notes,
            # Estado inicial
            "state": "draft",
            # LEGACY: Mantener subject_id para compatibilidad backward
            "subject_id": self.subject_id.id if self.subject_id else False,
        }

        # Agregar excepción de prerrequisitos si aplica
        if self.prerequisite_override:
            enrollment_vals["prerequisite_override"] = True
            enrollment_vals["override_reason"] = self.override_reason
            enrollment_vals["override_by"] = self.env.user.id

        # Crear la matrícula
        enrollment = self.env["benglish.enrollment"].create(enrollment_vals)

        _logger.info(
            f"[ENROLLMENT WIZARD] Matrícula creada: {enrollment.code}\n"
            f"  - Estudiante: {self.student_id.name}\n"
            f"  - Plan Comercial: {self.commercial_plan_id.name}\n"
            f"  - Asignatura inicial: {self.subject_id.name if self.subject_id else 'N/A'}\n"
            f"  - Progreso comercial generado: {len(enrollment.commercial_progress_ids)} niveles"
        )

        # Retornar acción para abrir la matrícula creada
        return {
            "name": _("Matrícula"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.enrollment",
            "res_id": enrollment.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_cancel(self):
        """Cancela el wizard"""
        return {"type": "ir.actions.act_window_close"}

    # UTILIDADES

    @api.model
    def default_get(self, fields_list):
        """Precarga programa, plan comercial, asignatura y modalidad desde el estudiante."""
        res = super().default_get(fields_list)

        student_id = self.env.context.get("default_student_id")
        student = (
            self.env["benglish.student"].browse(student_id) if student_id else False
        )
        
        # Usar plan comercial del estudiante si existe
        commercial_plan = student.commercial_plan_id if student else False
        
        if commercial_plan:
            res["commercial_plan_id"] = commercial_plan.id
            res["program_id"] = commercial_plan.program_id.id
        elif student and student.program_id:
            res["program_id"] = student.program_id.id

        # Asignatura por programa
        if res.get("program_id"):
            subject = self._get_default_subject_by_program(res["program_id"])
            if subject:
                res["subject_id"] = subject.id

        # Modalidad preferida
        if student:
            res["delivery_mode"] = student.preferred_delivery_mode or "presential"

        return res

    def _assign_default_subject(self):
        """
        Asigna la primera asignatura del plan si existe.
        Si no hay plan, deja subject_id vacío para selección manual.
        """
        if not self.plan_id:
            # No limpiar subject_id para permitir selección manual
            # self.subject_id = False
            _logger.info(
                "No hay plan asignado. El usuario debe seleccionar la asignatura manualmente."
            )
            return

        new_subject = self._get_default_subject(self.plan_id)

        if new_subject:
            # Log para debug
            _logger.info(
                "Asignando asignatura automática: %s (ID: %s) para plan: %s - Programa: %s",
                new_subject.name,
                new_subject.id,
                self.plan_id.name,
                (
                    new_subject.program_id.name
                    if new_subject.program_id
                    else "Sin programa"
                ),
            )
            self.subject_id = new_subject
        else:
            _logger.warning(
                "No se encontraron asignaturas para el plan %s. "
                "El usuario debe seleccionar manualmente.",
                self.plan_id.name,
            )

    def _get_default_subject(self, plan):
        """Retorna la primera asignatura del plan (orden nivel/sequence)."""
        if not plan:
            return False

        # Buscar asignaturas a través de los niveles del plan para mayor precisión
        # Esto evita problemas de campos calculados no actualizados
        subjects = (
            self.env["benglish.subject"]
            .search([("level_id", "in", plan.level_ids.ids)])
            .sorted(key=lambda s: (s.level_id.sequence or 0, s.sequence or 0))
        )

        return subjects[0] if subjects else False

    def _get_default_subject_by_program(self, program_id):
        """Retorna la primera asignatura del programa (orden nivel/sequence)."""
        if not program_id:
            return False

        subjects = self.env["benglish.subject"].search(
            [("program_id", "=", program_id)],
            order="level_id, sequence",
            limit=1,
        )

        return subjects[0] if subjects else False
