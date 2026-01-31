# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from ..utils.normalizers import normalize_to_uppercase, normalize_codigo
import re


class Campus(models.Model):
    """
    Modelo para gestionar las Sedes Principales.
    Una sede puede tener múltiples sub-sedes o aulas.
    """

    _name = "benglish.campus"
    _description = "Sede"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"
    _rec_name = "name"

    # Campos básicos
    name = fields.Char(
        string="Nombre de la Sede",
        required=True,
        tracking=True,
        help="Nombre de la sede principal",
    )
    code = fields.Char(
        string="Código",
        required=True,
        copy=False,
        default='/',
        tracking=True,
        help="Código único identificador de la sede (manual o generado)",
    )
    sequence = fields.Integer(
        string="Secuencia", default=10, help="Orden de visualización"
    )

    # Jerarquía de sedes por ciudad
    city_name = fields.Char(
        string="Ciudad",
        help="Nombre de la ciudad donde se encuentra la sede",
    )
    department_name = fields.Char(
        string="Departamento",
        help="Departamento (texto) según la parametrización operativa",
    )
    is_main_campus = fields.Boolean(
        string="Sede Principal de la Ciudad",
        default=False,
        help="Marca si esta es la sede principal de la ciudad",
    )
    parent_campus_id = fields.Many2one(
        comodel_name="benglish.campus",
        string="Sede Principal",
        domain="[('is_main_campus', '=', True), ('id', '!=', id)]",
        help="Sede principal a la que pertenece esta sede (solo aplica si no es sede principal)",
    )
    child_campus_ids = fields.One2many(
        comodel_name="benglish.campus",
        inverse_name="parent_campus_id",
        string="Sedes Secundarias",
        help="Sedes secundarias que dependen de esta sede principal",
    )
    child_campus_count = fields.Integer(
        string="Número de Sedes Secundarias",
        compute="_compute_child_campus_count",
        store=True,
    )

    # Información de contacto
    street = fields.Char(string="Calle")
    street2 = fields.Char(string="Calle 2")
    city = fields.Char(
        string="Barrio/Zona", help="Barrio o zona específica dentro de la ciudad"
    )
    state_id = fields.Many2one(
        comodel_name="res.country.state", string="Departamento/Estado"
    )
    country_id = fields.Many2one(comodel_name="res.country", string="País")
    zip = fields.Char(string="Código Postal")
    phone = fields.Char(string="Teléfono")
    email = fields.Char(string="Email")

    # Información adicional
    address = fields.Char(
        string="Dirección Completa",
        compute="_compute_address",
        store=True,
        help="Dirección completa de la sede",
    )

    # Tipo de sede
    campus_type = fields.Selection(
        selection=[
            ("main", "Sede Principal"),
            ("branch", "Sucursal"),
            ("online", "Virtual"),
        ],
        string="Tipo de Sede",
        default="branch",
        required=True,
        help="Tipo de sede",
    )

    # Capacidad
    capacity = fields.Integer(
        string="Capacidad Total", help="Capacidad total de estudiantes de la sede"
    )

    # Estado
    active = fields.Boolean(
        string="Activo",
        default=True,
        help="Si está inactivo, la sede no estará disponible para programación",
    )

    # CONFIGURACIÓN DE AGENDA (Sistema de Agenda Académica)

    # Horarios permitidos para programación de sesiones
    schedule_start_time = fields.Float(
        string="Hora de Inicio Permitida",
        default=7.0,  # 7:00 AM por defecto
        required=True,
        help="Hora mínima permitida para programar sesiones (formato 24h decimal: 7.0 = 7:00 AM, 18.0 = 6:00 PM)",
    )
    schedule_end_time = fields.Float(
        string="Hora de Fin Permitida",
        default=18.0,  # 6:00 PM por defecto
        required=True,
        help="Hora máxima permitida para programar sesiones (formato 24h decimal: 7.0 = 7:00 AM, 18.0 = 6:00 PM)",
    )

    # Días permitidos para programación (lunes=1, domingo=7)
    allow_monday = fields.Boolean(
        string="Lunes", default=True, help="Permitir sesiones los lunes"
    )
    allow_tuesday = fields.Boolean(
        string="Martes", default=True, help="Permitir sesiones los martes"
    )
    allow_wednesday = fields.Boolean(
        string="Miércoles", default=True, help="Permitir sesiones los miércoles"
    )
    allow_thursday = fields.Boolean(
        string="Jueves", default=True, help="Permitir sesiones los jueves"
    )
    allow_friday = fields.Boolean(
        string="Viernes", default=True, help="Permitir sesiones los viernes"
    )
    allow_saturday = fields.Boolean(
        string="Sábado", default=True, help="Permitir sesiones los sábados"
    )
    allow_sunday = fields.Boolean(
        string="Domingo", default=False, help="Permitir sesiones los domingos"
    )

    # Duración por defecto de las sesiones
    default_session_duration = fields.Float(
        string="Duración de Sesión por Defecto (horas)",
        default=1.0,
        required=True,
        help="Duración estándar en horas para las sesiones de clase en esta sede (ej: 1.0 = 1 hora, 1.5 = 1.5 horas)",
    )

    # Horas por defecto para nuevas clases
    default_start_time = fields.Float(
        string="Hora de Inicio por Defecto",
        default=8.0,  # 8:00 AM por defecto
        help="Hora de inicio por defecto para nuevas clases (formato 24h decimal: 8.0 = 8:00 AM, 14.5 = 2:30 PM)",
    )
    default_end_time = fields.Float(
        string="Hora de Fin por Defecto",
        default=10.0,  # 10:00 AM por defecto
        help="Hora de fin por defecto para nuevas clases (formato 24h decimal: 10.0 = 10:00 AM, 16.5 = 4:30 PM)",
    )

    # Campo computado para mostrar resumen de horarios
    schedule_summary = fields.Char(
        string="Resumen de Horarios",
        compute="_compute_schedule_summary",
        store=True,
        help="Resumen legible de los horarios y días permitidos",
    )
    schedule_text = fields.Text(
        string="Horario (texto)",
        help="Horario real de atención/operación por día y rangos",
    )
    class_duration_text = fields.Char(
        string="Duración de clases (texto)",
        help="Duración de la clase según la parametrización operativa",
    )

    # Relaciones
    subcampus_ids = fields.One2many(
        comodel_name="benglish.subcampus",
        inverse_name="campus_id",
        string="Sub-sedes/Aulas",
        help="Sub-sedes o aulas que pertenecen a esta sede",
    )

    # Responsable
    manager_id = fields.Many2one(
        comodel_name="res.users",
        string="Coordinador de Sede",
        help="Coordinador o responsable de la sede",
    )

    # Relaciones con Cursos, Grupos y Docentes
    course_ids = fields.One2many(
        comodel_name="benglish.course",
        inverse_name="campus_id",
        string="Cursos",
        help="Cursos que se dictan en esta sede",
    )
    group_ids = fields.One2many(
        comodel_name="benglish.group",
        inverse_name="campus_id",
        string="Grupos",
        help="Grupos que tienen clases en esta sede",
    )
    teacher_ids = fields.Many2many(
        comodel_name="res.users",
        relation="benglish_campus_teacher_rel",
        column1="campus_id",
        column2="user_id",
        string="Docentes",
        compute="_compute_teacher_ids",
        store=True,
        help="Docentes que dictan clases en esta sede",
    )
    session_ids = fields.One2many(
        comodel_name="benglish.class.session",
        inverse_name="campus_id",
        string="Sesiones Programadas",
        help="Sesiones de clase que se dictan en esta sede",
    )

    # Campos computados
    subcampus_count = fields.Integer(
        string="Número de Sub-sedes", compute="_compute_subcampus_count", store=True
    )
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
        string="Sesiones Programadas", compute="_compute_session_count", store=True
    )
    total_capacity = fields.Integer(
        string="Capacidad Total (incluye sub-sedes)",
        compute="_compute_total_capacity",
        store=True,
        help="Capacidad total sumando todas las sub-sedes",
    )

    # Restricciones SQL
    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "El código de la sede debe ser único."),
    ]

    @api.depends("street", "street2", "city", "state_id", "country_id", "zip")
    def _compute_address(self):
        """Calcula la dirección completa de la sede."""
        for campus in self:
            address_parts = []
            if campus.street:
                address_parts.append(campus.street)
            if campus.street2:
                address_parts.append(campus.street2)
            if campus.city:
                address_parts.append(campus.city)
            if campus.state_id:
                address_parts.append(campus.state_id.name)
            if campus.country_id:
                address_parts.append(campus.country_id.name)
            if campus.zip:
                address_parts.append(campus.zip)

            campus.address = ", ".join(address_parts) if address_parts else ""

    @api.depends(
        "schedule_start_time",
        "schedule_end_time",
        "allow_monday",
        "allow_tuesday",
        "allow_wednesday",
        "allow_thursday",
        "allow_friday",
        "allow_saturday",
        "allow_sunday",
    )
    def _compute_schedule_summary(self):
        """Calcula un resumen legible de la configuración de horarios."""
        for campus in self:
            # Convertir horas decimales a formato HH:MM
            start_hour = int(campus.schedule_start_time)
            start_minute = int((campus.schedule_start_time - start_hour) * 60)
            end_hour = int(campus.schedule_end_time)
            end_minute = int((campus.schedule_end_time - end_hour) * 60)

            time_range = (
                f"{start_hour:02d}:{start_minute:02d} - {end_hour:02d}:{end_minute:02d}"
            )

            # Construir lista de días permitidos
            days = []
            if campus.allow_monday:
                days.append("Lun")
            if campus.allow_tuesday:
                days.append("Mar")
            if campus.allow_wednesday:
                days.append("Mié")
            if campus.allow_thursday:
                days.append("Jue")
            if campus.allow_friday:
                days.append("Vie")
            if campus.allow_saturday:
                days.append("Sáb")
            if campus.allow_sunday:
                days.append("Dom")

            days_str = ", ".join(days) if days else "Ningún día permitido"

            campus.schedule_summary = f"{time_range} | {days_str}"

    @api.depends("subcampus_ids")
    def _compute_subcampus_count(self):
        """Calcula el número de sub-sedes."""
        for campus in self:
            campus.subcampus_count = len(campus.subcampus_ids)

    @api.depends("child_campus_ids")
    def _compute_child_campus_count(self):
        """Calcula el número de sedes secundarias."""
        for campus in self:
            campus.child_campus_count = len(campus.child_campus_ids)

    @api.depends("course_ids")
    def _compute_course_count(self):
        """Calcula el número de cursos."""
        for campus in self:
            campus.course_count = len(campus.course_ids)

    @api.depends("group_ids")
    def _compute_group_count(self):
        """Calcula el número de grupos."""
        for campus in self:
            campus.group_count = len(campus.group_ids)

    @api.depends(
        "group_ids.teacher_id",
        "course_ids.main_teacher_id",
        "course_ids.assistant_teacher_ids",
    )
    def _compute_teacher_ids(self):
        """Calcula los docentes que dictan en esta sede."""
        for campus in self:
            teachers = self.env["res.users"]
            # Docentes de grupos
            teachers |= campus.group_ids.mapped("teacher_id")
            # Docentes principales de cursos
            teachers |= campus.course_ids.mapped("main_teacher_id")
            # Docentes asistentes de cursos
            for course in campus.course_ids:
                teachers |= course.assistant_teacher_ids
            campus.teacher_ids = teachers

    @api.depends("teacher_ids")
    def _compute_teacher_count(self):
        """Calcula el número de docentes."""
        for campus in self:
            campus.teacher_count = len(campus.teacher_ids)

    @api.depends("session_ids.state")
    def _compute_session_count(self):
        """Calcula la cantidad de sesiones planificadas en la sede."""
        for campus in self:
            campus.session_count = len(
                campus.session_ids.filtered(lambda s: s.state != "cancelled")
            )

    @api.depends("capacity", "subcampus_ids.capacity")
    def _compute_total_capacity(self):
        """Calcula la capacidad total incluyendo sub-sedes."""
        for campus in self:
            subcampus_capacity = sum(campus.subcampus_ids.mapped("capacity"))
            campus.total_capacity = (campus.capacity or 0) + subcampus_capacity

    @api.constrains("code")
    def _check_code_format(self):
        """Valida el formato del código de la sede."""
        for campus in self:
            if (
                campus.code
                and not campus.code.replace("_", "").replace("-", "").isalnum()
            ):
                raise ValidationError(
                    _(
                        "El código de la sede solo puede contener letras, números, guiones y guiones bajos."
                    )
                )

    @api.constrains("schedule_start_time", "schedule_end_time")
    def _check_schedule_times(self):
        """
        Valida que los horarios de programación sean coherentes.
        - La hora de inicio debe ser menor que la hora de fin
        - Ambas deben estar en el rango válido 0-24
        """
        for campus in self:
            if campus.schedule_start_time < 0 or campus.schedule_start_time >= 24:
                raise ValidationError(
                    _(
                        "La hora de inicio debe estar entre 0:00 y 23:59. Valor actual: %.2f"
                    )
                    % campus.schedule_start_time
                )
            if campus.schedule_end_time < 0 or campus.schedule_end_time > 24:
                raise ValidationError(
                    _(
                        "La hora de fin debe estar entre 0:00 y 24:00. Valor actual: %.2f"
                    )
                    % campus.schedule_end_time
                )
            if campus.schedule_start_time >= campus.schedule_end_time:
                raise ValidationError(
                    _(
                        "La hora de inicio (%.2f) debe ser menor que la hora de fin (%.2f)."
                    )
                    % (campus.schedule_start_time, campus.schedule_end_time)
                )

    @api.constrains(
        "allow_monday",
        "allow_tuesday",
        "allow_wednesday",
        "allow_thursday",
        "allow_friday",
        "allow_saturday",
        "allow_sunday",
    )
    def _check_at_least_one_day(self):
        """Valida que al menos un día de la semana esté permitido."""
        for campus in self:
            if not any(
                [
                    campus.allow_monday,
                    campus.allow_tuesday,
                    campus.allow_wednesday,
                    campus.allow_thursday,
                    campus.allow_friday,
                    campus.allow_saturday,
                    campus.allow_sunday,
                ]
            ):
                raise ValidationError(
                    _(
                        "Debe permitir al menos un día de la semana para programar sesiones."
                    )
                )

    @api.constrains("default_session_duration")
    def _check_default_session_duration(self):
        """Valida que la duración por defecto sea positiva y razonable."""
        for campus in self:
            if campus.default_session_duration <= 0:
                raise ValidationError(
                    _("La duración de sesión por defecto debe ser mayor a cero.")
                )
            if campus.default_session_duration > 8:
                raise ValidationError(
                    _("La duración de sesión por defecto no puede exceder 8 horas.")
                )

    @api.constrains("default_start_time", "default_end_time")
    def _check_default_times(self):
        """Valida que las horas por defecto sean coherentes."""
        for campus in self:
            # Validar rango válido 0-24
            if campus.default_start_time < 0 or campus.default_start_time >= 24:
                raise ValidationError(
                    _("La hora de inicio por defecto debe estar entre 0:00 y 23:59. Valor actual: %.2f") % campus.default_start_time
                )
            if campus.default_end_time <= 0 or campus.default_end_time > 24:
                raise ValidationError(
                    _("La hora de fin por defecto debe estar entre 0:01 y 24:00. Valor actual: %.2f") % campus.default_end_time
                )
            # La hora de inicio debe ser menor que la hora de fin
            if campus.default_start_time >= campus.default_end_time:
                raise ValidationError(
                    _("La hora de inicio por defecto (%.2f) debe ser menor que la hora de fin (%.2f).") 
                    % (campus.default_start_time, campus.default_end_time)
                )
            # Verificar que estén dentro del horario permitido de la sede
            if campus.default_start_time < campus.schedule_start_time:
                raise ValidationError(
                    _("La hora de inicio por defecto (%.2f) debe estar dentro del horario permitido de la sede (%.2f - %.2f).") 
                    % (campus.default_start_time, campus.schedule_start_time, campus.schedule_end_time)
                )
            if campus.default_end_time > campus.schedule_end_time:
                raise ValidationError(
                    _("La hora de fin por defecto (%.2f) debe estar dentro del horario permitido de la sede (%.2f - %.2f).") 
                    % (campus.default_end_time, campus.schedule_start_time, campus.schedule_end_time)
                )

    @api.constrains("campus_type", "city_name")
    def _check_city_required_for_non_online(self):
        """Valida que las sedes no virtuales tengan ciudad."""
        for campus in self:
            if campus.campus_type != "online" and not campus.city_name:
                raise ValidationError(
                    _("La ciudad es obligatoria para sedes presenciales o sucursales.")
                )

    @api.constrains("is_main_campus", "parent_campus_id", "city_name")
    def _check_campus_hierarchy(self):
        """Valida la jerarquía de sedes."""
        for campus in self:
            if campus.campus_type == "online":
                continue
            # Una sede principal no puede tener sede padre
            if campus.is_main_campus and campus.parent_campus_id:
                raise ValidationError(
                    _(
                        "Una sede principal no puede tener una sede padre. "
                        'Desmarque "Sede Principal de la Ciudad" o elimine la sede principal asignada.'
                    )
                )

            # Una sede secundaria debe tener sede padre
            if not campus.is_main_campus and not campus.parent_campus_id:
                raise ValidationError(
                    _(
                        "Una sede secundaria debe tener asignada una sede principal. "
                        'Seleccione una sede principal o marque esta sede como "Sede Principal de la Ciudad".'
                    )
                )

            # Validar que la sede padre sea de la misma ciudad
            if (
                campus.parent_campus_id
                and campus.city_name != campus.parent_campus_id.city_name
            ):
                raise ValidationError(
                    _(
                        "La sede secundaria debe pertenecer a la misma ciudad que su sede principal. "
                        "Ciudad actual: %s, Ciudad de sede principal: %s"
                    )
                    % (campus.city_name, campus.parent_campus_id.city_name)
                )

            # Evitar duplicidad de sede principal por ciudad
            if campus.is_main_campus:
                existing_main = self.search(
                    [
                        ("city_name", "=", campus.city_name),
                        ("is_main_campus", "=", True),
                        ("id", "!=", campus.id),
                    ],
                    limit=1,
                )
                if existing_main:
                    raise ValidationError(
                        _(
                            'Ya existe una sede principal para la ciudad "%s": %s. '
                            "Solo puede haber una sede principal por ciudad."
                        )
                        % (campus.city_name, existing_main.name)
                    )

    @api.onchange("is_main_campus")
    def _onchange_is_main_campus(self):
        """Limpia la sede padre cuando se marca como sede principal."""
        if self.is_main_campus:
            self.parent_campus_id = False

    @api.onchange("campus_type")
    def _onchange_campus_type(self):
        """Limpia jerarquia cuando la sede es virtual."""
        if self.campus_type == "online":
            self.parent_campus_id = False
            self.is_main_campus = False

    def is_day_allowed(self, weekday):
        """
        Verifica si un día de la semana está permitido para programación.

        Args:
            weekday (int): Día de la semana (1=Lunes, 2=Martes, ..., 7=Domingo)

        Returns:
            bool: True si el día está permitido, False en caso contrario
        """
        self.ensure_one()
        day_mapping = {
            1: self.allow_monday,
            2: self.allow_tuesday,
            3: self.allow_wednesday,
            4: self.allow_thursday,
            5: self.allow_friday,
            6: self.allow_saturday,
            7: self.allow_sunday,
        }
        return day_mapping.get(weekday, False)

    def is_time_in_schedule(self, time_float):
        """
        Verifica si una hora está dentro del rango permitido de la sede.

        Args:
            time_float (float): Hora en formato decimal (ej: 14.5 = 14:30)

        Returns:
            bool: True si la hora está en el rango permitido, False en caso contrario
        """
        self.ensure_one()
        return self.schedule_start_time <= time_float <= self.schedule_end_time

    def validate_session_schedule(self, start_datetime, end_datetime):
        """
        Valida que un horario de sesión cumpla con las restricciones de la sede.

        IMPORTANTE: Maneja correctamente la zona horaria de Colombia (America/Bogota, UTC-5).
        Los datetime se almacenan en UTC en Odoo, pero se validan contra horarios locales.

        Args:
            start_datetime (datetime): Fecha y hora de inicio de la sesión (en UTC)
            end_datetime (datetime): Fecha y hora de fin de la sesión (en UTC)

        Raises:
            ValidationError: Si el horario no cumple con las restricciones

        Returns:
            bool: True si la validación es exitosa
        """
        self.ensure_one()

        from datetime import datetime
        import pytz

        # Convertir a datetime si es necesario
        if isinstance(start_datetime, str):
            start_datetime = fields.Datetime.to_datetime(start_datetime)
        if isinstance(end_datetime, str):
            end_datetime = fields.Datetime.to_datetime(end_datetime)

        # Definir zona horaria de Colombia (America/Bogota = UTC-5)
        tz_colombia = pytz.timezone("America/Bogota")

        # Convertir de UTC a zona horaria de Colombia
        # Los datetime de Odoo están en UTC y son "naive" (sin tzinfo)
        # Primero los hacemos "aware" en UTC, luego convertimos a Colombia
        utc_tz = pytz.UTC
        start_datetime_utc = utc_tz.localize(start_datetime)
        end_datetime_utc = utc_tz.localize(end_datetime)

        start_datetime_local = start_datetime_utc.astimezone(tz_colombia)
        end_datetime_local = end_datetime_utc.astimezone(tz_colombia)

        # Validar día de la semana (isoweekday: 1=Lunes, 7=Domingo)
        # Usar la fecha LOCAL para validar el día correcto
        weekday = start_datetime_local.isoweekday()
        if not self.is_day_allowed(weekday):
            day_names = {
                1: "Lunes",
                2: "Martes",
                3: "Miércoles",
                4: "Jueves",
                5: "Viernes",
                6: "Sábado",
                7: "Domingo",
            }
            raise ValidationError(
                _('La sede "%s" no permite programar sesiones los días %s.')
                % (self.name, day_names.get(weekday, "desconocido"))
            )

        # Validar hora de inicio (usando hora LOCAL de Colombia)
        start_time_float = (
            start_datetime_local.hour + start_datetime_local.minute / 60.0
        )
        if not self.is_time_in_schedule(start_time_float):
            raise ValidationError(
                _(
                    'La hora de inicio (%02d:%02d hora de Colombia) está fuera del horario permitido de la sede "%s" (%s).'
                )
                % (
                    start_datetime_local.hour,
                    start_datetime_local.minute,
                    self.name,
                    self.schedule_summary,
                )
            )

        # Validar hora de fin (usando hora LOCAL de Colombia)
        end_time_float = end_datetime_local.hour + end_datetime_local.minute / 60.0
        if not self.is_time_in_schedule(end_time_float):
            raise ValidationError(
                _(
                    'La hora de fin (%02d:%02d hora de Colombia) está fuera del horario permitido de la sede "%s" (%s).'
                )
                % (
                    end_datetime_local.hour,
                    end_datetime_local.minute,
                    self.name,
                    self.schedule_summary,
                )
            )

        return True

    def action_view_child_campus(self):
        """Acción para ver las sedes secundarias."""
        self.ensure_one()
        return {
            "name": _("Sedes Secundarias"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.campus",
            "view_mode": "list,form",
            "domain": [("parent_campus_id", "=", self.id)],
            "context": {
                "default_parent_campus_id": self.id,
                "default_city_name": self.city_name,
                "default_is_main_campus": False,
            },
        }

    def action_view_subcampus(self):
        """Acción para ver las sub-sedes."""
        self.ensure_one()
        return {
            "name": _("Sub-sedes / Aulas"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.subcampus",
            "view_mode": "list,form",
            "domain": [("campus_id", "=", self.id)],
            "context": {"default_campus_id": self.id},
        }

    def action_view_courses(self):
        """Acción para ver los cursos de la sede."""
        self.ensure_one()
        return {
            "name": _("Cursos en la Sede"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.course",
            "view_mode": "list,form",
            "domain": [("campus_id", "=", self.id)],
            "context": {"default_campus_id": self.id},
        }

    def action_view_groups(self):
        """Acción para ver los grupos de la sede."""
        self.ensure_one()
        return {
            "name": _("Grupos en la Sede"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.group",
            "view_mode": "list,form",
            "domain": [("campus_id", "=", self.id)],
            "context": {"default_campus_id": self.id},
        }

    def action_view_teachers(self):
        """Acción para ver los docentes de la sede."""
        self.ensure_one()
        return {
            "name": _("Docentes en la Sede"),
            "type": "ir.actions.act_window",
            "res_model": "res.users",
            "view_mode": "list,form",
            "domain": [("id", "in", self.teacher_ids.ids)],
        }

    def action_view_sessions(self):
        """Acción para ver las sesiones programadas en la sede."""
        self.ensure_one()
        return {
            "name": _("Sesiones en la Sede"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.class.session",
            "view_mode": "calendar,list,form",
            "domain": [("campus_id", "=", self.id)],
            "context": {
                "default_campus_id": self.id,
                "search_default_campus_id": self.id,
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Genera código automático para sedes si no se proporciona y normaliza campos."""
        for vals in vals_list:
            if "name" in vals and vals["name"]:
                vals["name"] = normalize_to_uppercase(vals["name"])
            if "city_name" in vals and vals["city_name"]:
                vals["city_name"] = normalize_to_uppercase(vals["city_name"])
            if "department_name" in vals and vals["department_name"]:
                vals["department_name"] = normalize_to_uppercase(
                    vals["department_name"]
                )

            if vals.get("code", "/") in (None, "", "/"):
                vals["code"] = self._next_unique_code("SE-", "benglish.campus")
            else:
                vals["code"] = normalize_codigo(vals["code"])

        return super(Campus, self).create(vals_list)

    def _next_unique_code(self, prefix, seq_code):
        env = self.env
        existing = self.search([("code", "ilike", f"{prefix}%")])
        seq = env["ir.sequence"].search([("code", "=", seq_code)], limit=1)

        if not existing:
            if seq:
                seq.number_next = 1
            return f"{prefix}1"

        max_n = 0
        for rec in existing:
            if not rec.code:
                continue
            m = re.search(r"(\d+)$", rec.code)
            if m:
                try:
                    n = int(m.group(1))
                except Exception:
                    n = 0
                if n > max_n:
                    max_n = n

        next_n = max_n + 1
        if seq and (not seq.number_next or seq.number_next <= next_n):
            seq.number_next = next_n + 1
        return f"{prefix}{next_n}"


class SubCampus(models.Model):
    """
    Modelo para gestionar las Sub-sedes o Aulas.
    Una sub-sede pertenece a una sede principal y representa un espacio físico específico.
    """

    _name = "benglish.subcampus"
    _description = "Sub-sede / Aula"
    _order = "campus_id, sequence, name"
    _rec_name = "complete_name"

    # Campos básicos
    name = fields.Char(
        string="Nombre",
        required=True,
        help="Nombre del aula o sub-sede (ej: Aula 101, Sala Virtual A)",
    )
    code = fields.Char(
        string="Código", required=True, copy=False, default='/', help="Código único identificador"
    )
    sequence = fields.Integer(
        string="Secuencia", default=10, help="Orden de visualización"
    )
    complete_name = fields.Char(
        string="Nombre Completo",
        compute="_compute_complete_name",
        store=True,
        help="Nombre completo incluyendo sede principal",
    )
    description = fields.Text(
        string="Descripción", help="Descripción o características del aula"
    )

    # Tipo
    subcampus_type = fields.Selection(
        selection=[
            ("classroom", "Aula Física"),
            ("lab", "Laboratorio"),
            ("virtual", "Sala Virtual"),
            ("auditorium", "Auditorio"),
        ],
        string="Tipo",
        default="classroom",
        required=True,
        help="Tipo de sub-sede o aula",
    )

    # Capacidad
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

    # Relaciones
    campus_id = fields.Many2one(
        comodel_name="benglish.campus",
        string="Sede Principal",
        required=True,
        ondelete="restrict",
        help="Sede principal a la que pertenece",
    )

    # Equipamiento
    has_projector = fields.Boolean(string="Tiene Proyector", default=False)
    has_computer = fields.Boolean(string="Tiene Computador", default=False)
    has_whiteboard = fields.Boolean(string="Tiene Tablero", default=True)
    has_internet = fields.Boolean(string="Tiene Internet", default=True)

    # Restricciones SQL
    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "El código del aula debe ser único."),
        (
            "capacity_positive",
            "CHECK(capacity > 0)",
            "La capacidad debe ser mayor a cero.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Genera código automático para sub-sedes/aulas si no se proporciona y normaliza nombre."""
        for vals in vals_list:
            if "name" in vals and vals["name"]:
                vals["name"] = normalize_to_uppercase(vals["name"])
            if vals.get("code", "/") in (None, "", "/"):
                # Use AU- sequence for subcampus
                vals["code"] = self.env["ir.sequence"].next_by_code("benglish.subcampus") or self._next_unique_code("AU-", "benglish.subcampus")
            else:
                vals["code"] = normalize_codigo(vals["code"])

        return super(SubCampus, self).create(vals_list)

    @api.depends("name", "campus_id.name")
    def _compute_complete_name(self):
        """Calcula el nombre completo incluyendo la sede principal."""
        for subcampus in self:
            if subcampus.campus_id:
                subcampus.complete_name = (
                    f"{subcampus.campus_id.name} / {subcampus.name}"
                )
            else:
                subcampus.complete_name = subcampus.name

    @api.constrains("code")
    def _check_code_format(self):
        """Valida el formato del código del aula."""
        for subcampus in self:
            if (
                subcampus.code
                and not subcampus.code.replace("_", "").replace("-", "").isalnum()
            ):
                raise ValidationError(
                    _(
                        "El código del aula solo puede contener letras, números, guiones y guiones bajos."
                    )
                )

    # NORMALIZACIÓN AUTOMÁTICA

    @api.model_create_multi
    def create(self, vals_list):
        """Sobrescribe create para normalizar datos y generar código automático si no se proporciona."""
        for vals in vals_list:
            if "name" in vals and vals["name"]:
                vals["name"] = normalize_to_uppercase(vals["name"])
            if "city_name" in vals and vals["city_name"]:
                vals["city_name"] = normalize_to_uppercase(vals["city_name"])
            if "department_name" in vals and vals["department_name"]:
                vals["department_name"] = normalize_to_uppercase(
                    vals["department_name"]
                )

            # If no manual code provided, generate using sequence SE-1, SE-2 ...
            if vals.get("code", "/") in (None, "", "/"):
                vals["code"] = self.env["ir.sequence"].next_by_code("benglish.campus") or "/"
            else:
                # normalize provided code
                vals["code"] = normalize_codigo(vals["code"])

        return super(Campus, self).create(vals_list)

    def write(self, vals):
        """Sobrescribe write para normalizar datos a MAYÚSCULAS automáticamente."""
        if "name" in vals and vals["name"]:
            vals["name"] = normalize_to_uppercase(vals["name"])
        if "city_name" in vals and vals["city_name"]:
            vals["city_name"] = normalize_to_uppercase(vals["city_name"])
        if "department_name" in vals and vals["department_name"]:
            vals["department_name"] = normalize_to_uppercase(vals["department_name"])
        if "code" in vals and vals["code"]:
            vals["code"] = normalize_codigo(vals["code"])

        return super(Campus, self).write(vals)

    # Subcampus create is implemented in SubCampus class below; keep definitions separate
