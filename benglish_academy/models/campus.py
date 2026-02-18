# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from ..utils.normalizers import normalize_to_uppercase, normalize_codigo
import re


class Campus(models.Model):
    """
    Modelo para gestionar las Sedes.
    Una sede puede tener múltiples aulas.
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
        help="Código único identificador de la sede (generado automáticamente)",
    )
    sequence = fields.Integer(
        string="Secuencia", default=10, help="Orden de visualización"
    )

    # Campos de ubicación
    city_name = fields.Char(
        string="Ciudad",
        compute="_compute_city_name",
        store=True,
        help="Nombre de la ciudad donde se encuentra la sede",
    )
    department_name = fields.Char(
        string="Departamento",
        compute="_compute_department_name",
        store=True,
        help="Departamento según la ciudad seleccionada",
    )

    # Información de contacto - País, Departamento, Ciudad con filtros cascada
    country_id = fields.Many2one(
        comodel_name="res.country",
        string="País",
        help="País donde se encuentra la sede",
    )
    state_id = fields.Many2one(
        comodel_name="res.country.state",
        string="Departamento/Estado",
        domain="[('country_id', '=', country_id)]",
        help="Departamento o estado del país",
    )
    city_id = fields.Many2one(
        comodel_name="res.city",
        string="Ciudad",
        domain="[('state_id', '=', state_id)]",
        help="Ciudad donde se encuentra la sede",
    )
    direccion = fields.Char(
        string="Dirección",
        help="Dirección completa de la sede",
    )
    zip = fields.Char(string="Código Postal")
    phone = fields.Char(string="Teléfono")
    email = fields.Char(string="Email")

    # Campo para sede virtual
    is_virtual_sede = fields.Boolean(
        string="¿Es sede virtual?",
        default=False,
        tracking=True,
        help="Marcar si es una sede virtual. Los campos de ubicación y contacto se ocultarán.",
    )

    # Tipo de sede
    campus_type = fields.Selection(
        selection=[
            ("branch", "Presencial"),
            ("online", "Virtual"),
        ],
        string="Tipo de Sede",
        default="branch",
        required=True,
        help="Tipo de sede",
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
    monday_start_time = fields.Float(
        string="Lunes - Hora Inicio",
        default=0.0,
        help="Hora de inicio el lunes (0 = usar horario general)",
    )
    monday_end_time = fields.Float(
        string="Lunes - Hora Fin",
        default=0.0,
        help="Hora de fin el lunes (0 = usar horario general)",
    )
    allow_tuesday = fields.Boolean(
        string="Martes", default=True, help="Permitir sesiones los martes"
    )
    tuesday_start_time = fields.Float(
        string="Martes - Hora Inicio",
        default=0.0,
        help="Hora de inicio el martes (0 = usar horario general)",
    )
    tuesday_end_time = fields.Float(
        string="Martes - Hora Fin",
        default=0.0,
        help="Hora de fin el martes (0 = usar horario general)",
    )
    allow_wednesday = fields.Boolean(
        string="Miércoles", default=True, help="Permitir sesiones los miércoles"
    )
    wednesday_start_time = fields.Float(
        string="Miércoles - Hora Inicio",
        default=0.0,
        help="Hora de inicio el miércoles (0 = usar horario general)",
    )
    wednesday_end_time = fields.Float(
        string="Miércoles - Hora Fin",
        default=0.0,
        help="Hora de fin el miércoles (0 = usar horario general)",
    )
    allow_thursday = fields.Boolean(
        string="Jueves", default=True, help="Permitir sesiones los jueves"
    )
    thursday_start_time = fields.Float(
        string="Jueves - Hora Inicio",
        default=0.0,
        help="Hora de inicio el jueves (0 = usar horario general)",
    )
    thursday_end_time = fields.Float(
        string="Jueves - Hora Fin",
        default=0.0,
        help="Hora de fin el jueves (0 = usar horario general)",
    )
    allow_friday = fields.Boolean(
        string="Viernes", default=True, help="Permitir sesiones los viernes"
    )
    friday_start_time = fields.Float(
        string="Viernes - Hora Inicio",
        default=0.0,
        help="Hora de inicio el viernes (0 = usar horario general)",
    )
    friday_end_time = fields.Float(
        string="Viernes - Hora Fin",
        default=0.0,
        help="Hora de fin el viernes (0 = usar horario general)",
    )
    allow_saturday = fields.Boolean(
        string="Sábado", default=True, help="Permitir sesiones los sábados"
    )
    saturday_start_time = fields.Float(
        string="Sábado - Hora Inicio",
        default=0.0,
        help="Hora de inicio el sábado (0 = usar horario general)",
    )
    saturday_end_time = fields.Float(
        string="Sábado - Hora Fin",
        default=0.0,
        help="Hora de fin el sábado (0 = usar horario general)",
    )
    allow_sunday = fields.Boolean(
        string="Domingo", default=False, help="Permitir sesiones los domingos"
    )
    sunday_start_time = fields.Float(
        string="Domingo - Hora Inicio",
        default=0.0,
        help="Hora de inicio el domingo (0 = usar horario general)",
    )
    sunday_end_time = fields.Float(
        string="Domingo - Hora Fin",
        default=0.0,
        help="Hora de fin el domingo (0 = usar horario general)",
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
        string="Aulas",
        help="Aulas que pertenecen a esta sede",
    )

    # Responsable
    manager_id = fields.Many2one(
        comodel_name="res.users",
        string="Coordinador de Sede",
        help="Coordinador o responsable de la sede",
    )

    # Relación con sesiones
    session_ids = fields.One2many(
        comodel_name="benglish.class.session",
        inverse_name="campus_id",
        string="Sesiones Programadas",
        help="Sesiones de clase que se dictan en esta sede",
    )

    # Campos computados
    subcampus_count = fields.Integer(
        string="Número de Aulas", compute="_compute_subcampus_count", store=True
    )
    session_count = fields.Integer(
        string="Sesiones Programadas", compute="_compute_session_count", store=True
    )
    total_capacity = fields.Integer(
        string="Capacidad Total",
        compute="_compute_total_capacity",
        store=True,
        help="Capacidad total sumando todas las aulas (solo para sedes presenciales)",
    )

    campus_display = fields.Char(
        string="Tipo (display)",
        compute="_compute_campus_display",
        store=True,
        help="Etiqueta legible para mostrar en listas/kanban: 'Virtual' o 'Presencial'",
    )

    campus_type_code = fields.Selection(
        selection=[('branch', 'Presencial'), ('online', 'Virtual')],
        string='Tipo',
        compute='_compute_campus_type_code',
        store=True,
        help='Campo computado para facilitar badges con decoración (toma en cuenta is_virtual_sede).',
    )

    # Restricciones SQL
    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "El código de la sede debe ser único."),
    ]

    # Métodos computados para city_name y department_name
    @api.depends("city_id", "city_id.name")
    def _compute_city_name(self):
        """Calcula el nombre de la ciudad desde el Many2one."""
        for campus in self:
            campus.city_name = campus.city_id.name if campus.city_id else ""

    @api.depends("state_id", "state_id.name")
    def _compute_department_name(self):
        """Calcula el nombre del departamento desde el Many2one."""
        for campus in self:
            campus.department_name = campus.state_id.name if campus.state_id else ""

    # Onchange para filtros en cascada: País -> Departamento -> Ciudad
    @api.onchange("country_id")
    def _onchange_country_id(self):
        """Limpia el departamento y ciudad cuando cambia el país."""
        if self.state_id and self.state_id.country_id != self.country_id:
            self.state_id = False
            self.city_id = False

    @api.onchange("state_id")
    def _onchange_state_id(self):
        """Limpia la ciudad cuando cambia el departamento."""
        if self.city_id and self.city_id.state_id != self.state_id:
            self.city_id = False

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
        """Calcula el número de aulas."""
        for campus in self:
            campus.subcampus_count = len(campus.subcampus_ids)

    @api.depends("session_ids.state")
    def _compute_session_count(self):
        """Calcula la cantidad de sesiones planificadas en la sede."""
        for campus in self:
            campus.session_count = len(
                campus.session_ids.filtered(lambda s: s.state != "cancelled")
            )

    @api.depends("subcampus_ids.capacity", "is_virtual_sede")
    def _compute_total_capacity(self):
        """
        Calcula la capacidad total sumando las capacidades de todas las aulas.
        Para sedes virtuales, la capacidad es 0 (no aplica).
        """
        for campus in self:
            if campus.is_virtual_sede or campus.campus_type == 'online':
                campus.total_capacity = 0
            else:
                campus.total_capacity = sum(campus.subcampus_ids.mapped("capacity"))

    @api.depends("is_virtual_sede", "campus_type")
    def _compute_campus_display(self):
        """Campo computado que centraliza la etiqueta que se mostrará en vistas.

        - Si `is_virtual_sede` es True -> 'Virtual'
        - En otro caso utiliza `campus_type` ('Presencial'/'Virtual')
        Esto evita depender de widgets booleanos en listas/kanban.
        """
        for campus in self:
            if campus.is_virtual_sede:
                campus.campus_display = "Virtual"
            else:
                if campus.campus_type == "branch":
                    campus.campus_display = "Presencial"
                elif campus.campus_type == "online":
                    campus.campus_display = "Virtual"
                else:
                    campus.campus_display = ""

    @api.depends('is_virtual_sede', 'campus_type')
    def _compute_campus_type_code(self):
        """Devuelve un código tipo ('branch'|'online') teniendo en cuenta el toggle is_virtual_sede.

        Esto permite usar `decoration-info` / `decoration-warning` y `widget='badge'` sin mostrar HTML crudo.
        """
        for campus in self:
            if campus.is_virtual_sede:
                campus.campus_type_code = 'online'
            else:
                campus.campus_type_code = campus.campus_type or 'branch'
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

    @api.constrains(
        "schedule_start_time", "schedule_end_time",
        "monday_start_time", "monday_end_time",
        "tuesday_start_time", "tuesday_end_time",
        "wednesday_start_time", "wednesday_end_time",
        "thursday_start_time", "thursday_end_time",
        "friday_start_time", "friday_end_time",
        "saturday_start_time", "saturday_end_time",
        "sunday_start_time", "sunday_end_time",
    )
    def _check_day_schedules_within_general(self):
        """
        Valida que los horarios específicos por día estén dentro del horario general de operación.
        Los horarios por día son un subconjunto del horario general.
        """
        day_fields = [
            ("Lunes", "monday_start_time", "monday_end_time", "allow_monday"),
            ("Martes", "tuesday_start_time", "tuesday_end_time", "allow_tuesday"),
            ("Miércoles", "wednesday_start_time", "wednesday_end_time", "allow_wednesday"),
            ("Jueves", "thursday_start_time", "thursday_end_time", "allow_thursday"),
            ("Viernes", "friday_start_time", "friday_end_time", "allow_friday"),
            ("Sábado", "saturday_start_time", "saturday_end_time", "allow_saturday"),
            ("Domingo", "sunday_start_time", "sunday_end_time", "allow_sunday"),
        ]
        
        for campus in self:
            for day_name, start_field, end_field, allow_field in day_fields:
                day_start = getattr(campus, start_field)
                day_end = getattr(campus, end_field)
                is_allowed = getattr(campus, allow_field)
                
                # Solo validar si el día está habilitado y tiene horario específico
                if is_allowed and (day_start > 0 or day_end > 0):
                    # Si solo uno está configurado, ambos deben estarlo
                    if (day_start > 0) != (day_end > 0):
                        raise ValidationError(
                            _("El día %s tiene configuración incompleta. "
                              "Debe especificar tanto hora de inicio como hora de fin, "
                              "o dejar ambos en 00:00 para usar el horario general.")
                            % day_name
                        )
                    
                    # Validar que inicio < fin
                    if day_start >= day_end:
                        raise ValidationError(
                            _("El horario del %s es inválido: la hora de inicio (%.2f) "
                              "debe ser menor que la hora de fin (%.2f).")
                            % (day_name, day_start, day_end)
                        )
                    
                    # Validar que el horario esté dentro del horario general
                    if day_start < campus.schedule_start_time:
                        raise ValidationError(
                            _("El horario del %s inicia a las %.2f, pero el horario general "
                              "de operación de la sede inicia a las %.2f. "
                              "El horario por día debe estar dentro del horario general.")
                            % (day_name, day_start, campus.schedule_start_time)
                        )
                    
                    if day_end > campus.schedule_end_time:
                        raise ValidationError(
                            _("El horario del %s termina a las %.2f, pero el horario general "
                              "de operación de la sede termina a las %.2f. "
                              "El horario por día debe estar dentro del horario general.")
                            % (day_name, day_end, campus.schedule_end_time)
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

    @api.constrains("campus_type", "city_name", "is_virtual_sede")
    def _check_city_required_for_non_online(self):
        """Valida que las sedes no virtuales tengan ciudad."""
        for campus in self:
            # Si es sede virtual, no requiere ciudad
            if campus.is_virtual_sede or campus.campus_type == "online":
                continue
            if not campus.city_name:
                raise ValidationError(
                    _("La ciudad es obligatoria para sedes presenciales.")
                )

    @api.onchange("campus_type")
    def _onchange_campus_type(self):
        """Sincroniza is_virtual_sede cuando la sede es virtual."""
        if self.campus_type == "online":
            self.is_virtual_sede = True
        else:
            self.is_virtual_sede = False

    @api.onchange("is_virtual_sede")
    def _onchange_is_virtual_sede(self):
        """
        Limpia campos de ubicación y contacto cuando se marca como sede virtual.
        """
        if self.is_virtual_sede:
            self.city_id = False
            self.state_id = False
            self.country_id = False
            self.direccion = False
            self.zip = False
            self.phone = False
            self.email = False
            self.campus_type = "online"

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

    def get_day_schedule(self, weekday):
        """
        Obtiene el horario de operación para un día específico.
        Si el día tiene horario configurado (valores > 0), usa ese.
        Si no, usa el horario general de la sede.

        Args:
            weekday (int): Día de la semana (1=Lunes, 2=Martes, ..., 7=Domingo)

        Returns:
            tuple: (hora_inicio, hora_fin) en formato decimal
        """
        self.ensure_one()
        day_schedules = {
            1: (self.monday_start_time, self.monday_end_time),
            2: (self.tuesday_start_time, self.tuesday_end_time),
            3: (self.wednesday_start_time, self.wednesday_end_time),
            4: (self.thursday_start_time, self.thursday_end_time),
            5: (self.friday_start_time, self.friday_end_time),
            6: (self.saturday_start_time, self.saturday_end_time),
            7: (self.sunday_start_time, self.sunday_end_time),
        }
        day_start, day_end = day_schedules.get(weekday, (0.0, 0.0))
        
        # Si el día tiene horario específico (ambos valores > 0), usarlo
        if day_start > 0 and day_end > 0:
            return (day_start, day_end)
        
        # Si no, usar el horario general
        return (self.schedule_start_time, self.schedule_end_time)

    def is_time_in_schedule(self, time_float, weekday=None):
        """
        Verifica si una hora está dentro del rango permitido de la sede.

        Args:
            time_float (float): Hora en formato decimal (ej: 14.5 = 14:30)
            weekday (int, optional): Día de la semana para verificar horario específico

        Returns:
            bool: True si la hora está en el rango permitido, False en caso contrario
        """
        self.ensure_one()
        if weekday:
            start_time, end_time = self.get_day_schedule(weekday)
        else:
            start_time = self.schedule_start_time
            end_time = self.schedule_end_time
        return start_time <= time_float <= end_time

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
        # Obtener horario del día específico
        day_start, day_end = self.get_day_schedule(weekday)
        if not self.is_time_in_schedule(start_time_float, weekday):
            # Formatear horario del día para el mensaje
            start_h = int(day_start)
            start_m = int((day_start - start_h) * 60)
            end_h = int(day_end)
            end_m = int((day_end - end_h) * 60)
            day_schedule_str = f"{start_h:02d}:{start_m:02d} - {end_h:02d}:{end_m:02d}"
            raise ValidationError(
                _(
                    'La hora de inicio (%02d:%02d hora de Colombia) está fuera del horario permitido de la sede "%s" para ese día (%s).'
                )
                % (
                    start_datetime_local.hour,
                    start_datetime_local.minute,
                    self.name,
                    day_schedule_str,
                )
            )

        # Validar hora de fin (usando hora LOCAL de Colombia)
        end_time_float = end_datetime_local.hour + end_datetime_local.minute / 60.0
        if not self.is_time_in_schedule(end_time_float, weekday):
            # Formatear horario del día para el mensaje
            start_h = int(day_start)
            start_m = int((day_start - start_h) * 60)
            end_h = int(day_end)
            end_m = int((day_end - end_h) * 60)
            day_schedule_str = f"{start_h:02d}:{start_m:02d} - {end_h:02d}:{end_m:02d}"
            raise ValidationError(
                _(
                    'La hora de fin (%02d:%02d hora de Colombia) está fuera del horario permitido de la sede "%s" para ese día (%s).'
                )
                % (
                    end_datetime_local.hour,
                    end_datetime_local.minute,
                    self.name,
                    day_schedule_str,
                )
            )

        return True

    def action_view_subcampus(self):
        """Acción para ver las aulas de la sede."""
        self.ensure_one()
        return {
            "name": _("Aulas"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.subcampus",
            "view_mode": "list,form",
            "domain": [("campus_id", "=", self.id)],
            "context": {"default_campus_id": self.id},
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
        string="Sede:",
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
