# -*- coding: utf-8 -*-
"""
Modelo de Línea de Plan Comercial.

Define la configuración de cantidad de asignaturas por tipo que un estudiante
debe cursar en un plan comercial específico.

Modos de cálculo:
- POR NIVEL: X asignaturas por cada nivel (ej: 2 electivas por nivel)
- CADA X NIVELES: 1 asignatura cada X niveles (ej: 1 oral test cada 4 niveles)
- TOTAL FIJO: Cantidad fija total (para casos especiales)
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class CommercialPlanLine(models.Model):
    """
    Línea de configuración del Plan Comercial.
    
    Cada línea define cuántas asignaturas de un tipo específico
    debe cursar el estudiante y cómo se calculan.
    
    Ejemplos:
    - Selección: 1 por nivel → 24 niveles = 24 selecciones
    - Oral Test: 1 cada 4 niveles → 24 niveles = 6 oral tests
    - Electivas: 2 por nivel → 24 niveles = 48 electivas
    """

    _name = "benglish.commercial.plan.line"
    _description = "Línea de Plan Comercial"
    _order = "plan_id, sequence, subject_type_id"
    _rec_name = "display_name"

    # ═══════════════════════════════════════════════════════════════════════════
    # IDENTIFICACIÓN
    # ═══════════════════════════════════════════════════════════════════════════

    display_name = fields.Char(
        string="Nombre",
        compute="_compute_display_name",
        store=True,
    )

    sequence = fields.Integer(
        string="Secuencia",
        default=10,
        help="Orden de visualización",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RELACIÓN CON PLAN COMERCIAL
    # ═══════════════════════════════════════════════════════════════════════════

    plan_id = fields.Many2one(
        comodel_name="benglish.commercial.plan",
        string="Plan Comercial",
        required=True,
        ondelete="cascade",
        index=True,
        help="Plan comercial al que pertenece esta configuración",
    )

    program_id = fields.Many2one(
        comodel_name="benglish.program",
        string="Programa",
        related="plan_id.program_id",
        store=True,
        readonly=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # TIPO DE ASIGNATURA
    # ═══════════════════════════════════════════════════════════════════════════

    subject_type_id = fields.Many2one(
        comodel_name="benglish.subject.type",
        string="Tipo de Asignatura",
        required=True,
        index=True,
        ondelete="restrict",
        help="Tipo de asignatura configurable que determina esta línea del plan comercial",
    )

    subject_type_code = fields.Char(
        string="Código del Tipo",
        related="subject_type_id.code",
        store=True,
        readonly=True,
        help="Código del tipo de asignatura para facilitar comparaciones",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # MODO DE CÁLCULO
    # ═══════════════════════════════════════════════════════════════════════════

    calculation_mode = fields.Selection(
        selection=[
            ("per_level", "Por Nivel"),
            ("per_x_levels", "Cada X Niveles"),
            ("fixed_total", "Total Fijo"),
        ],
        string="Modo de Cálculo",
        required=True,
        default="per_level",
        help="Cómo se calcula la cantidad de asignaturas:\n"
             "- Por Nivel: X asignaturas por cada nivel\n"
             "- Cada X Niveles: 1 asignatura cada X niveles\n"
             "- Total Fijo: Cantidad fija total",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # VALORES DE CONFIGURACIÓN
    # ═══════════════════════════════════════════════════════════════════════════

    quantity_per_level = fields.Integer(
        string="Cantidad por Nivel",
        default=1,
        help="Número de asignaturas de este tipo por cada nivel.\n"
             "Aplica cuando el modo es 'Por Nivel'.\n"
             "Ejemplo: 2 electivas por nivel",
    )

    levels_interval = fields.Integer(
        string="Intervalo de Niveles",
        default=4,
        help="Cada cuántos niveles se requiere una asignatura de este tipo.\n"
             "Aplica cuando el modo es 'Cada X Niveles'.\n"
             "Ejemplo: 1 oral test cada 4 niveles",
    )

    fixed_quantity = fields.Integer(
        string="Cantidad Fija",
        default=0,
        help="Cantidad fija total de asignaturas de este tipo.\n"
             "Aplica cuando el modo es 'Total Fijo'.",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # TOTAL CALCULADO
    # ═══════════════════════════════════════════════════════════════════════════

    calculated_total = fields.Integer(
        string="Total Calculado",
        compute="_compute_calculated_total",
        store=True,
        help="Total de asignaturas de este tipo según la configuración",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURACIÓN ADICIONAL PARA ELECTIVAS
    # ═══════════════════════════════════════════════════════════════════════════

    elective_pool_id = fields.Many2one(
        comodel_name="benglish.elective.pool",
        string="Pool de Electivas",
        ondelete="set null",
        help="Pool de electivas del cual se tomarán las asignaturas.\n"
             "Solo aplica para tipo 'Electiva'.",
    )

    use_phase_pool = fields.Boolean(
        string="Usar Pool de la Fase",
        default=True,
        help="Si está marcado, se usará el pool de electivas de la fase actual del estudiante.\n"
             "Si no, se usará el pool específico configurado.",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # DESCRIPCIÓN Y NOTAS
    # ═══════════════════════════════════════════════════════════════════════════

    notes = fields.Text(
        string="Notas",
        help="Notas adicionales sobre esta configuración",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RESTRICCIONES SQL
    # ═══════════════════════════════════════════════════════════════════════════

    _sql_constraints = [
        (
            "unique_plan_subject_type",
            "UNIQUE(plan_id, subject_type_id)",
            "Solo puede haber una configuración por tipo de asignatura en cada plan.",
        ),
        (
            "quantity_positive",
            "CHECK(quantity_per_level >= 0 AND fixed_quantity >= 0)",
            "Las cantidades deben ser positivas o cero.",
        ),
        (
            "interval_positive",
            "CHECK(levels_interval > 0)",
            "El intervalo de niveles debe ser mayor a cero.",
        ),
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTODOS COMPUTE
    # ═══════════════════════════════════════════════════════════════════════════

    @api.depends("subject_type_id", "subject_type_id.name", "calculation_mode", "calculated_total")
    def _compute_display_name(self):
        mode_names = dict(self._fields["calculation_mode"].selection)
        
        for record in self:
            type_name = record.subject_type_id.name if record.subject_type_id else "Sin Tipo"
            mode_name = mode_names.get(record.calculation_mode, "")
            record.display_name = f"{type_name} ({mode_name}) = {record.calculated_total}"

    @api.depends(
        "calculation_mode", 
        "quantity_per_level", 
        "levels_interval", 
        "fixed_quantity",
        "plan_id.total_levels"
    )
    def _compute_calculated_total(self):
        """Calcula el total de asignaturas según el modo de cálculo."""
        for record in self:
            total_levels = record.plan_id.total_levels if record.plan_id else 0
            
            if record.calculation_mode == "per_level":
                # X asignaturas por cada nivel
                record.calculated_total = record.quantity_per_level * total_levels
                
            elif record.calculation_mode == "per_x_levels":
                # 1 asignatura cada X niveles
                if record.levels_interval > 0:
                    record.calculated_total = total_levels // record.levels_interval
                else:
                    record.calculated_total = 0
                    
            elif record.calculation_mode == "fixed_total":
                # Cantidad fija
                record.calculated_total = record.fixed_quantity
            else:
                record.calculated_total = 0

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTODOS DE NEGOCIO
    # ═══════════════════════════════════════════════════════════════════════════

    def get_quantity_for_level(self, level_sequence, total_levels):
        """
        Obtiene la cantidad de asignaturas de este tipo para un nivel específico.
        
        Args:
            level_sequence: Número de secuencia del nivel (1, 2, 3... 24)
            total_levels: Total de niveles del plan
            
        Returns:
            int: Cantidad de asignaturas de este tipo para ese nivel
        """
        self.ensure_one()
        
        if self.calculation_mode == "per_level":
            # Siempre la misma cantidad por nivel
            return self.quantity_per_level
            
        elif self.calculation_mode == "per_x_levels":
            # Solo en niveles múltiplos del intervalo
            # Por ejemplo, si intervalo es 4: niveles 4, 8, 12, 16, 20, 24
            if level_sequence % self.levels_interval == 0:
                return 1
            return 0
            
        elif self.calculation_mode == "fixed_total":
            # Distribuir equitativamente entre todos los niveles
            # O devolver 0 si se maneja de otra forma
            if total_levels > 0:
                per_level = self.fixed_quantity // total_levels
                remainder = self.fixed_quantity % total_levels
                # Los primeros niveles reciben el extra si no es divisible exactamente
                if level_sequence <= remainder:
                    return per_level + 1
                return per_level
            return 0
        
        return 0

    def get_level_numbers_with_this_type(self):
        """
        Obtiene los números de nivel donde aplica este tipo de asignatura.
        
        Returns:
            list: Lista de números de nivel donde se requiere este tipo
        """
        self.ensure_one()
        result = []
        
        if not self.plan_id:
            return result
        
        for level_num in range(self.plan_id.level_start, self.plan_id.level_end + 1):
            quantity = self.get_quantity_for_level(
                level_num, 
                self.plan_id.total_levels
            )
            if quantity > 0:
                result.append({
                    'level': level_num,
                    'quantity': quantity,
                })
        
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTODOS ONCHANGE
    # ═══════════════════════════════════════════════════════════════════════════

    @api.onchange("calculation_mode")
    def _onchange_calculation_mode(self):
        """Establece valores por defecto según el modo de cálculo."""
        if self.calculation_mode == "per_level":
            self.quantity_per_level = 1
            self.levels_interval = 0
            self.fixed_quantity = 0
        elif self.calculation_mode == "per_x_levels":
            self.quantity_per_level = 0
            self.levels_interval = 4
            self.fixed_quantity = 0
        elif self.calculation_mode == "fixed_total":
            self.quantity_per_level = 0
            self.levels_interval = 0
            self.fixed_quantity = 10

    @api.onchange("subject_type_id")
    def _onchange_subject_type(self):
        """Sugiere modo de cálculo según el tipo de asignatura."""
        if self.subject_type_code == "oral_test":
            # Los oral tests típicamente son cada X niveles
            self.calculation_mode = "per_x_levels"
            self.levels_interval = 4
        elif self.subject_type_code in ("selection", "elective", "bskills"):
            # Estos típicamente son por nivel
            self.calculation_mode = "per_level"
            self.quantity_per_level = 1 if self.subject_type_code == "selection" else 2
