# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from ..utils.normalizers import normalize_to_uppercase, normalize_codigo
import re


class SubCampus(models.Model):
    """
    Modelo para gestionar las Sub-sedes/Aulas.
    Una sub-sede pertenece a una sede principal (campus) y representa
    un espacio físico o virtual específico donde se imparten clases.
    """

    _name = "benglish.subcampus"
    _description = "Sub-sede / Aula"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "campus_id, sequence, name"
    _rec_name = "complete_name"

    # Campos básicos
    name = fields.Char(
        string="Nombre del Aula",
        required=True,
        tracking=True,
        help="Nombre del aula o sub-sede (ej: Aula 101, Sala Virtual A)",
    )
    code = fields.Char(
        string="Código",
        required=True,
        copy=False,
        default="/",
        tracking=True,
        help="Código único identificador del aula (generado automáticamente)",
    )
    sequence = fields.Integer(
        string="Secuencia", default=10, help="Orden de visualización dentro de la sede"
    )
    complete_name = fields.Char(
        string="Nombre Completo",
        compute="_compute_complete_name",
        store=True,
        help="Nombre completo incluyendo la sede principal",
    )
    description = fields.Text(
        string="Descripción",
        help="Descripción adicional o características especiales del aula",
    )
    space_label = fields.Char(
        string="Tipo de espacio (texto)",
        help="Etiqueta exacta del tipo de espacio (ej: Salón kids)",
    )

    # Modalidad de clase
    modality = fields.Selection(
        selection=[
            ("presential", "Presencial"),
            ("virtual", "Virtual"),
            ("hybrid", "Híbrida (Presencial O Virtual)"),
        ],
        string="Modalidad",
        required=True,
        default="presential",
        help="Modalidad en la que se dictan las clases en este espacio",
    )

    # Capacidades específicas por modalidad
    presential_capacity = fields.Integer(
        string="Capacidad Presencial",
        compute="_compute_presential_capacity",
        store=True,
        help="Capacidad máxima de estudiantes presenciales",
    )
    virtual_capacity = fields.Integer(
        string="Capacidad Virtual",
        default=0,
        help="Capacidad máxima de estudiantes remotos (solo para modalidad híbrida/virtual)",
    )
    total_capacity = fields.Integer(
        string="Capacidad Total",
        compute="_compute_total_capacity",
        store=True,
        help="Capacidad total efectiva del aula. Para aulas híbridas es la máxima entre presencial y virtual.",
    )

    # Relaciones
    campus_id = fields.Many2one(
        comodel_name="benglish.campus",
        string="Sede Principal",
        required=True,
        ondelete="restrict",
        help="Sede principal a la que pertenece esta sub-sede",
    )

    # Relaciones con Cursos, Grupos y Docentes
    course_ids = fields.Many2many(
        comodel_name="benglish.course",
        relation="benglish_course_subcampus_rel",
        column1="subcampus_id",
        column2="course_id",
        string="Cursos",
        help="Cursos que se dictan en esta aula",
    )
    group_ids = fields.One2many(
        comodel_name="benglish.group",
        inverse_name="subcampus_id",
        string="Grupos",
        help="Grupos que tienen clases en esta aula",
    )
    teacher_ids = fields.Many2many(
        comodel_name="res.users",
        relation="benglish_subcampus_teacher_rel",
        column1="subcampus_id",
        column2="user_id",
        string="Docentes",
        compute="_compute_teacher_ids",
        store=True,
        help="Docentes que dictan clases en esta aula",
    )
    session_ids = fields.One2many(
        comodel_name="benglish.class.session",
        inverse_name="subcampus_id",
        string="Sesiones Programadas",
        help="Sesiones calendarizadas en este espacio",
    )

    # Contadores
    course_count = fields.Integer(
        string="Número de Cursos", compute="_compute_course_count", store=True
    )
    group_count = fields.Integer(
        string="Número de Grupos", compute="_compute_group_count", store=True
    )
    teacher_count = fields.Integer(
        string="Número de Docentes", compute="_compute_teacher_count", store=True
    )
    session_count = fields.Integer(
        string="Número de Sesiones", compute="_compute_session_count", store=True
    )

    # Tipo de sub-sede
    subcampus_type = fields.Selection(
        selection=[
            ("classroom", "Aula Física"),
            ("lab", "Laboratorio de Idiomas"),
            ("virtual", "Sala Virtual"),
            ("hybrid", "Aula Híbrida"),
            ("auditorium", "Auditorio"),
            ("conference", "Sala de Conferencias"),
        ],
        string="Tipo de Espacio",
        required=True,
        default="classroom",
        help="Tipo de sub-sede o aula",
    )

    # Capacidad y disponibilidad
    capacity = fields.Integer(
        string="Capacidad",
        required=True,
        default=20,
        help="Capacidad máxima de estudiantes",
    )

    # Estado
    active = fields.Boolean(
        string="Activo",
        default=True,
        help="Si está inactivo, el aula no estará disponible para programación",
    )
    is_available = fields.Boolean(
        string="Disponible",
        default=True,
        help="Indica si el aula está disponible para uso",
    )

    # Equipamiento y recursos
    has_projector = fields.Boolean(
        string="Proyector", default=False, help="El aula cuenta con proyector"
    )
    has_computer = fields.Boolean(
        string="Computador", default=False, help="El aula cuenta con computador"
    )
    has_whiteboard = fields.Boolean(
        string="Tablero", default=True, help="El aula cuenta con tablero o pizarra"
    )
    has_internet = fields.Boolean(
        string="Internet", default=True, help="El aula cuenta con conexión a internet"
    )
    has_audio_system = fields.Boolean(
        string="Sistema de Audio",
        default=False,
        help="El aula cuenta con sistema de audio",
    )
    has_air_conditioning = fields.Boolean(
        string="Aire Acondicionado",
        default=False,
        help="El aula cuenta con aire acondicionado",
    )

    # Notas
    notes = fields.Text(string="Notas", help="Notas adicionales sobre el aula")

    # Restricciones SQL
    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "El código del aula debe ser único."),
        (
            "capacity_positive",
            "CHECK(capacity > 0)",
            "La capacidad debe ser mayor a cero.",
        ),
    ]

    # Métodos computados
    @api.depends("name", "code", "campus_id.name", "modality")
    def _compute_complete_name(self):
        """Calcula el nombre completo del aula - SOLO código y nombre (sin sede)."""
        for subcampus in self:
            modality_label = ""
            if subcampus.modality == "virtual":
                modality_label = " [Virtual]"
            elif subcampus.modality == "hybrid":
                modality_label = " [Híbrido]"

            # Formato simplificado: solo código y nombre
            base_name = (
                f"{subcampus.code} - {subcampus.name}"
                if subcampus.code
                else subcampus.name
            )
            subcampus.complete_name = f"{base_name}{modality_label}"

    @api.depends("modality", "capacity")
    def _compute_presential_capacity(self):
        """Calcula la capacidad presencial según la modalidad."""
        for subcampus in self:
            if subcampus.modality == "virtual":
                subcampus.presential_capacity = 0
            else:
                subcampus.presential_capacity = subcampus.capacity

    @api.depends("modality", "capacity", "virtual_capacity")
    def _compute_total_capacity(self):
        """Calcula la capacidad total.
        
        Para aulas híbridas, la capacidad total es la MÁXIMA entre presencial y virtual,
        no la suma, ya que los estudiantes pueden estar físicos O remotos, no ambos simultáneamente.
        """
        for subcampus in self:
            if subcampus.modality == "presential":
                subcampus.total_capacity = subcampus.capacity
            elif subcampus.modality == "virtual":
                subcampus.total_capacity = subcampus.virtual_capacity
            else:  # hybrid
                # Para modalidad híbrida, tomar el máximo entre capacidad presencial y virtual
                # No sumar, ya que es excluyente: estudiantes están presencial O virtual
                subcampus.total_capacity = max(
                    subcampus.capacity, subcampus.virtual_capacity
                )

    def name_get(self):
        """Personaliza cómo se muestra el nombre del aula en campos Many2one.
        Si el contexto tiene 'show_only_name', muestra solo el nombre del aula.
        Si no, muestra el complete_name (con sede incluida).
        """
        result = []
        show_only_name = self.env.context.get("show_only_name", False)

        for subcampus in self:
            if show_only_name:
                # Mostrar solo el nombre del aula sin la sede
                name = subcampus.name
            else:
                # Mostrar el nombre completo con la sede
                name = subcampus.complete_name or subcampus.name

            result.append((subcampus.id, name))

        return result

    # Validaciones
    @api.constrains("capacity")
    def _check_capacity(self):
        """Valida que la capacidad sea positiva."""
        for subcampus in self:
            if subcampus.capacity <= 0:
                raise ValidationError(_("La capacidad del aula debe ser mayor a cero."))

    @api.constrains("modality", "virtual_capacity")
    def _check_modality_requirements(self):
        """Valida los requisitos según la modalidad."""
        for subcampus in self:
            # Validar capacidad virtual solo para modalidad virtual
            if subcampus.modality == "virtual" and subcampus.virtual_capacity <= 0:
                raise ValidationError(
                    _(
                        "Las aulas virtuales deben tener una capacidad virtual mayor a cero."
                    )
                )

    @api.onchange("modality")
    def _onchange_modality(self):
        """Ajusta campos según la modalidad seleccionada."""
        if self.modality == "presential":
            self.virtual_capacity = 0
        elif self.modality == "virtual":
            self.capacity = 0
            if not self.virtual_capacity:
                self.virtual_capacity = 50  # Valor por defecto
        elif self.modality == "hybrid":
            if not self.virtual_capacity:
                self.virtual_capacity = 30  # Valor por defecto para híbrido

    # Métodos computados para relaciones
    @api.depends("course_ids")
    def _compute_course_count(self):
        """Calcula el número de cursos."""
        for subcampus in self:
            subcampus.course_count = len(subcampus.course_ids)

    @api.depends("group_ids")
    def _compute_group_count(self):
        """Calcula el número de grupos."""
        for subcampus in self:
            subcampus.group_count = len(subcampus.group_ids)

    @api.depends(
        "group_ids.teacher_id",
        "course_ids.main_teacher_id",
        "course_ids.assistant_teacher_ids",
    )
    def _compute_teacher_ids(self):
        """Calcula los docentes que dictan en esta aula."""
        for subcampus in self:
            teachers = self.env["res.users"]
            # Docentes de grupos
            teachers |= subcampus.group_ids.mapped("teacher_id")
            # Docentes principales de cursos
            teachers |= subcampus.course_ids.mapped("main_teacher_id")
            # Docentes asistentes de cursos
            for course in subcampus.course_ids:
                teachers |= course.assistant_teacher_ids
            subcampus.teacher_ids = teachers

    @api.depends("teacher_ids")
    def _compute_teacher_count(self):
        """Calcula el número de docentes."""
        for subcampus in self:
            subcampus.teacher_count = len(subcampus.teacher_ids)

    @api.depends("session_ids.state")
    def _compute_session_count(self):
        """Calcula el número de sesiones planificadas."""
        for subcampus in self:
            subcampus.session_count = len(
                subcampus.session_ids.filtered(lambda s: s.state != "cancelled")
            )

    # Métodos de negocio
    def toggle_availability(self):
        """Cambia el estado de disponibilidad del aula."""
        for subcampus in self:
            subcampus.is_available = not subcampus.is_available

    def action_mark_unavailable(self):
        """Marca el aula como no disponible."""
        self.write({"is_available": False})

    def action_mark_available(self):
        """Marca el aula como disponible."""
        self.write({"is_available": True})

    def action_view_courses(self):
        """Acción para ver los cursos del aula."""
        self.ensure_one()
        return {
            "name": _("Cursos en el Aula"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.course",
            "view_mode": "list,form",
            "domain": [("subcampus_ids", "in", self.id)],
            "context": {
                "default_subcampus_ids": [(6, 0, [self.id])],
                "default_campus_id": self.campus_id.id,
            },
        }

    def action_view_groups(self):
        """Acción para ver los grupos del aula."""
        self.ensure_one()
        return {
            "name": _("Grupos en el Aula"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.group",
            "view_mode": "list,form",
            "domain": [("subcampus_id", "=", self.id)],
            "context": {
                "default_subcampus_id": self.id,
                "default_campus_id": self.campus_id.id,
            },
        }

    def action_view_sessions(self):
        """Acción para ver las sesiones del aula."""
        self.ensure_one()
        return {
            "name": _("Sesiones en el Aula"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.class.session",
            "view_mode": "calendar,list,form",
            "domain": [("subcampus_id", "=", self.id)],
            "context": {
                "default_subcampus_id": self.id,
                "default_campus_id": self.campus_id.id,
                "search_default_subcampus_id": self.id,
            },
        }

    def action_view_teachers(self):
        """Acción para ver los docentes del aula."""
        self.ensure_one()
        return {
            "name": _("Docentes en el Aula"),
            "type": "ir.actions.act_window",
            "res_model": "res.users",
            "view_mode": "list,form",
            "domain": [("id", "in", self.teacher_ids.ids)],
        }

    # NORMALIZACIÓN AUTOMÁTICA

    def _next_unique_code(self, prefix, seq_code):
        """Calcula el siguiente código libre con prefijo, reutilizando huecos."""
        import re
        
        existing = self.search([("code", "=like", f"{prefix}%")])
        
        if not existing:
            return f"{prefix}1"
        
        used_numbers = set()
        for rec in existing:
            if rec.code:
                m = re.search(r"(\d+)$", rec.code)
                if m:
                    try:
                        used_numbers.add(int(m.group(1)))
                    except ValueError:
                        pass
        
        if not used_numbers:
            return f"{prefix}1"
        
        for num in range(1, max(used_numbers) + 2):
            if num not in used_numbers:
                return f"{prefix}{num}"
        
        return f"{prefix}{max(used_numbers) + 1}"

    @api.model_create_multi
    def create(self, vals_list):
        """Sobrescribe create para generar código automático y normalizar datos a MAYÚSCULAS."""
        for vals in vals_list:
            # Generar código automático si no se proporciona o es '/'
            if vals.get("code", "/") == "/":
                vals["code"] = self._next_unique_code("AU-", "benglish.subcampus")
            
            # Normalizar datos a mayúsculas
            if "name" in vals and vals["name"]:
                vals["name"] = normalize_to_uppercase(vals["name"])
            if "code" in vals and vals["code"] and vals["code"] != "/":
                vals["code"] = normalize_codigo(vals["code"])

        return super(SubCampus, self).create(vals_list)

    def write(self, vals):
        """Sobrescribe write para normalizar datos a MAYÚSCULAS automáticamente."""
        if "name" in vals and vals["name"]:
            vals["name"] = normalize_to_uppercase(vals["name"])
        if "code" in vals and vals["code"]:
            vals["code"] = normalize_codigo(vals["code"])

        return super(SubCampus, self).write(vals)
