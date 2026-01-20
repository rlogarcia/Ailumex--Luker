# -*- coding: utf-8 -*-
"""
ARCHIVO NUEVO: portal_coach/models/academic_session_inherit.py

Este modelo HEREDA de benglish.academic.session y le agrega los campos de novedad
SIN tocar el módulo benglish_academy.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AcademicSessionInherit(models.Model):
    """
    Herencia del modelo benglish.academic.session para agregar campos de novedad
    """
    _inherit = 'benglish.academic.session'
    
    # ========================================
    # CAMPOS DE NOVEDAD (AGREGADOS POR PORTAL_COACH)
    # ========================================
    
    novelty_type = fields.Selection(
        selection=[
            ('postponed', 'Aplazada'),
            ('material', 'Material'),
        ],
        string="Tipo de Novedad",
        help="Tipo de novedad cuando no hay estudiantes que asistieron. "
             "Material requiere adjuntar archivos. Aplazada no requiere adjuntos.",
        tracking=True,
    )
    
    novelty_observation = fields.Text(
        string="Observación de Novedad",
        help="Observaciones adicionales sobre la novedad (opcional)",
    )
    
    novelty_attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='benglish_session_novelty_attachment_rel',
        column1='session_id',
        column2='attachment_id',
        string="Adjuntos de Novedad",
        help="Archivos adjuntos relacionados con la novedad (fotos, documentos, etc.)"
    )
    
    novelty_attachment_count = fields.Integer(
        string="Cantidad de Adjuntos",
        compute='_compute_novelty_attachment_count',
        help="Número de archivos adjuntos en la novedad",
    )
    
    @api.depends('novelty_attachment_ids')
    def _compute_novelty_attachment_count(self):
        """Calcula la cantidad de archivos adjuntos"""
        for record in self:
            record.novelty_attachment_count = len(record.novelty_attachment_ids)
    
    # ========================================
    # SOBREESCRITURA DE MÉTODO action_finish
    # ========================================
    
    def action_finish(self):
        """
        Sobreescribe action_finish para validar novedad ANTES de llamar al método original.
        
        VALIDACIÓN DE NOVEDAD:
        Si NO hay estudiantes que asistieron, requiere una novedad antes de cerrar.
        """
        
        for record in self:
            if record.state != "started":
                raise UserError(
                    _("Solo se pueden marcar como dictadas sesiones iniciadas.")
                )
            
            # ========================================
            # VALIDACIÓN DE NOVEDAD (AGREGADA POR PORTAL_COACH)
            # ========================================
            # Contar estudiantes que ASISTIERON
            attended_students = record.enrollment_ids.filtered(lambda e: e.state == "attended")
            
            if not attended_students:
                # NO hay estudiantes que asistieron → REQUIERE NOVEDAD
                
                if not record.novelty_type:
                    raise UserError(
                        _("No hay estudiantes que asistieron a la clase.\n\n"
                          "Debe seleccionar un TIPO DE NOVEDAD antes de cerrar la sesión:\n"
                          "• Aplazada: Clase reprogramada\n"
                          "• Material: Se entregó material o contenido")
                    )
                
                # Si escogió MATERIAL → DEBE tener adjuntos
                if record.novelty_type == 'material':
                    if not record.novelty_attachment_ids:
                        raise UserError(
                            _("Seleccionó novedad tipo 'Material'.\n\n"
                              "Debe adjuntar al menos un archivo (foto, documento, etc.) "
                              "antes de cerrar la sesión.")
                        )
                
                # Log de novedad
                _logger.info(
                    f"[PORTAL_COACH] Session {record.id} closed with novelty: "
                    f"Type={record.novelty_type}, Attachments={len(record.novelty_attachment_ids)}, "
                    f"Observation={bool(record.novelty_observation)}"
                )
        
        # Llamar al método original de benglish_academy
        return super(AcademicSessionInherit, self).action_finish()
