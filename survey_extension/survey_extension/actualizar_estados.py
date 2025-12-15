#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para actualizar los estados de respuesta en los registros existentes
Ejecutar desde Odoo shell: python odoo-bin shell -d odoo18 -c odoo.conf
"""

def actualizar_estados_respuesta():
    """Actualiza x_response_status basado en el campo state"""
    
    # Obtener todos los registros de survey.user_input
    user_inputs = env['survey.user_input'].search([])
    
    print(f"📊 Encontrados {len(user_inputs)} registros de participaciones")
    
    actualizados = 0
    for rec in user_inputs:
        # Mapear el estado real al nuevo x_response_status
        if rec.state == 'done':
            nuevo_estado = 'done'
        elif rec.state == 'in_progress':
            nuevo_estado = 'in_progress'
        else:
            nuevo_estado = 'new'
        
        # Actualizar si es diferente
        if rec.x_response_status != nuevo_estado:
            rec.write({'x_response_status': nuevo_estado})
            actualizados += 1
    
    print(f"✅ Actualizados {actualizados} registros")
    
    # Recalcular rankings
    print("🔄 Recalculando rankings...")
    encuestas = env['survey.survey'].search([('x_is_gradable', '=', True)])
    
    for encuesta in encuestas:
        participaciones = env['survey.user_input'].search([('survey_id', '=', encuesta.id)])
        if participaciones:
            participaciones._compute_ranking_metrics()
            print(f"  ✓ Encuesta: {encuesta.name} - {len(participaciones)} participaciones")
    
    env.cr.commit()
    print("✅ ¡Proceso completado!")

# Ejecutar la función
if __name__ == '__main__':
    actualizar_estados_respuesta()
