# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import pytz
import logging

_logger = logging.getLogger(__name__)


class AcademicSession(models.Model):
    """
    Modelo para gestionar Sesiones de Clase dentro de una Agenda Académica.
    Cada sesión representa una clase específica en una fecha, hora, aula y con docente asignado.
    Maneja inscripciones de estudiantes y validaciones de conflictos.
    """

    _name = "benglish.academic.session"
    _description = "Sesión de Clase (Agenda Académica)"
    _inherit = ["mail.thread", "mail.activity.mixin", "benglish.session.sync.mixin"]
    _order = "date, time_start, subject_id"
    _rec_name = "display_name"

    # RELACIÓN CON AGENDA (OBLIGATORIA)

    agenda_id = fields.Many2one(
        comodel_name="benglish.academic.agenda",
        string="Horario",
        required=True,
        ondelete="cascade",
        tracking=True,
        index=True,
        help="Horario académico al que pertenece esta sesión",
    )

    # IDENTIFICACIÓN

    name = fields.Char(
        string="Nombre Interno",
        compute="_compute_name",
        store=True,
        help="Nombre generado automáticamente para identificación",
    )

    display_name = fields.Char(
        string="Nombre a Mostrar",
        compute="_compute_display_name",
        store=True,
        help="Nombre completo para visualización",
    )

    session_code = fields.Char(
        string="Código de Sesión",
        help="Código único/identificador opcional para la sesión (ej: H-0001). Configurable mediante parámetros.",
    )

    # FECHA Y HORA (HEREDADAS DE AGENDA)

    date = fields.Date(
        string="Fecha",
        required=True,
        tracking=True,
        index=True,
        help="Fecha de la sesión (debe estar dentro del rango del horario)",
    )

    time_start = fields.Float(
        string="Hora de Inicio",
        required=True,
        tracking=True,
        help="Hora de inicio (formato 24h decimal: 7.0 = 7:00 AM, 14.5 = 2:30 PM)",
    )

    time_end = fields.Float(
        string="Hora de Fin",
        required=True,
        tracking=True,
        help="Hora de fin (formato 24h decimal: 18.0 = 6:00 PM, 20.5 = 8:30 PM)",
    )

    # Etiquetas legibles para mostrar en vistas (corrigen unidades erróneas)
    time_start_label = fields.Char(
        string="Hora Inicio (label)", compute="_compute_time_labels", store=True
    )
    time_end_label = fields.Char(
        string="Hora Fin (label)", compute="_compute_time_labels", store=True
    )

    duration_hours = fields.Float(
        string="Duración (horas)",
        compute="_compute_duration",
        store=True,
        help="Duración de la sesión en horas",
    )

    all_day = fields.Boolean(
        string="Todo el día",
        default=False,
        help="Campo técnico para compatibilidad con vista calendar (siempre False)",
    )

    # Campos Datetime para vista calendar (combinan date + time)
    datetime_start = fields.Datetime(
        string="Fecha y Hora de Inicio",
        compute="_compute_datetime_fields",
        store=True,
        help="Datetime de inicio para vista calendar",
    )

    datetime_end = fields.Datetime(
        string="Fecha y Hora de Fin",
        compute="_compute_datetime_fields",
        store=True,
        help="Datetime de fin para vista calendar",
    )

    # Campo auxiliar para búsquedas por día de la semana
    weekday = fields.Selection(
        selection=[
            ("0", "Lunes"),
            ("1", "Martes"),
            ("2", "Miércoles"),
            ("3", "Jueves"),
            ("4", "Viernes"),
            ("5", "Sábado"),
            ("6", "Domingo"),
        ],
        string="Día de la Semana",
        compute="_compute_weekday",
        store=True,
        help="Día de la semana calculado desde la fecha",
    )

    # UBICACIÓN (HEREDADA DE AGENDA)

    # Campos computados desde la agenda
    location_city = fields.Selection(
        selection="_get_city_selection",
        string="Ciudad",
        related="agenda_id.location_city",
        store=True,
        readonly=True,
        help="Ciudad heredada de la agenda",
    )

    campus_id = fields.Many2one(
        comodel_name="benglish.campus",
        string="Sede",
        related="agenda_id.campus_id",
        store=True,
        readonly=True,
        help="Sede heredada del horario",
    )

    # Campos auxiliares para dominios dinámicos de disponibilidad
    available_teacher_ids = fields.Many2many(
        comodel_name="hr.employee",
        relation="academic_session_available_teacher_rel",
        column1="session_id",
        column2="employee_id",
        compute="_compute_available_resources",
        string="Docentes Disponibles",
        help="IDs de docentes (hr.employee con is_teacher=True) disponibles en este horario",
    )

    available_classroom_ids = fields.Many2many(
        comodel_name="benglish.subcampus",
        relation="academic_session_available_classroom_rel",
        column1="session_id",
        column2="subcampus_id",
        compute="_compute_available_resources",
        string="Aulas Disponibles",
        help="IDs de aulas disponibles en este horario",
    )

    subcampus_id = fields.Many2one(
        comodel_name="benglish.subcampus",
        string="Aula",
        required=False,
        ondelete="restrict",
        tracking=True,
        domain="[('id', 'in', available_classroom_ids)]",
        index=True,
        help="Aula específica donde se dicta la clase (solo para modalidad presencial o híbrida)",
    )

    # INFORMACIÓN ACADÉMICA (SIMPLIFICADA)

    program_id = fields.Many2one(
        comodel_name="benglish.program",
        string="Programa",
        required=True,
        ondelete="restrict",
        tracking=True,
        help="Programa académico (ej: Benglish, B teens)",
    )

    subject_id = fields.Many2one(
        comodel_name="benglish.subject",
        string="Asignatura",
        required=True,
        ondelete="cascade",
        tracking=True,
        domain="[('program_id', '=', program_id), ('active', '=', True)]",
        index=True,
        help="Asignatura a dictar (muestra solo código + nombre)",
    )

    subject_code = fields.Char(
        string="Código Asignatura",
        related="subject_id.code",
        store=True,
        readonly=True,
    )

    subject_name = fields.Char(
        string="Nombre Asignatura",
        related="subject_id.name",
        store=True,
        readonly=True,
    )

    template_id = fields.Many2one(
        comodel_name="benglish.agenda.template",
        string="Plantilla",
        ondelete="restrict",
        domain="['|', ('program_id', '=', False), ('program_id', '=', program_id)]",
        help="Tipo/plantilla de horario usada para homologación por estudiante.",
    )

    audience_phase_id = fields.Many2one(
        comodel_name="benglish.phase",
        string="Fase Audiencia",
        ondelete="restrict",
        domain="[('program_id', '=', program_id), ('active', '=', True)]",
        help="Fase (rango de unidades) objetivo para la sesión.",
    )

    audience_unit_from = fields.Integer(
        string="Unidad Desde",
        help="Unidad inicial del rango de audiencia (1-24).",
    )
    audience_unit_to = fields.Integer(
        string="Unidad Hasta",
        help="Unidad final del rango de audiencia (1-24).",
    )
    
    is_oral_test_template = fields.Boolean(
        string="Es Oral Test",
        compute="_compute_is_oral_test_template",
        store=False,
        help="Indica si el template es de categoría oral_test",
    )

    student_alias = fields.Char(
        string="Alias Estudiante",
        compute="_compute_student_alias",
        store=True,
        help="Nombre visible para el estudiante (alias de plantilla).",
    )

    # TIPO Y MODALIDAD

    session_type = fields.Selection(
        selection=[
            ("regular", "Clase Regular"),
            ("makeup", "Clase de Recuperación"),
            ("evaluation", "Evaluación"),
            ("workshop", "Taller"),
        ],
        string="Tipo de Sesión",
        default="regular",
        required=True,
        tracking=True,
        help="Tipo de sesión académica",
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
        help="Modalidad de entrega de la clase",
    )

    meeting_link = fields.Char(
        string="Enlace de Reunión",
        help="Enlace para clase virtual o híbrida",
    )

    # DOCENTE (ÚNICO CAMPO - HR.EMPLOYEE)

    teacher_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Docente",
        domain="[('id', 'in', available_teacher_ids), ('is_teacher', '=', True)]",
        tracking=True,
        index=True,
        required=True,
        help="Docente asignado a la sesión (debe ser empleado marcado como docente y estar disponible en este horario)",
    )

    # Campos relacionados desde el docente
    teacher_meeting_link = fields.Char(
        string="Enlace de Reunión",
        related="teacher_id.meeting_link",
        readonly=True,
        help="Enlace de reunión del docente",
    )

    teacher_meeting_id = fields.Char(
        string="ID de Reunión",
        related="teacher_id.meeting_id",
        readonly=True,
        help="ID de reunión del docente",
    )

    # CAPACIDAD Y ESTUDIANTES

    max_capacity = fields.Integer(
        string="Capacidad Máxima",
        default=15,
        required=True,
        tracking=True,
        help="Número máximo de estudiantes que pueden inscribirse",
    )

    # Capacidades específicas para modalidad híbrida
    max_capacity_presential = fields.Integer(
        string="Capacidad Máxima Presencial",
        default=10,
        help="Capacidad máxima para estudiantes presenciales (solo aplica en modalidad híbrida)",
    )

    max_capacity_virtual = fields.Integer(
        string="Capacidad Máxima Virtual",
        default=10,
        help="Capacidad máxima para estudiantes virtuales (solo aplica en modalidad híbrida)",
    )

    enrollment_ids = fields.One2many(
        comodel_name="benglish.session.enrollment",
        inverse_name="session_id",
        string="Inscripciones",
        help="Estudiantes inscritos en esta sesión",
    )

    student_ids = fields.Many2many(
        comodel_name="benglish.student",
        string="Estudiantes",
        compute="_compute_student_ids",
        store=True,
        help="Estudiantes inscritos (desde enrollments)",
    )

    enrolled_count = fields.Integer(
        string="Estudiantes Inscritos",
        compute="_compute_capacity_stats",
        store=True,
        help="Número de estudiantes inscritos",
    )

    available_spots = fields.Integer(
        string="Cupos Disponibles",
        compute="_compute_capacity_stats",
        store=True,
        help="Cupos disponibles",
    )

    is_full = fields.Boolean(
        string="Sesión Llena",
        compute="_compute_capacity_stats",
        store=True,
        help="Indica si alcanzó capacidad máxima",
    )

    occupancy_rate = fields.Float(
        string="Tasa de Ocupación (%)",
        compute="_compute_capacity_stats",
        store=True,
        help="Porcentaje de ocupación",
    )

    # ESTADO

    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("active", "Activa"),
            ("with_enrollment", "En horario"),
            ("started", "Iniciada"),
            ("done", "Dictada"),
            ("cancelled", "Cancelada"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
        help="Estado del ciclo de vida de la sesión",
    )

    # Campo para indicar si la sesión está publicada (controlado por la agenda)
    is_published = fields.Boolean(
        string="Publicada",
        default=False,
        readonly=True,
        help="Indica si esta sesión fue publicada junto con su horario",
    )

    # CAMPOS AUXILIARES

    active = fields.Boolean(
        string="Activa",
        default=True,
        help="Si está inactiva, no es visible en operaciones normales",
    )

    notes = fields.Text(
        string="Notas",
        help="Observaciones sobre la sesión",
    )

    # Campos para observaciones del Portal Coach
    general_observations = fields.Text(
        string="Observaciones Generales",
        help="Observaciones generales de la sesión desde Portal Coach",
    )

    novelty_observations = fields.Text(
        string="Observaciones de Novedad",
        help="Observaciones específicas de la novedad reportada",
    )

    novelty_type = fields.Selection(
        selection=[
            ('postponed', 'Aplazada'),
            ('materials', 'Materiales'),
            ('homework', 'Tareas'),
            ('behavior', 'Comportamiento'),
            ('technical', 'Técnico'),
            ('other', 'Otro'),
        ],
        string="Tipo de Novedad",
        help="Tipo de novedad reportada en la sesión",
    )

    color = fields.Integer(
        string="Color",
        help="Color para calendario (opcional)",
    )

    # RESTRICCIONES SQL

    _sql_constraints = [
        (
            "check_times",
            "CHECK(time_end > time_start)",
            "La hora de fin debe ser mayor que la hora de inicio.",
        ),
        (
            "check_capacity",
            "CHECK(max_capacity > 0)",
            "La capacidad debe ser mayor a cero.",
        ),
    ]

    # MÉTODOS AUXILIARES
    
    @api.depends('template_id', 'template_id.subject_category')
    def _compute_is_oral_test_template(self):
        """Determina si el template seleccionado es de categoría oral_test."""
        for record in self:
            record.is_oral_test_template = (
                record.template_id and 
                record.template_id.subject_category == 'oral_test'
            )

    @api.model
    def _get_city_selection(self):
        """Obtiene lista de ciudades desde sedes activas."""
        cities = (
            self.env["benglish.campus"]
            .search([("active", "=", True)])
            .mapped("city_name")
        )
        return [(city, city) for city in sorted(set(cities)) if city]

    def _get_default_times_from_campus(self, campus):
        """Obtiene horas por defecto desde la sede con fallback seguro."""
        start_time = 8.0
        end_time = 18.0
        if campus:
            if campus.default_start_time not in (False, None):
                start_time = campus.default_start_time
            elif campus.schedule_start_time not in (False, None):
                start_time = campus.schedule_start_time
            if campus.default_end_time not in (False, None):
                end_time = campus.default_end_time
            elif campus.schedule_end_time not in (False, None):
                end_time = campus.schedule_end_time
            if end_time <= start_time:
                duration = campus.default_session_duration or 2.0
                end_time = start_time + duration
        return start_time, end_time

    # COMPUTED FIELDS

    @api.depends("subject_id", "date", "time_start")
    def _compute_name(self):
        """Genera nombre interno único."""
        for record in self:
            # Si se proporciona un código de sesión explícito, usarlo como nombre interno
            if record.session_code:
                record.name = record.session_code
                continue

            if record.subject_id and record.date and record.time_start:
                time_str = self._format_time(record.time_start)
                record.name = f"{record.subject_id.code} - {record.date} {time_str}"
            else:
                record.name = "Nueva Sesión"

    @api.depends("name", "subject_id.name", "teacher_id.name")
    def _compute_display_name(self):
        """Genera nombre para visualización."""
        for record in self:
            parts = []

            if record.template_id:
                template_label = record.template_id.name or record.template_id.alias_student
                if record.template_id.code:
                    parts.append(f"[{record.template_id.code}] {template_label}")
                else:
                    parts.append(template_label)
            elif record.subject_id:
                parts.append(f"[{record.subject_id.code}] {record.subject_id.name}")

            if record.date:
                parts.append(str(record.date))

            if record.time_start:
                parts.append(self._format_time(record.time_start))

            if record.teacher_id:
                parts.append(f"Docente: {record.teacher_id.name}")

            record.display_name = " | ".join(parts) if parts else "Nueva Sesión"

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = args or []
        if name:
            domain = [
                "|",
                ("session_code", operator, name),
                ("display_name", operator, name),
            ]
            sessions = self.search(domain + args, limit=limit)
            return sessions.name_get()
        return super().name_search(name=name, args=args, operator=operator, limit=limit)

    @api.depends("template_id.alias_student", "subject_id.alias", "subject_id.name")
    def _compute_student_alias(self):
        for record in self:
            if record.template_id and record.template_id.alias_student:
                record.student_alias = record.template_id.alias_student
            elif record.subject_id:
                record.student_alias = record.subject_id.alias or record.subject_id.name
            else:
                record.student_alias = "Clase"

    @api.depends("time_start", "time_end")
    def _compute_duration(self):
        """Calcula duración en horas."""
        for record in self:
            if record.time_start and record.time_end:
                record.duration_hours = record.time_end - record.time_start
            else:
                record.duration_hours = 0

    @api.depends("date")
    def _compute_weekday(self):
        """Calcula día de la semana."""
        for record in self:
            if record.date:
                record.weekday = str(record.date.weekday())
            else:
                record.weekday = False

    @api.depends("time_start", "time_end")
    def _compute_time_labels(self):
        """Genera etiquetas `HH:MM` desde los floats de hora.

        Detecta valores mayores a 24 (posible caso: valores en minutos) y los
        trata como minutos convirtiéndolos a horas y minutos.
        """
        for record in self:
            def fmt(val):
                if val is False or val is None:
                    return ""
                # Si el valor parece representar minutos (ej: > 24), convertir
                if float(val) > 24:
                    total_minutes = int(round(float(val)))
                    hours = total_minutes // 60
                    minutes = total_minutes % 60
                else:
                    hours = int(float(val))
                    minutes = int(round((float(val) - hours) * 60))
                    if minutes >= 60:
                        hours += 1
                        minutes = 0
                return f"{hours:02d}:{minutes:02d}"

            record.time_start_label = fmt(record.time_start)
            record.time_end_label = fmt(record.time_end)

    @api.depends("date", "time_start", "time_end")
    def _compute_datetime_fields(self):
        """Convierte date + time_start/end a datetime UTC para vista calendar.

        PROBLEMA IDENTIFICADO: Cuando Odoo recibe un datetime naive (sin timezone),
        lo interpreta como UTC. Por eso si guardas 13:00 naive, Odoo lo toma como
        13:00 UTC, y al mostrarlo en timezone America/Bogota (UTC-5), lo muestra como 08:00.

        SOLUCIÓN: Convertir explícitamente de hora colombiana a UTC antes de guardar.
        """
        colombia_tz = pytz.timezone("America/Bogota")

        for record in self:
            _logger.info(f"=== COMPUTE DATETIME FIELDS para sesión ID {record.id} ===")
            _logger.info(
                f"Date: {record.date}, time_start: {record.time_start}, time_end: {record.time_end}"
            )
            _logger.info(
                f"Usuario actual: {self.env.user.name}, Timezone: {self.env.user.tz}"
            )

            if record.date and record.time_start is not False:
                # Convertir time_start (float) a horas y minutos (redondeo seguro)
                hours_start = int(record.time_start)
                minutes_start = int(round((record.time_start % 1) * 60))
                if minutes_start >= 60:
                    hours_start += 1
                    minutes_start = 0
                _logger.info(
                    f"Hora inicio calculada (Colombia): {hours_start}:{minutes_start:02d}"
                )

                # Crear datetime naive en hora colombiana
                naive_dt = datetime.combine(record.date, datetime.min.time()).replace(
                    hour=hours_start, minute=minutes_start
                )
                _logger.info(f"Datetime naive (Colombia): {naive_dt}")

                # Localizar a timezone Colombia y convertir a UTC
                local_dt = colombia_tz.localize(naive_dt)
                utc_dt = local_dt.astimezone(pytz.UTC)
                # Guardar como naive UTC (sin tzinfo) como espera Odoo
                record.datetime_start = utc_dt.replace(tzinfo=None)
                _logger.info(f"datetime_start final (UTC): {record.datetime_start}")
            else:
                record.datetime_start = False

            if record.date and record.time_end is not False:
                # Convertir time_end (float) a horas y minutos (redondeo seguro)
                hours_end = int(record.time_end)
                minutes_end = int(round((record.time_end % 1) * 60))
                if minutes_end >= 60:
                    hours_end += 1
                    minutes_end = 0
                _logger.info(
                    f"Hora fin calculada (Colombia): {hours_end}:{minutes_end:02d}"
                )

                # Crear datetime naive en hora colombiana
                naive_dt = datetime.combine(record.date, datetime.min.time()).replace(
                    hour=hours_end, minute=minutes_end
                )
                _logger.info(f"Datetime naive (Colombia): {naive_dt}")

                # Localizar a timezone Colombia y convertir a UTC
                local_dt = colombia_tz.localize(naive_dt)
                utc_dt = local_dt.astimezone(pytz.UTC)
                # Guardar como naive UTC (sin tzinfo) como espera Odoo
                record.datetime_end = utc_dt.replace(tzinfo=None)
                _logger.info(f"datetime_end final (UTC): {record.datetime_end}")
            else:
                record.datetime_end = False

    @api.depends("date", "time_start", "time_end", "agenda_id", "agenda_id.campus_id")
    def _compute_available_resources(self):
        """
        Calcula los docentes, coaches y aulas disponibles en el horario de esta sesión.
        Solo muestra recursos que NO están ocupados en el mismo horario.
        Usa lógica de traslape de intervalos: dos intervalos [a1,a2] y [b1,b2] se traslapan si a1 < b2 AND b1 < a2
        """
        _logger.info("=" * 80)
        _logger.info("🔍 INICIO _compute_available_resources")

        for record in self:
            _logger.info(f"\n📋 Procesando Sesión ID: {record.id}")
            _logger.info(f"   Fecha: {record.date}")
            _logger.info(f"   Horario: {record.time_start} - {record.time_end}")
            _logger.info(
                f"   Campus: {record.campus_id.name if record.campus_id else 'Sin campus'}"
            )

            # Sin horario definido, mostrar todos los docentes activos
            if not all([record.date, record.time_start, record.time_end]):
                _logger.info("   ⚠️ Sin horario completo - mostrando todos los docentes")

                all_teachers = self.env["hr.employee"].search(
                    [("is_teacher", "=", True), ("active", "=", True)]
                )

                if record.campus_id:
                    all_classrooms = self.env["benglish.subcampus"].search(
                        [
                            ("campus_id", "=", record.campus_id.id),
                            ("active", "=", True),
                            ("is_available", "=", True),
                        ]
                    )
                else:
                    all_classrooms = self.env["benglish.subcampus"].search(
                        [("active", "=", True), ("is_available", "=", True)]
                    )

                _logger.info(
                    f"   ✅ Total sin filtrar - Teachers: {len(all_teachers)}, Classrooms: {len(all_classrooms)}"
                )

                record.available_teacher_ids = all_teachers
                record.available_classroom_ids = all_classrooms
                continue

            # Buscar sesiones en la misma fecha que se traslapan con este horario
            # Dos intervalos [a1, a2] y [b1, b2] se traslapan si: a1 < b2 AND b1 < a2
            # En nuestro caso: time_start < record.time_end AND time_end > record.time_start
            domain = [
                ("id", "!=", record.id),  # Excluir esta sesión
                ("date", "=", record.date),
                (
                    "state",
                    "in",
                    ["draft", "active", "with_enrollment", "started"],
                ),  # Solo sesiones activas (no dictadas ni canceladas)
                (
                    "time_start",
                    "<",
                    record.time_end,
                ),  # Inicia antes de que esta termine
                (
                    "time_end",
                    ">",
                    record.time_start,
                ),  # Termina después de que esta inicie
            ]

            conflicting_sessions = self.search(domain)

            _logger.info(
                f"   📅 Sesiones en conflicto encontradas: {len(conflicting_sessions)}"
            )
            for conf in conflicting_sessions:
                _logger.info(
                    "      - Sesión %s: %s-%s | Teacher: %s | Aula: %s",
                    conf.id,
                    conf.time_start,
                    conf.time_end,
                    conf.teacher_id.name if conf.teacher_id else "-",
                    conf.subcampus_id.name if conf.subcampus_id else "-",
                )

            # Obtener IDs ocupados (filtrar None)
            occupied_teachers = conflicting_sessions.mapped("teacher_id")
            occupied_classrooms = conflicting_sessions.mapped("subcampus_id")

            occupied_teacher_ids = [t.id for t in occupied_teachers if t]
            occupied_classroom_ids = [c.id for c in occupied_classrooms if c]

            _logger.info(
                f"   🚫 Docentes ocupados: {[(t.id, t.name) for t in occupied_teachers if t]}"
            )
            _logger.info(
                f"   🚫 Aulas ocupadas: {[(c.id, c.name) for c in occupied_classrooms if c]}"
            )
            _logger.info(
                f"   🚫 IDs ocupados - Teachers: {occupied_teacher_ids}, Aulas: {occupied_classroom_ids}"
            )

            # Calcular disponibles - excluir los ocupados
            all_teachers = self.env["hr.employee"].search(
                [("is_teacher", "=", True), ("active", "=", True)]
            )

            _logger.info(f"   📊 Total docentes en BD: {len(all_teachers)}")

            available_teachers = all_teachers.filtered(
                lambda t: t.id not in occupied_teacher_ids
            )

            # Para aulas, primero filtrar por campus si existe
            if record.campus_id:
                _logger.info(
                    f"   🏢 Filtrando aulas por campus: {record.campus_id.name}"
                )
                all_classrooms = self.env["benglish.subcampus"].search(
                    [
                        ("campus_id", "=", record.campus_id.id),
                        ("active", "=", True),
                        ("is_available", "=", True),
                    ]
                )
            else:
                _logger.info(f"   🏢 Sin campus - buscando todas las aulas")
                all_classrooms = self.env["benglish.subcampus"].search(
                    [
                        ("active", "=", True),
                        ("is_available", "=", True),
                    ]
                )

            _logger.info(f"   📊 Total aulas en campus: {len(all_classrooms)}")
            _logger.info(f"      Aulas del campus: {all_classrooms.mapped('name')}")

            # Filtrar las ocupadas
            available_classrooms = all_classrooms.filtered(
                lambda c: c.id not in occupied_classroom_ids
            )

            _logger.info(
                f"   ✅ DISPONIBLES - Teachers: {len(available_teachers)}/{len(all_teachers)}"
            )
            _logger.info(f"      IDs: {available_teachers.ids}")
            _logger.info(f"      Nombres: {available_teachers.mapped('name')}")
            _logger.info(
                f"   ✅ DISPONIBLES - Classrooms: {len(available_classrooms)}/{len(all_classrooms)}"
            )
            _logger.info(f"      IDs: {available_classrooms.ids}")
            _logger.info(f"      Nombres: {available_classrooms.mapped('name')}")

            record.available_teacher_ids = available_teachers
            record.available_classroom_ids = available_classrooms

        _logger.info("🏁 FIN _compute_available_resources")
        _logger.info("=" * 80)

    @api.onchange("teacher_id")
    def _onchange_teacher_id(self):
        """
        Autocompletado del enlace de reunión al seleccionar un docente.
        Copia el meeting_link del docente seleccionado al campo de la sesión.
        """
        if self.teacher_id and self.teacher_id.meeting_link:
            self.meeting_link = self.teacher_id.meeting_link
            _logger.info(
                f"📋 Enlace de reunión autocompletado desde docente: {self.teacher_id.name}"
            )
        elif not self.teacher_id:
            # Limpiar el enlace si se deselecciona el docente
            self.meeting_link = False

    @api.onchange("delivery_mode")
    def _onchange_delivery_mode(self):
        """Limpia el aula si la modalidad es virtual y ajusta capacidades."""
        if self.delivery_mode == "virtual":
            self.subcampus_id = False
        # Si cambia de híbrida a otra modalidad, usar max_capacity
        if self.delivery_mode != "hybrid":
            if self.max_capacity_presential or self.max_capacity_virtual:
                # Sumar ambas capacidades si existen
                self.max_capacity = (self.max_capacity_presential or 0) + (self.max_capacity_virtual or 0)
        # Si cambia a híbrida, dividir la capacidad actual
        elif self.delivery_mode == "hybrid" and self.max_capacity:
            if not self.max_capacity_presential and not self.max_capacity_virtual:
                # Dividir equitativamente
                half = self.max_capacity // 2
                self.max_capacity_presential = half
                self.max_capacity_virtual = self.max_capacity - half

    @api.onchange("subcampus_id")
    def _onchange_subcampus_id(self):
        """Autocompleta la capacidad máxima con la capacidad del aula seleccionada."""
        if self.subcampus_id and self.subcampus_id.capacity:
            if self.delivery_mode == "hybrid":
                # Para híbrida, dividir la capacidad del aula
                half = self.subcampus_id.capacity // 2
                self.max_capacity_presential = half
                self.max_capacity_virtual = self.subcampus_id.capacity - half
            else:
                self.max_capacity = self.subcampus_id.capacity

    @api.onchange("max_capacity_presential", "max_capacity_virtual")
    def _onchange_hybrid_capacities(self):
        """Actualiza max_capacity cuando cambian las capacidades híbridas."""
        if self.delivery_mode == "hybrid":
            self.max_capacity = (self.max_capacity_presential or 0) + (self.max_capacity_virtual or 0)

    @api.onchange("date", "time_start", "time_end", "agenda_id")
    def _onchange_schedule(self):
        """
        Actualiza dinámicamente los dominios de recursos cuando cambia el horario.
        Fuerza el recálculo en el cliente para que los dropdowns se actualicen.
        IMPORTANTE: Este método limpia los campos si el recurso seleccionado ya no está disponible.
        """
        result = {}

        # Verificar si tenemos horario completo
        if self.date and self.time_start and self.time_end:
            # Forzar recálculo de disponibilidad
            self._compute_available_resources()

            # Construir dominios con los recursos disponibles
            classroom_domain = (
                [("id", "in", self.available_classroom_ids.ids)]
                if self.available_classroom_ids
                else [("id", "=", False)]
            )
            teacher_domain = (
                [
                    ("id", "in", self.available_teacher_ids.ids),
                    ("is_teacher", "=", True),
                ]
                if self.available_teacher_ids
                else [("id", "=", False)]
            )

            result["domain"] = {
                "subcampus_id": classroom_domain,
                "teacher_id": teacher_domain,
            }

            _logger.info(f"🔄 ONCHANGE - Aplicando dominios dinámicos")
            _logger.info(f"   Aulas disponibles: {self.available_classroom_ids.ids}")
            _logger.info(f"   Teachers disponibles: {self.available_teacher_ids.ids}")

            # Limpiar campos si el recurso seleccionado ya no está disponible
            if (
                self.subcampus_id
                and self.subcampus_id.id not in self.available_classroom_ids.ids
            ):
                _logger.warning(
                    f"⚠️ Aula {self.subcampus_id.name} ya no disponible - limpiando campo"
                )
                self.subcampus_id = False
                result["warning"] = {
                    "title": "Aula no disponible",
                    "message": "El aula seleccionada ya está ocupada en este horario. Por favor selecciona otra.",
                }

            if (
                self.teacher_id
                and self.teacher_id.id not in self.available_teacher_ids.ids
            ):
                _logger.warning(
                    f"⚠️ Docente {self.teacher_id.name} ya no disponible - limpiando campo"
                )
                self.teacher_id = False
                if not result.get("warning"):
                    result["warning"] = {
                        "title": "Docente no disponible",
                        "message": "El docente seleccionado ya tiene una clase en este horario. Por favor selecciona otro.",
                    }
        else:
            # Sin horario completo - permitir todos los recursos del campus
            if self.campus_id:
                result["domain"] = {
                    "subcampus_id": [
                        ("campus_id", "=", self.campus_id.id),
                        ("active", "=", True),
                        ("is_available", "=", True),
                    ],
                    "teacher_id": [("is_teacher", "=", True), ("active", "=", True)],
                }
            else:
                result["domain"] = {
                    "subcampus_id": [
                        ("active", "=", True),
                        ("is_available", "=", True),
                    ],
                    "teacher_id": [("is_teacher", "=", True), ("active", "=", True)],
                }
            _logger.info(
                f"🔄 ONCHANGE - Sin horario completo, mostrando docentes activos"
            )

        return result

    @api.depends("enrollment_ids", "enrollment_ids.state")
    def _compute_student_ids(self):
        """Obtiene estudiantes desde enrollments confirmados."""
        for record in self:
            confirmed = record.enrollment_ids.filtered(lambda e: e.state == "confirmed")
            record.student_ids = confirmed.mapped("student_id")

    @api.depends("max_capacity", "max_capacity_presential", "max_capacity_virtual", 
                 "delivery_mode", "enrollment_ids", "enrollment_ids.state", "enrollment_ids.student_delivery_mode")
    def _compute_capacity_stats(self):
        """Calcula estadísticas de capacidad considerando modalidad híbrida."""
        for record in self:
            confirmed = record.enrollment_ids.filtered(lambda e: e.state == "confirmed")
            enrolled = len(confirmed)

            # Para modalidad híbrida, calcular capacidades separadas
            if record.delivery_mode == "hybrid":
                presential_enrolled = len(confirmed.filtered(lambda e: e.student_delivery_mode == "presential"))
                virtual_enrolled = len(confirmed.filtered(lambda e: e.student_delivery_mode == "virtual"))
                
                max_presential = record.max_capacity_presential or 0
                max_virtual = record.max_capacity_virtual or 0
                total_max = max_presential + max_virtual
                
                available_presential = max(0, max_presential - presential_enrolled)
                available_virtual = max(0, max_virtual - virtual_enrolled)
                
                record.enrolled_count = enrolled
                record.available_spots = available_presential + available_virtual
                record.is_full = (presential_enrolled >= max_presential and virtual_enrolled >= max_virtual)
                record.occupancy_rate = (enrolled / total_max * 100.0) if total_max else 0
            else:
                # Para modalidad presencial o virtual, usar capacidad única
                record.enrolled_count = enrolled
                record.available_spots = max(0, record.max_capacity - enrolled)
                record.is_full = enrolled >= record.max_capacity
                record.occupancy_rate = (
                    (enrolled / record.max_capacity * 100.0) if record.max_capacity else 0
                )

    # VALIDACIONES

    @api.constrains("delivery_mode", "subcampus_id")
    def _check_classroom_required(self):
        """Valida que el aula sea obligatoria para modalidad presencial o híbrida."""
        for record in self:
            if (
                record.delivery_mode in ("presential", "hybrid")
                and not record.subcampus_id
            ):
                raise ValidationError(
                    _("El aula es obligatoria para clases presenciales o híbridas.")
                )

    @api.constrains("delivery_mode", "max_capacity", "max_capacity_presential", "max_capacity_virtual")
    def _check_hybrid_capacity(self):
        """Valida que las capacidades híbridas sean válidas."""
        for record in self:
            if record.delivery_mode == "hybrid":
                if not record.max_capacity_presential or record.max_capacity_presential <= 0:
                    raise ValidationError(
                        _("La capacidad presencial debe ser mayor a 0 para modalidad híbrida.")
                    )
                if not record.max_capacity_virtual or record.max_capacity_virtual <= 0:
                    raise ValidationError(
                        _("La capacidad virtual debe ser mayor a 0 para modalidad híbrida.")
                    )
            else:
                if not record.max_capacity or record.max_capacity <= 0:
                    raise ValidationError(
                        _("La capacidad máxima debe ser mayor a 0.")
                    )

    @api.constrains("agenda_id", "date")
    def _check_date_in_agenda(self):
        """Valida que la fecha esté dentro del rango de la agenda."""
        for record in self:
            if record.agenda_id and record.date:
                if not (
                    record.agenda_id.date_start
                    <= record.date
                    <= record.agenda_id.date_end
                ):
                    raise ValidationError(
                        _(
                            "La fecha %(date)s está fuera del rango de la agenda (%(start)s - %(end)s)."
                        )
                        % {
                            "date": record.date,
                            "start": record.agenda_id.date_start,
                            "end": record.agenda_id.date_end,
                        }
                    )

                # Verificar que el día esté habilitado en la sede
                if not record.agenda_id.is_date_valid(record.date):
                    weekday_names = [
                        "Lunes",
                        "Martes",
                        "Miércoles",
                        "Jueves",
                        "Viernes",
                        "Sábado",
                        "Domingo",
                    ]
                    day_name = weekday_names[record.date.weekday()]
                    raise ValidationError(
                        _(
                            "El día %(day)s (%(date)s) no está habilitado para sesiones en la sede '%(campus)s'."
                        )
                        % {
                            "day": day_name,
                            "date": record.date,
                            "campus": record.campus_id.name,
                        }
                    )

    @api.constrains("agenda_id", "time_start", "time_end")
    def _check_time_in_agenda(self):
        """Valida que las horas estén dentro del rango de la agenda."""
        for record in self:
            if record.agenda_id and record.time_start and record.time_end:
                agenda = record.agenda_id

                if not (
                    agenda.time_start <= record.time_start
                    and record.time_end <= agenda.time_end
                ):
                    raise ValidationError(
                        _(
                            "Los horarios de la sesión (%(session_start)s - %(session_end)s) deben estar "
                            "dentro del rango de la agenda (%(agenda_start)s - %(agenda_end)s)."
                        )
                        % {
                            "session_start": self._format_time(record.time_start),
                            "session_end": self._format_time(record.time_end),
                            "agenda_start": self._format_time(agenda.time_start),
                            "agenda_end": self._format_time(agenda.time_end),
                        }
                    )

    @api.constrains("date", "time_start", "time_end", "teacher_id", "subcampus_id")
    def _check_no_conflicts(self):
        """
        Valida que NO existan conflictos en la misma celda (fecha + hora).
        Se permite múltiples sesiones SOLO SI no se repite:
        - Docente
        - Aula

        CRÍTICO: Esta validación es la última línea de defensa contra doble asignación.
        El dominio dinámico previene selección, pero esta constraint garantiza integridad.
        """
        for record in self:
            if not all([record.date, record.time_start, record.time_end]):
                continue

            # Buscar sesiones en la misma celda (fecha + rango horario)
            domain = [
                ("id", "!=", record.id),
                ("date", "=", record.date),
                ("state", "in", ["draft", "started"]),  # Solo sesiones activas
                "|",
                "&",
                ("time_start", "<", record.time_end),
                ("time_end", ">", record.time_start),
                "&",
                ("time_start", ">=", record.time_start),
                ("time_start", "<", record.time_end),
            ]

            conflicting_sessions = self.search(domain)

            if not conflicting_sessions:
                continue

            # Verificar conflictos de DOCENTE
            if record.teacher_id:
                teacher_conflicts = conflicting_sessions.filtered(
                    lambda s: s.teacher_id and s.teacher_id.id == record.teacher_id.id
                )
                if teacher_conflicts:
                    raise ValidationError(
                        _(
                            "❌ CONFLICTO DE DOCENTE\n\n"
                            "El docente '%(teacher)s' ya tiene una sesión programada:\n"
                            "• Fecha: %(date)s\n"
                            "• Horario: %(start)s - %(end)s\n"
                            "• Sesión en conflicto: %(conflict)s\n\n"
                            "Por favor selecciona otro docente o modifica el horario."
                        )
                        % {
                            "teacher": record.teacher_id.name,
                            "date": record.date,
                            "start": self._format_time(record.time_start),
                            "end": self._format_time(record.time_end),
                            "conflict": teacher_conflicts[0].display_name,
                        }
                    )

            # Verificar conflictos de AULA
            if record.subcampus_id:
                room_conflicts = conflicting_sessions.filtered(
                    lambda s: s.subcampus_id
                    and s.subcampus_id.id == record.subcampus_id.id
                )
                if room_conflicts:
                    raise ValidationError(
                        _(
                            "❌ CONFLICTO DE AULA\n\n"
                            "El aula '%(room)s' ya está ocupada:\n"
                            "• Fecha: %(date)s\n"
                            "• Horario: %(start)s - %(end)s\n"
                            "• Sesión en conflicto: %(conflict)s\n\n"
                            "Por favor selecciona otra aula o modifica el horario."
                        )
                        % {
                            "room": record.subcampus_id.name,
                            "date": record.date,
                            "start": self._format_time(record.time_start),
                            "end": self._format_time(record.time_end),
                            "conflict": room_conflicts[0].display_name,
                        }
                    )

    # Validación _check_campus_city no es necesaria porque campus_id ahora es related de agenda

    @api.constrains("campus_id", "subcampus_id")
    def _check_subcampus_campus(self):
        """Valida que el aula pertenezca a la sede."""
        for record in self:
            if record.subcampus_id and record.campus_id:
                if record.subcampus_id.campus_id.id != record.campus_id.id:
                    raise ValidationError(
                        _("El aula '%(room)s' no pertenece a la sede '%(campus)s'.")
                        % {
                            "room": record.subcampus_id.name,
                            "campus": record.campus_id.name,
                        }
                    )

    @api.constrains("max_capacity", "subcampus_id")
    def _check_capacity_vs_room(self):
        """Valida que la capacidad máxima de la clase no supere la capacidad del aula."""
        for record in self:
            if record.subcampus_id and record.max_capacity:
                if record.max_capacity > record.subcampus_id.capacity:
                    raise ValidationError(
                        _(
                            "La capacidad máxima de la clase (%(session_capacity)s) no puede superar "
                            "la capacidad del aula '%(room)s' (%(room_capacity)s estudiantes)."
                        )
                        % {
                            "session_capacity": record.max_capacity,
                            "room": record.subcampus_id.name,
                            "room_capacity": record.subcampus_id.capacity,
                        }
                    )

    @api.constrains("template_id", "program_id")
    def _check_template_program(self):
        for record in self:
            if (
                record.template_id
                and record.template_id.program_id
                and record.program_id
                and record.template_id.program_id != record.program_id
            ):
                raise ValidationError(
                    _("La plantilla seleccionada no corresponde al programa de la sesión.")
                )

    @api.constrains("audience_unit_from", "audience_unit_to")
    def _check_audience_range(self):
        for record in self:
            if record.audience_unit_from and record.audience_unit_to:
                if record.audience_unit_from > record.audience_unit_to:
                    raise ValidationError(
                        _("El rango de audiencia es inválido (Unidad Desde > Unidad Hasta).")
                    )

    # ONCHANGE

    @api.onchange("agenda_id")
    def _onchange_agenda_id(self):
        """Al cambiar agenda, hereda rango temporal."""
        if self.agenda_id:
            if not self.date:
                self.date = self.agenda_id.date_start
            if self.env.context.get("default_datetime_start"):
                return
            start_time, end_time = self._get_default_times_from_campus(
                self.agenda_id.campus_id
            )
            self.time_start = start_time
            self.time_end = end_time

    @api.onchange("template_id")
    def _onchange_template_id(self):
        if not self.template_id:
            return
        if (
            self.template_id.program_id
            and self.program_id
            and self.template_id.program_id != self.program_id
        ):
            self.template_id = False
            return {
                "warning": {
                    "title": _("Plantilla inválida"),
                    "message": _(
                        "La plantilla seleccionada no pertenece al programa actual."
                    ),
                }
            }
        placeholder = self._get_placeholder_subject_from_template()
        if placeholder:
            self.subject_id = placeholder

    @api.onchange("audience_phase_id")
    def _onchange_audience_phase_id(self):
        if not self.audience_phase_id:
            return
        
        unit_from, unit_to = self._get_phase_unit_range(self.audience_phase_id)
        if unit_from and unit_to:
            self.audience_unit_from = unit_from
            self.audience_unit_to = unit_to
        placeholder = self._get_placeholder_subject_from_template()
        if placeholder:
            self.subject_id = placeholder

    @api.onchange("coach_id")
    def _onchange_coach_id(self):
        """Al seleccionar coach, auto-completa link de reunión si aplica."""
        if self.coach_id and self.coach_id.meeting_link:
            if self.delivery_mode in ["virtual", "hybrid"]:
                self.meeting_link = self.coach_id.meeting_link

    @api.onchange("date", "time_start", "time_end")
    def _onchange_schedule(self):
        """
        Al cambiar fecha/horario, actualiza los dominios de docentes y aulas disponibles.
        Si el docente o aula actual ya no está disponible, limpia el campo.
        """
        if not all([self.date, self.time_start, self.time_end]):
            return {}

        # Obtener disponibles
        available_teachers = self.get_available_teachers(
            self.date, self.time_start, self.time_end, self.id
        )

        available_classrooms = self.get_available_classrooms(
            self.campus_id.id if self.campus_id else None,
            self.date,
            self.time_start,
            self.time_end,
            self.id,
        )

        # Limpiar campos si ya no están disponibles
        if self.teacher_id and self.teacher_id not in available_teachers:
            self.teacher_id = False
            return {
                "warning": {
                    "title": _("Docente No Disponible"),
                    "message": _(
                        "El docente seleccionado no está disponible en este horario y ha sido removido."
                    ),
                }
            }

        if self.subcampus_id and self.subcampus_id not in available_classrooms:
            self.subcampus_id = False
            return {
                "warning": {
                    "title": _("Aula No Disponible"),
                    "message": _(
                        "El aula seleccionada no está disponible en este horario y ha sido removida."
                    ),
                }
            }

        return {}

    # CRUD OVERRIDES

    @api.model
    def default_get(self, fields_list):
        """Prellenar campos cuando se crea desde el calendario."""
        res = super(AcademicSession, self).default_get(fields_list)

        # Cuando se hace click en el calendario, Odoo pasa datetime_start en el contexto
        context_start = self.env.context.get("default_datetime_start")
        context_end = self.env.context.get("default_datetime_end")

        if context_start:
            # Convertir de datetime UTC a fecha y hora local
            user_tz = pytz.timezone(self.env.user.tz or "UTC")

            # Convertir string a datetime si es necesario
            if isinstance(context_start, str):
                context_start = datetime.fromisoformat(
                    context_start.replace("Z", "+00:00")
                )

            # Localizar a UTC y convertir a timezone del usuario
            if not context_start.tzinfo:
                # Es un datetime naive, Odoo lo envía en UTC
                utc_dt = pytz.UTC.localize(context_start)
            else:
                utc_dt = context_start.astimezone(pytz.UTC)

            # Convertir a hora local del usuario
            local_dt = utc_dt.astimezone(user_tz)

            # Extraer fecha
            res["date"] = local_dt.date()

            # Redondear hora al inicio de la hora completa (sin minutos)
            # Si es 8:30, se redondea a 8:00
            # Si es 14:45, se redondea a 14:00
            res["time_start"] = float(local_dt.hour)

            _logger.info(f"=== DEFAULT_GET desde calendario ===")
            _logger.info(f"Context datetime_start (UTC): {context_start}")
            _logger.info(f"Local datetime: {local_dt}")
            _logger.info(f"Hora redondeada: {local_dt.hour}:00")
            _logger.info(f"Date: {res['date']}, time_start: {res['time_start']}")

        if context_end:
            # Convertir datetime_end de la misma forma
            user_tz = pytz.timezone(self.env.user.tz or "UTC")

            if isinstance(context_end, str):
                context_end = datetime.fromisoformat(context_end.replace("Z", "+00:00"))

            if not context_end.tzinfo:
                utc_dt = pytz.UTC.localize(context_end)
            else:
                utc_dt = context_end.astimezone(pytz.UTC)

            local_dt = utc_dt.astimezone(user_tz)

            # Redondear time_end también a hora completa
            res["time_end"] = float(local_dt.hour)

            _logger.info(f"time_end redondeado: {res['time_end']}")

        if not self.env.context.get("default_datetime_start"):
            campus_id = res.get("campus_id") or self.env.context.get("default_campus_id")
            if campus_id:
                campus = self.env["benglish.campus"].browse(campus_id)
                start_time, end_time = self._get_default_times_from_campus(campus)
                res["time_start"] = start_time
                res["time_end"] = end_time

        subcampus_id = res.get("subcampus_id") or self.env.context.get(
            "default_subcampus_id"
        )
        if subcampus_id:
            default_capacity = self._fields["max_capacity"].default
            if callable(default_capacity):
                default_capacity = default_capacity(self)
            if (
                res.get("max_capacity") is None
                or res.get("max_capacity") == default_capacity
            ):
                subcampus = self.env["benglish.subcampus"].browse(subcampus_id)
                if subcampus.exists() and subcampus.capacity:
                    res["max_capacity"] = subcampus.capacity

        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Validaciones al crear."""
        # Los campos location_city y campus_id ahora son related de agenda
        # No es necesario setearlos manualmente
        for vals in vals_list:
            if vals.get("template_id"):
                template = self.env["benglish.agenda.template"].browse(
                    vals.get("template_id")
                )
                
                # B-checks y Oral Tests siempre son virtuales
                if template.subject_category in ('bcheck', 'oral_test'):
                    vals["delivery_mode"] = "virtual"
                
                # Oral Tests: si solo se proporciona audience_unit_to (unidad objetivo),
                # copiar a audience_unit_from para que el rango sea [X, X]
                if template.subject_category == 'oral_test':
                    if vals.get('audience_unit_to') and not vals.get('audience_unit_from'):
                        vals['audience_unit_from'] = vals['audience_unit_to']
                    # Si no se proporciona audience_unit_to pero se proporciona audience_unit_from,
                    # asumir que es una sesión para esa unidad específica
                    elif vals.get('audience_unit_from') and not vals.get('audience_unit_to'):
                        vals['audience_unit_to'] = vals['audience_unit_from']
                
                if not vals.get("program_id"):
                    if template.program_id:
                        vals["program_id"] = template.program_id.id
                if vals.get("audience_phase_id") and (
                    not vals.get("audience_unit_from") or not vals.get("audience_unit_to")
                ):
                    phase = self.env["benglish.phase"].browse(vals.get("audience_phase_id"))
                    unit_from, unit_to = self._get_phase_unit_range(phase)
                    if unit_from and unit_to:
                        vals.setdefault("audience_unit_from", unit_from)
                        vals.setdefault("audience_unit_to", unit_to)
                if not vals.get("subject_id"):
                    virtual = self.new(vals)
                    placeholder = virtual._get_placeholder_subject_from_template()
                    if placeholder:
                        vals["subject_id"] = placeholder.id
                    elif template.subject_category == 'oral_test':
                        # Para Oral Tests, si no se encuentra un subject específico,
                        # buscar cualquier oral test del programa como fallback
                        program_to_search = template.program_id.id if template.program_id else vals.get("program_id")
                        if program_to_search:
                            oral_test_fallback = self.env["benglish.subject"].sudo().search([
                                ("program_id", "=", program_to_search),
                                ("active", "=", True),
                                ("subject_category", "=", "oral_test"),
                            ], limit=1)
                            if oral_test_fallback:
                                vals["subject_id"] = oral_test_fallback.id
                            else:
                                # Último recurso: crear un placeholder temporal para oral test
                                # Esto permitirá que se cree la sesión y después se pueda resolver dinámicamente
                                import logging
                                _logger = logging.getLogger(__name__)
                                _logger.warning(
                                    f"[ACADEMIC SESSION] No se encontró subject específico para Oral Test en programa {program_to_search}. "
                                    f"Buscando fallback general..."
                                )
                                # Buscar CUALQUIER oral test del sistema como placeholder
                                any_oral_test = self.env["benglish.subject"].sudo().search([
                                    ("active", "=", True),
                                    ("subject_category", "=", "oral_test"),
                                ], limit=1)
                                if any_oral_test:
                                    vals["subject_id"] = any_oral_test.id
                                    _logger.info(f"[ACADEMIC SESSION] Usando oral test fallback: {any_oral_test.name} (ID: {any_oral_test.id})")
                                else:
                                    # Error crítico: no hay oral tests en el sistema
                                    _logger.error("[ACADEMIC SESSION] No hay ningún oral test en el sistema. No se puede crear la sesión.")
                                    raise ValidationError(
                                        _("Error: No se encontraron asignaturas de tipo 'Oral Test' en el sistema. "
                                          "Contacte al administrador para configurar las asignaturas.")
                                    )
                # Validación final: asegurar que siempre hay subject_id para oral tests
                if template.subject_category == 'oral_test' and not vals.get("subject_id"):
                    raise ValidationError(
                        _("Error crítico: No se pudo asignar una asignatura para la sesión de Oral Test. "
                          "Verifique que:\n"
                          "1. El programa tenga asignaturas de tipo 'Oral Test' configuradas\n"
                          "2. La plantilla tenga mapping_mode = 'block'\n"
                          "3. Las asignaturas tengan unit_block_start y unit_block_end configurados\n"
                          "4. Se haya especificado audience_unit_to en la sesión")
                    )
        sessions = super(AcademicSession, self).create(vals_list)

        # Post-procesamiento de sesiones creadas
        for session in sessions:
            # Si no se proporcionó un código de sesión, generarlo automáticamente
            if not session.session_code:
                try:
                    session.session_code = session._generate_session_code()
                except Exception:
                    # No bloquear la creación por errores menores en generación de código
                    pass

            # Para oral tests, intentar resolver el subject_id correcto si es necesario
            if (session.template_id and 
                session.template_id.subject_category == 'oral_test' and
                session.audience_unit_to):
                try:
                    better_subject = session._get_placeholder_subject_from_template()
                    if better_subject and better_subject.id != session.subject_id.id:
                        session.subject_id = better_subject.id
                except Exception as e:
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.warning(f"[ORAL TEST] No se pudo resolver mejor subject para sesión {session.id}: {str(e)}")

            if session.agenda_id:
                session._create_session_log("create")

        return sessions

    def write(self, vals):
        """Validaciones al actualizar."""
        # Oral Tests: si solo se proporciona audience_unit_to, copiar a audience_unit_from
        if vals.get('audience_unit_to') and not vals.get('audience_unit_from'):
            for record in self:
                if record.template_id and record.template_id.subject_category == 'oral_test':
                    vals['audience_unit_from'] = vals['audience_unit_to']
        
        # Capturar estado anterior para sincronización
        old_states = {}
        if "state" in vals:
            for record in self:
                old_states[record.id] = record.state

        # Prevenir cambios en sesiones iniciadas/dictadas
        protected_states = ["started", "done", "cancelled"]
        if any(
            key in vals
            for key in [
                "date",
                "time_start",
                "time_end",
                "teacher_id",
                "coach_id",
                "subcampus_id",
            ]
        ):
            for record in self:
                if record.state in protected_states:
                    raise UserError(
                        _(
                            "No se pueden modificar datos clave de sesiones en estado %(state)s."
                        )
                        % {
                            "state": dict(self._fields["state"].selection).get(
                                record.state
                            )
                        }
                    )

        # Guardar valores antiguos antes de la modificación para el log
        old_values_per_session = {}
        relevant_fields = self._get_log_relevant_fields()
        for record in self:
            if record.agenda_id and any(field in vals for field in relevant_fields):
                old_values_per_session[record.id] = record._get_field_values(
                    relevant_fields
                )

        result = super(AcademicSession, self).write(vals)

        # Registrar logs de actualización
        for record in self:
            if record.id in old_values_per_session:
                new_values = record._get_field_values(relevant_fields)
                # Determinar si es un "move" (reprogramación) o un "update" genérico
                action = "move" if self._is_rescheduling_change(vals) else "update"
                record._create_session_log(
                    action, old_values_per_session[record.id], new_values
                )

        # SINCRONIZACIÓN CON PORTAL: Si estado cambió a 'done' o 'cancelled'
        if "state" in vals:
            new_state = vals["state"]
            for record in self:
                old_state = old_states.get(record.id)
                if old_state and old_state != new_state:
                    # Disparar sincronización del mixin
                    record._sync_session_to_portal_on_state_change(old_state, new_state)

        return result

    def unlink(self):
        """
        ELIMINACIÓN FORZADA HABILITADA PARA GESTORES.
        Permite eliminar sesiones sin restricciones para facilitar gestión.
        """
        # Registrar logs de eliminación ANTES de borrar
        for record in self:
            if record.agenda_id:
                record._create_session_log("delete")

        # Permitir eliminación forzada sin validaciones
        return super(AcademicSession, self).unlink()

    # TRANSICIONES DE ESTADO

    def action_start(self):
        """Inicia la sesión (marca como en curso)."""
        for record in self:
            if record.state not in ["draft", "active", "with_enrollment"]:
                raise UserError(
                    _(
                        "Solo se pueden iniciar sesiones que estén en Borrador o Activas (publicadas)."
                    )
                )

            # Validar campos obligatorios
            required = [
                record.subject_id,
                record.date,
                record.time_start,
                record.time_end,
                record.subcampus_id,
            ]
            if not all(required):
                raise UserError(
                    _(
                        "Complete todos los campos obligatorios antes de iniciar:\n"
                        "- Asignatura\n- Fecha\n- Hora inicio/fin\n- Aula"
                    )
                )

            if not (record.teacher_id or record.coach_id):
                raise UserError(
                    _("Debe asignar al menos un docente o coach antes de iniciar.")
                )

            record.write({"state": "started"})
            # Forzar persistencia inmediata en base de datos
            record.flush_recordset()
            record.message_post(
                body=_("Sesión iniciada."), subject=_("Sesión Iniciada")
            )

    def action_mark_done(self):
        """
        Marca la sesión como dictada.

        NUEVO COMPORTAMIENTO:
        Cuando una sesión pasa a estado 'done', automáticamente:
        1. Crea registros en el historial académico para cada estudiante inscrito
        2. Registra el estado de asistencia de cada estudiante
        3. Actualiza el progreso académico del estudiante

        Esto garantiza que las clases dictadas desaparezcan de la agenda
        y pasen al historial académico automáticamente.
        """
        History = self.env["benglish.academic.history"].sudo()

        for record in self:
            if record.state != "started":
                raise UserError(
                    _("Solo se pueden marcar como dictadas sesiones iniciadas.")
                )

            # Cambiar estado a 'done'
            record.write({"state": "done"})
            # Forzar persistencia inmediata en base de datos
            record.flush_recordset()
            record.message_post(
                body=_("Sesión completada."), subject=_("Sesión Dictada")
            )

            # CREAR REGISTROS DE HISTORIAL ACADÉMICO
            # Para cada estudiante inscrito en la sesión
            history_vals_list = []

            for enrollment in record.enrollment_ids:
                effective_subject = enrollment.effective_subject_id
                if not effective_subject:
                    effective_subject = record.resolve_effective_subject(
                        enrollment.student_id,
                        check_completed=False,
                        raise_on_error=False,
                    ) or record.subject_id
                    if effective_subject:
                        enrollment.sudo().write(
                            {"effective_subject_id": effective_subject.id}
                        )
                # Determinar estado de asistencia basado en el estado de la inscripción
                attendance_status = "pending"  # Por defecto: sin registrar

                if enrollment.state == "attended":
                    attendance_status = "attended"
                elif enrollment.state == "absent":
                    attendance_status = "absent"
                elif enrollment.state in ["confirmed", "pending"]:
                    # Si está confirmada pero no se marcó asistencia, queda pendiente
                    attendance_status = "pending"

                # Verificar que no exista ya un registro de historial (idempotencia)
                existing_history = History.search(
                    [
                        ("student_id", "=", enrollment.student_id.id),
                        ("session_id", "=", record.id),
                    ],
                    limit=1,
                )

                if existing_history:
                    # Ya existe, solo actualizar asistencia si cambió
                    if existing_history.attendance_status != attendance_status:
                        existing_history.write({"attendance_status": attendance_status})
                    _logger.info(
                        f"[SESSION DONE] History already exists for Student={enrollment.student_id.name}, "
                        f"Session={record.id}, updating attendance={attendance_status}"
                    )
                    continue

                # Preparar datos para el historial
                # NOTA: Solo Oral Tests deben tener notas descriptivas
                notes = ""
                if effective_subject and effective_subject.subject_category == "oral_test":
                    # Para Oral Tests, guardar información relevante
                    notes = f"Evaluación oral realizada."
                elif attendance_status == "absent":
                    # Solo anotar si faltó a la clase
                    notes = "Ausente a la clase"
                # Para Skills, B-checks, etc. → sin notas

                history_vals = {
                    "student_id": enrollment.student_id.id,
                    "session_id": record.id,
                    "enrollment_id": enrollment.id,
                    "session_date": record.date,
                    "session_time_start": record.time_start,
                    "session_time_end": record.time_end,
                    "program_id": record.program_id.id,
                    "plan_id": (
                        enrollment.student_id.plan_id.id
                        if enrollment.student_id.plan_id
                        else False
                    ),
                    "phase_id": (
                        enrollment.student_id.current_phase_id.id
                        if enrollment.student_id.current_phase_id
                        else False
                    ),
                    "level_id": (
                        enrollment.student_id.current_level_id.id
                        if enrollment.student_id.current_level_id
                        else False
                    ),
                    "subject_id": (
                        effective_subject.id
                        if effective_subject
                        else record.subject_id.id
                    ),
                    "campus_id": record.campus_id.id,
                    "teacher_id": record.teacher_id.id if record.teacher_id else False,
                    "delivery_mode": record.delivery_mode,
                    "attendance_status": attendance_status,
                    "notes": notes,
                }

                history_vals_list.append(history_vals)

            # Crear todos los registros de historial de una vez (batch)
            if history_vals_list:
                created_history = History.create(history_vals_list)
                _logger.info(
                    f"[SESSION DONE] Created {len(created_history)} history records for Session={record.id}, "
                    f"Subject={record.subject_id.name}, Date={record.date}"
                )

                # Notificar en el chatter
                record.message_post(
                    body=_(
                        "Se crearon %(count)s registros en el historial académico.\n"
                        "Asistencias: %(attended)s asistieron, %(absent)s ausentes, %(pending)s pendientes."
                    )
                    % {
                        "count": len(created_history),
                        "attended": len(
                            created_history.filtered(
                                lambda h: h.attendance_status == "attended"
                            )
                        ),
                        "absent": len(
                            created_history.filtered(
                                lambda h: h.attendance_status == "absent"
                            )
                        ),
                        "pending": len(
                            created_history.filtered(
                                lambda h: h.attendance_status == "pending"
                            )
                        ),
                    },
                    subject=_("Historial Académico Actualizado"),
                )
            else:
                _logger.warning(
                    f"[SESSION DONE] No enrollments found for Session={record.id}. No history records created."
                )

            # ⭐ NUEVO: Disparar sincronización con portal para limpiar agenda
            record._sync_session_to_portal_on_state_change("started", "done")

    def _sync_session_to_portal_on_state_change(self, old_state, new_state):
        """
        Sincroniza cambios de estado de sesión con el portal del estudiante.
        Cuando una sesión se marca como 'done', se eliminan las líneas de agenda del portal.
        """
        self.ensure_one()

        if new_state != "done":
            return

        # Buscar líneas de agenda del portal que referencian esta sesión
        PlanLine = self.env["portal.student.weekly.plan.line"].sudo()
        lines_to_remove = PlanLine.search([("session_id", "=", self.id)])

        if lines_to_remove:
            _logger.info(
                f"[PORTAL SYNC] Eliminando {len(lines_to_remove)} líneas de agenda del portal "
                f"para sesión {self.id} (marcada como dictada)"
            )
            lines_to_remove.unlink()
        else:
            _logger.info(
                f"[PORTAL SYNC] No se encontraron líneas de agenda del portal para sesión {self.id}"
            )

    def action_draft(self):
        """Regresa la sesión a borrador."""
        for record in self:
            if record.state not in ["started"]:
                raise UserError(
                    _(
                        "Solo se pueden regresar a borrador sesiones iniciadas (no dictadas)."
                    )
                )

            if record.enrollment_ids.filtered(lambda e: e.state == "confirmed"):
                raise UserError(
                    _(
                        "No se puede regresar a borrador porque tiene inscripciones confirmadas."
                    )
                )

            record.write({"state": "draft"})
            # Forzar persistencia inmediata en base de datos
            record.flush_recordset()
            record.message_post(
                body=_("Sesión regresada a borrador."),
                subject=_("Sesión en Borrador"),
            )

    def action_cancel(self, reason=None):
        """Cancela la sesión."""
        for record in self:
            if record.state == "done":
                raise UserError(_("No se puede cancelar una sesión ya dictada."))

            # Si tiene inscripciones confirmadas, prevenir cancelación automática
            if record.enrollment_ids.filtered(lambda e: e.state == "confirmed"):
                raise UserError(
                    _(
                        "No se puede cancelar la sesión porque tiene inscripciones confirmadas."
                    )
                )

            record.write({"state": "cancelled"})
            # Forzar persistencia inmediata en base de datos
            record.flush_recordset()
            record.message_post(
                body=_("Sesión cancelada."),
                subject=_("Sesión Cancelada"),
            )

    # MÉTODOS DE NEGOCIO

    def can_enroll_student(self):
        """Verifica si se pueden agregar más estudiantes."""
        self.ensure_one()
        return self.is_published and not self.is_full and self.available_spots > 0

    @api.model
    def get_available_teachers(
        self, date, time_start, time_end, exclude_session_id=None
    ):
        """
        Retorna los docentes (usuarios) que están disponibles en el horario especificado.

        Args:
            date: Fecha de la sesión
            time_start: Hora de inicio
            time_end: Hora de fin
            exclude_session_id: ID de sesión a excluir (para edición)

        Returns:
            recordset de hr.employee disponibles
        """
        if not all([date, time_start, time_end]):
            # Si no hay horario definido, retornar todos los docentes (hr.employee)
            return self.env["hr.employee"].search(
                [("is_teacher", "=", True), ("active", "=", True)]
            )

        # Buscar sesiones que se traslapen con este horario
        domain = [
            ("date", "=", date),
            ("state", "!=", "done"),  # Excluir sesiones finalizadas
            "|",
            "&",
            ("time_start", "<", time_end),
            ("time_end", ">", time_start),
            "&",
            ("time_start", ">=", time_start),
            ("time_start", "<", time_end),
        ]

        if exclude_session_id:
            domain.append(("id", "!=", exclude_session_id))

        conflicting_sessions = self.search(domain)
        occupied_teacher_ids = conflicting_sessions.mapped("teacher_id").ids

        # Retornar docentes (hr.employee) que NO estén ocupados
        return self.env["hr.employee"].search(
            [
                ("is_teacher", "=", True),
                ("active", "=", True),
                ("id", "not in", occupied_teacher_ids),
            ]
        )

    @api.model
    def get_available_classrooms(
        self, campus_id, date, time_start, time_end, exclude_session_id=None
    ):
        """
        Retorna las aulas disponibles en el horario especificado.

        Args:
            campus_id: ID de la sede
            date: Fecha de la sesión
            time_start: Hora de inicio
            time_end: Hora de fin
            exclude_session_id: ID de sesión a excluir (para edición)

        Returns:
            recordset de benglish.subcampus disponibles
        """
        if not all([campus_id, date, time_start, time_end]):
            # Si no hay horario definido, retornar todas las aulas de la sede
            if campus_id:
                return self.env["benglish.subcampus"].search(
                    [
                        ("campus_id", "=", campus_id),
                        ("active", "=", True),
                        ("is_available", "=", True),
                    ]
                )
            return self.env["benglish.subcampus"].search(
                [("active", "=", True), ("is_available", "=", True)]
            )

        # Buscar sesiones que se traslapen con este horario
        domain = [
            ("date", "=", date),
            ("state", "!=", "done"),  # Excluir sesiones finalizadas
            "|",
            "&",
            ("time_start", "<", time_end),
            ("time_end", ">", time_start),
            "&",
            ("time_start", ">=", time_start),
            ("time_start", "<", time_end),
        ]

        if exclude_session_id:
            domain.append(("id", "!=", exclude_session_id))

        conflicting_sessions = self.search(domain)
        occupied_room_ids = conflicting_sessions.mapped("subcampus_id").ids

        # Retornar aulas de la sede que NO estén ocupadas
        return self.env["benglish.subcampus"].search(
            [
                ("campus_id", "=", campus_id),
                ("active", "=", True),
                ("is_available", "=", True),
                ("id", "not in", occupied_room_ids),
            ]
        )

    # MÉTODOS AUXILIARES

    def _format_time(self, time_float):
        """Convierte tiempo decimal a formato HH:MM."""
        hours = int(time_float)
        minutes = int(round((time_float - hours) * 60))
        if minutes >= 60:
            hours += 1
            minutes = 0
        return f"{hours:02d}:{minutes:02d}"

    def _get_phase_unit_range(self, phase):
        if not phase:
            return (False, False)
        levels = phase.level_ids.filtered(lambda l: l.max_unit)
        if not levels:
            return (False, False)
        unit_min = min(levels.mapped("max_unit"))
        unit_max = max(levels.mapped("max_unit"))
        return (unit_min, unit_max)

    def _get_max_unit_for_program(self, program):
        if not program:
            return 0
        Subject = self.env["benglish.subject"].sudo()
        subjects = Subject.search([("program_id", "=", program.id), ("active", "=", True)])
        unit_values = []
        unit_values += [u for u in subjects.mapped("unit_number") if u]
        unit_values += [u for u in subjects.mapped("unit_block_end") if u]
        return max(unit_values) if unit_values else 0

    def _get_audience_unit_range(self):
        self.ensure_one()
        if self.audience_unit_from and self.audience_unit_to:
            return (self.audience_unit_from, self.audience_unit_to)
        if self.audience_phase_id:
            return self._get_phase_unit_range(self.audience_phase_id)
        max_unit = self._get_max_unit_for_program(self.program_id)
        return (1, max_unit or 0)

    def _get_placeholder_subject_from_template(self):
        self.ensure_one()
        template = self.template_id
        if not template:
            return False
        program = self.program_id or template.program_id
        if template.mapping_mode == "fixed" and template.fixed_subject_id:
            return template.fixed_subject_id
        if not program:
            return False
        
        Subject = self.env["benglish.subject"].sudo()
        
        # LÓGICA ESPECIAL PARA ORAL TESTS
        if template.subject_category == 'oral_test':
            # Si no hay audiencia específica, buscar cualquier oral test disponible
            if not (self.audience_unit_from and self.audience_unit_to):
                domain = [
                    ("program_id", "=", program.id),
                    ("active", "=", True),
                    ("subject_category", "=", "oral_test"),
                ]
                return Subject.search(domain, order="unit_block_end asc", limit=1)
        
        unit_from, unit_to = self._get_audience_unit_range()
        unit_from = unit_from or 1
        unit_to = unit_to or unit_from
        if template.mapping_mode == "pair" and not (self.audience_unit_from and self.audience_unit_to):
            pair_size = template.pair_size or 2
            unit_from = 1
            unit_to = max(unit_from, min(unit_from + pair_size - 1, unit_to))
        if template.mapping_mode == "block" and not (self.audience_unit_from and self.audience_unit_to):
            block_size = template.block_size or 4
            unit_from = 1
            unit_to = max(unit_from, min(unit_from + block_size - 1, unit_to))
        domain = [
            ("program_id", "=", program.id),
            ("active", "=", True),
            ("subject_category", "=", template.subject_category),
        ]
        # CAMBIO: Para bskills, NO filtrar por bskill_number
        # Las skills son intercambiables en el catálogo
        # if template.subject_category == "bskills" and template.skill_number:
        #     domain.append(("bskill_number", "=", template.skill_number))
        if template.mapping_mode in ("per_unit", "pair"):
            domain.append(("unit_number", "=", unit_from))
            subject = Subject.search(domain, limit=1)
            if subject:
                return subject
            domain[-1] = ("unit_number", ">=", unit_from)
            domain.append(("unit_number", "<=", unit_to))
            return Subject.search(domain, order="unit_number asc", limit=1)
        if template.mapping_mode == "block":
            domain = [
                ("program_id", "=", program.id),
                ("active", "=", True),
                ("subject_category", "=", template.subject_category),
                ("unit_block_start", "=", unit_from),
                ("unit_block_end", "=", unit_to),
            ]
            subject = Subject.search(domain, limit=1)
            if subject:
                return subject
            
            # FALLBACK ESPECÍFICO PARA ORAL TESTS: Si no encuentra con bloque exacto,
            # buscar cualquier oral test que tenga unit_block_end coincidente (unidad objetivo)
            if template.subject_category == 'oral_test':
                fallback_domain = [
                    ("program_id", "=", program.id),
                    ("active", "=", True),
                    ("subject_category", "=", "oral_test"),
                    ("unit_block_end", "=", unit_to),  # La unidad objetivo debe coincidir
                ]
                return Subject.search(fallback_domain, limit=1)
        return False

    def _get_student_target_unit(self, student, max_unit=None):
        """
        Calcula la unidad objetivo del estudiante para homologación.
        
        LÓGICA CORRECTA:
        - Solo avanzar a la siguiente unidad si la actual está COMPLETAMENTE terminada
        - Una unidad está completa cuando tiene B-check + 4 Skills completadas
        - Si la unidad está incompleta, permanecer en esa unidad
        """
        if not student:
            return 1
        
        # Obtener historial académico del estudiante
        History = self.env['benglish.academic.history'].sudo()
        completed_history = History.search([
            ('student_id', '=', student.id),
            ('attendance_status', '=', 'attended'),
            ('subject_id', '!=', False)
        ])
        
        if not completed_history:
            # Sin historial, empezar desde unidad 1
            return 1
        
        # Agrupar asignaturas completadas por unidad
        units_progress = {}
        for history in completed_history:
            subject = history.subject_id
            unit_num = subject.unit_number
            if not unit_num:
                continue
                
            if unit_num not in units_progress:
                units_progress[unit_num] = {
                    'bcheck': False,
                    'skills': 0
                }
            
            if subject.subject_category == 'bcheck':
                units_progress[unit_num]['bcheck'] = True
            elif subject.subject_category == 'bskills':
                # Contar CUALQUIER bskill, sin importar el número
                # El progreso se basa en cantidad de skills diferentes completadas
                units_progress[unit_num]['skills'] += 1
        
        # Determinar unidad objetivo
        if units_progress:
            highest_unit_started = max(units_progress.keys())
            progress = units_progress[highest_unit_started]
            
            # Una unidad está completa si tiene B-check + 4 Skills
            is_unit_complete = progress['bcheck'] and progress['skills'] >= 4
            
            if is_unit_complete:
                # Unidad completa, avanzar a la siguiente
                unit_target = highest_unit_started + 1
            else:
                # Unidad incompleta, quedarse en esta
                unit_target = highest_unit_started
        else:
            unit_target = 1
        
        # Aplicar límite máximo si existe
        unit_target = max(1, unit_target)
        if max_unit:
            unit_target = min(unit_target, max_unit)
            
        return unit_target

    def _get_completed_subject_ids(self, student):
        """
        Obtiene los IDs de asignaturas completadas por el estudiante.
        
        REGLAS DE NEGOCIO:
        - B-checks: SOLO 'attended' cuenta como completado
          → Si faltó ('absent'), puede agendar otro B-check de la MISMA unidad
        - B-skills: 'attended' o 'absent' (slot usado = avanzar)
          → Si faltó, pierde el slot pero no puede repetir
        - Oral Tests: 'attended' Y nota >= 70% (aprobar evaluación)
        - Otras asignaturas: solo 'attended'
        """
        History = self.env["benglish.academic.history"].sudo()
        
        # B-checks: SOLO asistidos (si faltó, puede recuperar)
        bchecks_completed = History.search([
            ("student_id", "=", student.id),
            ("attendance_status", "=", "attended"),  # ← SOLO 'attended', NO 'absent'
            ("subject_id.subject_category", "=", "bcheck")
        ])
        
        # B-skills: asistidos O inasistidos (slot usado, no recuperable)
        bskills_used = History.search([
            ("student_id", "=", student.id),
            ("attendance_status", "in", ["attended", "absent"]),
            ("subject_id.subject_category", "=", "bskills")
        ])
        
        # Oral Tests: asistió Y aprobó con >= 70%
        oral_tests = History.search([
            ("student_id", "=", student.id),
            ("attendance_status", "=", "attended"),
            ("subject_id.subject_category", "=", "oral_test"),
            ("grade", ">=", 70.0)
        ])
        
        # Otras asignaturas: solo asistidos
        other_subjects = History.search([
            ("student_id", "=", student.id),
            ("attendance_status", "=", "attended"),
            ("subject_id.subject_category", "not in", ["bcheck", "bskills", "oral_test"])
        ])
        
        completed = bchecks_completed | bskills_used | oral_tests | other_subjects
        completed_ids = set(completed.mapped("subject_id").ids)
        
        # Log de diagnóstico para B-checks
        import logging
        _logger = logging.getLogger(__name__)
        if bchecks_completed:
            _logger.info(
                f"[COMPLETED SUBJECTS] Estudiante {student.name} (ID: {student.id}), "
                f"B-checks ASISTIDOS: {len(bchecks_completed)} - "
                f"Units: {sorted([h.subject_id.unit_number for h in bchecks_completed if h.subject_id.unit_number])}"
            )
        
        # Log de B-checks con 'absent' (no completados, pueden recuperar)
        bchecks_absent = History.search([
            ("student_id", "=", student.id),
            ("attendance_status", "=", "absent"),
            ("subject_id.subject_category", "=", "bcheck")
        ])
        if bchecks_absent:
            _logger.info(
                f"[BCHECK RECOVERY] Estudiante {student.name} tiene B-checks con 'absent' (puede recuperar): "
                f"Units: {sorted([h.subject_id.unit_number for h in bchecks_absent if h.subject_id.unit_number])}"
            )
        
        return completed_ids
    
    def _get_unit_progress_details(self, student, unit_number):
        """
        Obtiene el progreso detallado de una unidad específica.
        
        LÓGICA CORRECTA:
        - Cuenta TODAS las skills sin importar bskill_number
        - Identifica slots únicos completados (sin duplicados)
        - Determina el siguiente slot disponible (1-4)
        
        Args:
            student: Estudiante a evaluar
            unit_number: Número de unidad (1-24)
        
        Returns:
            dict: {
                'bcheck': bool,
                'completed_slots': [1, 2, 3],  # Slots únicos completados
                'next_pending_slot': 4,  # Siguiente slot o None si completa
                'is_complete': bool  # True si B-check + 4 slots
            }
        """
        History = self.env['benglish.academic.history'].sudo()
        
        # Buscar historial de la unidad
        # Buscar historial de la unidad (asistencias + inasistencias)
        # IMPORTANTE: Contamos tanto 'attended' como 'absent' porque ambos usan un SLOT
        history_records = History.search([
            ('student_id', '=', student.id),
            ('attendance_status', 'in', ['attended', 'absent']),  # ← Slots USADOS (con o sin asistencia)
            ('subject_id.unit_number', '=', unit_number),
            ('subject_id.program_id', '=', student.program_id.id if student.program_id else False)
        ])
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # REGLA DE NEGOCIO PARA B-CHECK:
        # - B-check solo cuenta como "completado" si ASISTIÓ ('attended')
        # - Si faltó ('absent'), NO habilita las Skills → debe recuperar el B-check
        # ═══════════════════════════════════════════════════════════════════════════════
        bcheck_done = any(
            h.subject_id.subject_category == 'bcheck' and h.attendance_status == 'attended'
            for h in history_records
        )
        
        # Verificar si hay B-check con 'absent' (para logging/debugging)
        bcheck_absent = any(
            h.subject_id.subject_category == 'bcheck' and h.attendance_status == 'absent'
            for h in history_records
        )
        if bcheck_absent and not bcheck_done:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info(
                f"[BCHECK RECOVERY] Unit {unit_number}: Estudiante {student.name} tiene B-check con 'absent'. "
                f"NO puede agendar Skills hasta que asista a un nuevo B-check."
            )
        
        # Slots únicos USADOS (asistió o no asistió, pero ya pasó por ese slot)
        # IMPORTANTE: Usamos set para contar skills ÚNICAS, permitiendo repeticiones
        used_slot_numbers = set()
        for h in history_records:
            if h.subject_id.subject_category == 'bskills':
                # Solo contar si bskill_number está en rango válido 1-4
                if h.subject_id.bskill_number and 1 <= h.subject_id.bskill_number <= 4:
                    used_slot_numbers.add(h.subject_id.bskill_number)
        
        # Slots completados exitosamente (solo asistencias)
        completed_slot_numbers = set()
        for h in history_records:
            if h.subject_id.subject_category == 'bskills' and h.attendance_status == 'attended':
                if h.subject_id.bskill_number and 1 <= h.subject_id.bskill_number <= 4:
                    completed_slot_numbers.add(h.subject_id.bskill_number)
        
        completed_slots = sorted(completed_slot_numbers)
        
        # Determinar siguiente slot disponible (primer slot NO usado)
        all_slots = {1, 2, 3, 4}
        pending_slots = sorted(all_slots - used_slot_numbers)
        next_pending_slot = pending_slots[0] if pending_slots else None
        
        # Unidad completa: B-check asistido + 4 slots USADOS (no importa si asistió o no)
        is_complete = bcheck_done and len(used_slot_numbers) >= 4
        
        return {
            'bcheck': bcheck_done,
            'completed_slots': completed_slots,
            'next_pending_slot': next_pending_slot,
            'is_complete': is_complete
        }

    def resolve_effective_subject(self, student, check_completed=True, raise_on_error=True, check_prereq=True):
        """
        Resuelve la asignatura efectiva para un estudiante en esta sesión.
        
        LÓGICA CORRECTA REFACTORIZADA:
        - El slot asignado depende EXCLUSIVAMENTE del progreso del estudiante
        - NO depende del skill_number de la plantilla
        - Las skills son REPETIBLES: pueden tomarse múltiples veces
        - Cada skill completa el SIGUIENTE SLOT disponible (1, 2, 3 o 4)
        """
        self.ensure_one()

        if not student:
            if raise_on_error:
                raise UserError(_("Estudiante inválido para homologación."))
            return False

        # Sesiones legacy: usar subject_id directo
        if not self.template_id:
            return self.subject_id

        template = self.template_id
        if template.program_id and self.program_id and template.program_id != self.program_id:
            if raise_on_error:
                raise UserError(_("La plantilla no corresponde al programa de la sesión."))
            return False

        program = self.program_id or template.program_id
        if not program:
            if raise_on_error:
                raise UserError(_("No se pudo determinar el programa para homologar."))
            return False

        max_unit = self._get_max_unit_for_program(program)
        unit_target = self._get_student_target_unit(student, max_unit=max_unit)

        completed_ids = self._get_completed_subject_ids(student) if check_completed else set()

        unit_from, unit_to = self._get_audience_unit_range()
        unit_from = unit_from or 1
        unit_to = unit_to or (max_unit or unit_from)

        Subject = self.env["benglish.subject"].sudo()

        def subject_completed(subject):
            return subject and subject.id in completed_ids

        if template.mapping_mode == "per_unit":
            if not (unit_from <= unit_target <= unit_to):
                if raise_on_error:
                    raise UserError(_("La sesión no está disponible para la unidad del estudiante."))
                return False
            
            # ═══════════════════════════════════════════════════════════════
            # LÓGICA CORRECTA PARA BSKILLS (REFACTORIZADA)
            # ═══════════════════════════════════════════════════════════════
            if template.subject_category == "bskills":
                # Obtener progreso detallado de la unidad objetivo
                unit_progress = self._get_unit_progress_details(student, unit_target)
                
                # ═══════════════════════════════════════════════════════════════════════
                # VALIDACIÓN PARA SKILLS: B-check AGENDADO o COMPLETADO
                # ═══════════════════════════════════════════════════════════════════════
                # Para agendar Skills, el estudiante puede:
                # 1. Haber ASISTIDO al B-check (unit_progress['bcheck'] = True) O
                # 2. Tener el B-check AGENDADO en cualquier plan de la semana
                # ═══════════════════════════════════════════════════════════════════════
                bcheck_ok = unit_progress['bcheck']  # Asistió al B-check
                
                # Si no asistió, verificar si tiene B-check agendado en CUALQUIER plan
                if not bcheck_ok:
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.info(f"[SKILL VALIDATION] Buscando B-check agendado para Unit {unit_target}, Student {student.id}")
                    
                    # Buscar DIRECTAMENTE en la base de datos si hay un B-check agendado
                    PlanLine = self.env['portal.student.weekly.plan.line'].sudo()
                    Subject = self.env['benglish.subject'].sudo()
                    
                    # Buscar subjects de tipo B-check para esta unidad y programa
                    bcheck_subjects = Subject.search([
                        ('subject_category', '=', 'bcheck'),
                        ('unit_number', '=', unit_target),
                        ('program_id', '=', program.id)
                    ])
                    
                    _logger.info(f"[SKILL VALIDATION] B-check subjects encontrados: {bcheck_subjects.ids}")
                    
                    if bcheck_subjects:
                        # Buscar si hay alguna línea de plan con sesiones de B-check para este estudiante
                        bcheck_lines = PlanLine.search([
                            ('plan_id.student_id', '=', student.id),
                            ('session_id.template_id.subject_category', '=', 'bcheck'),
                        ])
                        
                        _logger.info(f"[SKILL VALIDATION] Líneas de B-check encontradas: {len(bcheck_lines)}")
                        
                        for line in bcheck_lines:
                            # Verificar si la sesión es para la unidad correcta
                            session = line.session_id
                            if session:
                                # Verificar audience_unit_from y audience_unit_to
                                unit_from = session.audience_unit_from or 0
                                unit_to = session.audience_unit_to or 0
                                _logger.info(f"[SKILL VALIDATION] Sesión {session.id}: unit_from={unit_from}, unit_to={unit_to}, target={unit_target}")
                                
                                if unit_from <= unit_target <= unit_to or unit_from == unit_target or unit_to == unit_target:
                                    bcheck_ok = True
                                    _logger.info(f"[SKILL VALIDATION] ✅ B-check encontrado agendado!")
                                    break
                
                # Si no tiene B-check completado ni agendado → ERROR
                if not bcheck_ok:
                    if raise_on_error:
                        raise UserError(
                            _("Para agendar Skills de la Unidad %s, debes tener el B-check de esa unidad:\n"
                              "• Completado (ya asististe) O\n"
                              "• Agendado en tu horario semanal\n\n"
                              "📚 ACCIÓN: Agenda el B-check de la Unidad %s primero") 
                            % (unit_target, unit_target)
                        )
                    return False
                
                # Obtener el siguiente slot disponible
                next_slot = unit_progress['next_pending_slot']
                
                if next_slot is None:
                    # Unidad completa, intentar avanzar a siguiente unidad
                    if template.allow_next_pending and unit_target < (max_unit or 999):
                        unit_target += 1
                        unit_progress = self._get_unit_progress_details(student, unit_target)
                        
                        # ═══════════════════════════════════════════════════════════════════════
                        # VALIDACIÓN PARA NUEVA UNIDAD: B-check AGENDADO o COMPLETADO
                        # ═══════════════════════════════════════════════════════════════════════
                        bcheck_new_unit_ok = unit_progress['bcheck']  # Asistió al B-check
                        
                        # Si no asistió, buscar directamente en BD
                        if not bcheck_new_unit_ok:
                            PlanLine = self.env['portal.student.weekly.plan.line'].sudo()
                            bcheck_lines = PlanLine.search([
                                ('plan_id.student_id', '=', student.id),
                                ('session_id.template_id.subject_category', '=', 'bcheck'),
                            ])
                            for line in bcheck_lines:
                                session = line.session_id
                                if session:
                                    unit_from = session.audience_unit_from or 0
                                    unit_to = session.audience_unit_to or 0
                                    if unit_from <= unit_target <= unit_to or unit_from == unit_target or unit_to == unit_target:
                                        bcheck_new_unit_ok = True
                                        break
                        
                        if not bcheck_new_unit_ok:
                            if raise_on_error:
                                raise UserError(
                                    _("Has completado la unidad %s. Para continuar con la Unidad %s, debes tener el B-check:\n"
                                      "• Completado (ya asististe) O\n"
                                      "• Agendado en tu horario semanal") 
                                    % (unit_target - 1, unit_target)
                                )
                            return False
                        
                        next_slot = unit_progress['next_pending_slot']
                        if next_slot is None:
                            if raise_on_error:
                                raise UserError(_("No hay slots disponibles en las unidades accesibles."))
                            return False
                    else:
                        if raise_on_error:
                            raise UserError(
                                _("Has completado todas las skills de la unidad %s. Continúa con la siguiente unidad.") 
                                % unit_target
                            )
                        return False
                
                # Buscar la asignatura correspondiente al SLOT (no al skill_number)
                subject = Subject.search([
                    ("program_id", "=", program.id),
                    ("active", "=", True),
                    ("subject_category", "=", "bskills"),
                    ("unit_number", "=", unit_target),
                    ("bskill_number", "=", next_slot),  # ← BASADO EN PROGRESO, NO EN PLANTILLA
                ], limit=1)
                
                if not subject:
                    if raise_on_error:
                        raise UserError(
                            _("Error de configuración: No existe asignatura para Unit %s, Slot %s. "
                              "Contacta al administrador.") % (unit_target, next_slot)
                        )
                    return False
                
                # Validación final: verificar que bskill_number esté en rango válido
                if not (1 <= subject.bskill_number <= 4):
                    if raise_on_error:
                        raise UserError(
                            _("Error de configuración: La asignatura '%s' tiene bskill_number inválido (%s). "
                              "Debe estar entre 1-4.") % (subject.name, subject.bskill_number)
                        )
                    return False
                
                return subject
            
            # ═══════════════════════════════════════════════════════════════
            # LÓGICA PARA OTRAS CATEGORÍAS (B-check, etc.) - SIN CAMBIOS
            # ═══════════════════════════════════════════════════════════════
            domain = [
                ("program_id", "=", program.id),
                ("active", "=", True),
                ("subject_category", "=", template.subject_category),
                ("unit_number", ">=", unit_from),
                ("unit_number", "<=", unit_to),
            ]
            
            candidates = Subject.search(domain, order="unit_number asc")
            # Buscar en la unidad objetivo
            primary = candidates.filtered(lambda s: s.unit_number == unit_target and not subject_completed(s))[:1]
            if primary:
                return primary
            # Si todas completadas en unit_target, buscar siguiente pendiente
            if template.allow_next_pending:
                pending = candidates.filtered(lambda s: not subject_completed(s) and s.unit_number >= unit_target)
                if pending:
                    return pending[0]
            if raise_on_error:
                raise UserError(_("No hay asignaturas pendientes disponibles para esta sesión."))
            return False

        if template.mapping_mode == "pair":
            pair_size = template.pair_size or 2
            pair_start = unit_target - ((unit_target - 1) % pair_size)
            pair_end = min(pair_start + pair_size - 1, max_unit or pair_start)
            
            # ═══════════════════════════════════════════════════════════════════════
            # CORRECCIÓN: Respetar audiencia específica de la sesión
            # ═══════════════════════════════════════════════════════════════════════
            # Si la sesión tiene audiencia específica (ej: solo Unit 8), 
            # NO buscar en toda la pareja, solo en la audiencia definida
            # 
            # Ejemplo:
            # - Sesión con audience 7-8 → Busca en [7, 8] 
            # - Sesión con audience 8-8 → Busca SOLO en [8]
            # ═══════════════════════════════════════════════════════════════════════
            if self.audience_unit_from and self.audience_unit_to:
                # Si hay audiencia específica, úsala en lugar de la pareja calculada
                pair_start = self.audience_unit_from
                pair_end = self.audience_unit_to
                
                # Validar que el estudiante esté dentro de la audiencia
                if not (pair_start <= unit_target <= pair_end):
                    if raise_on_error:
                        raise UserError(_("La sesión no está disponible para la unidad del estudiante."))
                    return False
            
            # Buscar B-checks solo en el rango definido (audiencia o pareja)
            domain = [
                ("program_id", "=", program.id),
                ("active", "=", True),
                ("subject_category", "=", template.subject_category),
                ("unit_number", ">=", pair_start),
                ("unit_number", "<=", pair_end),
            ]
            candidates = Subject.search(domain, order="unit_number asc")
            
            # Primero: Buscar B-check de la unidad exacta del estudiante
            primary = candidates.filtered(lambda s: s.unit_number == unit_target)[:1]
            if primary and not subject_completed(primary):
                return primary
            
            # Log de diagnóstico si B-check de unidad actual está completado
            if primary and subject_completed(primary):
                import logging
                _logger = logging.getLogger(__name__)
                _logger.info(
                    f"[RESOLVE B-CHECK] B-check Unit {unit_target} completado para {student.name}. "
                    f"Buscando siguiente pendiente con allow_next_pending={template.allow_next_pending}"
                )
            
            # Segundo: Si allow_next_pending, buscar siguiente pendiente DENTRO de la audiencia
            if template.allow_next_pending:
                pending = candidates.filtered(lambda s: not subject_completed(s) and s.unit_number >= unit_target)
                if pending:
                    pending_bcheck = pending[0]
                    
                    # ═══════════════════════════════════════════════════════════════
                    # CORRECCIÓN: B-checks NO requieren skills completas
                    # ═══════════════════════════════════════════════════════════════
                    # Los B-checks se publican en pareja (7-8, 9-10, etc.)
                    # Estudiantes pueden agendar el B-check de la siguiente unidad
                    # SIN necesidad de completar todas las skills de la unidad anterior
                    # 
                    # Ejemplo:
                    # - Estudiante en Unit 7, completó B-check 7, tiene 1/4 skills
                    # - Puede agendar B-check Unit 8 ✅ (NO requiere 4/4 skills)
                    # ═══════════════════════════════════════════════════════════════
                    
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.info(
                        f"[RESOLVE B-CHECK] Asignando B-check Unit {pending_bcheck.unit_number} "
                        f"para {student.name} (actualmente en Unit {unit_target})"
                    )
                    
                    return pending_bcheck
            
            if raise_on_error:
                raise UserError(_("No hay B-checks pendientes para esta sesión."))
            return False

        if template.mapping_mode == "block":
            block_size = template.block_size or 4
            
            # ═══════════════════════════════════════════════════════════════════════
            # CORRECCIÓN CRÍTICA: Para Oral Tests, usar audience_unit_to en lugar de unit_target
            # ═══════════════════════════════════════════════════════════════════════
            # Oral Tests se definen por el audience_unit_to que representa la última unidad del bloque
            # Ejemplo: Oral Test 4 (audience_unit_to=4) valida bloque 1-4
            # Oral Test 8 (audience_unit_to=8) valida bloque 5-8
            # ═══════════════════════════════════════════════════════════════════════
            if template.subject_category == "oral_test" and self.audience_unit_to:
                # Para Oral Tests, el bloque se determina por audience_unit_to
                reference_unit = self.audience_unit_to
            else:
                # Para otras categorías (bcheck, bskills), usar la unidad actual del estudiante
                reference_unit = unit_target
            
            block_start = ((reference_unit - 1) // block_size) * block_size + 1
            block_end = min(block_start + block_size - 1, max_unit or block_start)
            
            # ═══════════════════════════════════════════════════════════════════════
            # VALIDACIÓN SIMPLIFICADA PARA ORAL TESTS
            # ═══════════════════════════════════════════════════════════════════════
            # Para agendar un Oral Test, el estudiante solo necesita:
            # - Haber ASISTIDO al B-check de la ÚLTIMA UNIDAD del bloque (ej: Unit 16 para bloque 13-16)
            # - NO es obligatorio completar las skills
            # ═══════════════════════════════════════════════════════════════════════
            if check_prereq and template.subject_category == "oral_test":
                # Solo validar el B-check de la última unidad del bloque
                oral_test_unit = block_end  # Última unidad del bloque (ej: 16 para bloque 13-16)
                
                History = self.env['benglish.academic.history'].sudo()
                
                # Verificar si asistió al B-check de la unidad del Oral Test
                bcheck_attended = History.search([
                    ('student_id', '=', student.id),
                    ('attendance_status', '=', 'attended'),  # ← DEBE haber asistido
                    ('subject_id.subject_category', '=', 'bcheck'),
                    ('subject_id.unit_number', '=', oral_test_unit),
                    ('subject_id.program_id', '=', student.program_id.id if student.program_id else False)
                ], limit=1)
                
                if not bcheck_attended:
                    # Verificar si faltó al B-check para mensaje específico
                    bcheck_absent = History.search([
                        ('student_id', '=', student.id),
                        ('attendance_status', '=', 'absent'),
                        ('subject_id.subject_category', '=', 'bcheck'),
                        ('subject_id.unit_number', '=', oral_test_unit),
                        ('subject_id.program_id', '=', student.program_id.id if student.program_id else False)
                    ], limit=1)
                    
                    if raise_on_error:
                        if bcheck_absent:
                            raise UserError(
                                _("No puedes agendar este Oral Test.\n\n"
                                  "Para presentar el Oral Test de la Unidad %s, debías haber ASISTIDO "
                                  "al B-Check de esa unidad, pero faltaste.\n\n"
                                  "✅ SOLUCIÓN:\n"
                                  "1. Solicita que te habiliten un NUEVO B-Check de la Unidad %s\n"
                                  "2. Asiste al B-Check de recuperación\n"
                                  "3. Después podrás agendar el Oral Test") % (oral_test_unit, oral_test_unit)
                            )
                        else:
                            raise UserError(
                                _("No puedes agendar este Oral Test.\n\n"
                                  "Para presentar el Oral Test de la Unidad %s, debes haber ASISTIDO "
                                  "al B-Check de esa unidad.\n\n"
                                  "✅ PRÓXIMOS PASOS:\n"
                                  "1. Agenda el B-Check de la Unidad %s\n"
                                  "2. Asiste al B-Check\n"
                                  "3. Luego podrás agendar el Oral Test") % (oral_test_unit, oral_test_unit)
                            )
                    return False
                    
            domain = [
                ("program_id", "=", program.id),
                ("active", "=", True),
                ("subject_category", "=", template.subject_category),
                ("unit_block_start", "=", block_start),
                ("unit_block_end", "=", block_end),
            ]
            subject = Subject.search(domain, limit=1)
            if subject and not subject_completed(subject):
                return subject
            if raise_on_error:
                raise UserError(_("No hay Oral Test disponible para este bloque."))
            return False

        if template.mapping_mode == "fixed":
            subject = template.fixed_subject_id or self.subject_id
            if subject and not subject_completed(subject):
                return subject
            if raise_on_error:
                raise UserError(_("No hay asignatura fija disponible o ya fue completada."))
            return False

        if raise_on_error:
            raise UserError(_("No se pudo resolver la asignatura efectiva."))
        return False

    def _generate_session_code(self):
        """
        Genera un código de sesión secuencial usando `ir.sequence`.

        Comportamiento:
        - Lee los parámetros `benglish.session.prefix` y `benglish.session.padding` (opcionales)
          para crear la secuencia si no existe.
        - Usa la secuencia con código interno `benglish.academic.session`.
        - Si falla por alguna razón, cae al formato alterno (asignatura-fecha-hora).
        """
        self.ensure_one()

        seq_code = "benglish.academic.session"
        icp = self.env["ir.config_parameter"].sudo()

        # Parámetros configurables (opcionales)
        prefix = icp.get_param("benglish.session.prefix", "H-")
        padding = icp.get_param("benglish.session.padding", "4")
        try:
            padding = int(padding)
        except Exception:
            padding = 4

        # Buscar o crear la secuencia si no existe
        Sequence = self.env["ir.sequence"].sudo()
        seq = Sequence.search([("code", "=", seq_code)], limit=1)
        if not seq:
            try:
                seq = Sequence.create(
                    {
                        "name": "Código Sesión Benglish",
                        "code": seq_code,
                        "prefix": prefix,
                        "padding": padding,
                    }
                )
            except Exception:
                seq = False

        # Intentar obtener el siguiente valor de la secuencia
        if seq:
            try:
                next_code = self.env["ir.sequence"].sudo().next_by_code(seq_code)
                if next_code:
                    return next_code
            except Exception:
                # seguir a fallback
                pass

        # Fallback: formato basado en asignatura+fecha+hora (anterior)
        subject_part = (
            self.subject_id.code if self.subject_id and self.subject_id.code else "SESS"
        )
        date_part = self.date.strftime("%Y%m%d") if self.date else ""

        time_part = ""
        if self.time_start is not False and self.time_start is not None:
            h = int(self.time_start)
            m = int(round((self.time_start % 1) * 60))
            if m >= 60:
                h += 1
                m = 0
            time_part = f"{h:02d}{m:02d}"

        parts = [p for p in [subject_part, date_part, time_part] if p]
        return "-".join(parts)

    # ACCIONES DE VISTA

    def action_view_enrollments(self):
        """Acción para ver inscripciones de la sesión."""
        self.ensure_one()
        return {
            "name": _("Inscripciones - %s") % self.display_name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.session.enrollment",
            "view_mode": "list,form",
            "domain": [("session_id", "=", self.id)],
            "context": {"default_session_id": self.id},
        }

    def action_enroll_student(self):
        """Wizard para inscribir estudiante."""
        self.ensure_one()

        if not self.can_enroll_student():
            raise UserError(
                _(
                    "No se pueden agregar estudiantes:\n"
                    "- La sesión debe estar publicada\n"
                    "- Debe haber cupos disponibles"
                )
            )

        return {
            "name": _("Inscribir Estudiante"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.session.enrollment",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_session_id": self.id,
                "default_state": "confirmed",
            },
        }

    # MÉTODOS PARA REGISTRO DE LOGS (AUDITORÍA)

    def _get_log_relevant_fields(self):
        """
        Retorna la lista de campos relevantes para el logging.
        Solo se registrarán cambios en estos campos.
        """
        return [
            "date",
            "time_start",
            "time_end",
            "teacher_id",
            "subcampus_id",
            "subject_id",
            "session_type",
            "delivery_mode",
            "max_capacity",
            "state",
        ]

    def _get_field_values(self, field_names):
        """
        Obtiene los valores actuales de los campos especificados.
        Formatea los valores para que sean legibles en el log.

        :param field_names: Lista de nombres de campos
        :return: Diccionario con valores formateados
        """
        self.ensure_one()
        values = {}
        for fname in field_names:
            field = self._fields.get(fname)
            if not field:
                continue

            value = self[fname]

            # Formatear según tipo de campo
            if field.type == "many2one":
                values[fname] = value.display_name if value else ""
            elif field.type == "selection":
                selection_dict = dict(field._description_selection(self.env))
                values[fname] = selection_dict.get(value, value)
            elif field.type == "float":
                if fname in ["time_start", "time_end"]:
                    values[fname] = self._format_time(value)
                else:
                    values[fname] = value
            elif field.type == "date":
                values[fname] = value.strftime("%Y-%m-%d") if value else ""
            elif field.type == "datetime":
                values[fname] = value.strftime("%Y-%m-%d %H:%M") if value else ""
            else:
                values[fname] = str(value) if value else ""

        return values

    def _is_rescheduling_change(self, vals):
        """
        Determina si los cambios corresponden a una reprogramación.
        Se considera reprogramación si cambia fecha, hora, aula o docente.

        :param vals: Diccionario con valores a modificar
        :return: Boolean
        """
        rescheduling_fields = [
            "date",
            "time_start",
            "time_end",
            "teacher_id",
            "subcampus_id",
        ]
        return any(field in vals for field in rescheduling_fields)

    def _create_session_log(self, action, old_values=None, new_values=None):
        """
        Crea un registro de log para esta sesión.

        :param action: Tipo de acción ('create', 'delete', 'update', 'move')
        :param old_values: Diccionario con valores antiguos (opcional)
        :param new_values: Diccionario con valores nuevos (opcional)
        """
        self.ensure_one()

        if not self.agenda_id:
            return

        # Generar mensaje descriptivo en español
        message = self._generate_log_message(action, old_values, new_values)

        # Crear el log usando el modelo de logs
        # Usamos sudo() porque el usuario puede no tener permisos directos sobre el modelo de logs
        # pero sí sobre las sesiones, y queremos registrar la auditoría
        self.env["benglish.agenda.log"].sudo().create_log(
            agenda_id=self.agenda_id.id,
            session_id=self.id,
            action=action,
            message=message,
            old_values=old_values,
            new_values=new_values,
        )

    def _generate_log_message(self, action, old_values=None, new_values=None):
        """
        Genera un mensaje descriptivo legible para el log.

        :param action: Tipo de acción
        :param old_values: Valores anteriores (dict)
        :param new_values: Valores nuevos (dict)
        :return: String con el mensaje
        """
        self.ensure_one()

        # Información básica de la sesión
        subject = (
            f"{self.subject_code} - {self.subject_name}"
            if self.subject_id
            else "Sin asignatura"
        )
        date_str = self.date.strftime("%d/%m/%Y") if self.date else ""
        time_str = (
            f"{self._format_time(self.time_start)}-{self._format_time(self.time_end)}"
            if self.time_start and self.time_end
            else ""
        )
        teacher = self.teacher_id.name if self.teacher_id else "Sin docente"
        classroom = self.subcampus_id.name if self.subcampus_id else "Sin aula"

        if action == "create":
            return (
                f"Se creó nueva sesión:\n"
                f"  • Asignatura: {subject}\n"
                f"  • Fecha: {date_str} {time_str}\n"
                f"  • Docente: {teacher}\n"
                f"  • Aula: {classroom}"
            )

        elif action == "delete":
            return (
                f"Se eliminó sesión:\n"
                f"  • Asignatura: {subject}\n"
                f"  • Fecha: {date_str} {time_str}\n"
                f"  • Docente: {teacher}\n"
                f"  • Aula: {classroom}"
            )

        elif action == "move":
            # Reprogramación: destacar cambios de fecha/hora/ubicación
            changes = []
            if old_values and new_values:
                if old_values.get("date") != new_values.get("date"):
                    changes.append(
                        f"Fecha: {old_values.get('date')} → {new_values.get('date')}"
                    )
                if old_values.get("time_start") != new_values.get(
                    "time_start"
                ) or old_values.get("time_end") != new_values.get("time_end"):
                    changes.append(
                        f"Horario: {old_values.get('time_start')}-{old_values.get('time_end')} → {new_values.get('time_start')}-{new_values.get('time_end')}"
                    )
                if old_values.get("teacher_id") != new_values.get("teacher_id"):
                    changes.append(
                        f"Docente: {old_values.get('teacher_id')} → {new_values.get('teacher_id')}"
                    )
                if old_values.get("subcampus_id") != new_values.get("subcampus_id"):
                    changes.append(
                        f"Aula: {old_values.get('subcampus_id')} → {new_values.get('subcampus_id')}"
                    )

            changes_str = (
                "\n  • ".join(changes) if changes else "Cambios en programación"
            )
            return f"Se reprogramó sesión ({subject}):\n" f"  • {changes_str}"

        elif action == "update":
            # Modificación genérica: listar cambios
            changes = []
            if old_values and new_values:
                field_labels = {
                    "subject_id": "Asignatura",
                    "session_type": "Tipo de sesión",
                    "delivery_mode": "Modalidad",
                    "max_capacity": "Capacidad",
                    "state": "Estado",
                }
                for field in old_values:
                    if old_values.get(field) != new_values.get(field):
                        label = field_labels.get(field, field)
                        changes.append(
                            f"{label}: {old_values.get(field)} → {new_values.get(field)}"
                        )

            changes_str = (
                "\n  • ".join(changes) if changes else "Actualización de datos"
            )
            return (
                f"Se modificó sesión ({subject} - {date_str}):\n" f"  • {changes_str}"
            )

        return f"Acción: {action}"

    # MÉTODOS AUTOMÁTICOS PARA CIERRE DE SESIONES

    @api.model
    def _cron_auto_close_finished_sessions(self):
        """
        PROCESO AUTOMÁTICO (CRON JOB)

        Cierra automáticamente las sesiones que ya pasaron su fecha/hora de fin.
        Este método se ejecuta periódicamente (recomendado: cada 30 minutos).

        Comportamiento:
        1. Busca sesiones en estado 'started' cuya fecha/hora de fin ya pasó
        2. Las marca automáticamente como 'done' (dictadas)
        3. El método action_mark_done() se encarga de:
           - Crear registros en historial académico
           - Registrar asistencias
           - Actualizar progreso académico

        Es IDEMPOTENTE: puede ejecutarse múltiples veces sin duplicar registros.
        """
        now = fields.Datetime.now()

        # Buscar sesiones que deberían estar cerradas
        # Estado 'started' y fecha/hora de fin ya pasó
        sessions_to_close = self.search(
            [
                ("state", "=", "started"),
                ("datetime_end", "<", now),
            ]
        )

        if not sessions_to_close:
            _logger.info("[CRON AUTO-CLOSE] No sessions to close")
            return

        _logger.info(
            f"[CRON AUTO-CLOSE] Found {len(sessions_to_close)} sessions to close"
        )

        # Cerrar cada sesión
        closed_count = 0
        error_count = 0

        for session in sessions_to_close:
            try:
                _logger.info(
                    f"[CRON AUTO-CLOSE] Closing session {session.id}: "
                    f"{session.subject_id.name} on {session.date}"
                )

                # Llamar al método action_mark_done que ya tiene toda la lógica
                session.action_mark_done()
                closed_count += 1

            except Exception as e:
                error_count += 1
                _logger.error(
                    f"[CRON AUTO-CLOSE] Error closing session {session.id}: {str(e)}"
                )
                # Continuar con la siguiente sesión
                continue

        _logger.info(
            f"[CRON AUTO-CLOSE] Finished: {closed_count} closed, {error_count} errors"
        )

        return {
            "closed": closed_count,
            "errors": error_count,
            "total": len(sessions_to_close),
        }

    @api.model
    def _cron_auto_start_sessions(self):
        """
        PROCESO AUTOMÁTICO (CRON JOB)

        Inicia automáticamente las sesiones cuya hora de inicio ya llegó.

        Comportamiento:
        1. Busca sesiones en estado 'active' o 'with_enrollment'
        2. Verifica que su hora de inicio ya haya pasado
        3. Las marca automáticamente como 'started'

        Es IDEMPOTENTE: puede ejecutarse múltiples veces sin problemas.
        """
        now = fields.Datetime.now()

        # Buscar sesiones que deberían estar iniciadas
        sessions_to_start = self.search(
            [
                ("state", "in", ["active", "with_enrollment"]),
                ("datetime_start", "<=", now),
                ("datetime_end", ">", now),  # Aún no ha terminado
            ]
        )

        if not sessions_to_start:
            _logger.info("[CRON AUTO-START] No sessions to start")
            return

        _logger.info(
            f"[CRON AUTO-START] Found {len(sessions_to_start)} sessions to start"
        )

        started_count = 0
        error_count = 0

        for session in sessions_to_start:
            try:
                _logger.info(
                    f"[CRON AUTO-START] Starting session {session.id}: "
                    f"{session.subject_id.name} on {session.date}"
                )

                session.action_start()
                started_count += 1

            except Exception as e:
                error_count += 1
                _logger.error(
                    f"[CRON AUTO-START] Error starting session {session.id}: {str(e)}"
                )
                continue

        _logger.info(
            f"[CRON AUTO-START] Finished: {started_count} started, {error_count} errors"
        )

        return {
            "started": started_count,
            "errors": error_count,
            "total": len(sessions_to_start),
        }
