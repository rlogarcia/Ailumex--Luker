# -*- coding: utf-8 -*-
"""
Catálogo de Estados de Perfil del Estudiante

Define los estados posibles del perfil de un estudiante y las reglas de negocio
asociadas a cada uno (qué puede hacer: agendar, asistir, usar apps, consultar histórico).
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StudentProfileState(models.Model):
    """
    Catálogo de estados de perfil del estudiante.
    
    Cada estado define qué acciones puede realizar el estudiante:
    - Agendar clases
    - Asistir a clases programadas
    - Usar aplicaciones/recursos
    - Consultar histórico
    
    Estados predefinidos:
    - Activo: Puede hacer todo
    - Suspendido por Cartera: Solo consulta, no puede agendar ni asistir
    - Congelado: Solo consulta, fecha fin se extiende
    - Retracto: Proceso de devolución en curso
    - Finalizado: Completó su programa
    - Cambio de Beneficiario: En proceso de transferencia
    """
    _name = 'benglish.student.profile.state'
    _description = 'Estado de Perfil del Estudiante'
    _order = 'sequence, name'
    _rec_name = 'name'

    #  CAMPOS BÁSICOS 
    
    name = fields.Char(
        string='Nombre del Estado',
        required=True,
        translate=True,
        help='Nombre descriptivo del estado (ej: Activo, Suspendido por Cartera)'
    )
    code = fields.Char(
        string='Código',
        required=True,
        copy=False,
        help='Código único del estado (ej: active, suspended_billing)'
    )
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de visualización'
    )
    description = fields.Text(
        string='Descripción',
        translate=True,
        help='Descripción detallada del estado y cuándo aplica'
    )
    
    # APARIENCIA
    
    color = fields.Integer(
        string='Color',
        default=0,
        help='Color para visualización en vistas kanban'
    )
    icon = fields.Char(
        string='Icono',
        default='fa-user',
        help='Clase de icono FontAwesome (ej: fa-user, fa-ban, fa-snowflake-o)'
    )
    
    # REGLAS DE NEGOCIO 
    
    can_schedule = fields.Boolean(
        string='Puede Programar Clases',
        default=True,
        help='El estudiante puede programar nuevas clases'
    )
    can_attend = fields.Boolean(
        string='Puede Asistir a Clases',
        default=True,
        help='El estudiante puede asistir a las clases ya programadas'
    )
    can_use_apps = fields.Boolean(
        string='Puede Usar Apps/Recursos',
        default=True,
        help='El estudiante puede acceder a aplicaciones y recursos de estudio'
    )
    can_view_history = fields.Boolean(
        string='Puede Ver Histórico',
        default=True,
        help='El estudiante puede consultar su historial académico'
    )
    can_request_freeze = fields.Boolean(
        string='Puede Solicitar Congelamiento',
        default=False,
        help='El estudiante puede solicitar congelamiento de su plan'
    )
    blocks_enrollment = fields.Boolean(
        string='Bloquea Matrícula',
        default=False,
        help='Este estado impide realizar nuevas matrículas'
    )
    
    #  MENSAJE AL ESTUDIANTE
    
    student_message = fields.Text(
        string='Mensaje para el Estudiante',
        translate=True,
        help='Mensaje que se muestra al estudiante cuando está en este estado. '
             'Explica por qué no puede realizar ciertas acciones.'
    )
    portal_visible = fields.Boolean(
        string='Visible en Portal',
        default=True,
        help='Si el estado y su mensaje son visibles para el estudiante en el portal'
    )
    
    #  CONTROL 
    
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Estados inactivos no estarán disponibles para asignar'
    )
    is_default = fields.Boolean(
        string='Es Estado por Defecto',
        default=False,
        help='Este estado se asigna automáticamente a nuevos estudiantes'
    )
    is_frozen_state = fields.Boolean(
        string='Es Estado de Congelamiento',
        default=False,
        help='Indica si este es el estado que representa congelamiento activo'
    )
    requires_reason = fields.Boolean(
        string='Requiere Motivo',
        default=False,
        help='Al asignar este estado se requiere especificar un motivo'
    )
    
    #  RESTRICCIONES 
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'El código del estado debe ser único.'),
    ]
    
    #  MÉTODOS 
    
    @api.constrains('is_default')
    def _check_single_default(self):
        """Solo puede haber un estado por defecto."""
        for record in self:
            if record.is_default:
                other_defaults = self.search([
                    ('is_default', '=', True),
                    ('id', '!=', record.id)
                ])
                if other_defaults:
                    raise ValidationError(_(
                        'Solo puede haber un estado por defecto. '
                        'El estado "%s" ya está marcado como por defecto.'
                    ) % other_defaults[0].name)
    
    @api.constrains('is_frozen_state')
    def _check_single_frozen_state(self):
        """Solo puede haber un estado de congelamiento."""
        for record in self:
            if record.is_frozen_state:
                other_frozen = self.search([
                    ('is_frozen_state', '=', True),
                    ('id', '!=', record.id)
                ])
                if other_frozen:
                    raise ValidationError(_(
                        'Solo puede haber un estado de congelamiento. '
                        'El estado "%s" ya está marcado como estado de congelamiento.'
                    ) % other_frozen[0].name)
    
    @api.model
    def get_default_state(self):
        """Retorna el estado por defecto para nuevos estudiantes."""
        default_state = self.search([('is_default', '=', True)], limit=1)
        if not default_state:
            default_state = self.search([('code', '=', 'active')], limit=1)
        return default_state
    
    @api.model
    def get_frozen_state(self):
        """Retorna el estado de congelamiento."""
        return self.search([('is_frozen_state', '=', True)], limit=1)
    
    def get_permissions_summary(self):
        """Retorna un resumen de permisos del estado."""
        self.ensure_one()
        return {
            'can_schedule': self.can_schedule,
            'can_attend': self.can_attend,
            'can_use_apps': self.can_use_apps,
            'can_view_history': self.can_view_history,
            'can_request_freeze': self.can_request_freeze,
            'blocks_enrollment': self.blocks_enrollment,
        }
    
    def name_get(self):
        """Muestra el nombre con icono si está disponible."""
        result = []
        for record in self:
            name = record.name
            if record.icon:
                name = f"[{record.icon}] {name}"
            result.append((record.id, name))
        return result
