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
from odoo.exceptions import ValidationError, UserError
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
    _description = "Pool de Electivas por Fase"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "phase_id, sequence, name"
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

    description = fields.Text(
        string="Descripción",
        help="Descripción detallada del pool y sus electivas",
    )

    # ==========================================
    # RELACIONES ACADÉMICAS
    # ==========================================

    phase_id = fields.Many2one(
        comodel_name="benglish.phase",
        string="Fase",
        required=True,
        ondelete="restrict",
        tracking=True,
        index=True,
        help="Fase académica a la que pertenece este pool de electivas",
    )

    # Nota: En el modelo original se menciona Id_Periodo, pero en la estructura
    # actual no existe un modelo de Periodo Académico explícito.
    # Se puede agregar si existe o usar campos de fecha directamente.
    
    # Si existe modelo de periodo académico (benglish.academic.period), descomentar:
    # period_id = fields.Many2one(
    #     comodel_name="benglish.academic.period",
    #     string="Periodo Académico",
    #     required=True,
    #     ondelete="restrict",
    #     tracking=True,
    #     help="Periodo académico al que aplica este pool de electivas",
    # )

    # Alternativa: usar rango de fechas si no existe modelo de periodo
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
    # RELACIÓN CON ASIGNATURAS ELECTIVAS
    # ==========================================

    subject_ids = fields.Many2many(
        comodel_name="benglish.subject",
        relation="benglish_elective_pool_subject_rel",
        column1="pool_id",
        column2="subject_id",
        string="Asignaturas Electivas",
        tracking=True,
        help="Asignaturas electivas disponibles en este pool para la fase seleccionada",
    )

    subject_count = fields.Integer(
        string="Número de Asignaturas",
        compute="_compute_subject_count",
        store=True,
        help="Total de asignaturas electivas en este pool",
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
    # ESTADO Y CONTROL
    # ==========================================

    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("active", "Activo"),
            ("closed", "Cerrado"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
        help="Estado del pool: Borrador (configuración), Activo (disponible), Cerrado (histórico)",
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

    pool_summary = fields.Char(
        string="Resumen",
        compute="_compute_pool_summary",
        store=True,
        help="Resumen del pool para vistas de lista",
    )

    # ==========================================
    # MÉTODOS COMPUTADOS
    # ==========================================

    @api.depends("name", "code", "phase_id", "phase_id.name")
    def _compute_display_name(self):
        """Genera nombre completo para visualización."""
        for record in self:
            if record.code and record.code != "/":
                parts = [record.code]
            else:
                parts = []
            
            if record.name:
                parts.append(record.name)
            
            if record.phase_id:
                parts.append(f"({record.phase_id.name})")
            
            record.display_name = " - ".join(parts) if parts else _("Nuevo Pool de Electivas")

    @api.depends("subject_ids", "phase_id", "subject_count")
    def _compute_pool_summary(self):
        """Genera resumen para vistas de lista."""
        for record in self:
            if record.phase_id and record.subject_count > 0:
                record.pool_summary = f"{record.phase_id.name} | {record.subject_count} asignatura(s)"
            elif record.phase_id:
                record.pool_summary = f"{record.phase_id.name} | Sin asignaturas"
            else:
                record.pool_summary = "Sin configurar"

    @api.depends("subject_ids")
    def _compute_subject_count(self):
        """Cuenta el total de asignaturas en el pool."""
        for record in self:
            record.subject_count = len(record.subject_ids)

    # ==========================================
    # MÉTODOS ONCHANGE
    # ==========================================

    @api.onchange("phase_id")
    def _onchange_phase_id(self):
        """
        Al cambiar la fase, solo notificar (ya no se filtran asignaturas por fase).
        """
        pass  # Las asignaturas ya no tienen fase

    # ==========================================
    # MÉTODOS DE CREACIÓN Y CÓDIGO
    # ==========================================

    @api.model_create_multi
    def create(self, vals_list):
        """Genera código automático al crear."""
        for vals in vals_list:
            if vals.get("code", "/") == "/":
                vals["code"] = self.env["ir.sequence"].next_by_code(
                    "benglish.elective.pool"
                ) or "/"
        
        records = super(ElectivePool, self).create(vals_list)
        
        for record in records:
            _logger.info(
                "Pool de electivas creado: %s (ID: %s, Fase: %s)",
                record.code,
                record.id,
                record.phase_id.name if record.phase_id else "N/A",
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

    @api.constrains("subject_ids", "phase_id")
    def _check_subjects_phase_compatibility(self):
        """
        Validación de compatibilidad de asignaturas.
        NOTA: Las asignaturas ya no tienen fase, esta validación está deshabilitada.
        """
        pass  # Las asignaturas ya no tienen fase, no se requiere validación

    @api.constrains("phase_id", "name", "active")
    def _check_unique_active_pool_per_phase(self):
        """
        Valida que no haya múltiples pools activos con el mismo nombre en la misma fase.
        
        Nota: Esta validación se puede ajustar según necesidades de negocio.
        """
        for record in self:
            if record.active and record.phase_id:
                duplicates = self.search([
                    ("phase_id", "=", record.phase_id.id),
                    ("name", "=", record.name),
                    ("id", "!=", record.id),
                    ("active", "=", True),
                ])
                
                if duplicates:
                    raise ValidationError(
                        _(
                            "Pool duplicado detectado:\n\n"
                            "Ya existe un pool activo con el nombre '%s' para la fase '%s'.\n\n"
                            "Modifique el nombre o inactive el pool existente."
                        ) % (record.name, record.phase_id.name)
                    )

    # Constraints SQL
    _sql_constraints = [
        (
            "count_value_positive",
            "CHECK(count_value > 0)",
            "El valor por asignatura debe ser mayor a cero.",
        ),
    ]

    # ==========================================
    # MÉTODOS DE NEGOCIO
    # ==========================================

    def action_activate_pool(self):
        """Activa el pool (cambia estado a 'active')."""
        for record in self:
            if record.state != "active":
                # Validar que tenga al menos una asignatura
                if not record.subject_ids:
                    raise UserError(
                        _(
                            "No se puede activar el pool sin asignaturas.\n\n"
                            "Agregue al menos una asignatura electiva antes de activar."
                        )
                    )
                
                record.write({"state": "active"})
                record.message_post(
                    body=_(
                        "Pool activado: %s asignatura(s) electiva(s) disponible(s) para la fase %s."
                    ) % (record.subject_count, record.phase_id.name),
                    subject=_("Pool Activado"),
                )
        
        return True

    def action_close_pool(self):
        """Cierra el pool (histórico)."""
        for record in self:
            if record.state == "active":
                record.write({"state": "closed"})
                record.message_post(
                    body=_("Pool cerrado y archivado como histórico."),
                    subject=_("Pool Cerrado"),
                )
        
        return True

    def action_view_subjects(self):
        """Abre vista de asignaturas del pool."""
        self.ensure_one()
        
        return {
            "type": "ir.actions.act_window",
            "name": _("Asignaturas de %s") % self.display_name,
            "res_model": "benglish.subject",
            "domain": [("id", "in", self.subject_ids.ids)],
            "view_mode": "tree,form",
            "target": "current",
            "context": {"default_phase_id": self.phase_id.id, "default_subject_type": "elective"},
        }

    def action_add_subjects_wizard(self):
        """
        Abre wizard para agregar asignaturas al pool de forma masiva.
        
        TODO: Implementar wizard en fases posteriores si se requiere.
        """
        self.ensure_one()
        
        raise UserError(
            _(
                "Wizard de adición masiva no implementado.\n\n"
                "Use el campo 'Asignaturas Electivas' para agregar asignaturas manualmente."
            )
        )
