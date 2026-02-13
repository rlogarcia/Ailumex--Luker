# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SubjectType(models.Model):
    """
    Modelo para gestionar los Tipos de Asignatura.
    Permite configurar dinámicamente los tipos disponibles para las asignaturas.
    """

    _name = "benglish.subject.type"
    _description = "Tipo de Asignatura"
    _order = "sequence, name"

    name = fields.Char(
        string="Nombre",
        required=True,
        help="Nombre del tipo de asignatura (ej: Núcleo, Electiva, Complementaria)",
    )
    code = fields.Char(
        string="Código",
        help="Código único para identificar el tipo de asignatura",
    )
    sequence = fields.Integer(
        string="Secuencia",
        default=10,
        help="Orden de visualización del tipo de asignatura",
    )
    description = fields.Text(
        string="Descripción",
        help="Descripción detallada del tipo de asignatura",
    )
    active = fields.Boolean(
        string="Activo",
        default=True,
        help="Si está desmarcado, el tipo de asignatura no estará disponible para seleccionar",
    )
    color = fields.Integer(
        string="Color",
        help="Color para identificar visualmente el tipo de asignatura",
    )
    subject_count = fields.Integer(
        string="Asignaturas",
        compute="_compute_subject_count",
        help="Número de asignaturas con este tipo",
    )

    _sql_constraints = [
        (
            "code_unique",
            "UNIQUE(code)",
            "El código del tipo de asignatura debe ser único.",
        ),
    ]

    @api.depends()
    def _compute_subject_count(self):
        """Calcula el número de asignaturas que tienen este tipo."""
        for record in self:
            record.subject_count = self.env["benglish.subject"].search_count(
                [("subject_type_id", "=", record.id)]
            )

    def action_view_subjects(self):
        """Abre la vista de asignaturas filtrada por este tipo."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Asignaturas - {self.name}",
            "res_model": "benglish.subject",
            "view_mode": "tree,form",
            "domain": [("subject_type_id", "=", self.id)],
            "context": {"default_subject_type_id": self.id},
        }
