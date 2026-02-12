# -*- coding: utf-8 -*-
"""
Modelo de Periodo Académico.

Gestiona los períodos académicos (semestres, cuatrimestres, años, etc.)
para organizar la programación y matrícula de estudiantes.

Equivalencia con el modelo de datos:
- Tabla: Periodo
- Campos: Id_Periodo, Nom_Periodo, Estado_Periodo
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class AcademicPeriod(models.Model):
    """
    Periodo Académico.
    
    Define períodos de tiempo para organizar la programación académica.
    Puede ser usado para agrupar matrículas, agendas, clases, etc.
    
    Ejemplos:
    - Semestre 2026-1 (Ene-Jun 2026)
    - Cuatrimestre 2026-I (Ene-Abr 2026)
    - Año Académico 2026
    """

    _name = "benglish.academic.period"
    _description = "Periodo Académico"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_start desc, sequence, name"
    _rec_name = "display_name"

    # ═══════════════════════════════════════════════════════════════════════════
    # IDENTIFICACIÓN
    # ═══════════════════════════════════════════════════════════════════════════

    name = fields.Char(
        string="Nombre del Periodo",
        required=True,
        tracking=True,
        help="Nombre descriptivo del periodo (ej: Semestre 2026-1)",
    )

    code = fields.Char(
        string="Código",
        required=True,
        tracking=True,
        index=True,
        help="Código único del periodo (ej: 2026-1, 2026-I, etc.)",
    )

    display_name = fields.Char(
        string="Nombre Completo",
        compute="_compute_display_name",
        store=True,
    )

    sequence = fields.Integer(
        string="Secuencia",
        default=10,
        help="Orden de visualización",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # TIPO DE PERIODO
    # ═══════════════════════════════════════════════════════════════════════════

    period_type = fields.Selection(
        selection=[
            ("semester", "Semestre"),
            ("quarter", "Cuatrimestre"),
            ("trimester", "Trimestre"),
            ("year", "Año Académico"),
            ("month", "Mensual"),
            ("week", "Semanal"),
            ("custom", "Personalizado"),
        ],
        string="Tipo de Periodo",
        required=True,
        default="semester",
        tracking=True,
        help="Tipo de período académico",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # FECHAS
    # ═══════════════════════════════════════════════════════════════════════════

    date_start = fields.Date(
        string="Fecha de Inicio",
        required=True,
        tracking=True,
        index=True,
        help="Fecha de inicio del periodo",
    )

    date_end = fields.Date(
        string="Fecha de Fin",
        required=True,
        tracking=True,
        index=True,
        help="Fecha de fin del periodo",
    )

    enrollment_date_start = fields.Date(
        string="Inicio de Matrículas",
        help="Fecha desde la cual se pueden realizar matrículas para este periodo",
    )

    enrollment_date_end = fields.Date(
        string="Fin de Matrículas",
        help="Fecha límite para realizar matrículas en este periodo",
    )

    duration_days = fields.Integer(
        string="Duración (días)",
        compute="_compute_duration",
        store=True,
        help="Duración del periodo en días",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # ESTADO
    # ═══════════════════════════════════════════════════════════════════════════

    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("open", "Matrículas Abiertas"),
            ("active", "En Curso"),
            ("closed", "Cerrado"),
            ("archived", "Archivado"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
        help="Estado del periodo académico",
    )

    active = fields.Boolean(
        string="Activo",
        default=True,
        help="Si está inactivo, el periodo no aparecerá en las búsquedas normales",
    )

    is_current = fields.Boolean(
        string="Es Periodo Actual",
        compute="_compute_is_current",
        store=True,
        help="Indica si este es el periodo actual basado en las fechas",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RELACIONES
    # ═══════════════════════════════════════════════════════════════════════════

    program_id = fields.Many2one(
        comodel_name="benglish.program",
        string="Programa",
        ondelete="restrict",
        help="Si se define, este periodo aplica solo a un programa específico. "
        "Si está vacío, aplica a todos los programas.",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        default=lambda self: self.env.company,
        required=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # ESTADÍSTICAS
    # ═══════════════════════════════════════════════════════════════════════════

    enrollment_count = fields.Integer(
        string="Matrículas",
        compute="_compute_enrollment_count",
        help="Número de matrículas en este periodo",
    )

    agenda_count = fields.Integer(
        string="Agendas",
        compute="_compute_agenda_count",
        help="Número de agendas programadas en este periodo",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # NOTAS
    # ═══════════════════════════════════════════════════════════════════════════

    description = fields.Text(
        string="Descripción",
        help="Notas o descripción adicional del periodo",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RESTRICCIONES SQL
    # ═══════════════════════════════════════════════════════════════════════════

    _sql_constraints = [
        (
            "code_company_unique",
            "UNIQUE(code, company_id)",
            "El código del periodo debe ser único por compañía.",
        ),
        (
            "date_range_valid",
            "CHECK(date_end >= date_start)",
            "La fecha de fin debe ser posterior o igual a la fecha de inicio.",
        ),
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTODOS COMPUTE
    # ═══════════════════════════════════════════════════════════════════════════

    @api.depends("name", "code", "period_type")
    def _compute_display_name(self):
        period_labels = dict(self._fields["period_type"].selection)
        for record in self:
            parts = []
            if record.code:
                parts.append(f"[{record.code}]")
            if record.name:
                parts.append(record.name)
            record.display_name = " ".join(parts) if parts else "Nuevo Periodo"

    @api.depends("date_start", "date_end")
    def _compute_duration(self):
        for record in self:
            if record.date_start and record.date_end:
                record.duration_days = (record.date_end - record.date_start).days + 1
            else:
                record.duration_days = 0

    @api.depends("date_start", "date_end")
    def _compute_is_current(self):
        today = date.today()
        for record in self:
            if record.date_start and record.date_end:
                record.is_current = record.date_start <= today <= record.date_end
            else:
                record.is_current = False

    def _compute_enrollment_count(self):
        """Calcula el número de matrículas en este periodo."""
        Enrollment = self.env["benglish.enrollment"]
        for record in self:
            # Si hay campo period_id en enrollment
            if "period_id" in Enrollment._fields:
                record.enrollment_count = Enrollment.search_count([
                    ("period_id", "=", record.id),
                ])
            else:
                # Contar por rango de fechas
                record.enrollment_count = Enrollment.search_count([
                    ("enrollment_date", ">=", record.date_start),
                    ("enrollment_date", "<=", record.date_end),
                ])

    def _compute_agenda_count(self):
        """Calcula el número de agendas en este periodo."""
        Agenda = self.env["benglish.academic.agenda"]
        for record in self:
            # Si hay campo period_id en agenda
            if "period_id" in Agenda._fields:
                record.agenda_count = Agenda.search_count([
                    ("period_id", "=", record.id),
                ])
            else:
                # Contar por rango de fechas
                record.agenda_count = Agenda.search_count([
                    ("date_start", ">=", record.date_start),
                    ("date_end", "<=", record.date_end),
                ])

    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDACIONES
    # ═══════════════════════════════════════════════════════════════════════════

    @api.constrains("enrollment_date_start", "enrollment_date_end", "date_start", "date_end")
    def _check_enrollment_dates(self):
        for record in self:
            if record.enrollment_date_start and record.enrollment_date_end:
                if record.enrollment_date_end < record.enrollment_date_start:
                    raise ValidationError(
                        _("La fecha de fin de matrículas debe ser posterior al inicio.")
                    )

    # ═══════════════════════════════════════════════════════════════════════════
    # ACCIONES DE ESTADO
    # ═══════════════════════════════════════════════════════════════════════════

    def action_open_enrollment(self):
        """Abre el periodo para matrículas."""
        for record in self:
            record.state = "open"
        return True

    def action_start(self):
        """Marca el periodo como activo/en curso."""
        for record in self:
            record.state = "active"
        return True

    def action_close(self):
        """Cierra el periodo."""
        for record in self:
            record.state = "closed"
        return True

    def action_archive(self):
        """Archiva el periodo."""
        for record in self:
            record.state = "archived"
            record.active = False
        return True

    def action_set_draft(self):
        """Vuelve el periodo a borrador."""
        for record in self:
            record.state = "draft"
            record.active = True
        return True

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTODOS DE NEGOCIO
    # ═══════════════════════════════════════════════════════════════════════════

    @api.model
    def get_current_period(self, program_id=None):
        """
        Obtiene el periodo actual (activo y dentro de las fechas).
        
        Args:
            program_id: ID del programa (opcional) para filtrar
            
        Returns:
            benglish.academic.period record o False
        """
        today = date.today()
        domain = [
            ("date_start", "<=", today),
            ("date_end", ">=", today),
            ("state", "in", ["open", "active"]),
        ]
        
        if program_id:
            domain.append("|")
            domain.append(("program_id", "=", False))
            domain.append(("program_id", "=", program_id))
        
        return self.search(domain, limit=1, order="date_start desc")

    @api.model
    def get_enrollment_period(self, program_id=None):
        """
        Obtiene el periodo con matrículas abiertas.
        
        Args:
            program_id: ID del programa (opcional) para filtrar
            
        Returns:
            benglish.academic.period record o False
        """
        today = date.today()
        domain = [
            ("state", "=", "open"),
            "|",
            "&", ("enrollment_date_start", "=", False), ("enrollment_date_end", "=", False),
            "&", ("enrollment_date_start", "<=", today), ("enrollment_date_end", ">=", today),
        ]
        
        if program_id:
            domain.extend([
                "|",
                ("program_id", "=", False),
                ("program_id", "=", program_id),
            ])
        
        return self.search(domain, limit=1, order="date_start desc")

    def action_view_enrollments(self):
        """Acción para ver las matrículas del periodo."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Matrículas - {self.name}",
            "res_model": "benglish.enrollment",
            "view_mode": "list,form",
            "domain": [
                ("enrollment_date", ">=", self.date_start),
                ("enrollment_date", "<=", self.date_end),
            ],
            "context": {"default_enrollment_date": self.date_start},
        }

    def action_view_agendas(self):
        """Acción para ver las agendas del periodo."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Agendas - {self.name}",
            "res_model": "benglish.academic.agenda",
            "view_mode": "list,form,calendar",
            "domain": [
                ("date_start", ">=", self.date_start),
                ("date_end", "<=", self.date_end),
            ],
        }
