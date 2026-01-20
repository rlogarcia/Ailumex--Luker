# -*- coding: utf-8 -*-
"""
Script manual para limpiar clases dictadas de la agenda del portal.
Ejecutar desde consola Odoo o desde botón de acción.
"""

from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def cleanup_completed_sessions_from_agenda(env):
    """
    Limpia manualmente las clases dictadas/canceladas de la agenda del portal.
    """
    _logger.info("=" * 80)
    _logger.info("LIMPIEZA MANUAL DE AGENDA - INICIO")
    _logger.info("=" * 80)
    
    Line = env['portal.student.weekly.plan.line'].sudo()
    
    # Buscar TODAS las líneas cuya sesión ya terminó
    all_lines = Line.search([])
    
    _logger.info(f"Total de líneas en agenda: {len(all_lines)}")
    
    lines_to_clean = all_lines.filtered(
        lambda l: l.session_id and l.session_id.state in ['done', 'cancelled']
    )
    
    _logger.info(f"Líneas a limpiar (done/cancelled): {len(lines_to_clean)}")
    
    cleaned = 0
    for line in lines_to_clean:
        try:
            student_name = line.plan_id.student_id.name if line.plan_id and line.plan_id.student_id else "N/A"
            session_name = line.session_id.display_name if line.session_id else "N/A"
            session_state = line.session_id.state if line.session_id else "N/A"
            
            _logger.info(
                f"Limpiando línea {line.id}: "
                f"Estudiante: {student_name} | "
                f"Sesión: {session_name} | "
                f"Estado: {session_state}"
            )
            
            # Procesar según tipo
            if line.session_id.state == 'done':
                # Buscar inscripción y sincronizar a historial si es necesario
                enrollment = line.session_id.enrollment_ids.filtered(
                    lambda e: e.student_id == line.plan_id.student_id
                )[:1]
                
                if enrollment:
                    if enrollment.state == 'attended':
                        _logger.info(f"  → Estudiante ASISTIÓ, sincronizando a historial...")
                        try:
                            enrollment._sync_to_academic_history()
                        except Exception as e:
                            _logger.warning(f"  → Error sincronizando: {str(e)}")
                    elif enrollment.state == 'absent':
                        _logger.info(f"  → Estudiante NO ASISTIÓ")
                    else:
                        _logger.info(f"  → Asistencia pendiente (estado: {enrollment.state})")
            
            # Eliminar línea
            line.unlink()
            cleaned += 1
            _logger.info(f"  ✅ Línea {line.id} eliminada")
            
        except Exception as e:
            _logger.error(f"  ❌ Error limpiando línea {line.id}: {str(e)}")
    
    _logger.info("=" * 80)
    _logger.info(f"LIMPIEZA COMPLETADA: {cleaned}/{len(lines_to_clean)} líneas procesadas")
    _logger.info("=" * 80)
    
    return {
        'total_lines': len(all_lines),
        'lines_to_clean': len(lines_to_clean),
        'cleaned': cleaned,
    }


def run(env):
    """Punto de entrada para ejecutar desde consola."""
    return cleanup_completed_sessions_from_agenda(env)


# Si se ejecuta directamente desde shell:
# >>> from odoo import api, SUPERUSER_ID
# >>> with api.Environment.manage():
# ...     env = api.Environment(cr, SUPERUSER_ID, {})
# ...     exec(open('/ruta/al/script/manual_cleanup_agenda.py').read())
# ...     result = run(env)
# ...     print(result)
