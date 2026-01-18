# -*- coding: utf-8 -*-
"""
Configuración de Políticas de Congelamiento por Plan
=====================================================

Este modelo implementa
- Definir si un plan permite congelamiento
- Establecer días mínimos y máximos por solicitud
- Controlar el máximo acumulado de días durante la vigencia

-Se tiene que adecuar a las necesidades reales
Cada plan puede tener una configuración diferente según las reglas de negocio:
- Plus: Permite congelamiento, 15-60 días, máximo 90 acumulados
- Premium: Permite congelamiento, 15-90 días, máximo 120 acumulados
- Gold: Permite congelamiento, 15-90 días, máximo 150 acumulados
- Supreme: Permite congelamiento, 30-120 días, máximo 180 acumulados
- Cortesía: No permite congelamiento
- Módulo individual: No permite congelamiento
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PlanFreezeConfig(models.Model):
    _name = 'benglish.plan.freeze.config'
    _description = 'Configuración de Congelamiento por Plan'
    _order = 'plan_id'
    _rec_name = 'plan_id'
    
    # CAMPOS RELACIONALES
    
    plan_id = fields.Many2one(
        'benglish.plan',
        string='Plan',
        required=True,
        ondelete='cascade',
        index=True,
        help="Plan al que aplica esta configuración de congelamiento"
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        help="Compañía para configuraciones multi-empresa"
    )
    
    # CAMPOS DE CONFIGURACIÓN PRINCIPAL
    
    permite_congelamiento = fields.Boolean(
        string='Permite Congelamiento',
        default=True,
        help="Indica si el plan permite solicitar congelamiento. "
             "Algunos planes como Cortesía o Módulo Individual no permiten esta opción."
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True,
        help="Permite desactivar la configuración sin eliminarla"
    )
    
    # CAMPOS DE LÍMITES DE DÍAS
    
    min_dias_congelamiento = fields.Integer(
        string='Mínimo de Días',
        default=15,
        help="Número mínimo de días que se pueden solicitar en un congelamiento. "
             "Por defecto: 15 días"
    )
    
    max_dias_congelamiento = fields.Integer(
        string='Máximo de Días por Solicitud',
        default=60,
        help="Número máximo de días que se pueden solicitar en una sola solicitud. "
             "Por defecto: 60 días"
    )
    
    max_dias_acumulados = fields.Integer(
        string='Máximo de Días Acumulados',
        default=90,
        help="Número máximo de días de congelamiento acumulados permitidos "
             "durante toda la vigencia del plan. Por defecto: 90 días"
    )
    
    # CAMPOS DE RESTRICCIONES ADICIONALES
    
    requiere_pago_al_dia = fields.Boolean(
        string='Requiere Pagos al Día',
        default=True,
        help="Si está activo, el estudiante debe estar al día en sus pagos "
             "para poder solicitar congelamiento"
    )
    
    dias_minimos_cursados = fields.Integer(
        string='Días Mínimos Cursados',
        default=30,
        help="Número mínimo de días que el estudiante debe haber cursado "
             "antes de poder solicitar su primer congelamiento. 0 = sin restricción"
    )
    
    max_congelamientos_por_ciclo = fields.Integer(
        string='Máx. Congelamientos por Ciclo',
        default=0,
        help="Número máximo de solicitudes de congelamiento permitidas por ciclo/año. "
             "0 = sin límite de solicitudes"
    )
    
    # CAMPOS DE INFORMACIÓN
    
    descripcion = fields.Text(
        string='Descripción de la Política',
        help="Descripción detallada de las condiciones y restricciones "
             "de congelamiento para este plan"
    )
    
    notas_internas = fields.Text(
        string='Notas Internas',
        help="Notas visibles solo para el personal administrativo"
    )
    
    # CAMPOS COMPUTADOS
    
    plan_name = fields.Char(
        related='plan_id.name',
        string='Nombre del Plan',
        store=True,
        help="Nombre del plan para facilitar búsquedas"
    )
    
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True,
        help="Nombre para mostrar en vistas y reportes"
    )
    
    # RESTRICCIONES SQL
    
    _sql_constraints = [
        (
            'plan_unique',
            'UNIQUE(plan_id, company_id)',
            'Ya existe una configuración de congelamiento para este plan en esta compañía.'
        ),
        (
            'min_dias_positive',
            'CHECK(min_dias_congelamiento >= 0)',
            'El mínimo de días debe ser mayor o igual a cero.'
        ),
        (
            'max_dias_positive',
            'CHECK(max_dias_congelamiento > 0)',
            'El máximo de días por solicitud debe ser mayor a cero.'
        ),
        (
            'max_acumulados_positive',
            'CHECK(max_dias_acumulados > 0)',
            'El máximo de días acumulados debe ser mayor a cero.'
        ),
        (
            'min_menor_max',
            'CHECK(min_dias_congelamiento <= max_dias_congelamiento)',
            'El mínimo de días no puede ser mayor al máximo por solicitud.'
        ),
        (
            'max_menor_acumulados',
            'CHECK(max_dias_congelamiento <= max_dias_acumulados)',
            'El máximo por solicitud no puede ser mayor al máximo acumulado.'
        ),
    ]
    
    # MÉTODOS COMPUTADOS
    
    @api.depends('plan_id.name', 'permite_congelamiento')
    def _compute_display_name(self):
        """Genera el nombre para mostrar incluyendo estado de permisos."""
        for record in self:
            if record.plan_id:
                estado = "✓" if record.permite_congelamiento else "✗"
                record.display_name = f"{record.plan_id.name} [{estado}]"
            else:
                record.display_name = "Nueva Configuración"
    
    # VALIDACIONES
    
    @api.constrains('min_dias_congelamiento', 'max_dias_congelamiento', 'max_dias_acumulados')
    def _check_dias_configuration(self):
        """Valida la coherencia de la configuración de días."""
        for record in self:
            if record.min_dias_congelamiento < 0:
                raise ValidationError(
                    "El mínimo de días de congelamiento no puede ser negativo."
                )
            if record.max_dias_congelamiento < record.min_dias_congelamiento:
                raise ValidationError(
                    f"El máximo de días por solicitud ({record.max_dias_congelamiento}) "
                    f"debe ser mayor o igual al mínimo ({record.min_dias_congelamiento})."
                )
            if record.max_dias_acumulados < record.max_dias_congelamiento:
                raise ValidationError(
                    f"El máximo de días acumulados ({record.max_dias_acumulados}) "
                    f"debe ser mayor o igual al máximo por solicitud ({record.max_dias_congelamiento})."
                )
    
    @api.constrains('dias_minimos_cursados')
    def _check_dias_minimos_cursados(self):
        """Valida que los días mínimos cursados no sean negativos."""
        for record in self:
            if record.dias_minimos_cursados < 0:
                raise ValidationError(
                    "Los días mínimos cursados antes del congelamiento no pueden ser negativos."
                )
    
    # MÉTODOS DE NEGOCIO
    
    def get_config_for_plan(self, plan_id, company_id=None):
        """
        Obtiene la configuración de congelamiento para un plan específico.
        
        Args:
            plan_id: ID del plan o recordset de benglish.plan
            company_id: ID de la compañía (opcional, usa la actual si no se especifica)
        
        Returns:
            Recordset de benglish.plan.freeze.config o empty recordset
        """
        if isinstance(plan_id, models.Model):
            plan_id = plan_id.id
        
        if company_id is None:
            company_id = self.env.company.id
        
        return self.search([
            ('plan_id', '=', plan_id),
            ('company_id', '=', company_id),
            ('active', '=', True)
        ], limit=1)
    
    def can_request_freeze(self, dias_solicitados, dias_ya_usados=0):
        """
        Verifica si se puede solicitar un congelamiento con los días indicados.
        
        Args:
            dias_solicitados: Número de días que se desean solicitar
            dias_ya_usados: Días de congelamiento ya usados por el estudiante
        
        Returns:
            tuple: (puede_solicitar: bool, mensaje: str)
        """
        self.ensure_one()
        
        if not self.permite_congelamiento:
            return (False, "Este plan no permite solicitar congelamiento.")
        
        if dias_solicitados < self.min_dias_congelamiento:
            return (
                False,
                f"El mínimo de días para congelamiento es {self.min_dias_congelamiento}. "
                f"Solicitaste: {dias_solicitados}"
            )
        
        if dias_solicitados > self.max_dias_congelamiento:
            return (
                False,
                f"El máximo de días por solicitud es {self.max_dias_congelamiento}. "
                f"Solicitaste: {dias_solicitados}"
            )
        
        dias_totales = dias_ya_usados + dias_solicitados
        if dias_totales > self.max_dias_acumulados:
            disponibles = self.max_dias_acumulados - dias_ya_usados
            return (
                False,
                f"Excedes el máximo de días acumulados ({self.max_dias_acumulados}). "
                f"Ya has usado {dias_ya_usados} días. Disponibles: {disponibles}"
            )
        
        return (True, "La solicitud cumple con los requisitos del plan.")
    
    def get_available_days(self, dias_ya_usados=0):
        """
        Calcula los días de congelamiento disponibles para un estudiante.
        
        Args:
            dias_ya_usados: Días de congelamiento ya utilizados
        
        Returns:
            dict con información de disponibilidad
        """
        self.ensure_one()
        
        if not self.permite_congelamiento:
            return {
                'disponibles': 0,
                'min_solicitar': 0,
                'max_solicitar': 0,
                'ya_usados': dias_ya_usados,
                'max_acumulados': 0,
                'permite': False,
                'mensaje': 'Este plan no permite congelamiento'
            }
        
        disponibles = max(0, self.max_dias_acumulados - dias_ya_usados)
        max_solicitar = min(disponibles, self.max_dias_congelamiento)
        min_solicitar = min(self.min_dias_congelamiento, disponibles) if disponibles > 0 else 0
        
        return {
            'disponibles': disponibles,
            'min_solicitar': min_solicitar,
            'max_solicitar': max_solicitar,
            'ya_usados': dias_ya_usados,
            'max_acumulados': self.max_dias_acumulados,
            'permite': disponibles >= self.min_dias_congelamiento,
            'mensaje': (
                f"Tienes {disponibles} días disponibles de un máximo de {self.max_dias_acumulados}"
                if disponibles > 0 else "Has agotado tus días de congelamiento disponibles"
            )
        }
    
    def get_policy_summary(self):
        """
        Genera un resumen legible de la política de congelamiento.
        
        Returns:
            str: Texto descriptivo de la política
        """
        self.ensure_one()
        
        if not self.permite_congelamiento:
            return f"El plan {self.plan_id.name} no permite congelamiento."
        
        lines = [
            f"Política de Congelamiento - {self.plan_id.name}",
            "=" * 50,
            f"✓ Congelamiento permitido",
            f"• Mínimo por solicitud: {self.min_dias_congelamiento} días",
            f"• Máximo por solicitud: {self.max_dias_congelamiento} días",
            f"• Máximo acumulado: {self.max_dias_acumulados} días",
        ]
        
        if self.requiere_pago_al_dia:
            lines.append("• Requiere estar al día en pagos")
        
        if self.dias_minimos_cursados > 0:
            lines.append(f"• Mínimo {self.dias_minimos_cursados} días cursados antes de solicitar")
        
        if self.max_congelamientos_por_ciclo > 0:
            lines.append(f"• Máximo {self.max_congelamientos_por_ciclo} solicitudes por ciclo")
        
        return "\n".join(lines)
    
    # MÉTODOS DE CREACIÓN/ACTUALIZACIÓN
    
    @api.model_create_multi
    def create(self, vals_list):
        """Crea nuevas configuraciones validando duplicados."""
        for vals in vals_list:
            # Verificar si ya existe una configuración para el plan
            existing = self.search([
                ('plan_id', '=', vals.get('plan_id')),
                ('company_id', '=', vals.get('company_id', self.env.company.id))
            ], limit=1)
            if existing:
                raise ValidationError(
                    f"Ya existe una configuración de congelamiento para el plan "
                    f"'{existing.plan_id.name}'. Edite la existente en lugar de crear una nueva."
                )
        
        return super().create(vals_list)
    
    # ACCIONES
    
    def action_crear_config_para_todos_planes(self):
        """
        Crea configuraciones de congelamiento por defecto para todos los planes
        que no tengan una configuración aún.
        
        Returns:
            dict: Acción para mostrar las configuraciones creadas
        """
        Plan = self.env['benglish.plan']
        planes_sin_config = Plan.search([
            ('id', 'not in', self.search([]).mapped('plan_id').ids)
        ])
        
        created = self.env['benglish.plan.freeze.config']
        for plan in planes_sin_config:
            created |= self.create({
                'plan_id': plan.id,
                'permite_congelamiento': True,
                'min_dias_congelamiento': 15,
                'max_dias_congelamiento': 60,
                'max_dias_acumulados': 90,
            })
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Configuraciones Creadas ({len(created)})',
            'res_model': 'benglish.plan.freeze.config',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created.ids)],
            'context': {'create': False},
        }
