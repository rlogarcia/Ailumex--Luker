# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ClassType(models.Model):
    """
    Modelo para gestionar Tipos de Clases.
    Define las diferentes clases disponibles según el nivel académico.
    """

    _name = "benglish.class.type"
    _description = "Tipo de Clase"
    _order = "sequence, name"
    _rec_name = "name"

    # Campos básicos
    name = fields.Char(
        string="Nombre de la Clase",
        required=True,
        help="Nombre del tipo de clase (ej: B check, B skills, Oral test, etc.)",
    )
    code = fields.Char(
        string="Código",
        required=True,
        copy=False,
        help="Código único identificador de la clase",
    )
    sequence = fields.Integer(
        string="Secuencia", default=10, help="Orden de visualización"
    )

    # Categoría de clase
    category = fields.Selection(
        selection=[
            ("bcheck", "B Check"),
            ("bskills", "B Skills"),
            ("oral_test", "Oral Test"),
            ("master_class", "Master Class"),
            ("review", "Review"),
            ("conversation_club", "Conversation Club"),
            ("international_test", "International Test Prep"),
        ],
        string="Categoría",
        required=True,
        help="Categoría principal de la clase",
    )

    # Subcategorías para B Check
    bcheck_subcategory = fields.Selection(
        selection=[
            ("unit_1", "Unidad 1"),
            ("unit_2", "Unidad 2"),
            ("unit_3", "Unidad 3"),
            ("unit_4", "Unidad 4"),
            ("unit_5", "Unidad 5"),
            ("unit_6", "Unidad 6"),
            ("unit_7", "Unidad 7"),
            ("unit_8", "Unidad 8"),
            ("unit_9", "Unidad 9"),
            ("unit_10", "Unidad 10"),
            ("unit_11", "Unidad 11"),
            ("unit_12", "Unidad 12"),
            ("unit_13", "Unidad 13"),
            ("unit_14", "Unidad 14"),
            ("unit_15", "Unidad 15"),
            ("unit_16", "Unidad 16"),
            ("unit_17", "Unidad 17"),
            ("unit_18", "Unidad 18"),
            ("unit_19", "Unidad 19"),
            ("unit_20", "Unidad 20"),
            ("unit_21", "Unidad 21"),
            ("unit_22", "Unidad 22"),
            ("unit_23", "Unidad 23"),
            ("unit_24", "Unidad 24"),
        ],
        string="Subcategoría B Check",
        help="Unidad correspondiente para clases tipo B Check",
    )

    # Niveles aplicables
    level_ids = fields.Many2many(
        comodel_name="benglish.level",
        relation="benglish_class_type_level_rel",
        column1="class_type_id",
        column2="level_id",
        string="Niveles Aplicables",
        help="Niveles en los que está disponible esta clase",
    )

    # Programas aplicables
    program_ids = fields.Many2many(
        comodel_name="benglish.program",
        relation="benglish_class_type_program_rel",
        column1="class_type_id",
        column2="program_id",
        string="Programas Aplicables",
        help="Programas (cursos) en los que está disponible esta clase",
    )

    # Características especiales
    is_mandatory = fields.Boolean(
        string="Clase Obligatoria",
        default=False,
        help="Indica si esta clase es obligatoria para el estudiante",
    )
    is_first_class = fields.Boolean(
        string="Primera Clase",
        default=False,
        help="Indica si debe ser la primera clase programada (ej: B Check)",
    )
    requires_evaluation = fields.Boolean(
        string="Requiere Evaluación",
        default=False,
        help="Indica si requiere evaluación del coach (ej: Oral Test)",
    )
    updates_unit = fields.Boolean(
        string="Actualiza Unidad",
        default=False,
        help="Al asistir, actualiza la unidad del estudiante (aplica para B Check)",
    )
    requires_prerequisite = fields.Boolean(
        string="Requiere Prerrequisito",
        default=False,
        help="Requiere haber completado clases previas (ej: Oral Test)",
    )
    prerequisite_units = fields.Char(
        string="Unidades Requeridas",
        help="Unidades que deben completarse antes (ej: 4,8,12,16,20,24 para Oral Test)",
    )

    # Prerrequisito obligatorio para agendamiento (HU-E7, HU-E8)
    is_prerequisite = fields.Boolean(
        string="Es Prerrequisito Obligatorio",
        default=False,
        help="Si está marcado, esta clase debe ser programada ANTES que cualquier otra clase de la semana. "
        "Típicamente usado para BCheck. El estudiante no podrá programar otras clases sin programar primero esta.",
    )
    enforce_prerequisite_first = fields.Boolean(
        string="Forzar Prerrequisito Primero",
        default=False,
        help="Si está marcado, al intentar desprogramar esta clase se eliminarán automáticamente "
        "todas las demás clases de la semana (con advertencia al estudiante)",
    )

    # Restricción por plan
    restricted_to_plans = fields.Selection(
        selection=[
            ("all", "Todos los Planes"),
            ("gold_only", "Solo Gold y Superiores"),
            ("premium_plus", "Premium y Superiores"),
        ],
        string="Restricción por Plan",
        default="all",
        help="Define qué planes pueden acceder a esta clase",
    )

    # Duración y capacidad
    default_duration = fields.Float(
        string="Duración por Defecto (horas)",
        default=1.0,
        help="Duración estándar de la clase en horas",
    )
    default_capacity = fields.Integer(
        string="Capacidad por Defecto",
        default=8,
        help="Número de estudiantes por defecto para esta clase",
    )

    # Descripción
    description = fields.Text(
        string="Descripción", help="Descripción de la clase y sus objetivos"
    )
    notes = fields.Text(string="Notas", help="Notas adicionales sobre la clase")

    # CAMPOS ESTRUCTURALES PARA IDENTIFICACIÓN PROGRAMÁTICA
    # Permiten identificar tipos de clase sin depender de nombres


    unit_number = fields.Integer(
        string="Número de Unidad (B-check)",
        help="Número de unidad específico para B-checks (1-24). "
        'Permite identificar "B-check 1" como unit_number=1 sin depender del nombre.',
        index=True,
    )

    unit_block_start = fields.Integer(
        string="Inicio del Bloque (Oral Test)",
        help="Unidad de inicio para Oral Tests. Ejemplo: Oral Test (1-4) → unit_block_start=1",
        index=True,
    )

    unit_block_end = fields.Integer(
        string="Fin del Bloque (Oral Test)",
        help="Unidad final para Oral Tests. Ejemplo: Oral Test (1-4) → unit_block_end=4",
        index=True,
    )

    # Estado
    active = fields.Boolean(
        string="Activo",
        default=True,
        help="Si está inactivo, la clase no estará disponible",
    )

    # Restricciones SQL
    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "El código de la clase debe ser único."),
    ]

    @api.constrains("category", "bcheck_subcategory")
    def _check_bcheck_subcategory(self):
        """Valida que las clases B Check tengan subcategoría"""
        for record in self:
            if record.category == "bcheck" and not record.bcheck_subcategory:
                raise ValidationError(
                    _(
                        "Las clases tipo B Check deben tener una subcategoría (unidad) asignada."
                    )
                )

    @api.onchange("category")
    def _onchange_category(self):
        """Ajusta campos según la categoría"""
        if self.category == "bcheck":
            self.is_first_class = True
            self.updates_unit = True
            self.is_mandatory = True
            # BCheck es prerrequisito obligatorio (HU-E7, HU-E8)
            self.is_prerequisite = True
            self.enforce_prerequisite_first = True
        elif self.category == "oral_test":
            self.requires_evaluation = True
            self.requires_prerequisite = True
            self.prerequisite_units = "4,8,12,16,20,24"
            self.is_prerequisite = False
            self.enforce_prerequisite_first = False
        elif self.category == "international_test":
            self.restricted_to_plans = "gold_only"
            self.is_prerequisite = False
            self.enforce_prerequisite_first = False
        else:
            self.is_first_class = False
            self.updates_unit = False
            self.requires_evaluation = False
            self.requires_prerequisite = False
            self.prerequisite_units = False
            self.is_prerequisite = False
            self.enforce_prerequisite_first = False

    def name_get(self):
        """Personaliza el nombre mostrado"""
        result = []
        for record in self:
            name = record.name
            if record.category == "bcheck" and record.bcheck_subcategory:
                unit_label = dict(record._fields["bcheck_subcategory"].selection).get(
                    record.bcheck_subcategory
                )
                name = f"{record.name} - {unit_label}"
            result.append((record.id, name))
        return result
