# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import re
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
        readonly=True,
        default="/",
        tracking=True,
        help="Código único identificador del plan (generado automáticamente)",
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
        help="Fases asociadas al plan (pueden ser una selección de las fases del programa)",
    )

    level_ids = fields.Many2many(
        comodel_name="benglish.level",
        relation="benglish_level_plan_rel",
        column1="plan_id",
        column2="level_id",
        string="Niveles",
        help="Niveles asociados al plan (pueden ser una selección de los niveles del programa)",
    )

    subject_ids = fields.Many2many(
        comodel_name="benglish.subject",
        relation="benglish_subject_plan_rel",
        column1="plan_id",
        column2="subject_id",
        string="Asignaturas",
        help="Asignaturas asociadas al plan (pueden ser una selección de las asignaturas del programa)",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # REQUISITOS ACADÉMICOS POR NIVEL
    # ═══════════════════════════════════════════════════════════════════════════

    requirement_ids = fields.One2many(
        comodel_name="benglish.plan.requirement",
        inverse_name="plan_id",
        string="Requisitos Académicos",
        help="Requisitos académicos configurados por nivel para este plan. "
             "Definen prerrequisitos (COURSE), electivas (ELECTIVES), "
             "opciones (CHOICE) y desbloqueables (UNLOCKABLE) por nivel.",
    )

    requirement_count = fields.Integer(
        string="Número de Requisitos",
        compute="_compute_requirement_count",
        store=True,
        help="Total de requisitos académicos configurados en el plan",
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

    def _next_unique_code(self, prefix, seq_code):
        """Calcula el siguiente código libre con prefijo, reutilizando huecos."""
        import re
        
        # Buscar registros existentes con el prefijo
        existing = self.search([("code", "=like", f"{prefix}%")])
        
        if not existing:
            return f"{prefix}1"
        
        # Obtener todos los números usados
        used_numbers = set()
        for rec in existing:
            if rec.code:
                m = re.search(r"(\d+)$", rec.code)
                if m:
                    try:
                        used_numbers.add(int(m.group(1)))
                    except ValueError:
                        pass
        
        if not used_numbers:
            return f"{prefix}1"
        
        # Buscar primer hueco
        for num in range(1, max(used_numbers) + 2):
            if num not in used_numbers:
                return f"{prefix}{num}"
        
        return f"{prefix}{max(used_numbers) + 1}"

    @api.model_create_multi
    def create(self, vals_list):
        """Genera el código automáticamente según el tipo de programa y normaliza nombre."""
        for vals in vals_list:
            # Normalizar nombre a MAYÚSCULAS
            if "name" in vals and vals["name"]:
                vals["name"] = normalize_to_uppercase(vals["name"])
            # If no manual code provided, use unified simple sequence but ensure uniqueness
            if vals.get("code", "/") == "/":
                vals["code"] = self._next_unique_code("P-", "benglish.plan")
        records = super().create(vals_list)
        # Poblamos las relaciones iniciales con las fases/niveles del programa
        for rec in records:
            if rec.program_id:
                phases = self.env["benglish.phase"].search([("program_id", "=", rec.program_id.id)])
                rec.phase_ids = phases
                levels = self.env["benglish.level"].search([("phase_id", "in", phases.ids)])
                rec.level_ids = levels
                # Las asignaturas ya no están vinculadas a niveles - se asignan por tipo
                rec.subject_ids = False
        return records

    def write(self, vals):
        """Sobrescribe write para normalizar datos a MAYÚSCULAS automáticamente."""
        if "name" in vals and vals["name"]:
            vals["name"] = normalize_to_uppercase(vals["name"])
        return super().write(vals)

    @api.depends("name", "program_id.name")
    def _compute_complete_name(self):
        """Calcula el nombre completo del plan incluyendo el programa."""
        for plan in self:
            if plan.program_id:
                plan.complete_name = f"{plan.program_id.name} / {plan.name}"
            else:
                plan.complete_name = plan.name

    # Nota: las relaciones phase_ids/level_ids/subject_ids ahora son almacenadas
    # Many2many por plan. Se inicializan al crear el plan copiando la estructura
    # compartida del programa, y desde entonces se pueden editar manualmente
    # sin afectar al catálogo del programa.

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

    @api.depends("requirement_ids")
    def _compute_requirement_count(self):
        """Calcula el número de requisitos académicos configurados."""
        for plan in self:
            plan.requirement_count = len(plan.requirement_ids)

    # Los antiguos métodos inverses han sido eliminados porque ahora las
    # relaciones pertenecen al plan directamente y se persisten.

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
            "domain": [("program_id", "=", self.program_id.id)],
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
