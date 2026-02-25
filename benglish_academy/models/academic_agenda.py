# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class AcademicAgenda(models.Model):
    """
    Modelo para gestionar Horarios Académicos.
    Un horario define el marco temporal y espacial donde se pueden crear clases.
    No crea clases automáticamente, sino que define la matriz lógica de posibilidades.
    """

    _name = "benglish.academic.agenda"
    _description = "Horario Académico"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_start desc, code"
    _rec_name = "display_name"

    # CAMPOS BÁSICOS


    name = fields.Char(
        string="Nombre del Horario",
        compute="_compute_name",
        store=True,
        readonly=True,
        tracking=True,
        help="Nombre generado automáticamente como Planner-001, Planner-002, etc.",
    )

    code = fields.Char(
        string="Código",
        required=True,
        copy=False,
        readonly=True,
        default="/",
        tracking=True,
        index=True,
        help="Código único consecutivo generado automáticamente (ej: PL-001)",
    )

    display_name = fields.Char(
        string="Nombre a Mostrar",
        compute="_compute_display_name",
        store=True,
        help="Nombre completo para visualización",
    )

    description = fields.Text(
        string="Descripción",
        help="Descripción detallada del propósito de este horario",
    )

    active = fields.Boolean(
        string="Activa",
        default=True,
        tracking=True,
        help="Si está inactiva, no se pueden crear nuevas sesiones",
    )

    # UBICACIÓN (DETERMINA SEDE)


    location_city = fields.Selection(
        selection="_get_city_selection",
        string="Ubicación (Ciudad)",
        required=False,
        tracking=True,
        help="Ciudad donde se realizará el horario. Solo requerida para sedes presenciales.",
    )

    campus_id = fields.Many2one(
        comodel_name="benglish.campus",
        string="Sede",
        required=True,
        ondelete="restrict",
        tracking=True,
        domain="[('active', '=', True), '|', ('city_name', '=', location_city), ('campus_type', '=', 'online')]",
        help="Sede donde se dictarán las clases. Si seleccionas ciudad, verás sedes de esa ciudad + virtuales. Sin ciudad, solo virtuales.",
    )

    # MARCO TEMPORAL (DEFINE LA MATRIZ)


    date_start = fields.Date(
        string="Fecha de Inicio",
        required=True,
        tracking=True,
        help="Fecha de inicio del horario (primera fila de la matriz)",
    )

    date_end = fields.Date(
        string="Fecha de Fin",
        required=True,
        tracking=True,
        help="Fecha de fin del horario (última fila de la matriz)",
    )

    time_start = fields.Float(
        string="Hora de Inicio",
        required=True,
        tracking=True,
        help="Hora de inicio permitida (formato 24h decimal: 7.0 = 7:00 AM, 14.5 = 2:30 PM)",
    )

    time_end = fields.Float(
        string="Hora de Fin",
        required=True,
        tracking=True,
        help="Hora de fin permitida (formato 24h decimal: 18.0 = 6:00 PM, 20.5 = 8:30 PM)",
    )

    # Campos computados para resumen
    duration_days = fields.Integer(
        string="Duración (días)",
        compute="_compute_duration",
        store=True,
        help="Número total de días entre fecha inicio y fin",
    )

    duration_hours = fields.Float(
        string="Ventana Horaria (horas)",
        compute="_compute_duration",
        store=True,
        help="Rango de horas disponibles por día",
    )

    schedule_summary = fields.Char(
        string="Resumen de Horarios",
        compute="_compute_schedule_summary",
        store=True,
        help="Resumen legible de fechas, horas y días habilitados",
    )

    # RELACIÓN CON SESIONES (ONE2MANY)


    session_ids = fields.One2many(
        comodel_name="benglish.academic.session",
        inverse_name="agenda_id",
        string="Clases",
        help="Clases programadas dentro de este horario",
    )

    session_count = fields.Integer(
        string="Total de Clases",
        compute="_compute_session_stats",
        store=True,
        help="Número total de clases programadas en este horario",
    )

    session_published_count = fields.Integer(
        string="Clases Publicadas",
        compute="_compute_session_stats",
        store=True,
        help="Número de clases en estado publicado",
    )

    session_draft_count = fields.Integer(
        string="Clases en Borrador",
        compute="_compute_session_stats",
        store=True,
        help="Número de clases en estado borrador",
    )

    # RELACIÓN CON LOGS (HISTORIAL DE CAMBIOS)


    log_ids = fields.One2many(
        comodel_name="benglish.agenda.log",
        inverse_name="agenda_id",
        string="Historial de Cambios",
        help="Registros de auditoría de cambios en sesiones de este horario",
    )

    log_count = fields.Integer(
        string="Cantidad de Logs",
        compute="_compute_log_count",
        help="Número total de registros en el historial de cambios",
    )

    # ESTADO DE LA AGENDA


    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("active", "Activa"),
            ("published", "Publicada"),
            ("executed", "Ejecutada"),
            ("closed", "Cerrada"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
        compute="_compute_state",
        store=True,
        readonly=False,
        help="Estado del ciclo de vida del horario. Se actualiza automáticamente a 'Ejecutada' cuando la fecha de fin ha pasado.",
    )

    # AUDITORÍA


    created_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Creada por",
        default=lambda self: self.env.user,
        readonly=True,
        help="Usuario que creó el horario",
    )

    # RESTRICCIONES SQL


    _sql_constraints = [
        (
            "code_unique",
            "UNIQUE(code)",
            "El código de la agenda debe ser único.",
        ),
        (
            "check_dates",
            "CHECK(date_end >= date_start)",
            "La fecha de fin debe ser mayor o igual a la fecha de inicio.",
        ),
        (
            "check_times",
            "CHECK(time_end > time_start)",
            "La hora de fin debe ser mayor que la hora de inicio.",
        ),
    ]

    # MÉTODOS AUXILIARES


    @api.model
    def _get_city_selection(self):
        """Obtiene lista de ciudades únicas desde las sedes activas."""
        raw_cities = (
            self.env["benglish.campus"]
            .search([("active", "=", True)])
            .mapped("city_name")
        )
        cities = [
            city.strip()
            for city in raw_cities
            if isinstance(city, str) and city.strip()
        ]
        return [(city, city) for city in sorted(set(cities))]

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
                end_time = start_time + 2.0
        return start_time, end_time

    @api.model
    def default_get(self, fields_list):
        """Prellenar horarios desde la sede cuando exista en el contexto."""
        res = super(AcademicAgenda, self).default_get(fields_list)
        campus_id = res.get("campus_id") or self.env.context.get("default_campus_id")
        if campus_id:
            campus = self.env["benglish.campus"].browse(campus_id)
            start_time, end_time = self._get_default_times_from_campus(campus)
            res["time_start"] = start_time
            res["time_end"] = end_time
        return res

    @api.onchange("campus_id")
    def _onchange_campus_id(self):
        """Al cambiar sede, refresca el rango horario desde la configuración."""
        if not self.campus_id:
            return
        start_time, end_time = self._get_default_times_from_campus(self.campus_id)
        self.time_start = start_time
        self.time_end = end_time

    # COMPUTED FIELDS


    @api.depends("code")
    def _compute_name(self):
        """Genera el nombre automáticamente desde el código (Planner-001, Planner-002, etc)."""
        for record in self:
            if record.code and record.code != "/":
                # Extraer el número del código PL-006 -> 006, y crear Planner-006
                number = record.code.split("-")[-1] if "-" in record.code else "000"
                record.name = f"Planner-{number}"
            else:
                record.name = "Nueva Agenda"

    @api.depends("name", "code")
    def _compute_display_name(self):
        """Computa el nombre para visualización."""
        for record in self:
            if record.code and record.code != "/":
                record.display_name = f"{record.name} [{record.code}]"
            else:
                record.display_name = record.name or "Nueva Agenda"

    @api.depends("date_start", "date_end", "time_start", "time_end")
    def _compute_duration(self):
        """Calcula la duración en días y el rango horario."""
        for record in self:
            if record.date_start and record.date_end:
                delta = record.date_end - record.date_start
                record.duration_days = delta.days + 1
            else:
                record.duration_days = 0

            if record.time_start and record.time_end:
                record.duration_hours = record.time_end - record.time_start
            else:
                record.duration_hours = 0

    @api.depends(
        "date_start",
        "date_end",
        "time_start",
        "time_end",
        "campus_id.schedule_summary",
    )
    def _compute_schedule_summary(self):
        """Genera resumen legible de la agenda."""
        for record in self:
            if not all(
                [record.date_start, record.date_end, record.time_start, record.time_end]
            ):
                record.schedule_summary = "Fechas u horarios incompletos"
                continue

            # Formato de horas
            start_h = int(record.time_start)
            start_m = int((record.time_start - start_h) * 60)
            end_h = int(record.time_end)
            end_m = int((record.time_end - end_h) * 60)

            time_str = f"{start_h:02d}:{start_m:02d} - {end_h:02d}:{end_m:02d}"

            # Días disponibles de la sede
            days_info = ""
            if record.campus_id:
                days_info = f" | Días: según sede {record.campus_id.name}"

            record.schedule_summary = (
                f"{record.date_start} al {record.date_end} | {time_str}{days_info}"
            )

    @api.depends("session_ids", "session_ids.state", "session_ids.is_published")
    def _compute_session_stats(self):
        """Calcula estadísticas de las sesiones."""
        for record in self:
            sessions = record.session_ids
            record.session_count = len(sessions)
            record.session_published_count = len(
                sessions.filtered(lambda s: s.is_published)
            )
            record.session_draft_count = len(
                sessions.filtered(lambda s: s.state == "draft")
            )

    @api.depends("log_ids")
    def _compute_log_count(self):
        """Calcula la cantidad de logs asociados a esta agenda."""
        for record in self:
            record.log_count = len(record.log_ids)

    @api.depends("date_end", "state")
    def _compute_state(self):
        """Actualiza automáticamente el estado a 'Ejecutada' cuando la fecha de fin ha pasado."""
        today = fields.Date.today()
        for record in self:
            # Solo actualizar a ejecutada si está en estado publicada
            if record.state == 'published' and record.date_end and record.date_end < today:
                record.state = 'executed'
            elif not record.state or record.state == False:
                record.state = 'draft'

    # VALIDACIONES


    @api.constrains("date_start", "date_end")
    def _check_date_range(self):
        """Valida que el rango de fechas sea válido."""
        for record in self:
            if record.date_start and record.date_end:
                if record.date_end < record.date_start:
                    raise ValidationError(
                        _("La fecha de fin no puede ser anterior a la fecha de inicio.")
                    )

                # Validar que no exceda un rango razonable (ej: 1 año)
                delta = record.date_end - record.date_start
                if delta.days > 365:
                    raise ValidationError(
                        _(
                            "La agenda no puede exceder 1 año de duración. "
                            "Duración actual: %s días."
                        )
                        % delta.days
                    )

    @api.constrains("time_start", "time_end")
    def _check_time_range(self):
        """Valida que el rango horario sea válido."""
        for record in self:
            if record.time_start and record.time_end:
                if record.time_end <= record.time_start:
                    raise ValidationError(
                        _("La hora de fin debe ser posterior a la hora de inicio.")
                    )

                # Validar formato de horas (0.0 a 23.99)
                if not (0 <= record.time_start < 24 and 0 < record.time_end <= 24):
                    raise ValidationError(
                        _("Las horas deben estar en formato 24h decimal (0.0 a 24.0).")
                    )

    @api.constrains("time_start", "time_end", "campus_id")
    def _check_campus_schedule(self):
        """
        Valida que las horas de la agenda estén dentro del horario
        de atención de la sede seleccionada.
        """
        for record in self:
            if record.campus_id and record.time_start and record.time_end:
                campus = record.campus_id

                if (
                    record.time_start < campus.schedule_start_time
                    or record.time_end > campus.schedule_end_time
                ):
                    raise ValidationError(
                        _(
                            "Los horarios de la agenda (%(agenda_start)s - %(agenda_end)s) deben estar "
                            "dentro del horario de atención de la sede '%(campus)s' (%(campus_start)s - %(campus_end)s)."
                        )
                        % {
                            "agenda_start": self._format_time(record.time_start),
                            "agenda_end": self._format_time(record.time_end),
                            "campus": campus.name,
                            "campus_start": self._format_time(
                                campus.schedule_start_time
                            ),
                            "campus_end": self._format_time(campus.schedule_end_time),
                        }
                    )

    @api.constrains("location_city", "campus_id")
    def _check_campus_city(self):
        """
        Valida que la sede pertenezca a la ciudad seleccionada.
        Para sedes virtuales, la ciudad no es obligatoria.
        """
        for record in self:
            # Si la sede es virtual (online o is_virtual_sede=True), no validar ciudad
            if record.campus_id and (record.campus_id.campus_type == 'online' or record.campus_id.is_virtual_sede):
                continue
                
            # Para sedes presenciales, ciudad es obligatoria
            if record.campus_id and record.campus_id.campus_type != 'online' and not record.campus_id.is_virtual_sede and not record.location_city:
                raise ValidationError(
                    _("La ciudad es obligatoria para horarios con sedes presenciales.")
                )
            
            # Validar que la sede pertenezca a la ciudad seleccionada
            if record.location_city and record.campus_id:
                if record.campus_id.city_name != record.location_city:
                    raise ValidationError(
                        _("La sede '%(campus)s' no pertenece a la ciudad '%(city)s'.")
                        % {
                            "campus": record.campus_id.name,
                            "city": record.location_city,
                        }
                    )

    # CRUD OVERRIDES

    def _get_next_reusable_agenda_code(self):
        """
        Obtiene el próximo código de agenda reutilizando huecos si existen.
        Busca el primer número disponible entre los códigos existentes.
        """
        import re
        prefix = "PL-"
        padding = 3
        
        # Obtener todos los códigos usados
        existing = self.sudo().search([('code', '=like', f'{prefix}%')])
        used_numbers = set()
        
        for record in existing:
            if record.code:
                match = re.match(r'^PL-(\d+)$', record.code)
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
        """Genera código consecutivo único al crear, reutilizando huecos."""
        for vals in vals_list:
            if vals.get("code", "/") == "/":
                vals["code"] = self._get_next_reusable_agenda_code()
        return super(AcademicAgenda, self).create(vals_list)

    def write(self, vals):
        """Validaciones adicionales al actualizar."""
        # Prevenir cambios en agenda publicada o con sesiones activas
        if any(
            key in vals
            for key in ["date_start", "date_end", "time_start", "time_end", "campus_id"]
        ):
            for record in self:
                if record.state in ["published", "executed", "closed"]:
                    raise UserError(
                        _(
                            "No se pueden modificar fechas, horarios o sede de una agenda "
                            "publicada, ejecutada o cerrada."
                        )
                    )
                if record.session_ids.filtered(
                    lambda s: s.state in ["started", "done"]
                ):
                    raise UserError(
                        _(
                            "No se pueden modificar fechas, horarios o sede de una agenda "
                            "con sesiones iniciadas o finalizadas."
                        )
                    )
        return super(AcademicAgenda, self).write(vals)

    def unlink(self):
        """
        Permite eliminar agendas cerradas junto con sus sesiones.
        Previene eliminación de agendas activas o publicadas con sesiones.
        """
        for record in self:
            # Si la agenda está cerrada, eliminar todas sus sesiones primero
            if record.state == "closed" and record.session_ids:
                record.session_ids.unlink()
            # Si no está cerrada y tiene sesiones, prevenir eliminación
            elif record.session_ids:
                raise UserError(
                    _(
                        "No se puede eliminar la agenda '%(name)s' porque tiene %(count)s sesiones asociadas. "
                        "Cierre la agenda primero o elimine las sesiones manualmente."
                    )
                    % {"name": record.display_name, "count": len(record.session_ids)}
                )
        return super(AcademicAgenda, self).unlink()

    def copy(self, default=None):
        """
        Duplica la agenda con todas sus sesiones.
        La agenda duplicada se crea en estado borrador.
        """
        self.ensure_one()

        if default is None:
            default = {}

        # Forzar estado borrador en la copia
        default.update(
            {
                "state": "draft",
                "code": "/",  # Se generará uno nuevo automáticamente
            }
        )

        # Duplicar la agenda (sin sesiones aún)
        new_agenda = super(AcademicAgenda, self).copy(default)

        # Duplicar todas las sesiones asociadas
        for session in self.session_ids:
            session.copy(
                default={
                    "agenda_id": new_agenda.id,
                    "state": "draft",
                    "is_published": False,
                }
            )

        # Mensaje informativo
        self.message_post(
            body=_("Esta agenda fue duplicada desde: %(original)s")
            % {"original": self.display_name},
            subject=_("Agenda Duplicada"),
        )

        new_agenda.message_post(
            body=_(
                "Agenda duplicada desde: %(original)s con %(count)s sesiones copiadas."
            )
            % {"original": self.display_name, "count": len(self.session_ids)},
            subject=_("Copia de Agenda"),
        )

        return new_agenda

    # MÉTODOS DE NEGOCIO - TRANSICIONES DE ESTADO


    def action_activate(self):
        """Activa la agenda y muestra la matriz de programación de sesiones."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Solo se pueden activar agendas en estado Borrador."))

        # Validar campos obligatorios básicos
        if not all([
            self.name,
            self.campus_id,
            self.date_start,
            self.date_end,
            self.time_start,
            self.time_end,
        ]):
            raise UserError(
                _("Complete todos los campos obligatorios antes de activar la agenda.")
            )
        
        # Validar ciudad solo para sedes NO virtuales
        if self.campus_id.campus_type != 'online' and not self.campus_id.is_virtual_sede and not self.location_city:
            raise UserError(
                _("La ciudad es obligatoria para agendas con sedes presenciales.")
            )

        self.state = "active"
        self.message_post(
            body=_("Agenda activada. Ya se pueden programar clases."),
            subject=_("Agenda Activada"),
        )

        # Abrir la vista de calendario/matriz para programar clases
        return self.action_open_session_matrix()

    def action_publish(self):
        """
        Publica la agenda y todas sus clases.
        Las clases pasan a estar disponibles para inscripciones.
        
        IMPORTANTE: Las clases ya dictadas (estado 'done') mantienen su estado
        y solo se marca is_published=True para mantenerlas visibles.
        """
        self.ensure_one()
        if self.state != "active":
            raise UserError(_("Solo se pueden publicar horarios activos."))

        # Validar que haya al menos una clase
        if not self.session_ids:
            raise UserError(
                _(
                    "No se puede publicar una agenda sin clases. "
                    "Cree al menos una clase antes de publicar."
                )
            )

        # Validar que todas las clases tengan los campos obligatorios
        incomplete_sessions = []
        for s in self.session_ids:
            # Solo validar sesiones que NO estén ya dictadas o canceladas
            if s.state in ['done', 'cancelled']:
                continue
                
            # Campos básicos obligatorios
            # Para asignatura: subject_id O elective_pool_id (si es sesión electiva)
            has_subject_or_elective = bool(s.subject_id or (s.is_elective_session and s.elective_pool_id))
            required_fields = [
                has_subject_or_elective,  # Asignatura o pool de electivas
                s.date,
                s.time_start,
                s.time_end,
                (s.teacher_id or s.coach_id),  # Al menos uno debe existir
            ]

            # Aula es obligatoria solo si NO es virtual
            if s.delivery_mode != "virtual":
                required_fields.append(s.subcampus_id)

            if not all(required_fields):
                incomplete_sessions.append(s)

        if incomplete_sessions:
            raise UserError(
                _(
                    "Las siguientes clases tienen campos obligatorios incompletos:\n\n%s\n\n"
                    "Complete todas las clases antes de publicar la agenda."
                )
                % "\n".join([f"- {s.display_name}" for s in incomplete_sessions[:5]])
            )

        # Marcar todas las clases como publicadas
        # IMPORTANTE: Preservar el estado de clases ya dictadas ('done') o canceladas
        for s in self.session_ids:
            # Clases ya dictadas: solo publicar, NO cambiar estado
            if s.state == 'done':
                s.write({"is_published": True})
                _logger.info(
                    f"[PUBLISH] Sesión {s.id} ya dictada - preservando estado 'done', marcando is_published=True"
                )
                continue
            
            # Clases canceladas: solo publicar, NO cambiar estado
            if s.state == 'cancelled':
                s.write({"is_published": True})
                _logger.info(
                    f"[PUBLISH] Sesión {s.id} cancelada - preservando estado 'cancelled', marcando is_published=True"
                )
                continue
            
            # Clases pendientes: determinar nuevo estado
            # Buscar inscripciones confirmadas hechas desde el portal
            portal_confirmed = s.enrollment_ids.filtered(
                lambda e: e.state == "confirmed"
                and e.enrolled_by_id
                and e.enrolled_by_id.share
            )
            new_state = "with_enrollment" if portal_confirmed else "active"
            s.write({"is_published": True, "state": new_state})

        self.state = "published"
        self.message_post(
            body=_("Horario publicado. %(count)s clases disponibles para inscripciones.")
            % {"count": len(self.session_ids)},
            subject=_("Horario Publicado"),
        )

    def action_unpublish(self):
        """
        Despublica la agenda (devuelve al estado activo).
        
        Validaciones más flexibles:
        - NO permite despublicar si hay clases EN CURSO (in_progress)
        - SÍ permite despublicar si hay clases ya terminadas (done) - ya cumplieron su propósito
        - SÍ permite despublicar si hay clases canceladas (cancelled)
        - Advertencia si hay inscripciones confirmadas pendientes
        """
        self.ensure_one()
        if self.state != "published":
            raise UserError(_("Solo se pueden despublicar horarios publicados."))

        # Validar que no haya clases EN CURSO (in_progress es el único estado que bloquea)
        # Las clases 'done' ya terminaron y no deberían bloquear
        sessions_in_progress = self.session_ids.filtered(
            lambda s: s.state == "in_progress"
        )

        if sessions_in_progress:
            raise UserError(
                _(
                    "No se puede despublicar la agenda porque tiene %(count)s clase(s) "
                    "actualmente en curso.\n\n"
                    "Solo se pueden despublicar agendas sin clases en progreso.\n\n"
                    "Clases en curso: %(sessions)s"
                ) % {
                    'count': len(sessions_in_progress),
                    'sessions': ', '.join(sessions_in_progress.mapped('display_name')),
                }
            )

        # Advertencia informativa si hay inscripciones confirmadas (pero no bloquea)
        sessions_with_confirmed = self.session_ids.filtered(
            lambda s: s.enrollment_ids.filtered(lambda e: e.state == "confirmed")
        )

        if sessions_with_confirmed:
            # Registrar advertencia en el chatter pero permitir la operación
            self.message_post(
                body=_(
                    "<strong>⚠️ Advertencia al Despublicar</strong><br/>"
                    "Se despublicó la agenda con %(count)s clase(s) que tienen inscripciones confirmadas.<br/>"
                    "Las clases ya dictadas (estado 'done') fueron procesadas correctamente."
                ) % {'count': len(sessions_with_confirmed)},
                subject=_("Advertencia: Inscripciones Confirmadas"),
            )

        # Marcar todas las clases NO TERMINADAS como no publicadas
        # Las clases 'done' mantienen su estado (ya terminaron)
        for s in self.session_ids:
            if s.state == 'done':
                # Clase ya terminada: solo despublicar, mantener estado 'done'
                s.write({"is_published": False})
            elif s.state == 'cancelled':
                # Clase cancelada: despublicar y mantener cancelada
                s.write({"is_published": False})
            else:
                # Clases pendientes o planificadas: devolver a draft
                s.write({"is_published": False, "state": "draft"})

        self.state = "active"
        self.message_post(
            body=_(
                "Horario despublicado. Las clases ya no están disponibles para inscripciones."
            ),
            subject=_("Horario Despublicado"),
        )

    def action_close(self):
        """Cierra el horario. No se pueden crear más clases."""
        self.ensure_one()
        if self.state not in ["active", "published"]:
            raise UserError(_("Solo se pueden cerrar horarios activos o publicados."))

        self.state = "closed"
        self.message_post(
            body=_("Horario cerrado."),
            subject=_("Horario Cerrado"),
        )

    def action_reopen(self):
        """Reabre un horario cerrado."""
        self.ensure_one()
        if self.state != "closed":
            raise UserError(_("Solo se pueden reabrir horarios cerrados."))

        self.state = "published"
        self.active = True
        self.message_post(body=_("Horario reabierto."), subject=_("Horario Reabierto"))

    def action_open_session_matrix(self):
        """
        Abre una vista de calendario/matriz para programar clases dentro de esta agenda.
        Muestra las clases programadas y permite crear nuevas.
        """
        self.ensure_one()

        # Calcular horarios formateados
        hora_inicio = "{:02d}:{:02d}".format(
            int(self.time_start), int((self.time_start % 1) * 60)
        )
        hora_fin = "{:02d}:{:02d}".format(
            int(self.time_end), int((self.time_end % 1) * 60)
        )

        default_end_time = self.time_end or (
            self.campus_id.schedule_end_time if self.campus_id else 18.0
        )

        return {
            "name": _("📅 Matriz de Programación - %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.academic.session",
            "view_mode": "calendar,list,form",
            "views": [
                (
                    self.env.ref("benglish_academy.view_academic_session_calendar").id,
                    "calendar",
                ),
                (
                    self.env.ref("benglish_academy.view_academic_session_list").id,
                    "list",
                ),
                (
                    self.env.ref("benglish_academy.view_academic_session_form").id,
                    "form",
                ),
            ],
            "domain": [("agenda_id", "=", self.id)],
            "context": {
                "default_agenda_id": self.id,
                "default_location_city": self.location_city,
                "default_campus_id": self.campus_id.id,
                "default_date": self.date_start,
                "default_time_start": self.time_start,
                "default_time_end": default_end_time,
                "search_default_filter_all": 1,
                # Posicionar calendario en la fecha de inicio de la agenda
                "initial_date": (
                    self.date_start.isoformat() if self.date_start else False
                ),
                # Información de la agenda para validaciones en el frontend
                "agenda_id": self.id,
                "agenda_name": self.name,
                "agenda_date_start": (
                    self.date_start.isoformat() if self.date_start else False
                ),
                "agenda_date_end": (
                    self.date_end.isoformat() if self.date_end else False
                ),
                "agenda_time_start": self.time_start,
                "agenda_time_end": self.time_end,
                "agenda_time_start_formatted": hora_inicio,
                "agenda_time_end_formatted": hora_fin,
                "agenda_location": self.location_city,
                "agenda_campus_id": self.campus_id.id,
                "agenda_campus_name": self.campus_id.name,
            },
            "target": "current",
            "help": """
                <p class="o_view_nocontent_smiling_face">
                    📅 Matriz de Programación de Clases
                </p>
                <p>
                    <strong>Agenda:</strong> %s<br/>
                    <strong>Período:</strong> %s al %s<br/>
                    <strong>Horario permitido:</strong> %s - %s<br/>
                    <strong>Sede:</strong> %s<br/><br/>
                    Haz clic en un día/hora del calendario para crear una nueva clase.<br/>
                    Solo puedes programar dentro del rango de fechas y horarios de la agenda.
                </p>
            """
            % (
                self.name,
                self.date_start.strftime("%d/%m/%Y") if self.date_start else "",
                self.date_end.strftime("%d/%m/%Y") if self.date_end else "",
                hora_inicio,
                hora_fin,
                self.campus_id.name,
            ),
        }

    # MÉTODOS AUXILIARES DE NEGOCIO


    def is_date_valid(self, date_to_check):
        """
        Verifica si una fecha está dentro del rango de la agenda
        y si el día de la semana está habilitado en la sede.
        """
        self.ensure_one()

        if not (self.date_start <= date_to_check <= self.date_end):
            return False

        # Verificar día de la semana (lunes=0, domingo=6)
        weekday = date_to_check.weekday()
        campus = self.campus_id

        day_mapping = {
            0: campus.allow_monday,
            1: campus.allow_tuesday,
            2: campus.allow_wednesday,
            3: campus.allow_thursday,
            4: campus.allow_friday,
            5: campus.allow_saturday,
            6: campus.allow_sunday,
        }

        return day_mapping.get(weekday, False)

    def is_time_valid(self, time_to_check):
        """
        Verifica si una hora está dentro del rango permitido
        por la agenda y la sede.
        """
        self.ensure_one()

        return (
            self.time_start <= time_to_check <= self.time_end
            and self.campus_id.schedule_start_time
            <= time_to_check
            <= self.campus_id.schedule_end_time
        )

    def get_valid_dates(self):
        """
        Retorna lista de fechas válidas dentro de la agenda
        (considerando días habilitados en la sede).
        """
        self.ensure_one()

        valid_dates = []
        current_date = self.date_start

        while current_date <= self.date_end:
            if self.is_date_valid(current_date):
                valid_dates.append(current_date)
            current_date += timedelta(days=1)

        return valid_dates

    def _format_time(self, time_float):
        """Convierte tiempo decimal a formato HH:MM."""
        hours = int(time_float)
        minutes = int((time_float - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"

    # MÉTODOS DE VISTA


    def action_view_sessions(self):
        """Acción para ver las sesiones de la agenda en vista lista."""
        self.ensure_one()
        return {
            "name": _("Sesiones - %s") % self.display_name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.academic.session",
            "view_mode": "list,form,calendar",
            "domain": [("agenda_id", "=", self.id)],
            "context": {
                "default_agenda_id": self.id,
                "default_location_city": self.location_city,
                "default_campus_id": self.campus_id.id,
            },
        }

    def action_view_logs(self):
        """Acción para ver el historial de cambios de la agenda."""
        self.ensure_one()
        return {
            "name": _("Historial de Cambios - %s") % self.display_name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.agenda.log",
            "view_mode": "list,form",
            "domain": [("agenda_id", "=", self.id)],
            "context": {
                "default_agenda_id": self.id,
                "create": False,  # No permitir crear logs manualmente desde esta vista
            },
        }

    def action_create_session(self):
        """Acción para crear una nueva sesión en esta agenda."""
        self.ensure_one()

        if self.state not in ["active", "published"]:
            raise UserError(
                _("Solo se pueden crear sesiones en horarios activos o publicados.")
            )

        default_end_time = self.time_end or (
            self.campus_id.schedule_end_time if self.campus_id else 18.0
        )
        if default_end_time <= self.time_start:
            duration = self.campus_id.default_session_duration or 2.0
            default_end_time = self.time_start + duration

        # Determinar modalidad por defecto según tipo de sede
        is_virtual_campus = self.campus_id and (
            self.campus_id.is_virtual_sede or self.campus_id.campus_type == 'online'
        )
        default_delivery_mode = 'virtual' if is_virtual_campus else 'presential'
        # Capacidad por defecto: 15 para virtual
        default_capacity = 15 if is_virtual_campus else False

        context = {
            "default_agenda_id": self.id,
            "default_location_city": self.location_city,
            "default_campus_id": self.campus_id.id,
            "default_date": self.date_start,
            "default_time_start": self.time_start,
            "default_time_end": default_end_time,
            "default_delivery_mode": default_delivery_mode,
        }
        # Solo agregar capacidad si tiene valor
        if default_capacity:
            context["default_max_capacity"] = default_capacity

        return {
            "name": _("Nueva Sesión - %s") % self.display_name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.academic.session",
            "view_mode": "form",
            "target": "new",
            "context": context,
        }

    # MÉTODOS CRON

    @api.model
    def _cron_update_executed_agendas(self):
        """
        Método ejecutado por el cron job para actualizar automáticamente
        las agendas publicadas cuya fecha de fin ya ha pasado al estado "Ejecutada".
        """
        today = fields.Date.today()
        
        # Buscar todas las agendas publicadas cuya fecha de fin ha pasado
        agendas_to_update = self.search([
            ('state', '=', 'published'),
            ('date_end', '<', today)
        ])
        
        if agendas_to_update:
            agendas_to_update.write({'state': 'executed'})
            _logger.info(
                "Cron: %s horarios actualizados a estado 'Ejecutada'",
                len(agendas_to_update)
            )
        
        return True

    def action_duplicate_agenda_wizard(self):
        """
        Acción para abrir el wizard de duplicación inteligente de agenda.
        
        Este método se invoca desde el botón "Duplicar Agenda" en la vista form.
        Abre un wizard que permite al usuario configurar el nuevo periodo y
        opciones de duplicación antes de crear la nueva agenda.
        """
        self.ensure_one()

        return {
            'name': _('Duplicar Horario: %s') % self.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'benglish.duplicate.agenda.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_source_agenda_id': self.id,
            },
        }
