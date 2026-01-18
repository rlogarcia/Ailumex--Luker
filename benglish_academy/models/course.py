# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Course(models.Model):
    """
    Modelo para gestionar Cursos Académicos.
    Un curso representa una instancia específica de una asignatura que se dicta
    en un periodo determinado, en una sede específica, impartido por un docente.
    Puede tener múltiples grupos.
    """
    _name = 'benglish.course'
    _description = 'Curso Académico'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, name'
    _rec_name = 'name'

    # Campos básicos
    name = fields.Char(
        string='Nombre del Curso',
        required=True,
        tracking=True,
        help='Nombre identificador del curso'
    )
    code = fields.Char(
        string='Código',
        required=True,
        copy=False,
        tracking=True,
        help='Código único identificador del curso'
    )
    
    # Relaciones académicas
    subject_id = fields.Many2one(
        comodel_name='benglish.subject',
        string='Asignatura',
        required=True,
        ondelete='restrict',
        tracking=True,
        help='Asignatura que se dicta en este curso'
    )
    level_id = fields.Many2one(
        comodel_name='benglish.level',
        string='Nivel',
        related='subject_id.level_id',
        store=True,
        readonly=True,
        help='Nivel académico del curso'
    )
    phase_id = fields.Many2one(
        comodel_name='benglish.phase',
        string='Fase',
        related='level_id.phase_id',
        store=True,
        readonly=True,
        help='Fase académica del curso'
    )
    
    # Relaciones de ubicación
    campus_id = fields.Many2one(
        comodel_name='benglish.campus',
        string='Sede',
        required=True,
        ondelete='restrict',
        tracking=True,
        help='Sede donde se dicta este curso'
    )
    subcampus_ids = fields.Many2many(
        comodel_name='benglish.subcampus',
        relation='benglish_course_subcampus_rel',
        column1='course_id',
        column2='subcampus_id',
        string='Aulas',
        domain="[('campus_id', '=', campus_id), ('active', '=', True)]",
        help='Aulas donde se dictan las clases de este curso'
    )
    
    # Modalidad de entrega
    delivery_mode = fields.Selection(
        selection=[
            ('presential', 'Presencial'),
            ('virtual', 'Virtual'),
            ('hybrid', 'Híbrido (Presencial + Virtual)'),
        ],
        string='Modalidad de Entrega',
        required=True,
        default='presential',
        tracking=True,
        help='Modalidad en la que se dicta el curso'
    )
    
    # Campos para cursos virtuales/híbridos
    meeting_link = fields.Char(
        string='Enlace de Videollamada',
        help='Enlace para las clases virtuales (Google Meet, Zoom, Teams, etc.)'
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
    
    # Capacidades por modalidad
    presential_capacity = fields.Integer(
        string='Capacidad Presencial',
        compute='_compute_presential_capacity',
        store=True,
        help='Capacidad total presencial del curso'
    )
    online_capacity = fields.Integer(
        string='Capacidad Virtual',
        default=0,
        help='Capacidad máxima de estudiantes remotos (solo para modalidad híbrida/virtual)'
    )
    
    # Docentes
    main_teacher_id = fields.Many2one(
        comodel_name='res.users',
        string='Docente Principal',
        required=True,
        domain="[('share', '=', False)]",
        tracking=True,
        help='Docente principal encargado del curso'
    )
    assistant_teacher_ids = fields.Many2many(
        comodel_name='res.users',
        relation='benglish_course_assistant_teacher_rel',
        column1='course_id',
        column2='user_id',
        string='Docentes Asistentes',
        domain="[('share', '=', False)]",
        help='Docentes asistentes o de apoyo'
    )
    
    # Grupos asociados
    group_ids = fields.One2many(
        comodel_name='benglish.group',
        inverse_name='course_id',
        string='Grupos',
        help='Grupos que pertenecen a este curso'
    )
    group_count = fields.Integer(
        string='Número de Grupos',
        compute='_compute_group_count',
        store=True,
        help='Cantidad de grupos en este curso'
    )
    # DESHABILITADO: Ya no se usa course_id en class.session
    # session_ids = fields.One2many(
    #     comodel_name='benglish.class.session',
    #     inverse_name='course_id',
    #     string='Sesiones Programadas',
    #     readonly=True
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
    
    # Fechas y duración
    start_date = fields.Date(
        string='Fecha de Inicio',
        required=True,
        tracking=True,
        help='Fecha de inicio del curso'
    )
    end_date = fields.Date(
        string='Fecha de Finalización',
        required=True,
        tracking=True,
        help='Fecha de finalización del curso'
    )
    duration_hours = fields.Integer(
        string='Duración (horas)',
        help='Duración total del curso en horas'
    )
    
    # Horario
    schedule = fields.Text(
        string='Horario',
        help='Descripción del horario de clases'
    )
    
    # Capacidad
    max_students = fields.Integer(
        string='Capacidad Total',
        compute='_compute_max_students',
        store=True,
        help='Capacidad total del curso (suma de todos los grupos)'
    )
    current_students = fields.Integer(
        string='Estudiantes Matriculados',
        compute='_compute_current_students',
        store=True,
        help='Total de estudiantes matriculados en el curso'
    )
    
    # Estado
    active = fields.Boolean(
        string='Activo',
        default=True,
        tracking=True,
        help='Si está inactivo, el curso no estará disponible'
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('scheduled', 'Programado'),
            ('in_progress', 'En Progreso'),
            ('finished', 'Finalizado'),
            ('cancelled', 'Cancelado'),
        ],
        string='Estado',
        default='draft',
        required=True,
        tracking=True,
        help='Estado actual del curso'
    )
    
    # Información adicional
    description = fields.Text(
        string='Descripción',
        help='Descripción del curso'
    )
    notes = fields.Text(
        string='Notas',
        help='Notas adicionales sobre el curso'
    )
    
    # Restricciones SQL
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'El código del curso debe ser único.'),
        ('duration_positive', 'CHECK(duration_hours > 0)', 'La duración debe ser mayor a 0.'),
    ]
    
    @api.depends('group_ids')
    def _compute_group_count(self):
        """Calcula el número de grupos"""
        for record in self:
            record.group_count = len(record.group_ids)

    # DESHABILITADO: Ya no se usa course_id en class.session
    # @api.depends('session_ids.state', 'session_ids.start_datetime')
    # def _compute_session_metrics(self):
    #     """Calcula contadores y próxima sesión del curso."""
    #     now = fields.Datetime.now()
    #     for record in self:
    #         active_sessions = record.session_ids.filtered(lambda s: s.state != 'cancelled')
    #         record.session_count = len(active_sessions)
    #         upcoming = active_sessions.filtered(lambda s: s.start_datetime >= now)
    #         record.next_session_datetime = min(upcoming.mapped('start_datetime')) if upcoming else False
    
    @api.depends('delivery_mode', 'group_ids.presential_capacity', 'online_capacity')
    def _compute_presential_capacity(self):
        """Calcula la capacidad presencial total del curso"""
        for record in self:
            if record.delivery_mode == 'virtual':
                record.presential_capacity = 0
            else:
                record.presential_capacity = sum(record.group_ids.mapped('presential_capacity'))
    
    @api.depends('delivery_mode', 'group_ids.total_capacity', 'online_capacity')
    def _compute_max_students(self):
        """Calcula la capacidad total del curso (presencial + virtual)"""
        for record in self:
            if record.delivery_mode == 'presential':
                record.max_students = sum(record.group_ids.mapped('presential_capacity'))
            elif record.delivery_mode == 'virtual':
                record.max_students = record.online_capacity * len(record.group_ids) if record.group_ids else record.online_capacity
            else:  # hybrid
                presential = sum(record.group_ids.mapped('presential_capacity'))
                virtual = record.online_capacity * len(record.group_ids) if record.group_ids else record.online_capacity
                record.max_students = presential + virtual
    
    @api.depends('group_ids.current_students')
    def _compute_current_students(self):
        """Calcula el total de estudiantes matriculados"""
        for record in self:
            record.current_students = sum(record.group_ids.mapped('current_students'))
    
    @api.constrains('code')
    def _check_code_format(self):
        """Valida el formato del código"""
        for record in self:
            if record.code and not record.code.replace('-', '').replace('_', '').isalnum():
                raise ValidationError(_(
                    'El código debe contener solo letras, números, guiones y guiones bajos.'
                ))
    
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Valida que la fecha de finalización sea posterior a la de inicio"""
        for record in self:
            if record.start_date and record.end_date and record.end_date < record.start_date:
                raise ValidationError(_(
                    'La fecha de finalización debe ser posterior a la fecha de inicio.'
                ))
    
    @api.constrains('delivery_mode', 'meeting_link', 'subcampus_ids', 'online_capacity')
    def _check_delivery_mode_requirements(self):
        """Valida los requisitos según la modalidad de entrega"""
        for record in self:
            # Validar que cursos virtuales/híbridos tengan enlace de videollamada
            if record.delivery_mode in ('virtual', 'hybrid') and not record.meeting_link:
                raise ValidationError(_(
                    'Los cursos virtuales o híbridos deben tener un enlace de videollamada configurado.'
                ))
            
            # Validar que cursos presenciales/híbridos tengan aulas asignadas
            if record.delivery_mode in ('presential', 'hybrid') and not record.subcampus_ids:
                raise ValidationError(_(
                    'Los cursos presenciales o híbridos deben tener al menos un aula asignada.'
                ))
            
            # Validar capacidad online para virtuales/híbridos
            if record.delivery_mode in ('virtual', 'hybrid') and record.online_capacity <= 0:
                raise ValidationError(_(
                    'Los cursos virtuales o híbridos deben tener una capacidad virtual mayor a cero.'
                ))
    
    @api.onchange('delivery_mode')
    def _onchange_delivery_mode(self):
        """Ajusta campos según la modalidad de entrega"""
        if self.delivery_mode == 'presential':
            self.meeting_link = False
            self.meeting_platform = False
            self.online_capacity = 0
        elif self.delivery_mode == 'virtual':
            self.subcampus_ids = False
            if not self.online_capacity:
                self.online_capacity = 100  # Valor por defecto
        elif self.delivery_mode == 'hybrid':
            if not self.online_capacity:
                self.online_capacity = 50  # Valor por defecto para híbrido
    
    @api.onchange('campus_id')
    def _onchange_campus_id(self):
        """Limpia las aulas cuando se cambia la sede"""
        if self.campus_id:
            self.subcampus_ids = False
    
    @api.onchange('subject_id')
    def _onchange_subject_id(self):
        """Sugiere el nombre y duración del curso basado en la asignatura"""
        if self.subject_id:
            if not self.name:
                self.name = self.subject_id.name
            if not self.duration_hours and self.subject_id.hours:
                self.duration_hours = self.subject_id.hours
    
    def action_schedule(self):
        """Programa el curso"""
        self.write({'state': 'scheduled'})
    
    def action_start(self):
        """Inicia el curso"""
        self.write({'state': 'in_progress'})
    
    def action_finish(self):
        """Finaliza el curso"""
        self.write({'state': 'finished'})
    
    def action_cancel(self):
        """Cancela el curso"""
        self.write({'state': 'cancelled'})
    
    def action_draft(self):
        """Vuelve el curso a borrador"""
        self.write({'state': 'draft'})
    
    def action_view_groups(self):
        """Abre la vista de grupos del curso"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Grupos del Curso'),
            'res_model': 'benglish.group',
            'view_mode': 'list,form',
            'domain': [('course_id', '=', self.id)],
            'context': {'default_course_id': self.id, 'default_campus_id': self.campus_id.id},
        }
    
    def action_view_sessions(self):
        """Abre la vista de sesiones asociadas al curso (por asignatura y sede)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sesiones del Curso: %s') % self.name,
            'res_model': 'benglish.class.session',
            'view_mode': 'calendar,list,form',
            'domain': [('subject_id', '=', self.subject_id.id), ('campus_id', '=', self.campus_id.id)],
            'context': {
                'default_subject_id': self.subject_id.id,
                'default_campus_id': self.campus_id.id,
            },
        }
    
    def name_get(self):
        """Personaliza el nombre mostrado"""
        result = []
        for record in self:
            name = f"{record.name}"
            if record.code:
                name = f"[{record.code}] {record.name}"
            result.append((record.id, name))
        return result
