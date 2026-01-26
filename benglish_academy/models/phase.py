# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AcademicPhase(models.Model):
    """
    Modelo para gestionar las Fases Académicas.
    Una fase pertenece a un programa y contiene niveles compartidos por todos los planes.
    """

    _name = "benglish.phase"
    _description = "Fase Académica"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "program_id, sequence, name"
    _rec_name = "complete_name"

    # Campos básicos
    name = fields.Char(
        string="Nombre de la Fase",
        required=True,
        tracking=True,
        help="Nombre de la fase académica",
    )
    code = fields.Char(
        string="Código",
        required=True,
        copy=False,
        default="/",
        tracking=True,
        help="Código único identificador de la fase (generado automáticamente o manual)",
    )
    sequence = fields.Integer(
        string="Secuencia",
        default=10,
        required=True,
        help="Orden de la fase dentro del plan de estudio",
    )
    complete_name = fields.Char(
        string="Nombre Completo",
        compute="_compute_complete_name",
        store=True,
        help="Nombre completo incluyendo plan y programa",
    )
    description = fields.Text(
        string="Descripción", help="Descripción detallada de la fase"
    )

    # Información académica
    duration_months = fields.Integer(
        string="Duración (meses)", help="Duración estimada en meses de la fase"
    )

    # Estado
    active = fields.Boolean(
        string="Activo",
        default=True,
        help="Si está inactivo, la fase no estará disponible para nuevas operaciones",
    )

    # Relaciones
    shared_phase_id = fields.Many2one(
        comodel_name="benglish.phase",
        string="Fase Compartida",
        help="Fase de la cual esta fase comparte los niveles. Usado principalmente para fases de cortesía que comparten niveles con fases regulares.",
    )
    program_id = fields.Many2one(
        comodel_name="benglish.program",
        string="Programa",
        required=True,
        ondelete="restrict",
        help="Programa al que pertenece esta fase (compartida por todos los planes del programa)",
    )
    plan_ids = fields.Many2many(
        comodel_name="benglish.plan",
        relation="benglish_phase_plan_rel",
        column1="phase_id",
        column2="plan_id",
        string="Planes de Estudio",
        compute="_compute_plan_ids",
        store=False,
        help="Planes que usan esta fase (todos los del programa)",
    )
    level_ids = fields.One2many(
        comodel_name="benglish.level",
        inverse_name="phase_id",
        string="Niveles",
        compute="_compute_level_ids",
        help="Niveles que componen esta fase (incluye niveles compartidos)",
    )

    # Campos computados
    level_count = fields.Integer(
        string="Número de Niveles", compute="_compute_level_count", store=True
    )

    # Restricciones SQL
    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "El código de la fase debe ser único."),
        # NOTA: No se fuerza unicidad de secuencia para dar flexibilidad
        # a los usuarios en la gestión de sus propias estructuras curriculares.
        # El orden se maneja mediante el campo sequence pero no se restringe.
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Genera el código automáticamente según el tipo de programa."""
        for vals in vals_list:
            if vals.get("code", "/") == "/":
                program_id = vals.get("program_id")
                if program_id:
                    program = self.env["benglish.program"].browse(program_id)
                    program_type = program.program_type
                    if program_type == "bekids":
                        vals["code"] = (
                            self.env["ir.sequence"].next_by_code(
                                "benglish.phase.bekids"
                            )
                            or "/"
                        )
                    elif program_type == "bteens":
                        vals["code"] = (
                            self.env["ir.sequence"].next_by_code(
                                "benglish.phase.bteens"
                            )
                            or "/"
                        )
                    elif program_type == "benglish":
                        vals["code"] = (
                            self.env["ir.sequence"].next_by_code(
                                "benglish.phase.benglish"
                            )
                            or "/"
                        )
                    else:
                        vals["code"] = (
                            f"PHASE-{self.env['ir.sequence'].next_by_code('benglish.phase') or '001'}"
                        )
        return super().create(vals_list)

    @api.depends("name", "program_id.name")
    def _compute_complete_name(self):
        """Calcula el nombre completo de la fase incluyendo el programa."""
        for phase in self:
            if phase.program_id:
                phase.complete_name = f"{phase.program_id.name} / {phase.name}"
            else:
                phase.complete_name = phase.name

    @api.depends("program_id")
    def _compute_plan_ids(self):
        """Calcula los planes que usan esta fase (todos los del programa)."""
        for phase in self:
            if phase.program_id:
                phase.plan_ids = self.env["benglish.plan"].search(
                    [("program_id", "=", phase.program_id.id)]
                )
            else:
                phase.plan_ids = False

    @api.depends("shared_phase_id", "shared_phase_id.level_ids")
    def _compute_level_ids(self):
        """Calcula los niveles de la fase, incluyendo los compartidos."""
        for phase in self:
            if phase.shared_phase_id:
                # Si hay una fase compartida, usar sus niveles
                phase.level_ids = phase.shared_phase_id.level_ids
            else:
                # Sino, usar los niveles propios (relación One2many normal)
                phase.level_ids = self.env["benglish.level"].search([("phase_id", "=", phase.id)])
    
    @api.depends("level_ids")
    def _compute_level_count(self):
        """Calcula el número de niveles en la fase."""
        for phase in self:
            phase.level_count = len(phase.level_ids)

    @api.constrains("code")
    def _check_code_format(self):
        """Valida el formato del código de la fase."""
        for phase in self:
            if (
                phase.code
                and not phase.code.replace("_", "").replace("-", "").isalnum()
            ):
                raise ValidationError(
                    _(
                        "El código de la fase solo puede contener letras, números, guiones y guiones bajos."
                    )
                )

    def action_view_levels(self):
        """Acción para ver los niveles de la fase."""
        self.ensure_one()
        # Si tiene fase compartida, mostrar los niveles de esa fase
        phase_id = self.shared_phase_id.id if self.shared_phase_id else self.id
        return {
            "name": _("Niveles de la Fase"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.level",
            "view_mode": "list,form",
            "domain": [("phase_id", "=", phase_id)],
            "context": {"default_phase_id": phase_id, "create": False, "edit": False},
        }

    @api.model
    def _deactivate_duplicate_phases(self):
        """
        Desactiva las fases de cortesía duplicadas (separadas por modalidad).
        Se ejecuta automáticamente al actualizar el módulo.
        """
        import logging
        _logger = logging.getLogger(__name__)
        
        duplicate_codes = [
            'PHASE-BENGLISH-COR-V-BASIC',
            'PHASE-BENGLISH-COR-V-INTER',
            'PHASE-BENGLISH-COR-V-ADV',
            'PHASE-BENGLISH-COR-M-BASIC',
            'PHASE-BENGLISH-COR-M-INTER',
            'PHASE-BENGLISH-COR-M-ADV',
            'PHASE-BETEENS-COR-V-BASIC',
            'PHASE-BETEENS-COR-V-INTER',
            'PHASE-BETEENS-COR-V-ADV',
            'PHASE-BETEENS-COR-M-BASIC',
            'PHASE-BETEENS-COR-M-INTER',
            'PHASE-BETEENS-COR-M-ADV',
        ]
        
        phases = self.search([('code', 'in', duplicate_codes)])
        
        if phases:
            _logger.info(f"🗑️  Desactivando {len(phases)} fases duplicadas de cortesía...")
            for phase in phases:
                _logger.info(f"  - {phase.code}: {phase.name}")
            phases.write({'active': False})
            _logger.info("✅ Fases duplicadas desactivadas exitosamente")
        else:
            _logger.info("⏭️  No se encontraron fases duplicadas para desactivar")
        
        return True
