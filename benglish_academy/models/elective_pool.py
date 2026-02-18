# -*- coding: utf-8 -*-
"""
Modelo Pool de Electivas por Fase (Fase 2).

Permite configurar pools de asignaturas electivas por fase/periodo,
agrupando opciones electivas que los estudiantes pueden seleccionar
según su nivel académico y periodo de matrícula.

Reglas de negocio:
- RF3: Pool de Electivas por Fase
- Agrupa asignaturas electivas ofertadas para una fase específica
- Cada pool tiene un valor de conteo (normalmente 1 por asignatura seleccionada)
- Se vincula a un periodo académico y fase específica
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ElectivePool(models.Model):
    """
    Pool de Electivas por Fase.
    
    Tabla: benglish_elective_pool (equivalente a Pool_Electivas en BD)
    
    Agrupa asignaturas electivas ofertadas para una fase específica,
    permitiendo que el Gestor Académico configure qué asignaturas electivas
    están disponibles para cada fase del programa.
    
    En fases posteriores (Portal), los estudiantes verán solo las asignaturas
    electivas de su fase actual según estos pools.
    
    Ejemplo:
    - Pool "Electivas Básico 2025-1": Fase Básico, 10 asignaturas electivas
    - Pool "Electivas Intermedio 2025-1": Fase Intermedio, 15 asignaturas electivas
    """

    _name = "benglish.elective.pool"
    _description = "Pool de Electivas"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"
    _rec_name = "display_name"

    # ==========================================
    # CAMPOS BÁSICOS
    # ==========================================

    name = fields.Char(
        string="Nombre del Pool",
        required=True,
        tracking=True,
        help="Nombre descriptivo del pool de electivas (ej: 'Electivas Básico 2025-1')",
    )

    alias = fields.Char(
        string="Alias",
        tracking=True,
        help="Alias o nombre corto del pool para mostrar a los estudiantes",
    )

    code = fields.Char(
        string="Código",
        copy=False,
        readonly=True,
        default="/",
        tracking=True,
        index=True,
        help="Código único generado automáticamente (ej: POOL-001)",
    )

    sequence = fields.Integer(
        string="Secuencia",
        default=10,
        help="Orden de visualización del pool",
    )

    active = fields.Boolean(
        string="Activo",
        default=True,
        tracking=True,
        help="Si está inactivo, el pool no se muestra en portales ni agendamientos",
    )

    is_evaluable = fields.Boolean(
        string="¿Es Evaluable?",
        default=False,
        tracking=True,
        help="Indica si esta asignatura electiva es evaluable (tiene calificación/nota).",
    )

    description = fields.Text(
        string="Descripción",
        help="Descripción detallada del pool y sus electivas",
    )

    # ==========================================
    # CONFIGURACIÓN DE FECHAS/PERIODO
    # ==========================================

    # Rango de fechas para vigencia del pool
    date_start = fields.Date(
        string="Fecha de Inicio",
        tracking=True,
        help="Fecha de inicio de vigencia del pool (opcional)",
    )

    date_end = fields.Date(
        string="Fecha de Fin",
        tracking=True,
        help="Fecha de fin de vigencia del pool (opcional)",
    )

    # ==========================================
    # CONFIGURACIÓN DE VALOR
    # ==========================================

    count_value = fields.Integer(
        string="Valor por Asignatura",
        default=1,
        required=True,
        tracking=True,
        help=(
            "Valor que suma cada asignatura electiva seleccionada del pool. "
            "Normalmente 1, pero puede variar según configuración académica."
        ),
    )

    # ==========================================
    # CAMPOS COMPUTADOS
    # ==========================================

    display_name = fields.Char(
        string="Nombre Completo",
        compute="_compute_display_name",
        store=True,
        help="Nombre completo para visualización",
    )

    # ==========================================
    # MÉTODOS COMPUTADOS
    # ==========================================

    @api.depends("name", "code")
    def _compute_display_name(self):
        """Genera nombre completo para visualización."""
        for record in self:
            if record.code and record.code != "/":
                parts = [record.code]
            else:
                parts = []
            
            if record.name:
                parts.append(record.name)
            
            record.display_name = " - ".join(parts) if parts else _("Nuevo Pool de Electivas")

    # ==========================================
    # MÉTODOS DE CREACIÓN Y CÓDIGO
    # ==========================================

    def _get_next_reusable_pool_code(self):
        """
        Obtiene el próximo código de pool reutilizando huecos si existen.
        Busca el primer número disponible entre los códigos existentes.
        """
        import re
        prefix = "POOL-"
        padding = 3
        
        # Obtener todos los códigos usados
        existing = self.sudo().search([('code', '=like', f'{prefix}%')])
        used_numbers = set()
        
        for record in existing:
            if record.code:
                match = re.match(r'^POOL-(\d+)$', record.code)
                if match:
                    used_numbers.add(int(match.group(1)))
        
        # Buscar primer hueco
        if used_numbers:
            for num in range(1, max(used_numbers) + 2):
                if num not in used_numbers:
                    return f"{prefix}{num:0{padding}d}"
        
        # No hay registros existentes, empezar en 1
        return f"{prefix}001"

    @api.model_create_multi
    def create(self, vals_list):
        """Genera código automático al crear, reutilizando huecos."""
        for vals in vals_list:
            if vals.get("code", "/") == "/":
                vals["code"] = self._get_next_reusable_pool_code()
        
        records = super(ElectivePool, self).create(vals_list)
        
        for record in records:
            _logger.info(
                "Pool de electivas creado: %s (ID: %s)",
                record.code,
                record.id,
            )
        
        return records

    # ==========================================
    # VALIDACIONES Y CONSTRAINTS
    # ==========================================

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        """Valida que las fechas sean coherentes."""
        for record in self:
            if record.date_start and record.date_end:
                if record.date_end < record.date_start:
                    raise ValidationError(
                        _(
                            "Fechas inválidas:\n\n"
                            "La fecha de fin (%s) no puede ser anterior a la fecha de inicio (%s)."
                        ) % (record.date_end, record.date_start)
                    )

    @api.constrains("count_value")
    def _check_count_value(self):
        """Valida que el valor de conteo sea positivo."""
        for record in self:
            if record.count_value <= 0:
                raise ValidationError(
                    _(
                        "El valor por asignatura debe ser mayor a cero.\n\n"
                        "Valor actual: %s"
                    ) % record.count_value
                )

    @api.constrains("name", "active")
    def _check_unique_active_pool(self):
        """
        Valida que no haya múltiples pools activos con el mismo nombre.
        
        Nota: Esta validación se puede ajustar según necesidades de negocio.
        """
        for record in self:
            if record.active:
                duplicates = self.search([
                    ("name", "=", record.name),
                    ("id", "!=", record.id),
                    ("active", "=", True),
                ])
                
                if duplicates:
                    raise ValidationError(
                        _(
                            "Pool duplicado detectado:\n\n"
                            "Ya existe un pool activo con el nombre '%s'.\n\n"
                            "Modifique el nombre o inactive el pool existente."
                        ) % record.name
                    )

    # Constraints SQL
    _sql_constraints = [
        (
            "count_value_positive",
            "CHECK(count_value > 0)",
            "El valor por asignatura debe ser mayor a cero.",
        ),
    ]
