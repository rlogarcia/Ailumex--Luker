#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migración para asociar dispositivos a respuestas antiguas de encuestas.

Este script permite:
1. Crear dispositivos genéricos para respuestas sin dispositivo
2. Agrupar respuestas por patrones (fecha, hora, ubicación)
3. Asignar dispositivos manualmente desde la consola

Uso:
    python migrate_devices.py --database=NOMBRE_DB --mode=auto
    python migrate_devices.py --database=NOMBRE_DB --mode=manual

Modos:
    - auto: Crea dispositivos automáticamente agrupando por fecha/hora
    - manual: Interactivo, permite asignar dispositivos manualmente
    - report: Solo muestra un reporte sin hacer cambios
"""

import sys
import argparse
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)


def get_odoo_environment(database):
    """Conecta con Odoo y retorna el environment."""
    try:
        import odoo
        from odoo import api
        
        odoo.tools.config.parse_config(['-d', database])
        odoo.cli.server.report_configuration()
        
        registry = odoo.registry(database)
        with registry.cursor() as cr:
            env = api.Environment(cr, odoo.SUPERUSER_ID, {})
            return env, cr
    except Exception as e:
        _logger.error(f"Error al conectar con Odoo: {e}")
        sys.exit(1)


def report_mode(env):
    """Genera un reporte de respuestas sin dispositivo."""
    _logger.info("=== REPORTE DE RESPUESTAS SIN DISPOSITIVO ===")
    
    SurveyInput = env['survey.user_input']
    Device = env['survey.device']
    
    total_responses = SurveyInput.search_count([('state', '=', 'done')])
    responses_without_device = SurveyInput.search_count([
        ('state', '=', 'done'),
        ('device_id', '=', False)
    ])
    total_devices = Device.search_count([])
    
    _logger.info(f"Total de respuestas completadas: {total_responses}")
    _logger.info(f"Respuestas SIN dispositivo: {responses_without_device}")
    _logger.info(f"Respuestas CON dispositivo: {total_responses - responses_without_device}")
    _logger.info(f"Total de dispositivos registrados: {total_devices}")
    
    # Detalles por encuesta
    surveys = env['survey.survey'].search([])
    _logger.info("\n=== DESGLOSE POR ENCUESTA ===")
    for survey in surveys:
        total = SurveyInput.search_count([
            ('survey_id', '=', survey.id),
            ('state', '=', 'done')
        ])
        without = SurveyInput.search_count([
            ('survey_id', '=', survey.id),
            ('state', '=', 'done'),
            ('device_id', '=', False)
        ])
        if total > 0:
            _logger.info(f"  - {survey.title}: {without}/{total} sin dispositivo")
    
    return responses_without_device


def auto_mode(env, cr):
    """Modo automático: crea dispositivos genéricos y los asigna."""
    _logger.info("=== MODO AUTOMÁTICO: MIGRACIÓN DE DISPOSITIVOS ===")
    
    SurveyInput = env['survey.user_input']
    Device = env['survey.device']
    
    # Buscar respuestas sin dispositivo
    responses_without_device = SurveyInput.search([
        ('state', '=', 'done'),
        ('device_id', '=', False)
    ], order='create_date asc')
    
    if not responses_without_device:
        _logger.info("No hay respuestas sin dispositivo. ¡Todo está al día!")
        return
    
    _logger.info(f"Encontradas {len(responses_without_device)} respuestas sin dispositivo")
    
    # Estrategia: crear un dispositivo genérico por cada "grupo" de respuestas
    # Agrupamos por fecha (mismo día = probablemente mismo dispositivo)
    from collections import defaultdict
    groups = defaultdict(list)
    
    for response in responses_without_device:
        # Agrupar por día de creación
        day_key = response.create_date.date() if response.create_date else 'unknown'
        groups[day_key].append(response)
    
    _logger.info(f"Respuestas agrupadas en {len(groups)} grupos por fecha")
    
    # Obtener el último número de dispositivo para continuar la secuencia
    last_device = Device.search([('name', '=ilike', 'Dispositivo %')], order='id desc', limit=1)
    device_counter = 1
    if last_device:
        import re
        match = re.search(r'Dispositivo (\d+)', last_device.name)
        if match:
            device_counter = int(match.group(1)) + 1
    
    for day_key, responses in groups.items():
        # Crear un dispositivo con nombre consecutivo
        device_name = f"Dispositivo {device_counter}"
        device = Device.create({
            'name': device_name,
            'uuid': f'MIGRATED-{device_counter}-{str(day_key).replace("-", "")}',
            'active': True,
            'notes': f'Dispositivo creado automáticamente para migración. {len(responses)} respuestas del {day_key}.'
        })
        
        # Asignar todas las respuestas de este grupo al dispositivo
        for response in responses:
            response.write({
                'device_id': device.id,
                'device_uuid': device.uuid
            })
        
        device.update_last_response()
        _logger.info(f"  ✓ Creado {device_name}: {len(responses)} respuestas asignadas")
        device_counter += 1
    
    cr.commit()
    _logger.info(f"\n✓ Migración completada. {device_counter - 1} dispositivos creados.")


def manual_mode(env, cr):
    """Modo manual: permite asignar dispositivos interactivamente."""
    _logger.info("=== MODO MANUAL: ASIGNACIÓN INTERACTIVA ===")
    
    SurveyInput = env['survey.user_input']
    Device = env['survey.device']
    
    # Buscar respuestas sin dispositivo
    responses_without_device = SurveyInput.search([
        ('state', '=', 'done'),
        ('device_id', '=', False)
    ], order='create_date desc', limit=50)  # Limitar para no saturar
    
    if not responses_without_device:
        _logger.info("No hay respuestas sin dispositivo.")
        return
    
    _logger.info(f"Encontradas {len(responses_without_device)} respuestas recientes sin dispositivo")
    
    # Listar dispositivos existentes
    devices = Device.search([('active', '=', True)])
    _logger.info("\n=== DISPOSITIVOS DISPONIBLES ===")
    _logger.info("0. Crear nuevo dispositivo")
    for idx, device in enumerate(devices, 1):
        _logger.info(f"{idx}. {device.name} (UUID: {device.uuid}, {device.total_responses} respuestas)")
    
    print("\n" + "="*60)
    print("ASIGNACIÓN MANUAL DE DISPOSITIVOS")
    print("="*60)
    
    for response in responses_without_device:
        print(f"\nRespuesta ID: {response.id}")
        print(f"  Encuesta: {response.survey_id.title}")
        print(f"  Fecha: {response.create_date}")
        print(f"  Estado: {response.state}")
        
        choice = input("\n¿Asignar a dispositivo? (número, 's'=skip, 'q'=salir): ").strip().lower()
        
        if choice == 'q':
            break
        elif choice == 's':
            continue
        elif choice == '0':
            # Obtener el siguiente número consecutivo
            last_device = Device.search([('name', '=ilike', 'Dispositivo %')], order='id desc', limit=1)
            next_number = 1
            if last_device:
                import re
                match = re.search(r'Dispositivo (\d+)', last_device.name)
                if match:
                    next_number = int(match.group(1)) + 1
            
            suggested_name = f"Dispositivo {next_number}"
            print(f"Nombre sugerido: {suggested_name}")
            device_name = input(f"Nombre del nuevo dispositivo [{suggested_name}]: ").strip()
            if not device_name:
                device_name = suggested_name
            
            if device_name:
                new_device = Device.create({
                    'name': device_name,
                    'uuid': f'MANUAL-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                    'active': True,
                    'notes': 'Dispositivo creado manualmente durante migración.'
                })
                response.write({
                    'device_id': new_device.id,
                    'device_uuid': new_device.uuid
                })
                new_device.update_last_response()
                cr.commit()
                print(f"✓ Asignado a nuevo dispositivo: {device_name}")
        else:
            try:
                idx = int(choice)
                if 1 <= idx <= len(devices):
                    device = devices[idx - 1]
                    response.write({
                        'device_id': device.id,
                        'device_uuid': device.uuid
                    })
                    device.update_last_response()
                    cr.commit()
                    print(f"✓ Asignado a: {device.name}")
                else:
                    print("Número inválido")
            except ValueError:
                print("Entrada inválida")
    
    _logger.info("\nProceso manual completado.")


def main():
    parser = argparse.ArgumentParser(description='Migración de dispositivos para encuestas')
    parser.add_argument('--database', '-d', required=True, help='Nombre de la base de datos')
    parser.add_argument('--mode', '-m', choices=['auto', 'manual', 'report'], 
                        default='report', help='Modo de operación')
    
    args = parser.parse_args()
    
    env, cr = get_odoo_environment(args.database)
    
    try:
        if args.mode == 'report':
            count = report_mode(env)
            if count > 0:
                print(f"\n💡 Consejo: Ejecuta con --mode=auto para migrar automáticamente")
                print(f"   o con --mode=manual para asignación interactiva")
        elif args.mode == 'auto':
            auto_mode(env, cr)
        elif args.mode == 'manual':
            manual_mode(env, cr)
    except KeyboardInterrupt:
        _logger.info("\n\nProceso interrumpido por el usuario")
        cr.rollback()
    except Exception as e:
        _logger.error(f"Error durante la ejecución: {e}", exc_info=True)
        cr.rollback()
    finally:
        cr.close()


if __name__ == '__main__':
    main()
