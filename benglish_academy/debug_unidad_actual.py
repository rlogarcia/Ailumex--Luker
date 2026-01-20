#!/usr/bin/env python3
"""
Script para diagnosticar el cálculo de unidad actual del estudiante.
"""
import sys
import os

# Configurar path para Odoo
sys.path.insert(0, r"C:\Program Files\Odoo 18.0.20250614\server")
os.chdir(r"C:\Program Files\Odoo 18.0.20250614\server")

import odoo
from odoo import api
from odoo.modules.registry import Registry

# Inicializar Odoo
odoo.tools.config.parse_config(['--config=odoo.conf'])

# Cargar registry
registry = Registry('BenglishV1')

with registry.cursor() as cr:
    env = api.Environment(cr, odoo.SUPERUSER_ID, {})
    
    Student = env['benglish.student'].sudo()
    History = env['benglish.academic.history'].sudo()
    
    # Buscar estudiante 0001 (jose noreña)
    student = Student.search([('code', '=', '0001')], limit=1)
    
    if not student:
        print("❌ Estudiante 0001 no encontrado")
        sys.exit(1)
    
    print(f"\n{'='*80}")
    print(f"DIAGNÓSTICO DE UNIDAD ACTUAL")
    print(f"{'='*80}\n")
    
    print(f"👤 Estudiante: {student.name} (Código: {student.code})")
    print(f"   Programa: {student.program_id.name if student.program_id else 'N/A'}")
    print(f"   Nivel: {student.current_level_id.name if student.current_level_id else 'N/A'}")
    print(f"   max_unit_completed (campo): {student.max_unit_completed}")
    
    # Obtener historial académico
    completed_history = History.search([
        ('student_id', '=', student.id),
        ('attendance_status', '=', 'attended'),
        ('subject_id', '!=', False)
    ])
    
    print(f"\n📚 HISTORIAL ACADÉMICO ({len(completed_history)} clases completadas):\n")
    
    # Agrupar por unidad
    units_progress = {}
    for history in completed_history:
        subject = history.subject_id
        unit_num = subject.unit_number
        
        if not unit_num:
            continue
            
        if unit_num not in units_progress:
            units_progress[unit_num] = {
                'bcheck': False,
                'skills': [],
                'total': 0,
                'subjects': []
            }
        
        units_progress[unit_num]['total'] += 1
        units_progress[unit_num]['subjects'].append(subject.name)
        
        if subject.subject_category == 'bcheck':
            units_progress[unit_num]['bcheck'] = True
        elif subject.subject_category == 'bskills' and subject.bskill_number and subject.bskill_number <= 4:
            units_progress[unit_num]['skills'].append(subject.bskill_number)
    
    # Mostrar progreso por unidad
    for unit in sorted(units_progress.keys()):
        progress = units_progress[unit]
        skills_count = len(progress['skills'])
        
        print(f"  Unit {unit}:")
        print(f"    • B-check: {'✅' if progress['bcheck'] else '❌'}")
        print(f"    • Skills completadas: {skills_count}/4 {progress['skills']}")
        print(f"    • Total clases: {progress['total']}")
        print(f"    • Unidad completa: {'✅ SÍ' if (progress['bcheck'] and skills_count >= 4) else '❌ NO'}")
        print()
    
    # Calcular unidad actual con la lógica del controlador
    print(f"\n{'='*80}")
    print(f"CÁLCULO DE UNIDAD ACTUAL")
    print(f"{'='*80}\n")
    
    if not units_progress:
        current_unit = 1
        print(f"  ⚠️ Sin historial → Unidad actual: {current_unit}")
    else:
        highest_unit_started = max(units_progress.keys())
        progress = units_progress[highest_unit_started]
        
        is_unit_complete = progress['bcheck'] and len(progress['skills']) >= 4
        
        if is_unit_complete:
            current_unit = highest_unit_started + 1
            print(f"  ✅ Unit {highest_unit_started} completa → Avanzar a Unit {current_unit}")
        else:
            current_unit = highest_unit_started
            print(f"  ⏳ Unit {highest_unit_started} incompleta → Permanecer en Unit {current_unit}")
        
        print(f"\n  📍 UNIDAD ACTUAL CALCULADA: {current_unit}")
        
    # Buscar sesiones publicadas para este estudiante
    print(f"\n{'='*80}")
    print(f"SESIONES PUBLICADAS")
    print(f"{'='*80}\n")
    
    Session = env['benglish.academic.session'].sudo()
    sessions = Session.search([
        ('is_published', '=', True),
        ('datetime_start', '>', env.cr.now()),
        ('subject_id.program_id', '=', student.program_id.id)
    ], limit=20, order='datetime_start')
    
    print(f"  Total sesiones publicadas: {len(sessions)}\n")
    
    for session in sessions[:10]:
        subject = session.subject_id
        print(f"  📅 {session.display_name}")
        print(f"     Asignatura: {subject.name if subject else 'N/A'}")
        print(f"     Categoría: {subject.subject_category if subject else 'N/A'}")
        print(f"     Unit: {subject.unit_number if subject else 'N/A'}")
        print(f"     Audiencia: {session.audience_unit_from}-{session.audience_unit_to}")
        print(f"     Estudiante en rango: {'✅ SÍ' if (session.audience_unit_from <= current_unit <= session.audience_unit_to) else '❌ NO'}")
        print()
    
    print(f"\n{'='*80}")
    print(f"RESUMEN")
    print(f"{'='*80}\n")
    
    print(f"  • Estudiante debería ver sesiones de Unit: {current_unit}")
    print(f"  • max_unit_completed (campo Odoo): {student.max_unit_completed}")
    print(f"  • Unidad actual calculada: {current_unit}")
    
    if student.max_unit_completed and current_unit != student.max_unit_completed + 1:
        print(f"\n  ⚠️ DIFERENCIA DETECTADA:")
        print(f"     Odoo calcula: max_unit_completed + 1 = {student.max_unit_completed + 1}")
        print(f"     Portal debería calcular: {current_unit}")
