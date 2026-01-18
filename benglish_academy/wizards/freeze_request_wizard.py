# -*- coding: utf-8 -*-
"""
Wizard para Solicitar Congelamiento de Matrícula
================================================

Wizard simplificado que guía al estudiante (o administrativo) paso a paso
para crear una solicitud de congelamiento de matrícula.

Características:
- Interfaz amigable con validaciones en tiempo real
- Cálculo automático de días según fechas
- Muestra días disponibles del estudiante
- Valida contra política del plan
- Alerta si requiere documentación
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta


class FreezeRequestWizard(models.TransientModel):
    """Wizard para solicitar congelamiento de matrícula."""
    
    _name = 'benglish.freeze.request.wizard'
    _description = 'Solicitar Congelamiento'
    
    # CAMPOS BÁSICOS
    
    student_id = fields.Many2one(
        'benglish.student',
        string='Estudiante',
        required=True,
        default=lambda self: self._default_student_id(),
        help="Estudiante que solicita el congelamiento"
    )
    
    enrollment_id = fields.Many2one(
        'benglish.enrollment',
        string='Matrícula a Congelar',
        required=True,
        domain="[('student_id', '=', student_id), ('state', 'in', ['enrolled', 'in_progress'])]",
        help="Seleccione la matrícula que desea congelar"
    )
    
    plan_id = fields.Many2one(
        related='enrollment_id.plan_id',
        string='Plan',
        readonly=True
    )
    
    # MOTIVO
    
    freeze_reason_id = fields.Many2one(
        'benglish.freeze.reason',
        string='Motivo del Congelamiento',
        required=True,
        domain="[('active', '=', True), ('es_especial', '=', False)]",
        help="Seleccione el motivo de su solicitud"
    )
    
    motivo_detalle = fields.Text(
        string='Descripción Detallada',
        help="Proporcione información adicional (opcional pero recomendado)"
    )
    
    requiere_documentacion = fields.Boolean(
        related='freeze_reason_id.requiere_documentacion',
        string='Requiere Documentación'
    )
    
    tipos_documentos_requeridos = fields.Text(
        related='freeze_reason_id.tipos_documentos',
        string='Documentos Requeridos'
    )
    
    # FECHAS
    
    fecha_inicio = fields.Date(
        string='Fecha de Inicio',
        required=True,
        default=lambda self: fields.Date.context_today(self) + timedelta(days=7),
        help="Fecha en que iniciará el congelamiento (mínimo 7 días desde hoy)"
    )
    
    fecha_fin = fields.Date(
        string='Fecha de Finalización',
        required=True,
        help="Fecha en que finalizará el congelamiento"
    )
    
    dias_solicitados = fields.Integer(
        string='Días Solicitados',
        compute='_compute_dias_solicitados',
        help="Número de días del congelamiento"
    )
    
    # VALIDACIONES Y AYUDAS
    
    dias_usados = fields.Integer(
        string='Días Ya Usados',
        compute='_compute_disponibilidad',
        help="Días de congelamiento ya utilizados"
    )
    
    dias_disponibles = fields.Integer(
        string='Días Disponibles',
        compute='_compute_disponibilidad',
        help="Días de congelamiento disponibles"
    )
    
    dias_maximos_plan = fields.Integer(
        string='Máximo Permitido por Plan',
        compute='_compute_disponibilidad',
        help="Máximo de días acumulados según el plan"
    )
    
    puede_solicitar = fields.Boolean(
        string='Puede Solicitar',
        compute='_compute_puede_solicitar',
        help="Indica si la solicitud cumple con las validaciones"
    )
    
    mensaje_validacion = fields.Html(
        string='Estado de Validación',
        compute='_compute_puede_solicitar',
        help="Resultado de las validaciones"
    )
    
    estudiante_al_dia = fields.Boolean(
        string='Estudiante al Día',
        related='student_id.al_dia_en_pagos',
        help="Estado de cartera del estudiante"
    )
    
    # DEFAULTS
    
    def _default_student_id(self):
        """Obtiene el estudiante del contexto si existe."""
        return self.env.context.get('default_student_id', False)
    
    # COMPUTED
    
    @api.depends('fecha_inicio', 'fecha_fin')
    def _compute_dias_solicitados(self):
        """Calcula los días solicitados."""
        for wizard in self:
            if wizard.fecha_inicio and wizard.fecha_fin:
                if wizard.fecha_fin >= wizard.fecha_inicio:
                    delta = wizard.fecha_fin - wizard.fecha_inicio
                    wizard.dias_solicitados = delta.days + 1
                else:
                    wizard.dias_solicitados = 0
            else:
                wizard.dias_solicitados = 0
    
    @api.depends('student_id', 'enrollment_id')
    def _compute_disponibilidad(self):
        """Calcula días usados y disponibles."""
        for wizard in self:
            if wizard.student_id:
                wizard.dias_usados = wizard.student_id.dias_congelamiento_usados or 0
                wizard.dias_disponibles = wizard.student_id.dias_congelamiento_disponibles or 0
                
                # Obtener configuración del plan
                if wizard.enrollment_id and wizard.enrollment_id.plan_id:
                    config = self.env['benglish.plan.freeze.config'].get_config_for_plan(
                        wizard.enrollment_id.plan_id
                    )
                    wizard.dias_maximos_plan = config.max_dias_acumulados if config else 0
                else:
                    wizard.dias_maximos_plan = 0
            else:
                wizard.dias_usados = 0
                wizard.dias_disponibles = 0
                wizard.dias_maximos_plan = 0
    
    @api.depends('dias_solicitados', 'dias_disponibles', 'estudiante_al_dia',
                 'requiere_documentacion', 'enrollment_id', 'fecha_inicio')
    def _compute_puede_solicitar(self):
        """Valida si puede crear la solicitud."""
        today = fields.Date.context_today(self)
        
        for wizard in self:
            mensajes = []
            errores = []
            advertencias = []
            
            # Validación 1: Fecha de inicio
            if wizard.fecha_inicio:
                if wizard.fecha_inicio < today:
                    errores.append('❌ La fecha de inicio no puede ser en el pasado')
                elif wizard.fecha_inicio < today + timedelta(days=7):
                    advertencias.append('⚠ Se recomienda solicitar con al menos 7 días de anticipación')
                else:
                    mensajes.append('✅ Fecha de inicio válida')
            
            # Validación 2: Fechas coherentes
            if wizard.fecha_inicio and wizard.fecha_fin:
                if wizard.fecha_fin < wizard.fecha_inicio:
                    errores.append('❌ La fecha de fin debe ser posterior a la fecha de inicio')
                elif wizard.dias_solicitados < 15:
                    advertencias.append(f'⚠ Solicita solo {wizard.dias_solicitados} días. Mínimo recomendado: 15 días')
                else:
                    mensajes.append(f'✅ Período válido: {wizard.dias_solicitados} días')
            
            # Validación 3: Días disponibles
            if wizard.dias_solicitados > 0:
                if wizard.dias_solicitados > wizard.dias_disponibles:
                    errores.append(f'❌ Solicita {wizard.dias_solicitados} días pero solo tiene {wizard.dias_disponibles} disponibles')
                else:
                    mensajes.append(f'✅ Días disponibles suficientes ({wizard.dias_disponibles} días)')
            
            # Validación 4: Estado de cartera
            if wizard.enrollment_id and wizard.enrollment_id.plan_id:
                config = self.env['benglish.plan.freeze.config'].get_config_for_plan(
                    wizard.enrollment_id.plan_id
                )
                if config and config.requiere_pago_al_dia:
                    if wizard.estudiante_al_dia:
                        mensajes.append('✅ Estudiante al día en sus pagos')
                    else:
                        advertencias.append('⚠ Tiene pagos pendientes. Coordinación evaluará su solicitud')
            
            # Validación 5: Documentación
            if wizard.requiere_documentacion:
                advertencias.append(f'📎 <strong>Debe adjuntar:</strong> {wizard.tipos_documentos_requeridos}')
            
            # Resumen de uso
            if wizard.dias_usados > 0:
                progreso_pct = int((wizard.dias_usados / wizard.dias_maximos_plan) * 100) if wizard.dias_maximos_plan > 0 else 0
                mensajes.append(f'📊 Ha usado {wizard.dias_usados} de {wizard.dias_maximos_plan} días ({progreso_pct}%)')
            
            # Determinar si puede solicitar
            wizard.puede_solicitar = len(errores) == 0
            
            # Construir mensaje HTML
            html = '<div style="padding: 10px;">'
            
            if errores:
                html += '<div class="alert alert-danger"><strong>Errores que debe corregir:</strong><ul>'
                for error in errores:
                    html += f'<li>{error}</li>'
                html += '</ul></div>'
            
            if advertencias:
                html += '<div class="alert alert-warning"><strong>Advertencias:</strong><ul>'
                for adv in advertencias:
                    html += f'<li>{adv}</li>'
                html += '</ul></div>'
            
            if mensajes and wizard.puede_solicitar:
                html += '<div class="alert alert-success"><strong>Validaciones:</strong><ul>'
                for msg in mensajes:
                    html += f'<li>{msg}</li>'
                html += '</ul></div>'
            
            html += '</div>'
            wizard.mensaje_validacion = html
    
    # ONCHANGE
    
    @api.onchange('freeze_reason_id')
    def _onchange_freeze_reason(self):
        """Al seleccionar motivo, sugiere días máximos."""
        if self.freeze_reason_id and self.freeze_reason_id.dias_maximos_sugeridos > 0:
            if not self.fecha_inicio:
                self.fecha_inicio = fields.Date.context_today(self) + timedelta(days=7)
            
            self.fecha_fin = self.fecha_inicio + timedelta(days=self.freeze_reason_id.dias_maximos_sugeridos - 1)
    
    @api.onchange('student_id')
    def _onchange_student_id(self):
        """Al cambiar estudiante, limpiar matrícula."""
        self.enrollment_id = False
    
    # ACCIONES
    
    def action_create_request(self):
        """Crea la solicitud de congelamiento."""
        self.ensure_one()
        
        # Validación final
        if not self.puede_solicitar:
            raise ValidationError(
                _('No se puede crear la solicitud. Por favor corrija los errores indicados.')
            )
        
        # Crear el congelamiento
        freeze_period = self.env['benglish.student.freeze.period'].create({
            'student_id': self.student_id.id,
            'enrollment_id': self.enrollment_id.id,
            'freeze_reason_id': self.freeze_reason_id.id,
            'motivo_detalle': self.motivo_detalle,
            'fecha_inicio': self.fecha_inicio,
            'fecha_fin': self.fecha_fin,
            'estado': 'borrador',
        })
        
        # Mensaje de éxito
        message = _(
            'Solicitud creada exitosamente.\n\n'
            'Período: %s días (del %s al %s)\n'
            'Estado: Borrador\n\n'
            'Recuerde:\n'
            '- Completar todos los campos requeridos\n'
            '- Adjuntar documentación si es necesaria\n'
            '- Enviar a aprobación cuando esté lista'
        ) % (
            self.dias_solicitados,
            self.fecha_inicio.strftime('%d/%m/%Y'),
            self.fecha_fin.strftime('%d/%m/%Y')
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('✅ Solicitud Creada'),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'benglish.student.freeze.period',
                    'res_id': freeze_period.id,
                    'view_mode': 'form',
                    'views': [(False, 'form')],
                    'target': 'current',
                }
            }
        }
