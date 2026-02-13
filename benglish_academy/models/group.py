# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Group(models.Model):
    """
    Modelo para gestionar Grupos de Estudiantes.
    Un grupo representa un conjunto de estudiantes que toman clases juntos.
    Se asocia a una sede/subsede, un curso específico y un docente.
    """
    _name = 'benglish.group'
    _description = 'Grupo de Estudiantes'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'name'

    # Campos básicos
    name = fields.Char(
        string='Nombre del Grupo',
        required=True,
        tracking=True,
        help='Nombre identificador del grupo (ej: Grupo A - Básico 1)'
    )
    code = fields.Char(
        string='Código',
        required=True,
        copy=False,
        tracking=True,
        help='Código único identificador del grupo'
    )
    
    # Relaciones académicas
    course_id = fields.Many2one(
        comodel_name='benglish.course',
        string='Curso',
        ondelete='restrict',
        tracking=True,
        help='Curso al que pertenece este grupo'
    )
    subject_id = fields.Many2one(
        comodel_name='benglish.subject',
        string='Asignatura',
        required=True,
        ondelete='restrict',
        tracking=True,
        help='Asignatura que cursa este grupo'
    )
    class_type_id = fields.Many2one(
        comodel_name='benglish.class.type',
        string='Tipo de Clase',
        help='Tipo de clase (B check, B skills, Oral test, etc.)'
    )
    subject_type_id = fields.Many2one(
        comodel_name='benglish.subject.type',
        string='Tipo de Asignatura',
        related='subject_id.subject_type_id',
        store=True,
        readonly=True,
        help='Tipo de asignatura del grupo'
    )
    
    # Relaciones de ubicación
    campus_id = fields.Many2one(
        comodel_name='benglish.campus',
        string='Sede',
        required=True,
        ondelete='restrict',
        tracking=True,
        help='Sede donde se dictan las clases de este grupo'
    )
    subcampus_id = fields.Many2one(
        comodel_name='benglish.subcampus',
        string='Aula',
        domain="[('campus_id', '=', campus_id), ('active', '=', True), ('is_available', '=', True)]",
        tracking=True,
        help='Aula específica donde se dictan las clases'
    )
    
    # Modalidad de clase
    delivery_mode = fields.Selection(
        selection=[
            ('presential', 'Presencial'),
            ('virtual', 'Virtual'),
            ('hybrid', 'Híbrido (Presencial + Virtual)'),
        ],
        string='Modalidad',
        required=True,
        default='presential',
        compute='_compute_delivery_mode',
        store=True,
        readonly=False,
        help='Modalidad en la que se dictan las clases de este grupo'
    )
    
    # Campos para clases virtuales/híbridas
    meeting_link = fields.Char(
        string='Enlace de Videollamada',
        compute='_compute_meeting_link',
        store=True,
        readonly=False,
        help='Enlace para las clases virtuales (heredado del coach o definido manualmente)'
    )
    meeting_platform = fields.Selection(
        selection=[
            ('google_meet', 'Google Meet'),
            ('zoom', 'Zoom'),
            ('teams', 'Microsoft Teams'),
            ('jitsi', 'Jitsi Meet'),
            ('other', 'Otra plataforma'),
        ],
        string='Plataforma de Videoconferencia',
        help='Plataforma utilizada para las clases virtuales'
    )
    
    # Control de cupos (modificable solo por admin)
    max_students_override = fields.Integer(
        string='Cantidad de Estudiantes (Admin)',
        help='Permite al administrador ajustar la cantidad de estudiantes manualmente'
    )
    show_available_seats_to_students = fields.Boolean(
        string='Mostrar Cupos a Estudiantes',
        default=False,
        help='Si está marcado, los estudiantes pueden ver los cupos disponibles'
    )
    
    # Replicación de horario
    replicate_days = fields.Selection(
        selection=[
            ('no', 'No Replicar'),
            ('daily', 'Diariamente'),
            ('weekly', 'Semanalmente'),
            ('custom', 'Días Personalizados'),
        ],
        string='Replicar Clase',
        default='no',
        help='Permite replicar la clase en múltiples días'
    )
    replicate_until_date = fields.Date(
        string='Replicar Hasta',
        help='Fecha hasta la cual se replicará la clase'
    )
    
    # Coach / Docente
    coach_id = fields.Many2one(
        comodel_name='benglish.coach',
        string='Coach Asignado',
        tracking=True,
        help='Coach que dicta este grupo (el link se hereda automáticamente)'
    )
    teacher_id = fields.Many2one(
        comodel_name='res.users',
        string='Docente (Usuario)',
        domain="[('share', '=', False)]",
        tracking=True,
        help='Usuario docente (opcional, puede vincularse al coach)'
    )
    
    # Matrículas
    enrollment_ids = fields.One2many(
        comodel_name='benglish.enrollment',
        inverse_name='group_id',
        string='Matrículas',
        help='Estudiantes matriculados en este grupo'
    )
    enrollment_count = fields.Integer(
        string='Total Matrículas',
        compute='_compute_enrollment_count',
        store=True,
        help='Número total de matrículas en este grupo'
    )
    active_enrollment_count = fields.Integer(
        string='Matrículas Activas',
        compute='_compute_enrollment_count',
        store=True,
        help='Número de matrículas activas (enrolled/in_progress)'
    )
    
    # Capacidad y matrícula
    presential_capacity = fields.Integer(
        string='Capacidad Presencial',
        default=25,
        help='Número máximo de estudiantes presenciales'
    )
    virtual_capacity = fields.Integer(
        string='Capacidad Virtual',
        default=0,
        help='Número máximo de estudiantes remotos (solo para modalidad híbrida/virtual)'
    )
    total_capacity = fields.Integer(
        string='Capacidad Total',
        compute='_compute_total_capacity',
        store=True,
        help='Capacidad total (presencial + virtual)'
    )
    current_students = fields.Integer(
        string='Estudiantes Actuales',
        compute='_compute_current_students',
        store=True,
        help='Número actual de estudiantes matriculados'
    )
    current_presential = fields.Integer(
        string='Estudiantes Presenciales',
        default=0,
        help='Número actual de estudiantes presenciales'
    )
    current_virtual = fields.Integer(
        string='Estudiantes Remotos',
        default=0,
        help='Número actual de estudiantes remotos (solo modalidad híbrida/virtual)'
    )
    available_seats = fields.Integer(
        string='Cupos Disponibles',
        compute='_compute_available_seats',
        store=True,
        help='Número de cupos disponibles'
    )
    available_presential_seats = fields.Integer(
        string='Cupos Presenciales Disponibles',
        compute='_compute_available_presential_seats',
        store=True,
        help='Número de cupos presenciales disponibles'
    )
    available_virtual_seats = fields.Integer(
        string='Cupos Virtuales Disponibles',
        compute='_compute_available_virtual_seats',
        store=True,
        help='Número de cupos virtuales disponibles'
    )

    # DESHABILITADO: Ya no se usa group_id en class.session
    # # Sesiones programadas 
    # session_ids = fields.One2many(
    #     comodel_name='benglish.class.session',
    #     inverse_name='group_id',
    #     string='Sesiones Programadas'
    # )
    # session_count = fields.Integer(
    #     string='Sesiones activas',
    #     compute='_compute_session_metrics',
    #     store=True
    # )
    # next_session_datetime = fields.Datetime(
    #     string='Próxima sesión',
    #     compute='_compute_session_metrics',
    #     store=True
    # )
    
    # Horario
    schedule = fields.Text(
        string='Horario',
        help='Descripción del horario de clases (ej: Lun-Mie-Vie 8:00-10:00)'
    )
    start_date = fields.Date(
        string='Fecha de Inicio',
        tracking=True,
        help='Fecha de inicio del grupo'
    )
    end_date = fields.Date(
        string='Fecha de Finalización',
        tracking=True,
        help='Fecha de finalización del grupo'
    )
    
    # Estado
    active = fields.Boolean(
        string='Activo',
        default=True,
        tracking=True,
        help='Si está inactivo, el grupo no estará disponible'
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('confirmed', 'Confirmado'),
            ('in_progress', 'En Progreso'),
            ('finished', 'Finalizado'),
            ('cancelled', 'Cancelado'),
        ],
        string='Estado',
        default='draft',
        required=True,
        tracking=True,
        help='Estado actual del grupo'
    )
    
    # Notas
    notes = fields.Text(
        string='Notas',
        help='Notas adicionales sobre el grupo'
    )
    
    # Restricciones SQL
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'El código del grupo debe ser único.'),
        ('presential_capacity_positive', 'CHECK(presential_capacity >= 0)', 'La capacidad presencial no puede ser negativa.'),
        ('virtual_capacity_positive', 'CHECK(virtual_capacity >= 0)', 'La capacidad virtual no puede ser negativa.'),
    ]
    
    @api.depends('subcampus_id.modality', 'course_id.delivery_mode')
    def _compute_delivery_mode(self):
        """Calcula la modalidad basada en el aula o curso"""
        for record in self:
            if record.subcampus_id and record.subcampus_id.modality:
                record.delivery_mode = record.subcampus_id.modality
            elif record.course_id and record.course_id.delivery_mode:
                record.delivery_mode = record.course_id.delivery_mode
            elif not record.delivery_mode:
                record.delivery_mode = 'presential'
    
    @api.depends('coach_id', 'coach_id.meeting_link')
    def _compute_meeting_link(self):
        """Hereda el link del coach automáticamente"""
        for record in self:
            if not record.meeting_link:
                # Hereda del coach asignado
                if record.coach_id and record.coach_id.meeting_link:
                    record.meeting_link = record.coach_id.meeting_link
                    record.meeting_platform = record.coach_id.meeting_platform
    
    @api.depends('delivery_mode', 'presential_capacity', 'virtual_capacity')
    def _compute_total_capacity(self):
        """Calcula la capacidad total"""
        for record in self:
            if record.delivery_mode == 'presential':
                record.total_capacity = record.presential_capacity
            elif record.delivery_mode == 'virtual':
                record.total_capacity = record.virtual_capacity
            else:  # hybrid
                record.total_capacity = record.presential_capacity + record.virtual_capacity
    
    @api.depends('presential_capacity', 'current_presential')
    def _compute_available_presential_seats(self):
        """Calcula los cupos presenciales disponibles"""
        for record in self:
            record.available_presential_seats = record.presential_capacity - record.current_presential
    
    @api.depends('virtual_capacity', 'current_virtual')
    def _compute_available_virtual_seats(self):
        """Calcula los cupos virtuales disponibles"""
        for record in self:
            record.available_virtual_seats = record.virtual_capacity - record.current_virtual
    
    @api.depends('total_capacity', 'current_students')
    def _compute_available_seats(self):
        """Calcula los cupos disponibles totales"""
        for record in self:
            record.available_seats = record.total_capacity - record.current_students
    
    @api.depends('current_presential', 'current_virtual')
    def _compute_current_students(self):
        """Calcula el número total de estudiantes actuales"""
        for record in self:
            record.current_students = record.current_presential + record.current_virtual
    
    @api.depends('enrollment_ids', 'enrollment_ids.state')
    def _compute_enrollment_count(self):
        """Calcula el número de matrículas totales y activas"""
        for record in self:
            record.enrollment_count = len(record.enrollment_ids)
            record.active_enrollment_count = len(record.enrollment_ids.filtered(
                lambda e: e.state in ['enrolled', 'in_progress']
            ))

    # DESHABILITADO: Ya no se usa group_id en class.session
    # @api.depends('session_ids.state', 'session_ids.start_datetime')
    # def _compute_session_metrics(self):
    #     """Calcula contadores y próxima sesión programada."""
    #     now = fields.Datetime.now()
    #     for record in self:
    #         active_sessions = record.session_ids.filtered(lambda s: s.state != 'cancelled')
    #         record.session_count = len(active_sessions)
    #         upcoming = active_sessions.filtered(lambda s: s.start_datetime >= now)
    #         if upcoming:
    #             record.next_session_datetime = min(upcoming.mapped('start_datetime'))
    #         else:
    #             record.next_session_datetime = False
    
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Valida que la fecha de finalización sea posterior a la de inicio"""
        for record in self:
            if record.start_date and record.end_date and record.end_date < record.start_date:
                raise ValidationError(_(
                    'La fecha de finalización debe ser posterior a la fecha de inicio.'
                ))
    
    @api.constrains('delivery_mode', 'meeting_link', 'subcampus_id', 'virtual_capacity', 'presential_capacity')
    def _check_delivery_mode_requirements(self):
        """Valida los requisitos según la modalidad"""
        for record in self:
            # Validar que grupos virtuales/híbridos tengan enlace de videollamada
            if record.delivery_mode in ('virtual', 'hybrid') and not record.meeting_link:
                raise ValidationError(_(
                    'Los grupos virtuales o híbridos deben tener un enlace de videollamada configurado.'
                ))
            
            # Validar que grupos presenciales/híbridos tengan aula asignada
            if record.delivery_mode in ('presential', 'hybrid') and not record.subcampus_id:
                raise ValidationError(_(
                    'Los grupos presenciales o híbridos deben tener un aula asignada.'
                ))
            
            # Validar capacidad virtual para virtuales/híbridos
            if record.delivery_mode in ('virtual', 'hybrid') and record.virtual_capacity <= 0:
                raise ValidationError(_(
                    'Los grupos virtuales o híbridos deben tener una capacidad virtual mayor a cero.'
                ))
            
            # Validar capacidad presencial para presenciales/híbridos
            if record.delivery_mode in ('presential', 'hybrid') and record.presential_capacity <= 0:
                raise ValidationError(_(
                    'Los grupos presenciales o híbridos deben tener una capacidad presencial mayor a cero.'
                ))
    
    @api.onchange('campus_id')
    def _onchange_campus_id(self):
        """Limpia el aula cuando se cambia la sede"""
        if self.campus_id:
            self.subcampus_id = False
    
    @api.onchange('delivery_mode')
    def _onchange_delivery_mode(self):
        """Ajusta campos según la modalidad"""
        if self.delivery_mode == 'presential':
            self.meeting_link = False
            self.meeting_platform = False
            self.virtual_capacity = 0
        elif self.delivery_mode == 'virtual':
            self.subcampus_id = False
            self.presential_capacity = 0
            if not self.virtual_capacity:
                self.virtual_capacity = 50  # Valor por defecto
        elif self.delivery_mode == 'hybrid':
            if not self.virtual_capacity:
                self.virtual_capacity = 30  # Valor por defecto para híbrido
    
    @api.onchange('subcampus_id')
    def _onchange_subcampus_id(self):
        """Sugiere la capacidad basada en el aula y copia datos de videoconferencia"""
        if self.subcampus_id:
            # Ajustar modalidad según el aula
            if self.subcampus_id.modality:
                self.delivery_mode = self.subcampus_id.modality
            
            # Ajustar capacidades según modalidad del aula
            if self.subcampus_id.modality == 'presential':
                if self.subcampus_id.capacity:
                    self.presential_capacity = min(self.subcampus_id.capacity, 30)
                self.virtual_capacity = 0
            elif self.subcampus_id.modality == 'virtual':
                self.presential_capacity = 0
                if self.subcampus_id.virtual_capacity:
                    self.virtual_capacity = self.subcampus_id.virtual_capacity
            elif self.subcampus_id.modality == 'hybrid':
                if self.subcampus_id.capacity:
                    self.presential_capacity = min(self.subcampus_id.capacity, 25)
                if self.subcampus_id.virtual_capacity:
                    self.virtual_capacity = self.subcampus_id.virtual_capacity
            
            # Copiar datos de videoconferencia del aula
            if self.subcampus_id.meeting_url:
                self.meeting_link = self.subcampus_id.meeting_url
            if self.subcampus_id.meeting_platform:
                self.meeting_platform = self.subcampus_id.meeting_platform
    
    def action_confirm(self):
        """Confirma el grupo"""
        self.write({'state': 'confirmed'})
    
    def action_start(self):
        """Inicia el grupo"""
        self.write({'state': 'in_progress'})
    
    def action_finish(self):
        """Finaliza el grupo"""
        self.write({'state': 'finished'})
    
    def action_cancel(self):
        """Cancela el grupo"""
        self.write({'state': 'cancelled'})
    
    def action_draft(self):
        """Vuelve el grupo a borrador"""
        self.write({'state': 'draft'})
    
    def action_view_sessions(self):
        """Abre la vista de sesiones del grupo (filtradas por asignatura y sede)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sesiones del Grupo: %s') % self.name,
            'res_model': 'benglish.class.session',
            'view_mode': 'calendar,list,form',
            'domain': [('subject_id', '=', self.subject_id.id), ('campus_id', '=', self.campus_id.id)],
            'context': {
                'default_subject_id': self.subject_id.id,
                'default_campus_id': self.campus_id.id,
                'default_subcampus_id': self.subcampus_id.id,
                'default_teacher_id': self.teacher_id.id,
                'default_coach_id': self.coach_id.id,
            },
        }
    
    def action_view_enrollments(self):
        """Abre la vista de matrículas del grupo (HU5)"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Matrículas del Grupo: %s') % self.name,
            'res_model': 'benglish.enrollment',
            'view_mode': 'list,form,kanban',
            'domain': [('group_id', '=', self.id)],
            'context': {
                'default_group_id': self.id,
                'default_subject_id': self.subject_id.id,
                'default_campus_id': self.campus_id.id,
                'default_delivery_mode': self.delivery_mode,
            },
        }

    def name_get(self):
        """Personaliza el nombre mostrado"""
        result = []
        for record in self:
            name = f"{record.name}"
            if record.subject_id:
                name = f"{record.name} - {record.subject_id.name}"
            result.append((record.id, name))
        return result
