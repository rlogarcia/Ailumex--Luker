#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para actualizar program_id en asignaturas de Benglish y B-Teens.

Este script corrige el problema donde las asignaturas no tienen program_id
asignado correctamente porque es un campo relacionado que no se calculó
durante la instalación del módulo.

USO:
====
1. Con Odoo corriendo:
   python fix_subject_program_ids.py

2. Desde Odoo shell:
   odoo-bin shell -c odoo.conf -d benglish_db
   >>> exec(open('fix_subject_program_ids.py').read())
"""

import logging

_logger = logging.getLogger(__name__)


def fix_subject_program_ids(env):
    """
    Actualiza el program_id de todas las asignaturas basándose en
    level_id.phase_id.program_id.
    """
    Subject = env['benglish.subject'].sudo()
    
    _logger.info("=" * 80)
    _logger.info("INICIANDO CORRECCIÓN DE program_id EN ASIGNATURAS")
    _logger.info("=" * 80)
    
    # Buscar todas las asignaturas activas
    all_subjects = Subject.search([('active', '=', True)], order='code')
    
    _logger.info(f"Total de asignaturas encontradas: {len(all_subjects)}")
    
    # Separar por programa
    subjects_by_program = {
        'benglish': [],
        'beteens': [],
        'sin_programa': [],
    }
    
    fixed_count = 0
    error_count = 0
    
    for subject in all_subjects:
        try:
            # Obtener el program_id desde la jerarquía
            program = False
            if subject.level_id and subject.level_id.phase_id:
                program = subject.level_id.phase_id.program_id
            
            current_program = subject.program_id
            
            # Clasificar
            if program:
                program_type = program.program_type
                subjects_by_program[program_type].append(subject)
                
                # Si el program_id actual NO coincide, actualizarlo
                if current_program != program:
                    _logger.warning(
                        f"  ⚠️  {subject.code} - {subject.name}: "
                        f"program_id incorrecto (actual={current_program.name if current_program else 'None'}, "
                        f"debería ser={program.name})"
                    )
                    subject.write({'program_id': program.id})
                    fixed_count += 1
                else:
                    _logger.debug(
                        f"  ✓  {subject.code} - {subject.name}: program_id correcto ({program.name})"
                    )
            else:
                subjects_by_program['sin_programa'].append(subject)
                _logger.error(
                    f"  ❌ {subject.code} - {subject.name}: No se puede determinar program_id "
                    f"(level_id={subject.level_id.name if subject.level_id else 'None'}, "
                    f"phase_id={subject.level_id.phase_id.name if subject.level_id and subject.level_id.phase_id else 'None'})"
                )
                error_count += 1
        
        except Exception as e:
            _logger.error(f"  ❌ Error procesando {subject.name}: {e}")
            error_count += 1
    
    # Resumen
    _logger.info("=" * 80)
    _logger.info("RESUMEN DE CORRECCIÓN")
    _logger.info("=" * 80)
    _logger.info(f"Total asignaturas: {len(all_subjects)}")
    _logger.info(f"Programa Benglish: {len(subjects_by_program['benglish'])}")
    _logger.info(f"Programa B-Teens: {len(subjects_by_program['beteens'])}")
    _logger.info(f"Sin programa: {len(subjects_by_program['sin_programa'])}")
    _logger.info(f"Asignaturas corregidas: {fixed_count}")
    _logger.info(f"Errores: {error_count}")
    _logger.info("=" * 80)
    
    if fixed_count > 0:
        _logger.info("✅ CORRECCIÓN COMPLETADA")
        _logger.info("   Las asignaturas ahora tienen program_id correcto.")
        _logger.info("   El historial retroactivo debería funcionar correctamente.")
    else:
        _logger.info("ℹ️  No se requirieron correcciones.")
    
    return {
        'total': len(all_subjects),
        'benglish': len(subjects_by_program['benglish']),
        'beteens': len(subjects_by_program['beteens']),
        'sin_programa': len(subjects_by_program['sin_programa']),
        'fixed': fixed_count,
        'errors': error_count,
    }


# Si se ejecuta directamente desde Odoo
if __name__ == '__main__':
    # Esto solo funcionará si se ejecuta desde odoo shell
    try:
        import odoo
        from odoo import api, SUPERUSER_ID
        
        # Asumiendo que estás en odoo shell
        with api.Environment.manage():
            env = api.Environment(odoo.registry(), SUPERUSER_ID, {})
            fix_subject_program_ids(env)
    except Exception as e:
        print(f"Error: {e}")
        print("\nEste script debe ejecutarse desde:")
        print("1. Odoo shell: odoo-bin shell -c odoo.conf -d tu_base_datos")
        print("2. Luego: exec(open('fix_subject_program_ids.py').read())")
