# -*- coding: utf-8 -*-
"""
Wizard de Preview de Aprobación de Congelamiento
================================================

Muestra una vista previa de los cambios que se aplicarán al aprobar
un congelamiento, permitiendo al usuario confirmar con toda la información.

Preview de ajuste de fechas antes de aprobar
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta


class FreezeApprovalPreviewWizard(models.TransientModel):
    _name = 'benglish.freeze.approval.preview.wizard'
    _description = 'Preview de Aprobación de Congelamiento'
    
    # CAMPOS DEL CONGELAMIENTO
    
    freeze_period_id = fields.Many2one(
        'benglish.student.freeze.period',
        string='Solicitud de Congelamiento',
        required=True,
        readonly=True,
    )
    
    # INFORMACIÓN DEL ESTUDIANTE
    
    student_id = fields.Many2one(
        related='freeze_period_id.student_id',
        string='Estudiante',
        readonly=True,
    )
    
    student_name = fields.Char(
        related='freeze_period_id.student_id.name',
        string='Nombre del Estudiante',
        readonly=True,
    )
    
    enrollment_id = fields.Many2one(
        related='freeze_period_id.enrollment_id',
        string='Matrícula',
        readonly=True,
    )
    
    plan_name = fields.Char(
        related='freeze_period_id.plan_id.name',
        string='Plan',
        readonly=True,
    )
    
    # INFORMACIÓN DEL CONGELAMIENTO 
    
    fecha_inicio = fields.Date(
        related='freeze_period_id.fecha_inicio',
        string='Fecha Inicio Congelamiento',
        readonly=True,
    )
    
    fecha_fin = fields.Date(
        related='freeze_period_id.fecha_fin',
        string='Fecha Fin Congelamiento',
        readonly=True,
    )
    
    dias_congelamiento = fields.Integer(
        related='freeze_period_id.dias',
        string='Días de Congelamiento',
        readonly=True,
    )
    
    es_especial = fields.Boolean(
        related='freeze_period_id.es_especial',
        string='Es Especial',
        readonly=True,
    )
    
    tipo_especial = fields.Selection(
        related='freeze_period_id.tipo_especial',
        string='Tipo Especial',
        readonly=True,
    )
    
    # ESTADO DE CARTERA
    
    estudiante_al_dia = fields.Boolean(
        related='freeze_period_id.estudiante_al_dia',
        string='Estudiante al Día',
        readonly=True,
    )
    
    excepcion_cartera = fields.Boolean(
        related='freeze_period_id.excepcion_cartera',
        string='Excepción de Cartera',
        readonly=True,
    )
    
    # PREVIEW DE FECHAS (CALCULADOS)
    
    fecha_fin_actual = fields.Date(
        string='Fecha Fin Actual de Matrícula',
        compute='_compute_preview_fechas',
        readonly=True,
    )
    
    fecha_fin_nueva = fields.Date(
        string='Nueva Fecha Fin de Matrícula',
        compute='_compute_preview_fechas',
        readonly=True,
    )
    
    dias_extension = fields.Integer(
        string='Días de Extensión',
        compute='_compute_preview_fechas',
        readonly=True,
    )
    
    # ESTADÍSTICAS DE CONGELAMIENTO
    
    dias_usados_previamente = fields.Integer(
        string='Días Usados Previamente',
        compute='_compute_estadisticas',
        readonly=True,
    )
    
    dias_usados_despues = fields.Integer(
        string='Días Usados Después',
        compute='_compute_estadisticas',
        readonly=True,
    )
    
    dias_disponibles_despues = fields.Integer(
        string='Días Disponibles Después',
        compute='_compute_estadisticas',
        readonly=True,
    )
    
    max_dias_plan = fields.Integer(
        string='Máximo Días del Plan',
        compute='_compute_estadisticas',
        readonly=True,
    )
    
    #  VALIDACIONES
    
    puede_aprobar = fields.Boolean(
        string='Puede Aprobar',
        compute='_compute_puede_aprobar',
        readonly=True,
    )
    
    mensaje_validacion = fields.Text(
        string='Mensaje de Validación',
        compute='_compute_puede_aprobar',
        readonly=True,
    )
    
    alertas = fields.Text(
        string='Alertas',
        compute='_compute_alertas',
        readonly=True,
    )
    
    #  CAMPOS DE CONFIRMACIÓN
    
    confirmar_cambios = fields.Boolean(
        string='Confirmo que he revisado los cambios',
        default=False,
        help='Marque esta casilla para confirmar que ha revisado todos los cambios'
    )
    
    notas_aprobacion = fields.Text(
        string='Notas de Aprobación',
        help='Notas adicionales sobre la aprobación (opcional)'
    )
    
    #  MÉTODOS COMPUTADOS
    
    @api.depends('freeze_period_id')
    def _compute_preview_fechas(self):
        for wizard in self:
            if wizard.freeze_period_id and wizard.freeze_period_id.enrollment_id:
                enrollment = wizard.freeze_period_id.enrollment_id
                wizard.fecha_fin_actual = enrollment.end_date
                
                if enrollment.end_date and wizard.freeze_period_id.dias:
                    wizard.fecha_fin_nueva = enrollment.end_date + timedelta(days=wizard.freeze_period_id.dias)
                    wizard.dias_extension = wizard.freeze_period_id.dias
                else:
                    wizard.fecha_fin_nueva = False
                    wizard.dias_extension = 0
            else:
                wizard.fecha_fin_actual = False
                wizard.fecha_fin_nueva = False
                wizard.dias_extension = 0
    
    @api.depends('freeze_period_id')
    def _compute_estadisticas(self):
        for wizard in self:
            freeze = wizard.freeze_period_id
            if freeze:
                dias_usados = freeze._get_dias_usados_estudiante()
                wizard.dias_usados_previamente = dias_usados
                wizard.dias_usados_despues = dias_usados + (freeze.dias or 0)
                
                config = freeze.freeze_config_id
                if config and config.permite_congelamiento:
                    wizard.max_dias_plan = config.max_dias_acumulados
                    wizard.dias_disponibles_despues = max(
                        0, config.max_dias_acumulados - wizard.dias_usados_despues
                    )
                else:
                    wizard.max_dias_plan = 0
                    wizard.dias_disponibles_despues = 0
            else:
                wizard.dias_usados_previamente = 0
                wizard.dias_usados_despues = 0
                wizard.dias_disponibles_despues = 0
                wizard.max_dias_plan = 0
    
    @api.depends('freeze_period_id')
    def _compute_puede_aprobar(self):
        for wizard in self:
            freeze = wizard.freeze_period_id
            if not freeze:
                wizard.puede_aprobar = False
                wizard.mensaje_validacion = "No se encontró la solicitud de congelamiento."
                continue
            
            mensajes = []
            puede = True
            
            # Verificar estado
            if freeze.estado != 'pendiente':
                puede = False
                mensajes.append("• La solicitud no está en estado pendiente.")
            
            # Verificar cartera
            if freeze.freeze_config_id and freeze.freeze_config_id.requiere_pago_al_dia:
                if not freeze.estudiante_al_dia and not freeze.excepcion_cartera:
                    puede = False
                    mensajes.append("• El estudiante no está al día en pagos y no tiene excepción.")
            
            # Verificar política (si no es especial)
            if not freeze.es_especial and freeze.freeze_config_id:
                dias_usados = freeze._get_dias_usados_estudiante()
                puede_policy, msg = freeze.freeze_config_id.can_request_freeze(freeze.dias, dias_usados)
                if not puede_policy:
                    puede = False
                    mensajes.append(f"• {msg}")
            
            wizard.puede_aprobar = puede
            wizard.mensaje_validacion = "\n".join(mensajes) if mensajes else "✓ Todas las validaciones pasaron correctamente."
    
    @api.depends('freeze_period_id', 'dias_disponibles_despues')
    def _compute_alertas(self):
        for wizard in self:
            alertas = []
            freeze = wizard.freeze_period_id
            
            if freeze:
                # Alerta si es especial
                if freeze.es_especial:
                    alertas.append("⚠️ Este es un CONGELAMIENTO ESPECIAL - No visible en portal del estudiante")
                
                # Alerta si hay excepción de cartera
                if freeze.excepcion_cartera:
                    alertas.append("⚠️ Se está aplicando una EXCEPCIÓN DE CARTERA")
                
                # Alerta si queda poco saldo
                if wizard.dias_disponibles_despues <= 15 and wizard.dias_disponibles_despues > 0:
                    alertas.append(f"⚠️ Al estudiante le quedarán solo {wizard.dias_disponibles_despues} días disponibles")
                
                # Alerta si se agotan los días
                if wizard.dias_disponibles_despues == 0:
                    alertas.append("🔴 El estudiante AGOTARÁ sus días de congelamiento")
                
                # Alerta si la fecha fin nueva cae en fin de semana (opcional)
                if wizard.fecha_fin_nueva:
                    if wizard.fecha_fin_nueva.weekday() >= 5:  # Sábado o Domingo
                        alertas.append("📅 La nueva fecha de fin cae en fin de semana")
            
            wizard.alertas = "\n".join(alertas) if alertas else ""
    
    # ACCIONES
    
    def action_confirmar_aprobacion(self):
        """Confirma la aprobación después de revisar el preview."""
        self.ensure_one()
        
        if not self.puede_aprobar:
            raise UserError(_(
                "No se puede aprobar esta solicitud:\n%s"
            ) % self.mensaje_validacion)
        
        if not self.confirmar_cambios:
            raise UserError(_(
                "Debe confirmar que ha revisado los cambios antes de aprobar."
            ))
        
        # Llamar al método de aprobación del congelamiento
        self.freeze_period_id.action_aprobar()
        
        # Agregar notas si las hay
        if self.notas_aprobacion:
            self.freeze_period_id.message_post(
                body=f"<strong>Notas de Aprobación:</strong><br/>{self.notas_aprobacion}"
            )
        
        return {'type': 'ir.actions.act_window_close'}
    
    def action_cancelar(self):
        """Cancela el proceso de aprobación."""
        return {'type': 'ir.actions.act_window_close'}
