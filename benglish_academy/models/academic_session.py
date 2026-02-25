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

    # Campo auxiliar para detectar si la agenda tiene sede virtual
    is_virtual_agenda = fields.Boolean(
        string="Es Agenda Virtual",
        compute="_compute_is_virtual_agenda",
        store=True,
        help="Indica si la agenda tiene una sede virtual. Si es True, la modalidad debe ser virtual.",
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

    # Tipo de Asignatura - reemplaza session_type
    subject_type_id = fields.Many2one(
        comodel_name="benglish.subject.type",
        string="Tipo de Asignatura",
        ondelete="restrict",
        tracking=True,
        index=True,
        help="Tipo de asignatura. Filtra las asignaturas disponibles y determina si es sesión de pool de electivas.",
    )

    # Campo computado para usar en invisible de la vista
    is_elective_session = fields.Boolean(
        string="Es Sesión Electiva",
        compute="_compute_is_elective_session",
        store=False,
        help="Indica si el tipo de asignatura seleccionado es de pool de electivas",
    )

    # Pool de electivas - visible solo cuando subject_type_id.is_elective_pool = True
    elective_pool_id = fields.Many2one(
        comodel_name="benglish.elective.pool",
        string="Electivas",
        ondelete="restrict",
        tracking=True,
        index=True,
        help="Pool de electivas. Solo visible cuando el tipo de asignatura tiene 'Pool de Electivas' habilitado.",
    )

    subject_id = fields.Many2one(
        comodel_name="benglish.subject",
        string="Asignatura",
        required=False,
        ondelete="cascade",
        tracking=True,
        domain="[('program_id', '=', program_id), ('active', '=', True)]",
        index=True,
        help="Asignatura a dictar (muestra solo código + nombre). No requerido para sesiones de tipo electiva.",
    )

    @api.depends('subject_type_id', 'subject_type_id.is_elective_pool')
    def _compute_is_elective_session(self):
        """Computa si la sesión es de tipo electiva basándose en subject_type_id"""
        for record in self:
            record.is_elective_session = bool(
                record.subject_type_id and record.subject_type_id.is_elective_pool
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

    # Campo computado para mostrar asignatura o electiva en la lista
    subject_display_name = fields.Char(
        string="Asignatura",
        compute="_compute_subject_display_name",
        store=True,
        help="Muestra el nombre de la asignatura o del pool de electivas",
    )

    @api.depends('subject_id', 'subject_id.name', 'subject_id.code', 'elective_pool_id', 'elective_pool_id.name', 'elective_pool_id.code', 'is_elective_session')
    def _compute_subject_display_name(self):
        """Computa el nombre a mostrar: asignatura regular o pool de electivas"""
        for record in self:
            if record.is_elective_session and record.elective_pool_id:
                # Para electivas, mostrar el pool
                if record.elective_pool_id.code:
                    record.subject_display_name = f"{record.elective_pool_id.code} - {record.elective_pool_id.name}"
                else:
                    record.subject_display_name = record.elective_pool_id.name
            elif record.subject_id:
                # Para asignaturas regulares
                if record.subject_id.code:
                    record.subject_display_name = f"{record.subject_id.code} - {record.subject_id.name}"
                else:
                    record.subject_display_name = record.subject_id.name
            else:
                record.subject_display_name = False

    # ========================================================================
    # MÉTODOS ONCHANGE
    # ========================================================================

    @api.onchange('subject_type_id')
    def _onchange_subject_type_id(self):
        """
        Al cambiar el tipo de asignatura, limpia campos relacionados
        para evitar inconsistencias y actualiza dominio de subject_id
        """
        # Si el tipo NO tiene pool de electivas, limpia el pool
        if self.subject_type_id and not self.subject_type_id.is_elective_pool:
            self.elective_pool_id = False
        
        # Limpiar subject_id para forzar nueva selección según tipo
        if self.subject_type_id:
            self.subject_id = False

    @api.onchange('elective_pool_id')
    def _onchange_elective_pool_id(self):
        """
        Cuando se selecciona un pool de electivas, limpia subject_id ya que
        para sesiones electivas la asignatura es el pool seleccionado.
        """
        _logger.info(
            "[ACADEMIC_SESSION ONCHANGE] elective_pool_id cambiado a: %s",
            self.elective_pool_id.id if self.elective_pool_id else None
        )
        
        # Si es sesión electiva, limpiar subject_id (la asignatura es el pool)
        if self.subject_type_id and self.subject_type_id.is_elective_pool:
            self.subject_id = False
            _logger.info("[ACADEMIC_SESSION ONCHANGE] Sesión electiva - subject_id limpiado")

    # ========================================================================
    # MÉTODOS AUXILIARES DE SECUENCIA
    # ========================================================================

    def _get_next_reusable_session_code(self):
        """
        Obtiene el próximo código de sesión reutilizando huecos si existen.
        Busca el primer número disponible entre los códigos existentes.
        """
        import re
        prefix = "SES-"
        padding = 5
        
        # Obtener todos los códigos usados
        existing = self.sudo().search([('session_code', '=like', f'{prefix}%')])
        used_numbers = set()
        
        for record in existing:
            if record.session_code:
                match = re.match(r'^SES-(\d+)$', record.session_code)
                if match:
                    used_numbers.add(int(match.group(1)))
        
        # Buscar primer hueco
        if used_numbers:
            for num in range(1, max(used_numbers) + 2):
                if num not in used_numbers:
                    return f"{prefix}{num:0{padding}d}"
        
        # No hay registros existentes, empezar en 1
        return f"{prefix}00001"

    # ========================================================================
    # MÉTODOS CRUD
    # ========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """
        Al crear sesiones desde el wizard o la vista, asegurar que siempre exista
        un `subject_id`.
        
        ADEMÁS (R2 - FASE 1):
        Genera automáticamente el código único de sesión (session_code) usando secuencia
        con reutilización de huecos.
        
        ADEMÁS: Si la agenda tiene sede virtual, forzar modalidad virtual y capacidad 15.
        """
        for vals in vals_list:
            # R2: Generar código único de sesión si no existe (con reutilización de huecos)
            if not vals.get('session_code') or vals.get('session_code') == '/':
                vals['session_code'] = self._get_next_reusable_session_code()
                _logger.info("[ACADEMIC_SESSION CREATE] Código de sesión generado: %s", vals['session_code'])
            
            # Verificar si la agenda tiene sede virtual y ajustar modalidad/capacidad
            agenda_id = vals.get("agenda_id")
            if agenda_id:
                agenda = self.env["benglish.academic.agenda"].browse(agenda_id)
                if agenda and agenda.campus_id:
                    campus = agenda.campus_id
                    if campus.is_virtual_sede or campus.campus_type == 'online':
                        # Forzar modalidad virtual
                        vals['delivery_mode'] = 'virtual'
                        # Establecer capacidad por defecto 15 si no se especificó
                        if not vals.get('max_capacity'):
                            vals['max_capacity'] = 15
                        _logger.info(
                            "[ACADEMIC_SESSION CREATE] Sede virtual detectada - delivery_mode=virtual, max_capacity=%s",
                            vals.get('max_capacity')
                        )
            
            # Si es modalidad virtual y no tiene capacidad, poner 15
            if vals.get('delivery_mode') == 'virtual' and not vals.get('max_capacity'):
                vals['max_capacity'] = 15
            
            _logger.info(
                "[ACADEMIC_SESSION CREATE] Valores recibidos: subject_id=%s, program_id=%s, agenda_id=%s",
                vals.get("subject_id"),
                vals.get("program_id"),
                vals.get("agenda_id"),
            )
            
            try:
                # Verificar si el tipo de asignatura es de pool de electivas
                is_elective_type = False
                subject_type_id = vals.get("subject_type_id")
                if subject_type_id:
                    subject_type = self.env["benglish.subject.type"].browse(subject_type_id)
                    if subject_type and subject_type.is_elective_pool:
                        is_elective_type = True
                
                _logger.info(
                    "[ACADEMIC_SESSION CREATE] subject_type_id=%s, is_elective_type=%s, elective_pool_id=%s, subject_id=%s",
                    subject_type_id,
                    is_elective_type,
                    vals.get("elective_pool_id"),
                    vals.get("subject_id"),
                )
                
                # Si es tipo electiva (pool), NO necesita subject_id - la asignatura es el pool
                if is_elective_type:
                    # Asegurarse de que subject_id esté vacío para sesiones electivas
                    if vals.get("subject_id"):
                        _logger.info(
                            "[ACADEMIC_SESSION CREATE] Sesión electiva - limpiando subject_id (la asignatura es el pool)"
                        )
                        vals["subject_id"] = False
                    _logger.info(
                        "[ACADEMIC_SESSION CREATE] Sesión electiva creada con pool_id=%s",
                        vals.get("elective_pool_id"),
                    )
                # Si NO es tipo electiva y NO hay subject_id, intentar asignarlo
                elif not vals.get("subject_id"):
                    _logger.warning(
                        "[ACADEMIC_SESSION CREATE] subject_id no proporcionado, intentando asignar automáticamente..."
                    )
                    
                    program_to_search = vals.get("program_id")
                    
                    # Si tampoco hay program_id en vals, intentar obtenerlo de la agenda
                    if not program_to_search and vals.get("agenda_id"):
                        agenda = self.env["benglish.academic.agenda"].browse(vals.get("agenda_id"))
                        if agenda and agenda.program_id:
                            program_to_search = agenda.program_id.id
                            vals["program_id"] = program_to_search
                            _logger.info(
                                "[ACADEMIC_SESSION CREATE] program_id obtenido desde agenda: %s",
                                program_to_search,
                            )
                    
                    if program_to_search:
                        Subject = self.env["benglish.subject"].sudo()
                        subject = Subject.search(
                            [("active", "=", True), ("program_id", "=", program_to_search)],
                            limit=1,
                        )
                        if subject:
                            vals["subject_id"] = subject.id
                            _logger.info(
                                "[ACADEMIC_SESSION CREATE] Asignado subject_id por program_id: %s (%s)",
                                subject.id,
                                subject.display_name,
                            )
                
                    # Último recurso - cualquier subject activo
                    if not vals.get("subject_id"):
                        Subject = self.env["benglish.subject"].sudo()
                        any_subject = Subject.search([("active", "=", True)], limit=1)
                        if any_subject:
                            vals["subject_id"] = any_subject.id
                            _logger.warning(
                                "[ACADEMIC_SESSION CREATE] Asignado subject_id FALLBACK GENERAL: %s (%s)",
                                any_subject.id,
                                any_subject.display_name,
                            )
                        else:
                            _logger.error(
                                "[ACADEMIC_SESSION CREATE] NO SE ENCONTRÓ NINGÚN SUBJECT ACTIVO. Esto causará un error."
                            )
                            raise UserError(
                                _(
                                    "No se pudo asignar una asignatura a la sesión. "
                                    "Por favor, asegúrese de que existan asignaturas activas en el sistema."
                                )
                            )
                else:
                    _logger.info(
                        "[ACADEMIC_SESSION CREATE] subject_id ya proporcionado: %s", vals.get("subject_id")
                    )
                    
            except UserError:
                raise
            except Exception as e:
                _logger.exception(
                    "[ACADEMIC_SESSION CREATE] Error determinando subject_id: %s", str(e)
                )
                raise UserError(
                    _(
                        "Error al crear la sesión académica: %s\n\n"
                        "Por favor, verifique los datos e intente nuevamente."
                    ) % str(e)
                )

        return super(AcademicSession, self).create(vals_list)

    # NOTA: El campo template_id fue eliminado (modelo benglish.agenda.template ya no existe)
    # La lógica de homologación ahora se basa directamente en subject_id

    elective_pool_id = fields.Many2one(
        comodel_name="benglish.elective.pool",
        string="Pool de Electivas",
        ondelete="restrict",
        tracking=True,
        domain="[('active', '=', True)]",
        help="Pool de electivas disponibles para esta sesión (solo para tipo Electiva).",
    )

    audience_phase_id = fields.Many2one(
        comodel_name="benglish.phase",
        string="Fase Audiencia",
        ondelete="restrict",
        domain="[('active', '=', True)]",
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
    
    # NOTA: El campo is_oral_test_template fue eliminado junto con template_id
    # La lógica de oral test ahora se basa en subject_id.subject_classification

    student_alias = fields.Char(
        string="Alias Estudiante",
        compute="_compute_student_alias",
        store=True,
        help="Nombre visible para el estudiante (alias de plantilla).",
    )

    # TIPO Y MODALIDAD

    subject_type_id = fields.Many2one(
        comodel_name="benglish.subject.type",
        string="Tipo de Asignatura",
        required=True,
        ondelete="restrict",
        tracking=True,
        domain="[('active', '=', True)]",
        help="Tipo de asignatura para esta sesión. Las asignaturas disponibles se filtrarán según este tipo.",
    )

    # Campo legacy para compatibilidad (se mantiene por ahora)
    session_type = fields.Selection(
        selection=[
            ("regular", "Clase Regular"),
            ("elective", "Electiva"),
            ("makeup", "Clase de Recuperación"),
            ("evaluation", "Evaluación"),
            ("workshop", "Taller"),
        ],
        string="Tipo de Sesión (Legacy)",
        default="regular",
        tracking=True,
        help="Campo legacy - Usar 'Tipo de Asignatura' en su lugar",
    )

    delivery_mode = fields.Selection(
        selection=[
            ("presential", "Presencial"),
            ("virtual", "Virtual"),
            ("hybrid", "Híbrida"),
        ],
        string="Modalidad",
        default=lambda self: self._get_default_delivery_mode(),
        required=True,
        tracking=True,
        help="Modalidad de entrega de la clase. Si la agenda tiene sede virtual, este campo será 'Virtual' y no se puede cambiar.",
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
        compute="_compute_max_capacity",
        store=True,
        readonly=False,
        tracking=True,
        help="Número máximo de estudiantes que pueden inscribirse. Se calcula automáticamente según modalidad y aula.",
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
        help="Capacidad máxima para estudiantes virtuales (solo aplica en modalidad híbrida o virtual)",
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

    # ==========================================
    # PUBLICACIONES Y POOLS DE ELECTIVAS (FASE 2)
    # ==========================================

    # Publicaciones: Asignaturas a las que se oferta esta sesión
    # TODO: Descomentar cuando se cree el modelo benglish.session.publication
    # publication_ids = fields.One2many(
    #     comodel_name="benglish.session.publication",
    #     inverse_name="session_id",
    #     string="Publicaciones",
    #     help="Asignaturas para las cuales esta sesión está publicada/ofertada (permite pares de prerrequisitos)",
    # )

    # publication_count = fields.Integer(
    #     string="Asignaturas Publicadas",
    #     compute="_compute_publication_count",
    #     store=True,
    #     help="Número de asignaturas a las que se publica esta sesión",
    # )

    # published_subject_ids = fields.Many2many(
    #     comodel_name="benglish.subject",
    #     compute="_compute_published_subjects",
    #     string="Asignaturas Ofertadas",
    #     help="Asignaturas a las que se oferta esta sesión (desde publicaciones)",
    # )

    # Pools de electivas: Pools a los que pertenece esta sesión
    elective_pool_ids = fields.Many2many(
        comodel_name="benglish.elective.pool",
        relation="benglish_elective_pool_session_rel",
        column1="session_id",
        column2="pool_id",
        string="Pools de Electivas",
        help="Pools de electivas a los que pertenece esta sesión",
    )

    pool_count = fields.Integer(
        string="Pools Asociados",
        compute="_compute_pool_count",
        store=True,
        help="Número de pools de electivas a los que pertenece",
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
        (
            "session_code_unique",
            "UNIQUE(session_code)",
            "El código de sesión debe ser único. Ya existe otra sesión con este código.",
        ),
    ]

    # VALIDACIONES DE NEGOCIO - FASE 1

    @api.constrains('teacher_id')
    def _check_teacher_required(self):
        """
        R32: Docente obligatorio.
        Valida que toda sesión tenga un docente asignado.
        """
        for record in self:
            if not record.teacher_id:
                raise ValidationError(
                    _("La sesión debe tener un docente asignado. "
                      "No se puede guardar sin asignar un profesor responsable.")
                )

    @api.constrains('delivery_mode', 'subcampus_id')
    def _check_subcampus_requirement(self):
        """
        RF2: Aula obligatoria para modalidad Presencial o Híbrida.
        NO aplica para modalidad Virtual ni para agendas con sede virtual.
        """
        for record in self:
            # Si es modalidad virtual, no requiere aula
            if record.delivery_mode == 'virtual':
                continue
            # Si la agenda tiene sede virtual (verificar directamente), no requiere aula
            if record.agenda_id and record.agenda_id.campus_id:
                campus = record.agenda_id.campus_id
                if campus.is_virtual_sede or campus.campus_type == 'online':
                    continue
            # Para presencial o híbrida, requiere aula
            if record.delivery_mode in ['presential', 'hybrid']:
                if not record.subcampus_id:
                    mode_label = dict(record._fields['delivery_mode'].selection).get(record.delivery_mode)
                    raise ValidationError(
                        _("Para la modalidad %(mode)s es obligatorio asignar un aula.\n"
                          "Por favor seleccione una sede/aula antes de guardar.") % {'mode': mode_label}
                    )

    @api.constrains('delivery_mode', 'meeting_link', 'teacher_meeting_link')
    def _check_meeting_link_requirement(self):
        """
        RF4: Meeting URL obligatorio para modalidad Virtual o Híbrida.
        Acepta meeting_link directo O teacher_meeting_link del docente.
        """
        for record in self:
            if record.delivery_mode in ['virtual', 'hybrid']:
                # Verificar si existe meeting_link directo O teacher_meeting_link del docente
                has_meeting_link = (record.meeting_link and record.meeting_link.strip()) or \
                                   (record.teacher_meeting_link and record.teacher_meeting_link.strip())
                
                if not has_meeting_link:
                    mode_label = dict(record._fields['delivery_mode'].selection).get(record.delivery_mode)
                    raise ValidationError(
                        _("Para la modalidad %(mode)s es obligatorio proporcionar un enlace de reunión (Meeting URL).\n"
                          "Por favor ingrese el enlace antes de guardar.") % {'mode': mode_label}
                    )

    @api.constrains('audience_unit_from', 'audience_unit_to')
    def _check_audience_unit_range(self):
        """
        RF5: Validación de rango de unidades.
        Unidad_Desde debe ser menor o igual a Unidad_Hasta.
        """
        for record in self:
            if record.audience_unit_from and record.audience_unit_to:
                if record.audience_unit_from > record.audience_unit_to:
                    raise ValidationError(
                        _("El rango de unidades no es válido.\n"
                          "La unidad desde (%(unit_from)s) no puede ser mayor que la unidad hasta (%(unit_to)s).") % {
                              'unit_from': record.audience_unit_from,
                              'unit_to': record.audience_unit_to
                          }
                    )

    # MÉTODOS AUXILIARES

    def _get_default_delivery_mode(self):
        """
        Retorna la modalidad por defecto basada en el tipo de sede de la agenda.
        Si la agenda tiene una sede virtual, retorna 'virtual', de lo contrario 'presential'.
        """
        agenda_id = self.env.context.get('default_agenda_id')
        if agenda_id:
            agenda = self.env['benglish.academic.agenda'].browse(agenda_id)
            if agenda.campus_id and (agenda.campus_id.is_virtual_sede or agenda.campus_id.campus_type == 'online'):
                return 'virtual'
        return 'presential'

    @api.depends('agenda_id', 'agenda_id.campus_id', 'agenda_id.campus_id.is_virtual_sede', 'agenda_id.campus_id.campus_type')
    def _compute_is_virtual_agenda(self):
        """
        Detecta si la agenda tiene una sede virtual.
        Una sede es virtual si is_virtual_sede=True o campus_type='online'.
        """
        for record in self:
            campus = record.agenda_id.campus_id if record.agenda_id else False
            if campus:
                record.is_virtual_agenda = campus.is_virtual_sede or campus.campus_type == 'online'
            else:
                record.is_virtual_agenda = False

    @api.onchange('agenda_id')
    def _onchange_agenda_id_delivery_mode(self):
        """
        Cuando cambia la agenda, ajustar la modalidad si es sede virtual.
        """
        if self.agenda_id and self.agenda_id.campus_id:
            campus = self.agenda_id.campus_id
            if campus.is_virtual_sede or campus.campus_type == 'online':
                self.delivery_mode = 'virtual'
                # También establecer capacidad por defecto para virtual
                if not self.max_capacity:
                    self.max_capacity = 15

    @api.depends('delivery_mode', 'subcampus_id', 'subcampus_id.capacity', 'max_capacity_virtual')
    def _compute_max_capacity(self):
        """
        R3: Cálculo automático de Capacidad Máxima según modalidad.
        
        Reglas:
        - Presencial: Capacidad = Capacidad del Aula (pero usuario puede reducir)
        - Virtual: Capacidad = 15 por defecto (editable)
        - Híbrida: Capacidad = Presencial + Virtual
        
        NOTA: Como es readonly=False, el usuario puede editar el valor después.
        Este método solo establece el valor inicial o cuando cambian las dependencias.
        """
        for record in self:
            # Si ya tiene un valor guardado en BD y no estamos en modo de creación, mantenerlo
            # (el usuario puede haberlo editado)
            if record.id and record.max_capacity and record.max_capacity > 0:
                continue
                
            if record.delivery_mode == 'presential':
                # Modalidad Presencial: capacidad del aula por defecto
                if record.subcampus_id and record.subcampus_id.capacity:
                    record.max_capacity = record.subcampus_id.capacity
                else:
                    # Fallback si no hay aula asignada aún
                    record.max_capacity = 15

            elif record.delivery_mode == 'virtual':
                # Modalidad Virtual: capacidad por defecto 15
                record.max_capacity = 15

            elif record.delivery_mode == 'hybrid':
                # Modalidad Híbrida: capacidad = presencial + virtual
                aula_capacity = record.subcampus_id.capacity if record.subcampus_id else 0
                if not record.max_capacity_presential:
                    record.max_capacity_presential = aula_capacity
                virtual_capacity = record.max_capacity_virtual or 0
                record.max_capacity = (record.max_capacity_presential or 0) + virtual_capacity

            else:
                # Estado por defecto
                record.max_capacity = 15

    # NOTA: El método _compute_is_oral_test_template fue eliminado
    # ya que dependía del modelo benglish.agenda.template que ya no existe

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

            # Usar subject_id directamente (template_id fue eliminado)
            if record.subject_id:
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

    @api.depends("subject_id.alias", "subject_id.name", "elective_pool_id.alias", "elective_pool_id.name", "is_elective_session")
    def _compute_student_alias(self):
        for record in self:
            # Para sesiones electivas, usar el alias del pool de electivas
            if record.is_elective_session and record.elective_pool_id:
                record.student_alias = record.elective_pool_id.alias or record.elective_pool_id.name
            # Para asignaturas regulares, usar el alias de la asignatura
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

    # ==========================================
    # COMPUTED FIELDS - PUBLICACIONES Y POOLS (FASE 2)
    # ==========================================

    # TODO: Descomentar cuando se cree el modelo benglish.session.publication
    # @api.depends("publication_ids")
    # def _compute_publication_count(self):
    #     """Cuenta el número de asignaturas a las que se publica esta sesión."""
    #     for record in self:
    #         record.publication_count = len(record.publication_ids)

    # @api.depends("publication_ids", "publication_ids.subject_id")
    # def _compute_published_subjects(self):
    #     """Obtiene las asignaturas a las que se oferta esta sesión."""
    #     for record in self:
    #         if record.publication_ids:
    #             record.published_subject_ids = record.publication_ids.mapped("subject_id")
    #         else:
    #             record.published_subject_ids = False

    @api.depends("elective_pool_ids")
    def _compute_pool_count(self):
        """Cuenta el número de pools a los que pertenece esta sesión."""
        for record in self:
            record.pool_count = len(record.elective_pool_ids)

    # TODO: Descomentar cuando se cree el modelo benglish.session.publication
    # @api.depends("publication_ids")
    # def _compute_is_paired_session(self):
    #     """Detecta si esta sesión está publicada para múltiples asignaturas (par)."""
    #     for record in self:
    #         record.is_paired_session = len(record.publication_ids) > 1

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
        # Si es agenda virtual, forzar modalidad virtual
        if self.is_virtual_agenda and self.delivery_mode != "virtual":
            self.delivery_mode = "virtual"
            return
            
        if self.delivery_mode == "virtual":
            # Modalidad virtual no requiere aula.
            self.subcampus_id = False
            # Capacidad por defecto 15 si no está definida
            if not self.max_capacity:
                self.max_capacity = 15

        # Si cambia de híbrida a otra modalidad, recalcular `max_capacity`
        if self.delivery_mode != "hybrid":
            # Para presencial, `onchange_subcampus_id` ya completa la capacidad.
            if self.delivery_mode == "presential" and self.subcampus_id and self.subcampus_id.capacity:
                self.max_capacity = self.subcampus_id.capacity
            elif self.delivery_mode == "virtual":
                # Mantener capacidad si ya tiene valor, sino 15
                if not self.max_capacity:
                    self.max_capacity = 15
            else:
                # Como fallback, sumar presential+virtual si existen
                if self.max_capacity_presential or self.max_capacity_virtual:
                    self.max_capacity = (self.max_capacity_presential or 0) + (self.max_capacity_virtual or 0)

        # Si cambia a híbrida, asegurar que la capacidad presencial refleje la del aula
        elif self.delivery_mode == "hybrid":
            if self.subcampus_id and self.subcampus_id.capacity:
                self.max_capacity_presential = self.subcampus_id.capacity
            # total se compone de aula + cupo virtual (que debe ser definido por el usuario)
            self.max_capacity = (self.max_capacity_presential or 0) + (self.max_capacity_virtual or 0)

    @api.onchange("subcampus_id")
    def _onchange_subcampus_id(self):
        """Autocompleta la capacidad máxima con la capacidad del aula seleccionada."""
        if self.subcampus_id and self.subcampus_id.capacity:
            if self.delivery_mode == "hybrid":
                # Para híbrida, inicializar capacidad presencial con capacidad del aula
                # PERO el usuario puede reducirla después si lo desea.
                if not self.max_capacity_presential:
                    self.max_capacity_presential = self.subcampus_id.capacity
                # Validar que no exceda capacidad del aula
                elif self.max_capacity_presential > self.subcampus_id.capacity:
                    self.max_capacity_presential = self.subcampus_id.capacity
                # No modificar `max_capacity_virtual` automáticamente; el usuario lo define.
                self.max_capacity = (self.max_capacity_presential or 0) + (self.max_capacity_virtual or 0)
            else:
                self.max_capacity = self.subcampus_id.capacity

    @api.onchange("max_capacity_presential", "max_capacity_virtual")
    def _onchange_hybrid_capacities(self):
        """Actualiza max_capacity cuando cambian las capacidades híbridas."""
        if self.delivery_mode == "hybrid":
            # Validar que presencial no exceda capacidad del aula
            if self.subcampus_id and self.subcampus_id.capacity:
                if self.max_capacity_presential and self.max_capacity_presential > self.subcampus_id.capacity:
                    self.max_capacity_presential = self.subcampus_id.capacity
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
                # Modalidad virtual: usar capacidad definida (ahora no es infinita)
                # El usuario puede definir la capacidad que desee
                record.available_spots = max(0, (record.max_capacity or 15) - enrolled)
                record.is_full = enrolled >= (record.max_capacity or 15)
                record.occupancy_rate = (
                    (enrolled / (record.max_capacity or 15) * 100.0) if record.max_capacity else 0
                )

    # VALIDACIONES

    @api.constrains("delivery_mode", "subcampus_id")
    def _check_classroom_required(self):
        """Valida que el aula sea obligatoria para modalidad presencial o híbrida.
        NO aplica para modalidad Virtual ni para agendas con sede virtual."""
        for record in self:
            # Si es modalidad virtual, no requiere aula
            if record.delivery_mode == 'virtual':
                continue
            # Si la agenda tiene sede virtual (verificar directamente), no requiere aula
            if record.agenda_id and record.agenda_id.campus_id:
                campus = record.agenda_id.campus_id
                if campus.is_virtual_sede or campus.campus_type == 'online':
                    continue
            # Para presencial o híbrida, requiere aula
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
                # Presencial debe ser mayor a 0
                if not record.max_capacity_presential or record.max_capacity_presential <= 0:
                    raise ValidationError(
                        _("La capacidad presencial debe ser mayor a 0 para modalidad híbrida.")
                    )
                # Presencial no debe exceder la capacidad del aula (pero puede ser menor)
                if record.subcampus_id and record.subcampus_id.capacity:
                    if record.max_capacity_presential > record.subcampus_id.capacity:
                        raise ValidationError(
                            _(
                                "En modalidad híbrida, la capacidad presencial no puede exceder la capacidad del aula (%(cap)s)."
                            ) % {"cap": record.subcampus_id.capacity}
                        )
                if record.max_capacity_virtual is None or record.max_capacity_virtual < 0:
                    raise ValidationError(
                        _("La capacidad virtual debe ser 0 o mayor para modalidad híbrida.")
                    )
            elif record.delivery_mode == 'virtual':
                # Virtual: debe tener capacidad > 0
                if not record.max_capacity or record.max_capacity <= 0:
                    record.max_capacity = 15  # Valor por defecto
            else:
                # Presencial u otros: requerir capacidad > 0, pero no forzar igualdad con aula
                if not record.max_capacity or record.max_capacity <= 0:
                    raise ValidationError(
                        _("La capacidad máxima debe ser mayor a 0.")
                    )
                # Para presencial, validar que no exceda capacidad del aula
                if record.delivery_mode == 'presential' and record.subcampus_id and record.subcampus_id.capacity:
                    if record.max_capacity > record.subcampus_id.capacity:
                        raise ValidationError(
                            _(
                                "Para modalidad presencial la capacidad no puede exceder la capacidad del aula (%(cap)s)."
                            ) % {"cap": record.subcampus_id.capacity}
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
            # Aplicar validación estricta solo para modalidad presencial
            if record.subcampus_id and record.delivery_mode == 'presential':
                if not record.max_capacity or record.max_capacity != record.subcampus_id.capacity:
                    raise ValidationError(
                        _(
                            "Para modalidad presencial, la capacidad de la sesión (%(session_capacity)s) debe ser exactamente "
                            "la capacidad del aula '%(room)s' (%(room_capacity)s estudiantes)."
                        )
                        % {
                            "session_capacity": record.max_capacity,
                            "room": record.subcampus_id.name,
                            "room_capacity": record.subcampus_id.capacity,
                        }
                    )

    # NOTA: El constraint _check_template_program fue eliminado
    # ya que template_id ya no existe

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

    # NOTA: El método _onchange_template_id fue eliminado
    # ya que template_id ya no existe

    @api.onchange("session_type")
    def _onchange_session_type(self):
        """
        Al cambiar el tipo de sesión:
        - Si NO es 'elective': limpiar elective_pool_id
        """
        if self.session_type != "elective":
            self.elective_pool_id = False

    # NOTA: El onchange de elective_pool_id se encuentra en la sección de MÉTODOS ONCHANGE
    # (línea ~278) - Este bloque fue eliminado para evitar duplicación

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

    # NOTA: El segundo método create con lógica de template fue eliminado
    # La lógica principal está en el método create anterior

    def write(self, vals):
        """Validaciones al actualizar."""
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

            # Validar campos obligatorios según el tipo de sesión
            missing_fields = []
            
            # Validar Asignatura o Pool de Electivas según el tipo
            if record.is_elective_session:
                # Para sesiones electivas, se requiere elective_pool_id
                if not record.elective_pool_id:
                    missing_fields.append("- Electivas (Pool)")
            else:
                # Para sesiones regulares, se requiere subject_id
                if not record.subject_id:
                    missing_fields.append("- Asignatura")
            
            # Validar fecha y hora (siempre requeridos)
            if not record.date:
                missing_fields.append("- Fecha")
            if not record.time_start or not record.time_end:
                missing_fields.append("- Hora inicio/fin")
            
            # Validar Aula solo si NO es modalidad virtual
            if record.delivery_mode != 'virtual' and not record.subcampus_id:
                missing_fields.append("- Aula")
            
            if missing_fields:
                raise UserError(
                    _(
                        "Complete todos los campos obligatorios antes de iniciar:\n%s"
                    ) % "\n".join(missing_fields)
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
        # Modalidad virtual: sin límite (si está publicada, puede inscribirse)
        if self.delivery_mode == 'virtual':
            return bool(self.is_published)

        return bool(self.is_published and not self.is_full and (self.available_spots or 0) > 0)

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
        """
        NOTA: Este método fue simplificado después de eliminar el modelo benglish.agenda.template.
        Ahora simplemente retorna el subject_id de la sesión ya que no hay lógica de template.
        """
        self.ensure_one()
        return self.subject_id or False

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

    def _resolve_elective_pool_subject(self, student, check_completed=True, raise_on_error=True):
        """
        Resuelve la asignatura efectiva para un estudiante desde un Pool de Electivas.
        
        NOTA: El modelo ha cambiado - ahora el Pool de Electivas ES la asignatura electiva.
        Ya no contiene subject_ids. Este método simplemente verifica que haya un pool
        configurado y activo.
        
        Args:
            student: Estudiante para quien resolver la asignatura (usado para logging)
            check_completed: No aplica en la nueva lógica
            raise_on_error: Si levantar error cuando no hay pool (default: True)
        
        Returns:
            benglish.elective.pool: El pool de electivas configurado, o False si no hay
        
        Raises:
            UserError: Si no hay pool configurado y raise_on_error=True
        """
        self.ensure_one()
        
        pool = self.elective_pool_id
        if not pool:
            _logger.warning(
                "[ELECTIVE-POOL] Sesión %s (ID: %s) no tiene pool de electivas configurado.",
                self.display_name, self.id
            )
            if raise_on_error:
                raise UserError(
                    _("Esta sesión electiva no tiene un pool de electivas configurado.\n\n"
                      "Contacte al administrador para configurar el pool.")
                )
            return False
        
        if not pool.active:
            _logger.warning(
                "[ELECTIVE-POOL] Pool %s (ID: %s) está inactivo.",
                pool.display_name, pool.id
            )
            if raise_on_error:
                raise UserError(
                    _("El pool de electivas '%s' está inactivo.\n\n"
                      "Contacte al administrador.")
                    % pool.display_name
                )
            return False
        
        _logger.info(
            "✅ [ELECTIVE-POOL] Pool de electivas para estudiante %s: '%s' (ID: %s)",
            student.name if student else "N/A",
            pool.display_name,
            pool.id
        )
        
        return pool

    def resolve_effective_subject(self, student, check_completed=True, raise_on_error=True, check_prereq=True):
        """
        Resuelve la asignatura efectiva para un estudiante en esta sesión.
        
        NOTA: Simplificado después de eliminar el modelo benglish.agenda.template.
        Ahora retorna directamente subject_id para sesiones regulares.
        
        ELECTIVE POOLS (HU-POOL):
        - Si la sesión tiene elective_pool_id, el pool ES la asignatura electiva
        """
        self.ensure_one()

        if not student:
            if raise_on_error:
                raise UserError(_("Estudiante inválido para homologación."))
            return False

        # ═══════════════════════════════════════════════════════════════════════════════
        # LÓGICA: Sesiones con ELECTIVE POOL
        # ═══════════════════════════════════════════════════════════════════════════════
        if self.session_type == 'elective' and self.elective_pool_id:
            return self._resolve_elective_pool_subject(
                student, 
                check_completed=check_completed, 
                raise_on_error=raise_on_error
            )

        # Sesiones regulares: usar subject_id directo (lógica de template eliminada)
        return self.subject_id

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

    def action_view_publications(self):
        """Método temporal - La funcionalidad de publicaciones fue deshabilitada."""
        raise UserError(
            _("La funcionalidad de publicaciones ha sido deshabilitada temporalmente. "
              "Este módulo será implementado en una fase posterior.")
        )

    def action_view_elective_pools(self):
        """Acción para ver pools de electivas asociados (FASE 2)."""
        self.ensure_one()
        return {
            "name": _("Pools de Electivas - %s") % self.display_name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.elective.pool",
            "view_mode": "list,form",
            "domain": [("id", "in", self.elective_pool_ids.ids)],
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

    # ==========================================
    # RESOLUCIÓN DE ASIGNATURA EFECTIVA (POOL DE ELECTIVAS)
    # ==========================================

    def _get_completed_subject_ids(self, student):
        """
        Obtiene los IDs de asignaturas que el estudiante ya completó (attended).
        
        Args:
            student: Registro del estudiante (benglish.student)
            
        Returns:
            set: Conjunto de IDs de asignaturas completadas
        """
        if not student:
            return set()
        
        History = self.env['benglish.academic.history'].sudo()
        completed_history = History.search([
            ('student_id', '=', student.id),
            ('attendance_status', '=', 'attended'),
            ('subject_id', '!=', False)
        ])
        
        return set(completed_history.mapped('subject_id').ids)

    # NOTA: El método _resolve_elective_pool_subject ya está definido arriba (línea ~2632)
    # Este duplicado fue eliminado para evitar conflictos.

    def resolve_effective_subject(self, student, check_completed=True, raise_on_error=True, check_prereq=True):
        """
        Resuelve la asignatura efectiva para un estudiante en esta sesión.
        
        LÓGICA CORRECTA REFACTORIZADA:
        - El slot asignado depende EXCLUSIVAMENTE del progreso del estudiante
        - NO depende del skill_number de la plantilla
        - Las skills son REPETIBLES: pueden tomarse múltiples veces
        - Cada skill completa el SIGUIENTE SLOT disponible (1, 2, 3 o 4)
        
        ELECTIVE POOLS (HU-POOL):
        - Si la sesión tiene elective_pool_id, el pool ES la asignatura electiva
        
        Args:
            student: Estudiante para quien resolver la asignatura
            check_completed: Si verificar asignaturas ya completadas
            raise_on_error: Si levantar error cuando hay problemas
            check_prereq: Si verificar prerrequisitos
            
        Returns:
            benglish.subject o benglish.elective.pool: La asignatura efectiva para el estudiante
        """
        self.ensure_one()

        if not student:
            if raise_on_error:
                raise UserError(_("Estudiante inválido para homologación."))
            return False

        # ═══════════════════════════════════════════════════════════════════════════════
        # NUEVA LÓGICA: Sesiones con ELECTIVE POOL
        # ═══════════════════════════════════════════════════════════════════════════════
        if self.session_type == 'elective' and self.elective_pool_id:
            return self._resolve_elective_pool_subject(
                student, 
                check_completed=check_completed, 
                raise_on_error=raise_on_error
            )

        # ═══════════════════════════════════════════════════════════════════════════════
        # Sesiones legacy: usar subject_id directo
        # ═══════════════════════════════════════════════════════════════════════════════
        subject = self.subject_id
        
        if not subject:
            _logger.warning(
                "[RESOLVE] Sesión %s sin subject_id configurado",
                self.id
            )
            if raise_on_error:
                raise UserError(_("Esta sesión no tiene asignatura configurada."))
            return False
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # VALIDACIÓN DE ASIGNATURA COMPLETADA
        # ═══════════════════════════════════════════════════════════════════════════════
        if check_completed:
            History = self.env['benglish.academic.history'].sudo()
            
            # Verificar si ya completó esta asignatura
            has_attended = History.search_count([
                ('student_id', '=', student.id),
                ('subject_id', '=', subject.id),
                ('attendance_status', '=', 'attended')
            ])
            
            if has_attended > 0:
                # B-Checks permiten re-agendar si tuvo 'absent'
                is_bcheck = subject.subject_category == 'bcheck'
                
                if not is_bcheck:
                    _logger.info(
                        "[RESOLVE] Estudiante %s ya completó la asignatura %s",
                        student.name, subject.name
                    )
                    if raise_on_error:
                        raise UserError(
                            _("Ya completaste esta asignatura (%s). "
                              "No puedes programar la misma clase dos veces.")
                            % subject.name
                        )
                    return False
        
        return subject
