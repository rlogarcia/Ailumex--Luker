# -*- coding: utf-8 -*-
"""
Modelo de Plan Comercial.

Define la estructura comercial de lo que un estudiante debe cursar según el plan que compró.
A diferencia del Plan de Estudios (estático), el Plan Comercial define CANTIDADES
por tipo de asignatura que se verifican dinámicamente según el cumplimiento del estudiante.

Reglas de negocio:
- Un Plan Comercial pertenece a un Programa
- Define cuántas asignaturas de cada tipo debe ver el estudiante por nivel
- El total de asignaturas se calcula automáticamente basado en la configuración
- Permite diferentes estructuras para diferentes planes (Plus, Gold, Módulo, etc.)
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class CommercialPlan(models.Model):
    """
    Plan Comercial.
    
    Define la estructura de asignaturas que un estudiante debe cursar
    según el plan que compró. No es una lista fija de asignaturas,
    sino una configuración de CANTIDADES por tipo.
    
    Ejemplos:
    - Plan Plus: 24 selecciones + 6 oral tests + 48 electivas = 78 total
    - Plan Gold: 24 selecciones + 6 oral tests + 96 electivas = 126 total
    - Módulo: 8 selecciones + 2 oral tests + 32 electivas = 42 total
    """

    _name = "benglish.commercial.plan"
    _description = "Plan Comercial"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "program_id, sequence, name"
    _rec_name = "display_name"

    # ═══════════════════════════════════════════════════════════════════════════
    # IDENTIFICACIÓN
    # ═══════════════════════════════════════════════════════════════════════════

    name = fields.Char(
        string="Nombre del Plan",
        required=True,
        tracking=True,
        help="Nombre comercial del plan (ej: Plan Plus, Plan Gold, Módulo)",
    )

    code = fields.Char(
        string="Código",
        copy=False,
        readonly=True,
        default="/",
        tracking=True,
        index=True,
        help="Código único generado automáticamente (ej: CP-001)",
    )

    display_name = fields.Char(
        string="Nombre Completo",
        compute="_compute_display_name",
        store=True,
        help="Nombre para mostrar incluyendo código y programa",
    )

    sequence = fields.Integer(
        string="Secuencia",
        default=10,
        help="Orden de visualización",
    )

    description = fields.Text(
        string="Descripción",
        help="Descripción detallada del plan comercial y sus beneficios",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # ESTADO DEL PLAN
    # ═══════════════════════════════════════════════════════════════════════════

    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("active", "Activo"),
            ("archived", "Archivado"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
        help="Estado del plan comercial: Borrador (en preparación), Activo (disponible para matrículas), Archivado (ya no disponible)",
    )

    active = fields.Boolean(
        string="Activo",
        default=True,
        tracking=True,
        compute="_compute_active",
        store=True,
        readonly=False,
        help="Si está inactivo, el plan no estará disponible para nuevas matrículas",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # VALOR COMERCIAL
    # ═══════════════════════════════════════════════════════════════════════════

    commercial_value = fields.Integer(
        string="Valor Comercial",
        default=1,
        tracking=True,
        help="Valor numérico del plan para diferenciación comercial (ej: 1=Plus, 2=Premium, 3=Gold)",
    )

    price = fields.Float(
        string="Precio Referencial",
        digits=(12, 2),
        tracking=True,
        help="Precio referencial del plan (informativo)",
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moneda",
        default=lambda self: self.env.company.currency_id,
        help="Moneda del precio referencial",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RELACIÓN CON PROGRAMA
    # ═══════════════════════════════════════════════════════════════════════════

    program_id = fields.Many2one(
        comodel_name="benglish.program",
        string="Programa",
        required=True,
        ondelete="restrict",
        tracking=True,
        index=True,
        help="Programa académico al que pertenece este plan comercial",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURACIÓN DE NIVELES
    # ═══════════════════════════════════════════════════════════════════════════

    level_start = fields.Integer(
        string="Nivel Inicial",
        default=1,
        required=True,
        tracking=True,
        help="Nivel desde el cual aplica este plan (inclusive)",
    )

    level_end = fields.Integer(
        string="Nivel Final",
        default=24,
        required=True,
        tracking=True,
        help="Nivel hasta el cual aplica este plan (inclusive)",
    )

    total_levels = fields.Integer(
        string="Total de Niveles",
        compute="_compute_total_levels",
        store=True,
        help="Cantidad total de niveles que cubre este plan",
    )

    # Relación con niveles del programa (calculada)
    level_ids = fields.Many2many(
        comodel_name="benglish.level",
        string="Niveles Incluidos",
        compute="_compute_level_ids",
        help="Niveles del programa que están incluidos en este plan comercial",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # LÍNEAS DE CONFIGURACIÓN
    # ═══════════════════════════════════════════════════════════════════════════

    line_ids = fields.One2many(
        comodel_name="benglish.commercial.plan.line",
        inverse_name="plan_id",
        string="Configuración de Asignaturas",
        help="Define cuántas asignaturas de cada tipo debe cursar el estudiante",
    )

    line_count = fields.Integer(
        string="Líneas de Configuración",
        compute="_compute_line_count",
        store=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # TOTALES CALCULADOS
    # ═══════════════════════════════════════════════════════════════════════════

    total_subjects = fields.Integer(
        string="Total de Asignaturas",
        compute="_compute_totals",
        store=True,
        help="Total de asignaturas que debe cursar el estudiante con este plan",
    )

    total_selection = fields.Integer(
        string="Total Selección",
        compute="_compute_totals",
        store=True,
        help="Total de asignaturas de tipo Selección",
    )

    total_oral_test = fields.Integer(
        string="Total Oral Tests",
        compute="_compute_totals",
        store=True,
        help="Total de Oral Tests que debe presentar",
    )

    total_electives = fields.Integer(
        string="Total Electivas",
        compute="_compute_totals",
        store=True,
        help="Total de electivas que debe cursar",
    )

    total_regular = fields.Integer(
        string="Total Regulares",
        compute="_compute_totals",
        store=True,
        help="Total de asignaturas regulares",
    )

    total_bskills = fields.Integer(
        string="Total B-Skills",
        compute="_compute_totals",
        store=True,
        help="Total de B-Skills",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # ESTADÍSTICAS DE USO
    # ═══════════════════════════════════════════════════════════════════════════

    enrollment_count = fields.Integer(
        string="Matrículas Activas",
        compute="_compute_enrollment_count",
        help="Número de estudiantes matriculados con este plan comercial",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RESTRICCIONES SQL
    # ═══════════════════════════════════════════════════════════════════════════

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "El código del plan comercial debe ser único."),
        (
            "level_range_valid",
            "CHECK(level_end >= level_start)",
            "El nivel final debe ser mayor o igual al nivel inicial.",
        ),
        (
            "level_start_positive",
            "CHECK(level_start > 0)",
            "El nivel inicial debe ser mayor a 0.",
        ),
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTODOS COMPUTE
    # ═══════════════════════════════════════════════════════════════════════════

    @api.depends("name", "code", "program_id.name")
    def _compute_display_name(self):
        for record in self:
            parts = []
            if record.code and record.code != "/":
                parts.append(f"[{record.code}]")
            if record.name:
                parts.append(record.name)
            if record.program_id:
                parts.append(f"({record.program_id.name})")
            record.display_name = " ".join(parts) if parts else "Nuevo Plan Comercial"

    @api.depends("state")
    def _compute_active(self):
        """Active se calcula basado en el estado: solo es activo si el estado no es archived."""
        for record in self:
            record.active = record.state != "archived"

    @api.depends("level_start", "level_end")
    def _compute_total_levels(self):
        for record in self:
            if record.level_start and record.level_end:
                record.total_levels = record.level_end - record.level_start + 1
            else:
                record.total_levels = 0

    @api.depends("program_id", "level_start", "level_end")
    def _compute_level_ids(self):
        """Calcula los niveles incluidos basado en la secuencia dentro del programa."""
        for record in self:
            if record.program_id and record.level_start and record.level_end:
                # Buscar niveles del programa ordenados por secuencia
                levels = self.env["benglish.level"].search([
                    ("program_id", "=", record.program_id.id),
                    ("active", "=", True),
                ], order="sequence, id")
                
                # Tomar los niveles en el rango configurado
                if levels:
                    start_idx = record.level_start - 1  # Convertir a índice 0-based
                    end_idx = record.level_end
                    record.level_ids = levels[start_idx:end_idx]
                else:
                    record.level_ids = False
            else:
                record.level_ids = False

    @api.depends("line_ids")
    def _compute_line_count(self):
        for record in self:
            record.line_count = len(record.line_ids)

    @api.depends("line_ids.calculated_total", "line_ids.subject_type_code")
    def _compute_totals(self):
        """Calcula los totales por tipo de asignatura y el total general."""
        for record in self:
            total_selection = 0
            total_oral_test = 0
            total_electives = 0
            total_regular = 0
            total_bskills = 0
            
            for line in record.line_ids:
                if line.subject_type_code == "selection":
                    total_selection += line.calculated_total
                elif line.subject_type_code == "oral_test":
                    total_oral_test += line.calculated_total
                elif line.subject_type_code == "elective":
                    total_electives += line.calculated_total
                elif line.subject_type_code == "regular":
                    total_regular += line.calculated_total
                elif line.subject_type_code == "bskills":
                    total_bskills += line.calculated_total
            
            record.total_selection = total_selection
            record.total_oral_test = total_oral_test
            record.total_electives = total_electives
            record.total_regular = total_regular
            record.total_bskills = total_bskills
            record.total_subjects = (
                total_selection + total_oral_test + total_electives + 
                total_regular + total_bskills
            )

    def _compute_enrollment_count(self):
        """Calcula el número de matrículas activas con este plan comercial."""
        for record in self:
            record.enrollment_count = self.env["benglish.enrollment"].search_count([
                ("commercial_plan_id", "=", record.id),
                ("state", "in", ["active", "in_progress", "enrolled"]),
            ])

    # ═══════════════════════════════════════════════════════════════════════════
    # ACCIONES DE CAMBIO DE ESTADO
    # ═══════════════════════════════════════════════════════════════════════════

    def action_activate(self):
        """Activa el plan comercial haciéndolo disponible para matrículas."""
        for record in self:
            if not record.line_ids:
                raise ValidationError(
                    _("No puede activar un plan comercial sin líneas de configuración.")
                )
            record.state = "active"
        return True

    def action_set_draft(self):
        """Vuelve el plan a borrador."""
        for record in self:
            if record.enrollment_count > 0:
                raise ValidationError(
                    _("No puede pasar a borrador un plan con matrículas activas. "
                      "Debe archivar el plan en su lugar.")
                )
            record.state = "draft"
        return True

    def action_archive(self):
        """Archiva el plan comercial, dejándolo como histórico."""
        for record in self:
            record.state = "archived"
        return True

    def action_unarchive(self):
        """Reactiva un plan archivado, volviéndolo a estado activo."""
        for record in self:
            record.state = "active"
        return True

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTODOS CRUD
    # ═══════════════════════════════════════════════════════════════════════════

    @api.model_create_multi
    def create(self, vals_list):
        """Genera código automático al crear."""
        for vals in vals_list:
            if vals.get("code", "/") == "/":
                vals["code"] = self.env["ir.sequence"].next_by_code(
                    "benglish.commercial.plan"
                ) or self._generate_code()
        return super().create(vals_list)

    def _generate_code(self):
        """Genera código si no hay secuencia configurada."""
        max_code = self.search([], order="id desc", limit=1)
        if max_code and max_code.code and max_code.code != "/":
            try:
                num = int(max_code.code.replace("CP-", ""))
                return f"CP-{num + 1:03d}"
            except ValueError:
                pass
        return "CP-001"

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTODOS DE NEGOCIO
    # ═══════════════════════════════════════════════════════════════════════════

    def get_requirements_for_level(self, level_sequence):
        """
        Obtiene los requisitos de asignaturas para un nivel específico.
        
        Args:
            level_sequence: Número de secuencia del nivel (1, 2, 3... 24)
            
        Returns:
            dict: Diccionario con cantidades por tipo de asignatura para ese nivel
            {
                'selection': 1,
                'oral_test': 0 o 1 (según intervalo),
                'elective': 2,
                ...
            }
        """
        self.ensure_one()
        result = {
            'selection': 0,
            'oral_test': 0,
            'elective': 0,
            'regular': 0,
            'bskills': 0,
        }
        
        # Verificar que el nivel esté en el rango del plan
        if level_sequence < self.level_start or level_sequence > self.level_end:
            return result
        
        for line in self.line_ids:
            quantity = line.get_quantity_for_level(level_sequence, self.total_levels)
            result[line.subject_type] = quantity
        
        return result

    def get_all_level_requirements(self):
        """
        Obtiene los requisitos para todos los niveles del plan.
        
        Returns:
            list: Lista de diccionarios con requisitos por nivel
        """
        self.ensure_one()
        requirements = []
        
        for level_num in range(self.level_start, self.level_end + 1):
            level_req = self.get_requirements_for_level(level_num)
            level_req['level_number'] = level_num
            requirements.append(level_req)
        
        return requirements

    def action_view_enrollments(self):
        """Acción para ver las matrículas con este plan comercial."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Matrículas - {self.name}",
            "res_model": "benglish.enrollment",
            "view_mode": "list,form",
            "domain": [("commercial_plan_id", "=", self.id)],
            "context": {"default_commercial_plan_id": self.id},
        }

    def action_preview_requirements(self):
        """Acción para previsualizar los requisitos por nivel."""
        self.ensure_one()
        requirements = self.get_all_level_requirements()
        
        # Crear mensaje HTML con la tabla de requisitos
        html = "<table class='table table-sm'>"
        html += "<thead><tr>"
        html += "<th>Nivel</th><th>Selección</th><th>Oral Test</th>"
        html += "<th>Electivas</th><th>Regular</th><th>B-Skills</th><th>Total</th>"
        html += "</tr></thead><tbody>"
        
        for req in requirements:
            total = sum([
                req['selection'], req['oral_test'], req['elective'],
                req['regular'], req['bskills']
            ])
            html += f"<tr>"
            html += f"<td><strong>{req['level_number']}</strong></td>"
            html += f"<td>{req['selection']}</td>"
            html += f"<td>{req['oral_test']}</td>"
            html += f"<td>{req['elective']}</td>"
            html += f"<td>{req['regular']}</td>"
            html += f"<td>{req['bskills']}</td>"
            html += f"<td><strong>{total}</strong></td>"
            html += f"</tr>"
        
        html += "</tbody></table>"
        
        # Mostrar en un wizard o notificación
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": f"Requisitos por Nivel - {self.name}",
                "message": f"Total asignaturas: {self.total_subjects}",
                "type": "info",
                "sticky": False,
            }
        }
