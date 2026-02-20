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
    
    def _get_next_reusable_subject_type_code(self):
        """
        Obtiene el próximo código de tipo de asignatura reutilizando huecos si existen.
        Busca el primer número disponible entre los códigos existentes.
        """
        import re
        prefix = "TA-"
        padding = 3
        
        # Obtener todos los códigos usados
        existing = self.sudo().search([('code', '=like', f'{prefix}%')])
        used_numbers = set()
        
        for record in existing:
            if record.code:
                match = re.match(r'^TA-(\d+)$', record.code)
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
        """Genera el código automáticamente al crear, reutilizando huecos."""
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
        
        # PASO 2: Generar códigos para nuevos registros (con reutilización de huecos)
        for vals in vals_list:
            if vals.get("code", "/") == "/" or not vals.get("code"):
                vals["code"] = self._get_next_reusable_subject_type_code()
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
        """Abre la vista de asignaturas filtrada por este tipo (solo lectura)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Asignaturas - {self.name}",
            "res_model": "benglish.subject",
            "view_mode": "list,form",
            "domain": [("subject_type_id", "=", self.id)],
            "context": {
                "default_subject_type_id": self.id,
                "create": False,
                "edit": False,
                "delete": False,
            },
        }
