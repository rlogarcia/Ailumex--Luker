# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class ClassSession(models.Model):
    """Sesión individual dentro del plan de clases de un grupo."""

    _name = "benglish.class.session"
    _description = "Sesión de Clase"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_datetime asc, subject_id"
    _rec_name = "display_name"

    name = fields.Char(
        string="Nombre interno", help="Etiqueta corta para identificar la sesión."
    )
    display_name = fields.Char(
        string="Nombre a mostrar", compute="_compute_display_name", store=True
    )
    color = fields.Integer(string="Color")

    # Relaciones académicas
    program_id = fields.Many2one(
        comodel_name="benglish.program",
        string="Programa",
        required=True,
        ondelete="restrict",
        tracking=True,
        help="Programa académico al que pertenece esta sesión",
    )
    plan_id = fields.Many2one(
        comodel_name="benglish.plan",
        string="Plan de Estudio",
        required=False,
        ondelete="restrict",
        tracking=True,
        domain="[('program_id', '=', program_id)]",
        help="Plan de estudio del programa seleccionado (opcional)",
    )
    subject_id = fields.Many2one(
        comodel_name="benglish.subject",
        string="Asignatura",
        required=True,
        ondelete="restrict",
        tracking=True,
        domain="[('active', '=', True)]",
        help="Asignatura para esta sesión",
    )
    # Campo para marcar sesión como prerrequisito (ahora editable manualmente)
    is_prerequisite_session = fields.Boolean(
        string="Es Prerrequisito",
        default=False,
        tracking=True,
        help="Marca esta sesión como prerrequisito que debe tomarse primero",
    )

    # Ubicación
    location_city = fields.Selection(
        selection="_get_city_selection",
        string="Ubicación (Ciudad)",
        tracking=True,
        help="Ciudad donde se dicta la clase (solo para modalidad presencial o híbrida)",
    )
    campus_id = fields.Many2one(
        comodel_name="benglish.campus",
        string="Sede",
        required=True,
        ondelete="restrict",
        tracking=True,
        domain="[('city_name', '=', location_city)]",
        help="Sede donde se dicta la clase (filtrada por ciudad seleccionada)",
    )
    subcampus_id = fields.Many2one(
        comodel_name="benglish.subcampus",
        string="Aula",
        domain="[('campus_id', '=', campus_id), ('campus_id.city_name', '=', location_city), ('active', '=', True), ('is_available', '=', True)]",
        tracking=True,
    )

    # Docentes
    teacher_id = fields.Many2one(
        comodel_name="res.users",
        string="Docente (Usuario)",
        domain="[('share', '=', False)]",
        tracking=True,
    )
    coach_id = fields.Many2one(
        comodel_name="benglish.coach", string="Coach", tracking=True
    )
    
    # Campos relacionados del coach para heredar enlace de reunión
    coach_meeting_link = fields.Char(
        string="Enlace del Coach",
        related="coach_id.meeting_link",
        readonly=True,
        help="Enlace de reunión heredado del coach asignado",
    )
    coach_meeting_platform = fields.Selection(
        selection=[
            ("google_meet", "Google Meet"),
            ("zoom", "Zoom"),
            ("teams", "Microsoft Teams"),
            ("jitsi", "Jitsi Meet"),
            ("other", "Otra plataforma"),
        ],
        string="Plataforma del Coach",
        related="coach_id.meeting_platform",
        readonly=True,
        help="Plataforma de reunión heredada del coach asignado",
    )

    # Clasificación
    session_type = fields.Selection(
        selection=[
            ("regular", "Clase regular"),
            ("makeup", "Clase de recuperación"),
            ("replacement", "Reemplazo de docente"),
            ("evaluation", "Evaluación"),
        ],
        string="Tipo de sesión",
        default="regular",
        required=True,
        tracking=True,
    )
    delivery_mode = fields.Selection(
        selection=[
            ("presential", "Presencial"),
            ("virtual", "Virtual"),
            ("hybrid", "Híbrida"),
        ],
        string="Modalidad",
        default="presential",
        required=True,
        tracking=True,
        help="Modalidad de la sesión: Presencial (solo en sede), Virtual (online), Híbrida (combinada)",
    )

    meeting_link = fields.Char(string="Enlace de videollamada")
    meeting_platform = fields.Selection(
        selection=[
            ("google_meet", "Google Meet"),
            ("zoom", "Zoom"),
            ("teams", "Microsoft Teams"),
            ("jitsi", "Jitsi Meet"),
            ("other", "Otra plataforma"),
        ],
        string="Plataforma",
    )

    # SISTEMA DE AGENDA - CAPACIDAD Y ESTUDIANTES

    # Capacidad máxima de estudiantes (cupo)
    max_capacity = fields.Integer(
        string="Capacidad Máxima (Cupo)",
        default=15,
        required=True,
        tracking=True,
        help="Número máximo de estudiantes que pueden tomar esta sesión",
    )

    # Relación Many2many con estudiantes inscritos en la sesión
    student_ids = fields.Many2many(
        comodel_name="benglish.student",
        relation="benglish_class_session_student_rel",
        column1="session_id",
        column2="student_id",
        string="Estudiantes Inscritos",
        tracking=True,
        help="Estudiantes que están inscritos en esta sesión de clase",
    )

    # Campos computados para capacidad
    enrolled_count = fields.Integer(
        string="Estudiantes Inscritos",
        compute="_compute_enrolled_count",
        store=True,
        help="Número actual de estudiantes inscritos",
    )
    available_spots = fields.Integer(
        string="Cupos Disponibles",
        compute="_compute_available_spots",
        store=True,
        help="Número de cupos disponibles (capacidad - inscritos)",
    )
    is_full = fields.Boolean(
        string="Sesión Llena",
        compute="_compute_is_full",
        store=True,
        help="Indica si la sesión alcanzó su capacidad máxima",
    )
    occupancy_rate = fields.Float(
        string="Tasa de Ocupación (%)",
        compute="_compute_occupancy_rate",
        store=True,
        help="Porcentaje de ocupación de la sesión",
    )

    # Horario
    start_datetime = fields.Datetime(string="Inicio", required=True, tracking=True)
    end_datetime = fields.Datetime(string="Fin", required=True, tracking=True)
    date = fields.Date(string="Fecha", compute="_compute_aux_dates", store=True)
    start_time = fields.Float(
        string="Hora de inicio",
        default=8.0,
        store=True,
        help="Hora de inicio en formato 24h decimal (ej: 8.0 = 8:00 AM)",
    )
    end_time = fields.Float(
        string="Hora de fin",
        default=18.0,
        store=True,
        help="Hora de fin en formato 24h decimal (ej: 18.0 = 6:00 PM)",
    )

    @api.onchange('start_time')
    def _onchange_start_time(self):
        # Sincroniza start_datetime si hay fecha
        self._inverse_start_time()

    @api.onchange('end_time')
    def _onchange_end_time(self):
        # Sincroniza end_datetime si hay fecha
        self._inverse_end_time()
    def _inverse_start_time(self):
        """
        Al editar start_time, actualiza start_datetime manteniendo la fecha y zona horaria.
        """
        import pytz
        from datetime import datetime
        tz_colombia = pytz.timezone('America/Bogota')
        for record in self:
            if record.start_time is not False and record.date:
                hours = int(record.start_time)
                minutes = int(round((record.start_time % 1) * 60))
                # Crear datetime naive en hora Colombia
                naive_dt = datetime.combine(record.date, datetime.min.time()).replace(hour=hours, minute=minutes, second=0, microsecond=0)
                # Localizar y convertir a UTC
                local_dt = tz_colombia.localize(naive_dt)
                utc_dt = local_dt.astimezone(pytz.UTC)
                record.start_datetime = utc_dt.replace(tzinfo=None)

    def _inverse_end_time(self):
        """
        Al editar end_time, actualiza end_datetime manteniendo la fecha y zona horaria.
        """
        import pytz
        from datetime import datetime
        tz_colombia = pytz.timezone('America/Bogota')
        for record in self:
            if record.end_time is not False and record.date:
                hours = int(record.end_time)
                minutes = int(round((record.end_time % 1) * 60))
                naive_dt = datetime.combine(record.date, datetime.min.time()).replace(hour=hours, minute=minutes, second=0, microsecond=0)
                local_dt = tz_colombia.localize(naive_dt)
                utc_dt = local_dt.astimezone(pytz.UTC)
                record.end_datetime = utc_dt.replace(tzinfo=None)
    duration_hours = fields.Float(
        string="Duración (horas)", compute="_compute_duration", store=True
    )

    # Estado
    state = fields.Selection(
        selection=[
            ("planned", "Programada"),
            ("in_progress", "En curso"),
            ("done", "Dictada"),
            ("cancelled", "Cancelada"),
        ],
        string="Estado",
        default="planned",
        required=True,
        tracking=True,
    )
    cancellation_reason = fields.Text(string="Motivo de cancelación")
    cancelled_by_id = fields.Many2one(
        "res.users", string="Cancelada por", readonly=True
    )
    cancelled_at = fields.Datetime(string="Fecha de cancelación", readonly=True)

    # Publicación (para sincronización con portales)
    is_published = fields.Boolean(
        string="Publicada",
        default=False,
        help="Indica si la sesión está publicada y visible en portales de estudiantes",
    )
    published_at = fields.Datetime(string="Fecha de publicación", readonly=True)
    published_by_id = fields.Many2one(
        "res.users", string="Publicada por", readonly=True
    )

    # Reemplazo de docente (historial)
    original_teacher_id = fields.Many2one(
        comodel_name="res.users",
        string="Docente Original",
        domain="[('share', '=', False)]",
        help="Docente asignado originalmente antes del reemplazo",
    )
    replacement_reason = fields.Text(string="Motivo de reemplazo")
    replaced_at = fields.Datetime(string="Fecha de reemplazo", readonly=True)
    replaced_by_id = fields.Many2one(
        "res.users", string="Reemplazado por (usuario)", readonly=True
    )

    # Historial completo de reemplazos
    replacement_log_ids = fields.One2many(
        comodel_name="benglish.teacher.replacement.log",
        inverse_name="session_id",
        string="Historial de Reemplazos",
        readonly=True,
        help="Registro completo de todos los reemplazos de docente realizados",
    )
    replacement_count = fields.Integer(
        string="N° de Reemplazos", compute="_compute_replacement_count", store=True
    )

    # Auditoría
    notes = fields.Text(string="Notas internas")

    @api.model
    def default_get(self, fields_list):
        """
        Establece valores por defecto inteligentes para nuevas clases.
        """
        res = super(ClassSession, self).default_get(fields_list)
        from datetime import datetime
        import pytz
        tz_colombia = pytz.timezone('America/Bogota')
        campus_id = self.env.context.get('default_campus_id')
        campus = None
        if campus_id:
            campus = self.env['benglish.campus'].browse(campus_id)
        else:
            campus = self.env['benglish.campus'].search([('active', '=', True)], limit=1)
        if campus:
            if campus.default_start_time is not False:
                start_time_float = campus.default_start_time
            elif campus.schedule_start_time is not False:
                start_time_float = campus.schedule_start_time
            else:
                start_time_float = 8.0

            if campus.default_end_time is not False:
                end_time_float = campus.default_end_time
            elif campus.schedule_end_time is not False:
                end_time_float = campus.schedule_end_time
            else:
                end_time_float = 18.0
        else:
            start_time_float = 8.0
            end_time_float = 18.0
        # Guardar los floats para los campos editables
        res['start_time'] = start_time_float
        res['end_time'] = end_time_float
        # También inicializar los datetime para consistencia
        today = datetime.now(tz_colombia).date()
        start_hours = int(start_time_float)
        start_minutes = int((start_time_float % 1) * 60)
        end_hours = int(end_time_float)
        end_minutes = int((end_time_float % 1) * 60)
        start_naive = datetime.combine(today, datetime.min.time()).replace(hour=start_hours, minute=start_minutes, second=0, microsecond=0)
        end_naive = datetime.combine(today, datetime.min.time()).replace(hour=end_hours, minute=end_minutes, second=0, microsecond=0)
        start_local = tz_colombia.localize(start_naive)
        end_local = tz_colombia.localize(end_naive)
        res['start_datetime'] = start_local.astimezone(pytz.UTC).replace(tzinfo=None)
        res['end_datetime'] = end_local.astimezone(pytz.UTC).replace(tzinfo=None)
        return res

    @api.model
    def _get_city_selection(self):
        """Obtiene dinámicamente la lista de ciudades desde las sedes existentes."""
        cities = self.env["benglish.campus"].search([]).mapped("city_name")
        # Eliminar duplicados y ordenar
        unique_cities = sorted(set(filter(None, cities)))
        # Retornar como lista de tuplas (value, label)
        return [(city, city) for city in unique_cities]

    @api.onchange("program_id")
    def _onchange_program_id(self):
        """Cuando cambia el programa, limpia el plan y la asignatura."""
        if self.program_id:
            self.plan_id = False
            self.subject_id = False

    @api.onchange("plan_id")
    def _onchange_plan_id(self):
        """Cuando cambia el plan, limpia la asignatura."""
        if self.plan_id:
            self.subject_id = False

    @api.onchange("subject_id")
    def _onchange_subject_id(self):
        """Cuando cambia la asignatura, marca automáticamente si es prerrequisito."""
        if self.subject_id:
            # Si la asignatura tiene clasificación 'prerequisite', marca la sesión como prerrequisito
            self.is_prerequisite_session = (
                self.subject_id.subject_classification == "prerequisite"
            )

    @api.onchange("coach_id", "delivery_mode")
    def _onchange_coach_delivery_mode(self):
        """Cuando cambia el coach o la modalidad, copia el enlace si es virtual o híbrida."""
        if self.coach_id and self.delivery_mode in ["virtual", "hybrid"]:
            # Copiar el enlace y plataforma del coach
            self.meeting_link = self.coach_id.meeting_link
            self.meeting_platform = self.coach_id.meeting_platform
        elif self.delivery_mode == "presential":
            # Limpiar los campos si es presencial
            self.meeting_link = False
            self.meeting_platform = False

    @api.onchange("delivery_mode")
    def _onchange_delivery_mode(self):
        """Cuando cambia la modalidad, limpia la ubicación si es virtual."""
        if self.delivery_mode == "virtual":
            self.location_city = False
            # No limpiamos campus_id porque sigue siendo requerido

    @api.onchange("location_city")
    def _onchange_location_city(self):
        """Cuando cambia la ubicación, limpia la sede para forzar nueva selección."""
        if self.location_city:
            # Limpia la sede actual para forzar selección de una sede de la nueva ubicación
            self.campus_id = False
            self.subcampus_id = False

    @api.depends("student_ids")
    def _compute_enrolled_count(self):
        """Calcula el número de estudiantes inscritos en la sesión."""
        for record in self:
            record.enrolled_count = len(record.student_ids)

    @api.depends("max_capacity", "enrolled_count")
    def _compute_available_spots(self):
        """Calcula los cupos disponibles en la sesión."""
        for record in self:
            record.available_spots = max(0, record.max_capacity - record.enrolled_count)

    @api.depends("enrolled_count", "max_capacity")
    def _compute_is_full(self):
        """Determina si la sesión alcanzó su capacidad máxima."""
        for record in self:
            record.is_full = record.enrolled_count >= record.max_capacity

    @api.depends("enrolled_count", "max_capacity")
    def _compute_occupancy_rate(self):
        """Calcula el porcentaje de ocupación de la sesión."""
        for record in self:
            if record.max_capacity > 0:
                record.occupancy_rate = (
                    record.enrolled_count / record.max_capacity
                ) * 100.0
            else:
                record.occupancy_rate = 0.0

    @api.depends("subject_id", "start_datetime")
    def _compute_display_name(self):
        for record in self:
            parts = []
            if record.subject_id:
                parts.append(record.subject_id.name)
            if record.start_datetime:
                start_str = fields.Datetime.to_string(record.start_datetime)
                parts.append(start_str)
            if record.session_type and record.session_type != "regular":
                parts.append(
                    dict(record._fields["session_type"].selection).get(
                        record.session_type
                    )
                )
            record.display_name = " - ".join(parts) if parts else _("Nueva sesión")

    @api.depends("replacement_log_ids")
    def _compute_replacement_count(self):
        """Cuenta el número de reemplazos realizados."""
        for record in self:
            record.replacement_count = len(record.replacement_log_ids)

    @api.depends("start_datetime", "end_datetime")
    def _compute_duration(self):
        for record in self:
            if record.start_datetime and record.end_datetime:
                start_dt = fields.Datetime.to_datetime(record.start_datetime)
                end_dt = fields.Datetime.to_datetime(record.end_datetime)
                delta = end_dt - start_dt
                record.duration_hours = delta.total_seconds() / 3600.0
            else:
                record.duration_hours = 0.0

    @api.depends("start_datetime", "end_datetime")
    def _compute_aux_dates(self):
        for record in self:
            if record.start_datetime:
                record.date = fields.Datetime.to_datetime(record.start_datetime).date()
                record.start_time = record._datetime_to_float(record.start_datetime)
            else:
                record.date = False
                record.start_time = 0.0
            if record.end_datetime:
                record.end_time = record._datetime_to_float(record.end_datetime)
            else:
                record.end_time = 0.0

    def _datetime_to_float(self, value):
        dt = fields.Datetime.to_datetime(value) if value else None
        if not dt:
            return 0.0
        return dt.hour + dt.minute / 60.0

    def write(self, vals):
        """
        Sobrescribe write para controlar la gestión de estudiantes.
        Los coordinadores NO pueden agregar estudiantes manualmente.
        Solo pueden:
        - Remover estudiantes (liberar cupos)
        - Ajustar max_capacity (capacidad máxima)

        Los estudiantes solo se agregan automáticamente desde el portal.

        IMPORTANTE: También asegura que delivery_mode no se pierda al guardar.
        """
        # DEBUG: Log para ver qué se está intentando guardar
        if "delivery_mode" in vals:
            import logging

            _logger = logging.getLogger(__name__)
            _logger.info(f"WRITE - delivery_mode en vals: {vals.get('delivery_mode')}")

        # Verificar si se están agregando estudiantes
        if "student_ids" in vals:
            # Verificar si es el grupo de coordinadores (no managers/admins)
            is_coordinator = self.env.user.has_group(
                "benglish_academy.group_academic_coordinator"
            )
            is_manager = self.env.user.has_group(
                "benglish_academy.group_academic_manager"
            )

            # Si es coordinador (pero no manager), verificar que solo esté removiendo
            if is_coordinator and not is_manager:
                for record in self:
                    current_student_ids = set(record.student_ids.ids)
                    new_operations = vals["student_ids"]

                    # Analizar las operaciones de many2many
                    for operation in new_operations:
                        if isinstance(operation, (list, tuple)):
                            op_code = operation[0]
                            # Operación 4 = agregar (link), 3 = remover (unlink), 6 = reemplazar (set)
                            if op_code == 4:  # Intentando agregar un estudiante
                                raise UserError(
                                    _(
                                        "Los coordinadores no pueden agregar estudiantes manualmente a las sesiones.\n\n"
                                        "Los estudiantes se inscriben automáticamente desde el portal.\n\n"
                                        "Como coordinador, puedes:\n"
                                        "• Remover estudiantes haciendo clic en la 'X' (liberar cupos)\n"
                                        "• Ajustar la 'Capacidad Máxima' para controlar la disponibilidad"
                                    )
                                )
                            elif op_code == 6:  # Reemplazar lista completa
                                new_student_ids = set(operation[2])
                                # Verificar si se están agregando nuevos IDs
                                if new_student_ids - current_student_ids:
                                    raise UserError(
                                        _(
                                            "Los coordinadores no pueden agregar estudiantes manualmente a las sesiones.\n\n"
                                            "Los estudiantes se inscriben automáticamente desde el portal.\n\n"
                                            "Como coordinador, puedes:\n"
                                            "• Remover estudiantes haciendo clic en la 'X' (liberar cupos)\n"
                                            "• Ajustar la 'Capacidad Máxima' para controlar la disponibilidad"
                                        )
                                    )

        return super(ClassSession, self).write(vals)

    @api.onchange("campus_id")
    def _onchange_campus_id(self):
        """
        Al cambiar la sede, actualiza las horas de inicio y fin con los defaults de la nueva sede.
        También ajusta la duración de la sesión según la configuración de la sede.
        
        Comportamiento:
        - Si la sede tiene horas por defecto configuradas, actualiza start_datetime y end_datetime
        - Respeta la fecha actual (solo cambia la hora, no la fecha)
        - Si no hay horas configuradas, usa fallback razonable (8:00 - 10:00)
        """
        if not self.campus_id:
            return
        
        from datetime import datetime, timedelta
        import pytz
        
        # Zona horaria de Colombia
        tz_colombia = pytz.timezone('America/Bogota')
        
        # Obtener horas por defecto de la sede o usar fallback
        if self.campus_id.default_start_time is not False:
            start_time_float = self.campus_id.default_start_time
        elif self.campus_id.schedule_start_time is not False:
            start_time_float = self.campus_id.schedule_start_time
        else:
            start_time_float = 8.0

        if self.campus_id.default_end_time is not False:
            end_time_float = self.campus_id.default_end_time
        elif self.campus_id.schedule_end_time is not False:
            end_time_float = self.campus_id.schedule_end_time
        else:
            end_time_float = 18.0
        
        # Convertir float a horas y minutos
        start_hours = int(start_time_float)
        start_minutes = int((start_time_float % 1) * 60)
        end_hours = int(end_time_float)
        end_minutes = int((end_time_float % 1) * 60)
        
        # Determinar la fecha base (mantener fecha actual si existe, sino usar hoy)
        if self.start_datetime:
            base_datetime = fields.Datetime.to_datetime(self.start_datetime)
            # Convertir UTC a hora Colombia para obtener la fecha local
            base_datetime_utc = pytz.UTC.localize(base_datetime)
            base_datetime_local = base_datetime_utc.astimezone(tz_colombia)
            base_date = base_datetime_local.date()
        else:
            # Usar fecha de hoy en hora Colombia
            base_date = datetime.now(tz_colombia).date()
        
        # Crear datetime naive en hora Colombia
        start_datetime_naive = datetime.combine(
            base_date,
            datetime.min.time()
        ).replace(hour=start_hours, minute=start_minutes, second=0, microsecond=0)
        
        end_datetime_naive = datetime.combine(
            base_date,
            datetime.min.time()
        ).replace(hour=end_hours, minute=end_minutes, second=0, microsecond=0)
        
        # Convertir a UTC para Odoo
        start_datetime_local = tz_colombia.localize(start_datetime_naive)
        end_datetime_local = tz_colombia.localize(end_datetime_naive)
        start_datetime_utc = start_datetime_local.astimezone(pytz.UTC)
        end_datetime_utc = end_datetime_local.astimezone(pytz.UTC)
        
        # Actualizar los campos (sin tzinfo porque Odoo los guarda naive en UTC)
        self.start_datetime = start_datetime_utc.replace(tzinfo=None)
        self.end_datetime = end_datetime_utc.replace(tzinfo=None)


    @api.onchange("subcampus_id")
    def _onchange_subcampus_id(self):
        if self.subcampus_id:
            # Solo actualizar campus_id si no está ya definido o si es diferente
            if not self.campus_id or self.campus_id != self.subcampus_id.campus_id:
                self.campus_id = self.subcampus_id.campus_id
            # Auto-asignar capacidad máxima del aula
            if self.subcampus_id.capacity:
                self.max_capacity = self.subcampus_id.capacity
            # Sugerir enlaces si el subcampus tiene, pero no cambiar la modalidad
            if self.subcampus_id.meeting_url and not self.meeting_link:
                self.meeting_link = self.subcampus_id.meeting_url
            if self.subcampus_id.meeting_platform and not self.meeting_platform:
                self.meeting_platform = self.subcampus_id.meeting_platform

    @api.constrains("start_datetime", "end_datetime")
    def _check_dates(self):
        for record in self:
            if (
                record.start_datetime
                and record.end_datetime
                and record.end_datetime <= record.start_datetime
            ):
                raise ValidationError(
                    _("La hora de fin debe ser posterior a la de inicio.")
                )

    @api.constrains("state", "cancellation_reason")
    def _check_cancellation_reason(self):
        for record in self:
            if record.state == "cancelled" and not (
                record.cancellation_reason
                or self.env.context.get("cancellation_reason")
            ):
                raise ValidationError(_("Debe indicar un motivo de cancelación."))

    @api.constrains(
        "start_datetime",
        "end_datetime",
        "teacher_id",
        "coach_id",
        "subcampus_id",
        "state",
    )
    def _check_overlaps(self):
        for record in self:
            if (
                not record.start_datetime
                or not record.end_datetime
                or record.state == "cancelled"
            ):
                continue
            base_domain = [
                ("id", "!=", record.id),
                ("state", "!=", "cancelled"),
                ("start_datetime", "<", record.end_datetime),
                ("end_datetime", ">", record.start_datetime),
            ]
            # Ya no validamos por grupo, cada sesión se gestiona independientemente por cupos
            if record.teacher_id:
                self._raise_if_conflict(
                    base_domain + [("teacher_id", "=", record.teacher_id.id)],
                    _("El docente ya tiene otra sesión en ese horario."),
                )
            if record.coach_id:
                self._raise_if_conflict(
                    base_domain + [("coach_id", "=", record.coach_id.id)],
                    _("El coach ya tiene otra sesión en ese horario."),
                )
            if record.subcampus_id:
                self._raise_if_conflict(
                    base_domain + [("subcampus_id", "=", record.subcampus_id.id)],
                    _("El aula ya está ocupada en ese horario."),
                )

    def _raise_if_conflict(self, domain, message):
        if self.search_count(domain):
            raise ValidationError(message)

    # VALIDACIONES DEL SISTEMA DE AGENDA

    @api.constrains("campus_id", "start_datetime", "end_datetime")
    def _check_campus_schedule(self):
        """
        Valida que la sesión cumpla con las restricciones de horario de la sede.
        - Horario permitido (ej: 7:00 AM - 6:00 PM)
        - Días permitidos (ej: Lunes a Sábado, sin Domingos)
        """
        for record in self:
            if (
                not record.campus_id
                or not record.start_datetime
                or not record.end_datetime
            ):
                continue

            # Validar usando el método del campus (que maneja zona horaria de Colombia)
            try:
                record.campus_id.validate_session_schedule(
                    record.start_datetime, record.end_datetime
                )
            except ValidationError as e:
                # Re-lanzar con contexto adicional
                raise ValidationError(
                    _(
                        'Error de programación en sesión "%s" (zona horaria: Colombia UTC-5):\n\n%s\n\n'
                        "Recuerde que los horarios se validan según la hora local de Colombia."
                    )
                    % (record.display_name or "Nueva sesión", str(e))
                )

    @api.constrains("student_ids", "max_capacity")
    def _check_capacity(self):
        """
        Valida que no se exceda la capacidad máxima de estudiantes.
        Esta validación se ejecuta cuando se agregan estudiantes o se modifica la capacidad.
        """
        for record in self:
            if len(record.student_ids) > record.max_capacity:
                raise ValidationError(
                    _(
                        'La sesión "%s" ha excedido su capacidad máxima.\n'
                        "Capacidad máxima: %d\n"
                        "Estudiantes inscritos: %d\n"
                        "Por favor, aumente la capacidad o retire algunos estudiantes."
                    )
                    % (
                        record.display_name or "Nueva sesión",
                        record.max_capacity,
                        len(record.student_ids),
                    )
                )

    @api.constrains("max_capacity")
    def _check_max_capacity_positive(self):
        """Valida que la capacidad máxima sea un número positivo."""
        for record in self:
            if record.max_capacity <= 0:
                raise ValidationError(
                    _("La capacidad máxima debe ser mayor a cero. Valor actual: %d")
                    % record.max_capacity
                )

    def _raise_if_conflict(self, domain, message):
        if self.search_count(domain):
            raise ValidationError(message)

    # MÉTODOS PARA GESTIÓN DE ESTUDIANTES

    def action_add_student(self, student_id):
        """
        Agrega un estudiante a la sesión respetando la capacidad máxima.

        Args:
            student_id (int): ID del estudiante a agregar

        Raises:
            UserError: Si la sesión está llena o el estudiante ya está inscrito
        """
        self.ensure_one()

        student = self.env["benglish.student"].browse(student_id)

        if not student.exists():
            raise UserError(_("El estudiante especificado no existe."))

        if student in self.student_ids:
            raise UserError(
                _('El estudiante "%s" ya está inscrito en esta sesión.') % student.name
            )

        if self.is_full:
            raise UserError(
                _(
                    'La sesión "%s" ha alcanzado su capacidad máxima (%d estudiantes).\n'
                    "No se pueden agregar más estudiantes."
                )
                % (self.display_name, self.max_capacity)
            )

        self.write({"student_ids": [(4, student_id)]})

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Estudiante Agregado"),
                "message": _('El estudiante "%s" fue inscrito exitosamente.')
                % student.name,
                "type": "success",
                "sticky": False,
            },
        }

    def action_remove_student(self, student_id):
        """
        Remueve un estudiante de la sesión.

        Args:
            student_id (int): ID del estudiante a remover

        Raises:
            UserError: Si el estudiante no está inscrito
        """
        self.ensure_one()

        student = self.env["benglish.student"].browse(student_id)

        if not student.exists():
            raise UserError(_("El estudiante especificado no existe."))

        if student not in self.student_ids:
            raise UserError(
                _('El estudiante "%s" no está inscrito en esta sesión.') % student.name
            )

        self.write({"student_ids": [(3, student_id)]})

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Estudiante Removido"),
                "message": _('El estudiante "%s" fue removido de la sesión.')
                % student.name,
                "type": "info",
                "sticky": False,
            },
        }

    def action_add_students_bulk(self, student_ids):
        """
        Agrega múltiples estudiantes a la sesión de forma masiva.

        Args:
            student_ids (list): Lista de IDs de estudiantes

        Raises:
            UserError: Si se excede la capacidad
        """
        self.ensure_one()

        # Filtrar estudiantes que no están inscritos
        current_ids = self.student_ids.ids
        new_student_ids = [sid for sid in student_ids if sid not in current_ids]

        if not new_student_ids:
            raise UserError(
                _("Todos los estudiantes seleccionados ya están inscritos.")
            )

        # Verificar capacidad
        total_after = len(current_ids) + len(new_student_ids)
        if total_after > self.max_capacity:
            raise UserError(
                _(
                    "No se pueden agregar %d estudiantes.\n"
                    "Capacidad máxima: %d\n"
                    "Inscritos actuales: %d\n"
                    "Cupos disponibles: %d"
                )
                % (
                    len(new_student_ids),
                    self.max_capacity,
                    len(current_ids),
                    self.available_spots,
                )
            )

        self.write({"student_ids": [(4, sid) for sid in new_student_ids]})

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Estudiantes Agregados"),
                "message": _("%d estudiantes fueron inscritos exitosamente.")
                % len(new_student_ids),
                "type": "success",
                "sticky": False,
            },
        }

    def get_available_students(self):
        """
        Retorna los estudiantes disponibles para inscribir (que no están ya inscritos).

        Returns:
            recordset: Estudiantes disponibles
        """
        self.ensure_one()
        return self.env["benglish.student"].search(
            [
                ("id", "not in", self.student_ids.ids),
                ("active", "=", True),
            ]
        )

    def action_open_manage_students_wizard(self):
        """
        Abre un wizard para que el coordinador pueda liberar cupos.
        Permite seleccionar y remover estudiantes inscritos.
        """
        self.ensure_one()

        if not self.student_ids:
            raise UserError(_("No hay estudiantes inscritos en esta sesión."))

        # Retornar acción de selección múltiple de estudiantes a remover
        return {
            "name": _("Liberar Cupos - Remover Estudiantes"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.student",
            "view_mode": "list",
            "domain": [("id", "in", self.student_ids.ids)],
            "target": "new",
            "context": {
                "session_id": self.id,
                "show_remove_action": True,
            },
            "views": [(False, "list")],
        }

    def action_remove_students_from_session(self, student_ids):
        """
        Remueve múltiples estudiantes de la sesión (libera cupos).
        Usado por el coordinador para gestionar cupos.

        Args:
            student_ids (list): IDs de estudiantes a remover
        """
        self.ensure_one()

        if not student_ids:
            raise UserError(_("Debe seleccionar al menos un estudiante para remover."))

        # Filtrar solo estudiantes que están inscritos
        students_to_remove = self.student_ids.filtered(lambda s: s.id in student_ids)

        if not students_to_remove:
            raise UserError(
                _("Los estudiantes seleccionados no están inscritos en esta sesión.")
            )

        # Remover estudiantes
        self.write({"student_ids": [(3, sid) for sid in students_to_remove.ids]})

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Cupos Liberados"),
                "message": _(
                    "%d estudiante(s) fueron removidos. Cupos disponibles: %d/%d"
                )
                % (len(students_to_remove), self.available_spots, self.max_capacity),
                "type": "success",
                "sticky": False,
            },
        }

    # Acciones de estado
    def action_mark_in_progress(self):
        for record in self.filtered(lambda s: s.state == "planned"):
            record.write({"state": "in_progress"})
            # Forzar persistencia inmediata en base de datos
            record.flush_recordset()

    def action_mark_done(self):
        for record in self.filtered(lambda s: s.state in ("planned", "in_progress")):
            record.write({"state": "done"})
            # Forzar persistencia inmediata en base de datos
            record.flush_recordset()

    def action_reset_to_planned(self):
        for record in self:
            record.write(
                {
                    "state": "planned",
                    "cancelled_by_id": False,
                    "cancelled_at": False,
                    "cancellation_reason": False,
                }
            )

    def action_cancel(self):
        """Cancela la sesión aplicando las reglas del negocio."""
        for record in self.filtered(lambda s: s.state != "done"):
            reason = (
                self.env.context.get("cancellation_reason")
                or record.cancellation_reason
            )
            if not reason:
                raise UserError(
                    _("Debe registrar un motivo antes de cancelar la sesión.")
                )
            record.write(
                {
                    "state": "cancelled",
                    "cancellation_reason": reason,
                    "cancelled_by_id": self.env.user.id,
                    "cancelled_at": fields.Datetime.now(),
                }
            )
            # Si estaba publicada, despublicarla automáticamente
            if record.is_published:
                record.action_unpublish()

    # Acciones de publicación
    def action_publish(self):
        """
        Publica la sesión para que sea visible en portales de estudiantes.
        Valida que la sesión cumpla con los horarios y días permitidos de la sede.

        IMPORTANTE: Preserva la modalidad (delivery_mode) seleccionada por el usuario.
        """
        for record in self:
            # CRÍTICO: Capturar la modalidad actual ANTES de cualquier operación
            # para asegurar que no se pierda durante el proceso de publicación
            current_delivery_mode = record.delivery_mode

            import logging

            _logger = logging.getLogger(__name__)
            _logger.info(
                f"ACTION_PUBLISH - Modalidad actual ANTES de publicar: {current_delivery_mode}"
            )

            # Validaciones básicas
            if record.state == "cancelled":
                raise UserError(_("No se puede publicar una sesión cancelada."))
            if not record.subject_id:
                raise UserError(
                    _("La sesión debe tener una asignatura asignada para publicarse.")
                )

            # VALIDACIÓN CRÍTICA: Verificar que la sesión cumple con horarios y días de la sede
            if record.campus_id and record.start_datetime and record.end_datetime:
                try:
                    # Usar el método de validación del campus
                    record.campus_id.validate_session_schedule(
                        record.start_datetime, record.end_datetime
                    )
                except ValidationError as e:
                    raise UserError(
                        _(
                            'No se puede publicar la sesión "%s".\n\n'
                            'La sesión no cumple con las restricciones de horario de la sede "%s":\n\n%s\n\n'
                            "Por favor, ajuste el horario de la sesión antes de publicarla."
                        )
                        % (record.display_name, record.campus_id.name, str(e))
                    )

            # Publicar la sesión Y PRESERVAR la modalidad seleccionada
            record.write(
                {
                    "is_published": True,
                    "published_at": fields.Datetime.now(),
                    "published_by_id": self.env.user.id,
                    "delivery_mode": current_delivery_mode,  # FORZAR la modalidad original
                }
            )

            _logger.info(
                f"ACTION_PUBLISH - Modalidad DESPUÉS de publicar: {record.delivery_mode}"
            )

    def action_unpublish(self):
        """Despublica la sesión para ocultarla de portales."""
        for record in self:
            record.write(
                {
                    "is_published": False,
                    "published_at": False,
                    "published_by_id": False,
                }
            )

    def action_publish_bulk(self, sessions=None):
        """
        Publica múltiples sesiones en lote (para coordinadores).
        Valida que todas cumplan con horarios y días de la sede.
        """
        sessions = sessions or self
        sessions_to_publish = sessions.filtered(
            lambda s: s.state != "cancelled" and s.subject_id
        )
        if not sessions_to_publish:
            raise UserError(_("No hay sesiones válidas para publicar."))

        # VALIDACIÓN: Verificar que todas las sesiones cumplan con restricciones de sede
        invalid_sessions = []
        for session in sessions_to_publish:
            if session.campus_id and session.start_datetime and session.end_datetime:
                try:
                    session.campus_id.validate_session_schedule(
                        session.start_datetime, session.end_datetime
                    )
                except ValidationError as e:
                    invalid_sessions.append(
                        {
                            "session": session.display_name,
                            "campus": session.campus_id.name,
                            "error": str(e),
                        }
                    )

        # Si hay sesiones inválidas, mostrar error detallado
        if invalid_sessions:
            error_msg = _(
                "No se pueden publicar las siguientes sesiones porque no cumplen con las restricciones de horario de sus sedes:\n\n"
            )
            for inv in invalid_sessions:
                error_msg += _("• %s (Sede: %s)\n  %s\n\n") % (
                    inv["session"],
                    inv["campus"],
                    inv["error"],
                )
            error_msg += _("Por favor, ajuste los horarios antes de publicar.")
            raise UserError(error_msg)

        # Si todas son válidas, publicar PRESERVANDO la modalidad de cada sesión
        for session in sessions_to_publish:
            current_delivery_mode = session.delivery_mode
            session.write(
                {
                    "is_published": True,
                    "published_at": fields.Datetime.now(),
                    "published_by_id": self.env.user.id,
                    "delivery_mode": current_delivery_mode,  # PRESERVAR modalidad
                }
            )
        # Notificación via bus
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "simple_notification",
            {
                "title": _("Publicación Exitosa"),
                "message": _("%s sesiones fueron publicadas.")
                % len(sessions_to_publish),
                "type": "success",
                "sticky": False,
            },
        )
        return True

    # Acción de reemplazo de docente
    def action_replace_teacher(self):
        """Reemplaza el docente registrando el historial completo."""
        self.ensure_one()
        if not self.teacher_id:
            raise UserError(_("No hay un docente asignado para reemplazar."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Reemplazar Docente"),
            "res_model": "benglish.replace.teacher.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_session_id": self.id,
                "default_original_teacher_id": self.teacher_id.id,
            },
        }

    def _do_replace_teacher(
        self, new_teacher_id, reason, replacement_type="single", notes=None
    ):
        """
        Ejecuta el reemplazo de docente con validaciones y log de auditoría.

        Args:
            new_teacher_id: ID del nuevo docente
            reason: Motivo del reemplazo
            replacement_type: Tipo de reemplazo ('single', 'future', 'all', 'massive')
            notes: Notas adicionales opcionales
        """
        ReplacementLog = self.env["benglish.teacher.replacement.log"]

        for record in self:
            if not record.teacher_id:
                continue

            # Guardar referencia al docente anterior
            original_teacher_id = record.teacher_id.id

            # Guardar docente original si no existe (primera vez)
            if not record.original_teacher_id:
                record.original_teacher_id = record.teacher_id

            # Actualizar docente y registrar auditoría en la sesión
            record.write(
                {
                    "teacher_id": new_teacher_id,
                    "replacement_reason": reason,
                    "replaced_at": fields.Datetime.now(),
                    "replaced_by_id": self.env.user.id,
                }
            )

            # Crear log de auditoría
            ReplacementLog.create_log(
                session_id=record.id,
                original_teacher_id=original_teacher_id,
                new_teacher_id=new_teacher_id,
                reason=reason,
                replacement_type=replacement_type,
                notes=notes,
            )

            # Revalidar solapamientos con el nuevo docente
            try:
                record._check_overlaps()
            except ValidationError as e:
                raise UserError(
                    _("El nuevo docente tiene un conflicto de horario: %s") % str(e)
                )

    def name_get(self):
        result = []
        for record in self:
            name = record.display_name or record.name or _("Sesión")
            result.append((record.id, name))
        return result

    # MÉTODOS PARA FILTRADO DE AGENDAS POR MODALIDAD

    @api.model
    def get_presential_agenda(self, domain=None, **kwargs):
        """
        Retorna solo sesiones presenciales.
        Útil para generar vistas de agenda presencial independiente.

        Args:
            domain (list): Dominio adicional de filtrado
            **kwargs: Parámetros adicionales (date_start, date_end, campus_id, etc.)

        Returns:
            recordset: Sesiones presenciales
        """
        base_domain = [("delivery_mode", "=", "presential")]
        if domain:
            base_domain += domain

        # Agregar filtros adicionales desde kwargs
        if kwargs.get("campus_id"):
            base_domain.append(("campus_id", "=", kwargs["campus_id"]))
        if kwargs.get("date_start"):
            base_domain.append(("start_datetime", ">=", kwargs["date_start"]))
        if kwargs.get("date_end"):
            base_domain.append(("start_datetime", "<=", kwargs["date_end"]))

        return self.search(base_domain)

    @api.model
    def get_virtual_agenda(self, domain=None, **kwargs):
        """
        Retorna solo sesiones virtuales.
        Útil para generar vistas de agenda virtual independiente.

        Args:
            domain (list): Dominio adicional de filtrado
            **kwargs: Parámetros adicionales

        Returns:
            recordset: Sesiones virtuales
        """
        base_domain = [("delivery_mode", "=", "virtual")]
        if domain:
            base_domain += domain

        if kwargs.get("campus_id"):
            base_domain.append(("campus_id", "=", kwargs["campus_id"]))
        if kwargs.get("date_start"):
            base_domain.append(("start_datetime", ">=", kwargs["date_start"]))
        if kwargs.get("date_end"):
            base_domain.append(("start_datetime", "<=", kwargs["date_end"]))

        return self.search(base_domain)

    @api.model
    def get_hybrid_agenda(self, domain=None, **kwargs):
        """
        Retorna sesiones híbridas (que incluyen modalidad híbrida o combinación de presencial y virtual).
        Útil para generar vistas de agenda integrada.

        Args:
            domain (list): Dominio adicional de filtrado
            **kwargs: Parámetros adicionales

        Returns:
            recordset: Sesiones híbridas o combinadas
        """
        base_domain = [("delivery_mode", "in", ["hybrid", "presential", "virtual"])]
        if domain:
            base_domain += domain

        if kwargs.get("campus_id"):
            base_domain.append(("campus_id", "=", kwargs["campus_id"]))
        if kwargs.get("date_start"):
            base_domain.append(("start_datetime", ">=", kwargs["date_start"]))
        if kwargs.get("date_end"):
            base_domain.append(("start_datetime", "<=", kwargs["date_end"]))

        return self.search(base_domain)

    @api.model
    def get_agenda_by_mode(self, mode, domain=None, **kwargs):
        """
        Método genérico para obtener agenda según modalidad.

        Args:
            mode (str): 'presential', 'virtual', 'hybrid', o 'all'
            domain (list): Dominio adicional
            **kwargs: Parámetros adicionales

        Returns:
            recordset: Sesiones filtradas por modalidad
        """
        if mode == "presential":
            return self.get_presential_agenda(domain, **kwargs)
        elif mode == "virtual":
            return self.get_virtual_agenda(domain, **kwargs)
        elif mode == "hybrid":
            return self.get_hybrid_agenda(domain, **kwargs)
        else:  # 'all' o cualquier otro valor
            base_domain = domain or []
            if kwargs.get("campus_id"):
                base_domain.append(("campus_id", "=", kwargs["campus_id"]))
            if kwargs.get("date_start"):
                base_domain.append(("start_datetime", ">=", kwargs["date_start"]))
            if kwargs.get("date_end"):
                base_domain.append(("start_datetime", "<=", kwargs["date_end"]))
            return self.search(base_domain)
