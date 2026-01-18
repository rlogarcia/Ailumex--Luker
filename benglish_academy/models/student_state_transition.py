# -*- coding: utf-8 -*-
"""
Transiciones Válidas entre Estados de Perfil
=============================================

Modelo para definir qué transiciones de estado son permitidas,
controlando el flujo de cambios de estado del perfil del estudiante.

Transiciones válidas entre estados - Control de flujo de negocio
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StudentStateTransition(models.Model):
    """
    Define las transiciones permitidas entre estados de perfil.
    
    Permite configurar de manera flexible qué cambios de estado son válidos,
    quién puede realizarlos y bajo qué condiciones.
    """
    _name = 'benglish.student.state.transition'
    _description = 'Transición de Estado de Perfil'
    _order = 'estado_origen_id, sequence'
    _rec_name = 'display_name'
    
    # CAMPOS PRINCIPALES 
    
    estado_origen_id = fields.Many2one(
        'benglish.student.profile.state',
        string='Estado Origen',
        required=True,
        ondelete='cascade',
        index=True,
        help='Estado desde el cual se permite la transición'
    )
    
    estado_destino_id = fields.Many2one(
        'benglish.student.profile.state',
        string='Estado Destino',
        required=True,
        ondelete='cascade',
        index=True,
        help='Estado al cual se puede transicionar'
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de aparición en listas'
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Transiciones inactivas no serán permitidas'
    )
    
    #  CONTROL DE ACCESO 
    
    requiere_motivo = fields.Boolean(
        string='Requiere Motivo',
        default=True,
        help='Si está activo, se debe indicar un motivo para realizar esta transición'
    )
    
    requiere_aprobacion = fields.Boolean(
        string='Requiere Aprobación',
        default=False,
        help='La transición requiere aprobación de un supervisor'
    )
    
    grupo_permitido_ids = fields.Many2many(
        'res.groups',
        'benglish_state_transition_group_rel',
        'transition_id',
        'group_id',
        string='Grupos Permitidos',
        help='Grupos de usuarios que pueden realizar esta transición. '
             'Si está vacío, cualquier usuario con acceso puede realizarla.'
    )
    
    #  AUTOMATIZACIÓN 
    
    es_automatica = fields.Boolean(
        string='Transición Automática',
        default=False,
        help='Esta transición puede ser ejecutada automáticamente por el sistema'
    )
    
    trigger = fields.Selection([
        ('none', 'Ninguno (Manual)'),
        # Triggers compatibles con datos y eventos internos (claves en español)
        ('congelamiento', 'Aprobación de Congelamiento'),
        ('descongelamiento', 'Fin de Congelamiento'),
        ('cartera', 'Incidencia de Cartera'),
        ('pago', 'Pago Regularizado'),
        ('matricula', 'Creación de Matrícula'),
        ('fin_programa', 'Fin de Programa'),
        ('retiro_voluntario', 'Retiro Voluntario'),
    ], string='Disparador', default='none',
       help='Evento que dispara la transición automática')
    
    #  INFORMACIÓN 
    
    descripcion = fields.Text(
        string='Descripción',
        help='Descripción de cuándo y por qué se realiza esta transición'
    )
    
    mensaje_confirmacion = fields.Text(
        string='Mensaje de Confirmación',
        help='Mensaje que se muestra al usuario antes de confirmar la transición'
    )
    
    #  CAMPOS COMPUTADOS 
    
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True
    )
    
    #  RESTRICCIONES 
    
    _sql_constraints = [
        (
            'unique_transition',
            'UNIQUE(estado_origen_id, estado_destino_id)',
            'Ya existe una transición entre estos estados.'
        ),
        (
            'no_self_transition',
            'CHECK(estado_origen_id != estado_destino_id)',
            'No se puede crear una transición de un estado a sí mismo.'
        ),
    ]
    
    #  MÉTODOS COMPUTADOS 
    
    @api.depends('estado_origen_id.name', 'estado_destino_id.name')
    def _compute_display_name(self):
        for record in self:
            if record.estado_origen_id and record.estado_destino_id:
                record.display_name = f"{record.estado_origen_id.name} → {record.estado_destino_id.name}"
            else:
                record.display_name = "Nueva Transición"
    
    #  MÉTODOS DE VALIDACIÓN 
    
    def puede_transicionar(self, user=None):
        """
        Verifica si el usuario puede realizar esta transición.
        
        Args:
            user: Recordset del usuario (None = usuario actual)
        
        Returns:
            tuple: (puede: bool, mensaje: str)
        """
        self.ensure_one()
        
        if not self.active:
            return (False, _("Esta transición no está activa."))
        
        user = user or self.env.user
        
        # Verificar grupos permitidos
        if self.grupo_permitido_ids:
            user_groups = user.groups_id
            if not (user_groups & self.grupo_permitido_ids):
                return (False, _("No tiene permisos para realizar esta transición."))
        
        return (True, _("Transición permitida."))
    
    #  MÉTODOS DE BÚSQUEDA 
    
    @api.model
    def get_transiciones_permitidas(self, estado_origen_id, user=None):
        """
        Obtiene las transiciones permitidas desde un estado origen.
        
        Args:
            estado_origen_id: ID del estado origen
            user: Usuario para verificar permisos
        
        Returns:
            Recordset de transiciones permitidas
        """
        user = user or self.env.user
        
        transiciones = self.search([
            ('estado_origen_id', '=', estado_origen_id),
            ('active', '=', True),
        ])
        
        # Filtrar por permisos
        permitidas = self.env['benglish.student.state.transition']
        for trans in transiciones:
            puede, _ = trans.puede_transicionar(user)
            if puede:
                permitidas |= trans
        
        return permitidas
    
    @api.model
    def get_estados_destino_permitidos(self, estado_origen_id, user=None):
        """
        Obtiene los estados destino permitidos desde un estado origen.
        
        Returns:
            Recordset de estados de perfil
        """
        transiciones = self.get_transiciones_permitidas(estado_origen_id, user)
        return transiciones.mapped('estado_destino_id')
    
    @api.model
    def validar_transicion(self, estado_origen_id, estado_destino_id, user=None):
        """
        Valida si una transición específica es permitida.
        
        Args:
            estado_origen_id: ID del estado origen
            estado_destino_id: ID del estado destino
            user: Usuario que realiza la transición
        
        Returns:
            tuple: (valida: bool, mensaje: str, transicion: recordset o False)
        """
        user = user or self.env.user
        
        # Buscar la transición
        transicion = self.search([
            ('estado_origen_id', '=', estado_origen_id),
            ('estado_destino_id', '=', estado_destino_id),
            ('active', '=', True),
        ], limit=1)
        
        if not transicion:
            # Verificar si existe pero está inactiva
            inactiva = self.search([
                ('estado_origen_id', '=', estado_origen_id),
                ('estado_destino_id', '=', estado_destino_id),
                ('active', '=', False),
            ], limit=1)
            
            if inactiva:
                return (False, _("Esta transición existe pero está desactivada."), False)
            else:
                return (False, _("No existe una transición válida entre estos estados."), False)
        
        puede, mensaje = transicion.puede_transicionar(user)
        return (puede, mensaje, transicion if puede else False)
    
    @api.model
    def get_transicion_automatica(self, estado_origen_id, trigger):
        """
        Busca una transición automática según el trigger.
        
        Args:
            estado_origen_id: ID del estado origen
            trigger: Tipo de disparador
        
        Returns:
            Recordset de la transición o empty
        """
        return self.search([
            ('estado_origen_id', '=', estado_origen_id),
            ('es_automatica', '=', True),
            ('trigger', '=', trigger),
            ('active', '=', True),
        ], limit=1)
