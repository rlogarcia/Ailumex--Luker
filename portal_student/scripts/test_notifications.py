# -*- coding: utf-8 -*-
"""Script de diagnóstico para el sistema de notificaciones."""

import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

def test_notifications():
    """Función para diagnosticar el estado de las notificaciones."""
    
    user = request.env.user
    
    # 1. Obtener notificaciones
    notif_list = request.env['benglish.academic.session'].sudo().search(
        [('is_published','=',True)], 
        order='create_date desc', 
        limit=5
    )
    
    _logger.info(f"=== DIAGNÓSTICO NOTIFICACIONES ===")
    _logger.info(f"Usuario: {user.name} (ID: {user.id})")
    _logger.info(f"Total notificaciones disponibles: {len(notif_list)}")
    
    for n in notif_list:
        _logger.info(f"  - Sesión ID: {n.id}, Asignatura: {n.subject_id.name}, Creada: {n.create_date}")
    
    # 2. Obtener notificaciones vistas
    viewed_ids = request.env['portal.notification.view'].sudo().search([
        ('user_id','=',user.id)
    ]).mapped('session_id').ids
    
    _logger.info(f"Notificaciones vistas por el usuario: {len(viewed_ids)}")
    _logger.info(f"IDs vistas: {viewed_ids}")
    
    # 3. Calcular no vistas
    unseen = [n for n in notif_list if n.id not in viewed_ids]
    _logger.info(f"Notificaciones NO vistas: {len(unseen)}")
    for n in unseen:
        _logger.info(f"  - NO VISTA: Sesión ID: {n.id}, Asignatura: {n.subject_id.name}")
    
    _logger.info(f"=== FIN DIAGNÓSTICO ===")
    
    return {
        'total': len(notif_list),
        'viewed': len(viewed_ids),
        'unseen': len(unseen),
        'unseen_ids': [n.id for n in unseen]
    }
