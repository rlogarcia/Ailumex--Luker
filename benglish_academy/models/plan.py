# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from ..utils.normalizers import normalize_to_uppercase, normalize_codigo


class StudyPlan(models.Model):
    """
    Modelo para gestionar los Planes de Estudio.
    Un plan de estudio pertenece a un programa y contiene fases.
    """

    _name = "benglish.plan"
    _description = "Plan de Estudio"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "program_id, sequence, name"
    _rec_name = "complete_name"

    # Campos básicos
    name = fields.Char(
        string="Nombre del Plan",
        required=True,
        tracking=True,
        help="Nombre del plan de estudio",
    )

    code = fields.Char(
        string="Código",
        required=True,
        copy=False,
        default="/",
        tracking=True,
        help="Código único identificador del plan (generado automáticamente o manual)",
    )
    sequence = fields.Integer(
        string="Secuencia", default=10, help="Orden de visualización"
    )

    # RF-01: Versionamiento de Planes
    version = fields.Char(
        string="Versión",
        default="1.0",
        required=True,
        tracking=True,
        help="Versión del plan de estudio (ej: 1.0, 1.1, 2.0)",
    )
    effective_date_start = fields.Date(
        string="Vigencia Desde",
        tracking=True,
        help="Fecha desde la cual este plan está vigente",
    )
    effective_date_end = fields.Date(
        string="Vigencia Hasta",
        tracking=True,
        help="Fecha hasta la cual este plan está vigente (dejar vacío si está activo)",
    )
    is_current_version = fields.Boolean(
        string="Versión Actual",
        default=True,
        tracking=True,
        help="Indica si esta es la versión actualmente vigente del plan",
    )
    complete_name = fields.Char(
        string="Nombre Completo",
        compute="_compute_complete_name",
        store=True,
        help="Nombre completo incluyendo programa",
    )
    description = fields.Text(
        string="Descripción", help="Descripción detallada del plan de estudio"
    )
    credits_value = fields.Integer(
        string="Creditos", help="Creditos de las asignaturas"
    )

    # Información académica
    duration_years = fields.Integer(
        string="Duración (años)", help="Duración estimada en años del plan de estudio"
    )
    duration_months = fields.Integer(
        string="Duración (meses)", help="Duración estimada en meses del plan de estudio"
    )
    total_hours = fields.Float(
        string="Total de Horas",
        help="Total de horas académicas del plan (usado para cálculo de progreso)",
    )

    # RF-04: Método de Cálculo de Progreso
    progress_calculation_method = fields.Selection(
        selection=[
            ("by_subjects", "Por Asignaturas"),
            ("by_hours", "Por Horas"),
            ("mixed", "Mixto (50% asignaturas + 50% horas)"),
        ],
        string="Método de Progreso",
        default="by_subjects",
        required=True,
        tracking=True,
        help="Método para calcular el progreso académico del estudiante en este plan",
    )

    periodicity = fields.Selection(
        [
            ("hours", "Horas"),
            ("days", "Días"),
            ("months", "Meses"),
            ("semesters", "Semestres"),
            ("years", "Años"),
        ],
        string="Periodicidad",
    )

    periodicity_value = fields.Integer(string="Cantidad")
    show_periodicity_value = fields.Boolean(compute="_compute_show_periodicity_value")

    # Modalidad del plan
    modality = fields.Selection(
        [
            ("presencial", "Presencial"),
            ("virtual", "Virtual"),
            ("hibrida", "Híbrida"),
        ],
        string="Modalidad",
        default="presencial",
        required=True,
        tracking=True,
        help="Modalidad en que se dictará el plan de estudio",
    )

    # Estado
    active = fields.Boolean(
        string="Activo",
        default=True,
        help="Si está inactivo, el plan no estará disponible para nuevas operaciones",
    )

    active_phase = fields.Boolean(
        string="Fases",
        default=False,
        help="Si está inactivo, el plan no enseñara las fases asociadas",
    )

    active_level = fields.Boolean(
        string="Niveles",
        default=False,
        help="Si está inactivo, el plan no enseñara los niveles asociados",
    )

    active_subject = fields.Boolean(
        string="Asignaturas",
        default=False,
        help="Si está inactivo, el plan no enseñara las asignaturas asociadas",
    )

    # Relaciones
    program_id = fields.Many2one(
        comodel_name="benglish.program",
        string="Programa",
        required=True,
        ondelete="restrict",
        help="Programa al que pertenece este plan de estudio",
    )
    phase_ids = fields.Many2many(
        comodel_name="benglish.phase",
        relation="benglish_phase_plan_rel",
        column1="plan_id",
        column2="phase_id",
        string="Fases",
        compute="_compute_phase_ids",
        inverse="_inverse_phase_ids",
        store=False,
        readonly=False,
        help="Fases compartidas del programa (todos los planes comparten las mismas fases)",
    )

    level_ids = fields.Many2many(
        comodel_name="benglish.level",
        relation="benglish_level_plan_rel",
        column1="plan_id",
        column2="level_id",
        string="Niveles",
        compute="_compute_level_ids",
        inverse="_inverse_level_ids",
        store=False,
        readonly=False,
        help="Niveles compartidos del programa (todos los planes comparten los mismos niveles)",
    )

    subject_ids = fields.Many2many(
        comodel_name="benglish.subject",
        relation="benglish_subject_plan_rel",
        column1="plan_id",
        column2="subject_id",
        string="Asignaturas",
        compute="_compute_subject_ids",
        inverse="_inverse_subject_ids",
        store=False,
        readonly=False,
        help="Asignaturas compartidas del programa (todos los planes comparten las mismas asignaturas)",
    )

    # Campos computados
    phase_count = fields.Integer(
        string="Número de Fases", compute="_compute_phase_count", store=True
    )

    level_count = fields.Integer(
        string="Número de Fases", compute="_compute_level_count", store=True
    )

    subject_count = fields.Integer(
        string="Número de Asignaturas", compute="_compute_subject_count", store=True
    )

    # Alias para compatibilidad con vistas
    total_subjects = fields.Integer(
        string="Total de Asignaturas",
        related="subject_count",
        help="Total de asignaturas en el plan (alias de subject_count)",
    )

    # Restricciones SQL
    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "El código del plan debe ser único."),
        (
            "duration_positive",
            "CHECK(duration_months >= 0 AND duration_years >= 0)",
            "La duración debe ser positiva.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Genera el código automáticamente según el tipo de programa y normaliza nombre."""
        for vals in vals_list:
            # Normalizar nombre a MAYÚSCULAS
            if "name" in vals and vals["name"]:
                vals["name"] = normalize_to_uppercase(vals["name"])

            if vals.get("code", "/") == "/":
                program_id = vals.get("program_id")
                if program_id:
                    program = self.env["benglish.program"].browse(program_id)
                    program_type = program.program_type
                    if program_type == "bekids":
                        vals["code"] = (
                            self.env["ir.sequence"].next_by_code("benglish.plan.bekids")
                            or "/"
                        )
                    elif program_type == "bteens":
                        vals["code"] = (
                            self.env["ir.sequence"].next_by_code("benglish.plan.bteens")
                            or "/"
                        )
                    elif program_type == "benglish":
                        vals["code"] = (
                            self.env["ir.sequence"].next_by_code(
                                "benglish.plan.benglish"
                            )
                            or "/"
                        )
                    else:
                        vals["code"] = (
                            f"PLAN-{self.env['ir.sequence'].next_by_code('benglish.plan') or '001'}"
                        )
        return super().create(vals_list)

    @api.depends("name", "program_id.name")
    def _compute_complete_name(self):
        """Calcula el nombre completo del plan incluyendo el programa."""
        for plan in self:
            if plan.program_id:
                plan.complete_name = f"{plan.program_id.name} / {plan.name}"
            else:
                plan.complete_name = plan.name

    @api.depends("program_id")
    def _compute_phase_ids(self):
        """Obtiene las fases compartidas del programa."""
        for plan in self:
            if plan.program_id:
                plan.phase_ids = self.env["benglish.phase"].search(
                    [("program_id", "=", plan.program_id.id)]
                )
            else:
                plan.phase_ids = False

    @api.depends("program_id")
    def _compute_level_ids(self):
        """Obtiene los niveles compartidos del programa."""
        for plan in self:
            if plan.program_id:
                phases = self.env["benglish.phase"].search(
                    [("program_id", "=", plan.program_id.id)]
                )
                plan.level_ids = self.env["benglish.level"].search(
                    [("phase_id", "in", phases.ids)]
                )
            else:
                plan.level_ids = False

    @api.depends("program_id")
    def _compute_subject_ids(self):
        """Obtiene las asignaturas compartidas del programa."""
        for plan in self:
            if plan.program_id:
                phases = self.env["benglish.phase"].search(
                    [("program_id", "=", plan.program_id.id)]
                )
                levels = self.env["benglish.level"].search(
                    [("phase_id", "in", phases.ids)]
                )
                plan.subject_ids = self.env["benglish.subject"].search(
                    [("level_id", "in", levels.ids)]
                )
            else:
                plan.subject_ids = False

    @api.depends("phase_ids")
    def _compute_phase_count(self):
        """Calcula el número de fases asociadas."""
        for plan in self:
            plan.phase_count = len(plan.phase_ids)

    @api.depends("level_ids")
    def _compute_level_count(self):
        """Calcula el número de niveles asociados."""
        for plan in self:
            plan.level_count = len(plan.level_ids)

    @api.depends("subject_ids")
    def _compute_subject_count(self):
        """Calcula el número de asignaturas asociadas."""
        for plan in self:
            plan.subject_count = len(plan.subject_ids)

    def _inverse_phase_ids(self):
        """Permite editar fases desde el plan. Las fases se asocian automáticamente al programa."""
        # No hacer nada: las fases se gestionan a través del programa
        # Este método inverse permite la edición en línea pero no persiste cambios
        pass

    def _inverse_level_ids(self):
        """Permite editar niveles desde el plan. Los niveles se asocian automáticamente al programa."""
        # No hacer nada: los niveles se gestionan a través del programa
        # Este método inverse permite la edición en línea pero no persiste cambios
        pass

    def _inverse_subject_ids(self):
        """Permite editar asignaturas desde el plan. Las asignaturas se asocian automáticamente al programa."""
        # No hacer nada: las asignaturas se gestionan a través del programa
        # Este método inverse permite la edición en línea pero no persiste cambios
        pass

    @api.constrains("code")
    def _check_code_format(self):
        """Valida el formato del código del plan."""
        for plan in self:
            if plan.code and not plan.code.replace("_", "").replace("-", "").isalnum():
                raise ValidationError(
                    _(
                        "El código del plan solo puede contener letras, números, guiones y guiones bajos."
                    )
                )

    def action_view_phases(self):
        """Acción para ver las fases compartidas del programa."""
        self.ensure_one()
        return {
            "name": _("Fases del Programa"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.phase",
            "view_mode": "list,form",
            "domain": [("program_id", "=", self.program_id.id)],
            "context": {"default_program_id": self.program_id.id},
        }

    def action_call_from_plan_phases(self):
        """Abre la vista de fases del programa para crearlas/editarlas."""
        self.ensure_one()
        if not self.program_id:
            raise ValidationError(_("Este plan no tiene un programa asociado."))

        return {
            "name": _("Fases del Programa: %s") % self.program_id.name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.phase",
            "view_mode": "list,form",
            "domain": [("program_id", "=", self.program_id.id)],
            "context": {
                "default_program_id": self.program_id.id,
                "search_default_program_id": self.program_id.id,
            },
            "target": "current",
        }

    def action_call_from_plan_levels(self):
        """Abre la vista de niveles del programa para crearlos/editarlos."""
        self.ensure_one()
        if not self.program_id:
            raise ValidationError(_("Este plan no tiene un programa asociado."))

        # Obtener todas las fases del programa
        phases = self.env["benglish.phase"].search(
            [("program_id", "=", self.program_id.id)]
        )

        return {
            "name": _("Niveles del Programa: %s") % self.program_id.name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.level",
            "view_mode": "list,form",
            "domain": [("phase_id", "in", phases.ids)],
            "context": {
                "default_program_id": self.program_id.id,
                "search_default_program_id": self.program_id.id,
            },
            "target": "current",
        }

    def action_call_from_plan_subjects(self):
        """Abre la vista de asignaturas del programa para crearlas/editarlas."""
        self.ensure_one()
        if not self.program_id:
            raise ValidationError(_("Este plan no tiene un programa asociado."))

        # Obtener todas las fases del programa
        phases = self.env["benglish.phase"].search(
            [("program_id", "=", self.program_id.id)]
        )
        # Obtener todos los niveles de esas fases
        levels = self.env["benglish.level"].search([("phase_id", "in", phases.ids)])

        return {
            "name": _("Asignaturas del Programa: %s") % self.program_id.name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.subject",
            "view_mode": "list,form",
            "domain": [("level_id", "in", levels.ids)],
            "context": {
                "default_program_id": self.program_id.id,
                "search_default_program_id": self.program_id.id,
            },
            "target": "current",
        }

    def action_open_program(self):
        """Abre el formulario del programa para gestionar la estructura académica compartida."""
        self.ensure_one()
        if not self.program_id:
            raise ValidationError(_("Este plan no tiene un programa asociado."))

        return {
            "name": _("Programa: %s") % self.program_id.name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.program",
            "res_id": self.program_id.id,
            "view_mode": "form",
            "target": "current",
            "context": self.env.context,
        }

    @api.depends("periodicity")
    def _compute_show_periodicity_value(self):
        for rec in self:
            rec.show_periodicity_value = bool(rec.periodicity)

    def write(self, vals):
        """
        MODIFICACIÓN FORZADA HABILITADA PARA GESTORES.
        Permite modificar planes sin restricciones para facilitar gestión.
        """
        # Normalizar nombre a MAYÚSCULAS
        if "name" in vals and vals["name"]:
            vals["name"] = normalize_to_uppercase(vals["name"])
        
        # Permitir modificación forzada sin validaciones
        return super(StudyPlan, self).write(vals)

    def unlink(self):
        """
        ELIMINACIÓN FORZADA HABILITADA PARA GESTORES.
        Permite eliminar planes sin restricciones para facilitar gestión.
        """
        # Permitir eliminación forzada sin validaciones
        return super(StudyPlan, self).unlink()
