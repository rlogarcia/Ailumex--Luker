#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de inicialización para poblar el Gestor de Contraseñas de Estudiantes.

Este script debe ejecutarse UNA SOLA VEZ después de instalar el módulo
para crear registros en benglish.student.password.manager para todos
los estudiantes que ya tienen usuario portal.

Uso:
    Desde Odoo shell:
    $ odoo-bin shell -d nombre_base_datos -c odoo.conf
    >>> exec(open('init_password_manager.py').read())

    O ejecutar manualmente desde Odoo como acción de servidor.
"""

import logging

_logger = logging.getLogger(__name__)


def init_password_manager(env):
    """
    Inicializa el gestor de contraseñas para todos los estudiantes con usuario portal.
    
    Args:
        env: Environment de Odoo
    """
    _logger.info("=" * 80)
    _logger.info("INICIANDO POBLACIÓN DEL GESTOR DE CONTRASEÑAS DE ESTUDIANTES")
    _logger.info("=" * 80)
    
    # Buscar todos los estudiantes que tienen usuario portal
    Student = env['benglish.student']
    PasswordManager = env['benglish.student.password.manager']
    
    students_with_portal = Student.sudo().search([
        ('user_id', '!=', False)
    ])
    
    total = len(students_with_portal)
    _logger.info(f"Se encontraron {total} estudiantes con usuario portal")
    
    if total == 0:
        _logger.info("No hay estudiantes con usuario portal para sincronizar")
        return {
            'success': True,
            'message': 'No hay estudiantes para sincronizar',
            'created': 0,
            'existing': 0,
        }
    
    created_count = 0
    existing_count = 0
    error_count = 0
    errors = []
    
    for idx, student in enumerate(students_with_portal, 1):
        try:
            # Verificar si ya existe un registro
            existing = PasswordManager.sudo().search([
                ('student_id', '=', student.id)
            ], limit=1)
            
            if existing:
                existing_count += 1
                _logger.debug(f"[{idx}/{total}] Ya existe registro para {student.name} ({student.code})")
            else:
                # Crear nuevo registro
                PasswordManager.sudo().create({
                    'student_id': student.id,
                })
                created_count += 1
                _logger.info(f"[{idx}/{total}] ✓ Creado registro para {student.name} ({student.code})")
            
            # Commit cada 50 registros para evitar problemas de memoria
            if idx % 50 == 0:
                env.cr.commit()
                _logger.info(f"  → Progreso: {idx}/{total} procesados")
                
        except Exception as e:
            error_count += 1
            error_msg = f"Error al procesar estudiante {student.name} ({student.code}): {str(e)}"
            errors.append(error_msg)
            _logger.error(error_msg)
    
    # Commit final
    env.cr.commit()
    
    _logger.info("=" * 80)
    _logger.info("RESUMEN DE INICIALIZACIÓN")
    _logger.info("=" * 80)
    _logger.info(f"Total estudiantes procesados: {total}")
    _logger.info(f"Registros creados: {created_count}")
    _logger.info(f"Registros existentes (no modificados): {existing_count}")
    _logger.info(f"Errores: {error_count}")
    
    if errors:
        _logger.warning("ERRORES ENCONTRADOS:")
        for error in errors:
            _logger.warning(f"  - {error}")
    
    _logger.info("=" * 80)
    _logger.info("INICIALIZACIÓN COMPLETADA")
    _logger.info("=" * 80)
    
    return {
        'success': error_count == 0,
        'message': f'Procesados: {total}, Creados: {created_count}, Existentes: {existing_count}, Errores: {error_count}',
        'total': total,
        'created': created_count,
        'existing': existing_count,
        'errors': error_count,
        'error_details': errors,
    }


if __name__ == '__main__':
    # Si se ejecuta desde Odoo shell, 'env' ya está disponible
    try:
        result = init_password_manager(env)
        print("\n" + "=" * 80)
        print("RESULTADO:")
        print(f"  {result['message']}")
        print("=" * 80)
    except NameError:
        print("Este script debe ejecutarse desde Odoo shell")
        print("Uso: odoo-bin shell -d database -c config.conf")
        print(">>> exec(open('init_password_manager.py').read())")
