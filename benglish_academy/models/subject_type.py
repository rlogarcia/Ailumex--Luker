# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SubjectType(models.Model):
    """
    Modelo para gestionar los Tipos de Asignatura.
    Permite configurar dinámicamente los tipos disponibles para las asignaturas.
    """

    _name = "benglish.subject.type"
    _description = "Tipo de Asignatura"
    _inherit = ["mail.thread"]
    _order = "sequence, name"

    name = fields.Char(
        string="Nombre",
        required=True,
        help="Nombre del tipo de asignatura (ej: Núcleo, Electiva, Complementaria)",
    )
    code = fields.Char(
        string="Código",
        readonly=True,
        copy=False,
        default="/",
        help="Código único autogenerado para identificar el tipo de asignatura",
    )
    sequence = fields.Integer(
        string="Secuencia",
        default=10,
        help="Orden de visualización del tipo de asignatura",
    )
    description = fields.Html(
        string="Descripción",
        help="Descripción detallada del tipo de asignatura",
    )
    
    # Estado del tipo de asignatura
    state = fields.Selection(
        selection=[
            ("active", "Activo"),
            ("inactive", "Inactivo"),
        ],
        string="Estado",
        default="active",
        required=True,
        tracking=True,
        help="Estado del tipo de asignatura",
    )
    active = fields.Boolean(
        string="Activo",
        compute="_compute_active",
        store=True,
        help="Calculado automáticamente según el estado",
    )
    
    # Pool de electivas
    is_elective_pool = fields.Boolean(
        string="Pool de Electivas",
        default=False,
        help="Si está marcado, las asignaturas con este tipo aparecerán en el pool de electivas",
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
    
    @api.depends("state")
    def _compute_active(self):
        """Calcula el campo active según el estado."""
        for record in self:
            record.active = record.state == "active"
    
    @api.model_create_multi
    def create(self, vals_list):
        """Genera el código automáticamente al crear."""
        import re
        
        # PASO 1: Limpiar registros legacy con código "/" antes de crear nuevos
        legacy_records = self.search([("code", "=", "/")])
        if legacy_records:
            # Actualizar registros legacy con códigos únicos
            for idx, rec in enumerate(legacy_records, start=1):
                existing = self.search([("code", "like", "TA-%")])
                max_num = 0
                for r in existing:
                    if r.code:
                        match = re.search(r"TA-(\d+)", r.code)
                        if match:
                            try:
                                n = int(match.group(1))
                                if n > max_num:
                                    max_num = n
                            except ValueError:
                                pass
                legacy_code = f"TA-{str(max_num + idx).zfill(3)}"
                # Actualizar directamente en SQL para evitar recursión
                self.env.cr.execute(
                    "UPDATE benglish_subject_type SET code = %s WHERE id = %s",
                    (legacy_code, rec.id)
                )
        
        # PASO 2: Generar códigos para nuevos registros
        for vals in vals_list:
            if vals.get("code", "/") == "/" or not vals.get("code"):
                # Generar código único usando secuencia
                new_code = self.env["ir.sequence"].next_by_code("benglish.subject.type")
                if not new_code:
                    # Fallback: buscar el máximo numérico entre códigos existentes TA-###
                    existing = self.search([("code", "like", "TA-%")])
                    max_num = 0
                    for rec in existing:
                        if rec.code:
                            match = re.search(r"TA-(\d+)", rec.code)
                            if match:
                                try:
                                    n = int(match.group(1))
                                    if n > max_num:
                                        max_num = n
                                except ValueError:
                                    pass
                    new_code = f"TA-{str(max_num + 1).zfill(3)}"
                
                vals["code"] = new_code
        return super().create(vals_list)
    
    def action_set_active(self):
        """Acción para activar el tipo de asignatura."""
        self.write({"state": "active"})
    
    def action_set_inactive(self):
        """Acción para inactivar el tipo de asignatura."""
        self.write({"state": "inactive"})

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
