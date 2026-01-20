#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para recalcular progreso de estudiantes
"""

import sys
import os

sys.path.insert(0, r'C:\Program Files\Odoo 18.0.20250614\server')
os.chdir(r'C:\Program Files\Odoo 18.0.20250614\server')

import odoo
from odoo import api
from odoo.modules.registry import Registry

# Configurar
odoo.tools.config.parse_config(['-c', r'C:\Program Files\Odoo 18.0.20250614\server\odoo.conf', '--stop-after-init'])

# Obtener registry
registry = Registry('BenglishV1')

with registry.cursor() as cr:
    env = api.Environment(cr, 1, {})
    
    print("\n" + "=" * 80)
    print("RECÁLCULO DE PROGRESO ACADÉMICO")
    print("=" * 80)
    
    Student = env['benglish.student'].sudo()
    History = env['benglish.academic.history'].sudo()
    Enrollment = env['benglish.enrollment'].sudo()
    Progress = env['benglish.enrollment.progress'].sudo()
    
    # Buscar estudiante 0001
    student = Student.search([('code', '=', '0001')], limit=1)
    
    if not student:
        print("❌ Estudiante 0001 no encontrado")
        sys.exit(1)
    
    print(f"\n👤 Estudiante: {student.name} (Código: {student.code})")
    print(f"   Programa: {student.program_id.name if student.program_id else 'Sin programa'}")
    print(f"   Nivel: {student.current_level_id.name if student.current_level_id else 'Sin nivel'}")
    
    # 1. Verificar historial académico
    history = History.search([
        ('student_id', '=', student.id),
        ('attendance_status', '=', 'attended')
    ])
    
    print(f"\n📚 Historial académico: {len(history)} clases completadas")
    for h in history:
        print(f"   • {h.subject_id.name} (Unit {h.subject_id.unit_number})")
    
    # 2. Verificar matrícula activa
    active_enrollment = student.active_enrollment_ids.filtered(
        lambda e: e.plan_id
    )[:1]
    
    if not active_enrollment:
        active_enrollment = student.enrollment_ids.filtered(
            lambda e: e.plan_id
        )[:1]
    
    if not active_enrollment:
        print("\n❌ No hay matrícula al plan")
        sys.exit(1)
    
    print(f"\n📋 Matrícula: {active_enrollment.id}")
    print(f"   Plan: {active_enrollment.plan_id.name}")
    print(f"   Estado: {active_enrollment.state}")
    
    # 3. Verificar/crear progreso para cada asignatura completada en historial
    print(f"\n🔄 Sincronizando progreso con historial...")
    
    created_count = 0
    updated_count = 0
    
    for hist in history:
        subject = hist.subject_id
        if not subject:
            continue
        
        # Buscar progreso existente
        existing_progress = Progress.search([
            ('enrollment_id', '=', active_enrollment.id),
            ('subject_id', '=', subject.id)
        ], limit=1)
        
        if existing_progress:
            # Actualizar si NO está completado
            if existing_progress.state != 'completed':
                existing_progress.write({
                    'state': 'completed',
                    'end_date': hist.session_date,
                    'final_grade': hist.grade if hist.grade else 0,
                })
                updated_count += 1
                print(f"   ✅ Actualizado: {subject.name}")
        else:
            # Crear nuevo
            Progress.create({
                'enrollment_id': active_enrollment.id,
                'subject_id': subject.id,
                'state': 'completed',
                'start_date': hist.session_date,
                'end_date': hist.session_date,
                'final_grade': hist.grade if hist.grade else 0,
            })
            created_count += 1
            print(f"   ➕ Creado: {subject.name}")
    
    print(f"\n   📊 Registros creados: {created_count}")
    print(f"   📊 Registros actualizados: {updated_count}")
    
    # 4. Forzar recálculo de campos computados
    print(f"\n🔄 Recalculando campos computados...")
    
    # Invalidar cache
    student.invalidate_recordset([
        'max_unit_completed',
        'academic_progress_percentage',
        'completed_hours',
        'academic_history_ids'
    ])
    
    active_enrollment.invalidate_recordset([
        'enrollment_progress_ids'
    ])
    
    # Forzar recálculo
    student._compute_max_unit_from_history()
    student._compute_academic_progress()
    
    # Commit
    cr.commit()
    
    # 5. Verificar resultados
    print(f"\n" + "=" * 80)
    print("RESULTADOS")
    print("=" * 80)
    
    # Re-leer estudiante
    student = Student.browse(student.id)
    
    print(f"\n👤 {student.name}:")
    print(f"   max_unit_completed: {student.max_unit_completed}")
    print(f"   academic_progress: {student.academic_progress_percentage}%")
    print(f"   completed_hours: {student.completed_hours}")
    
    # Verificar progreso
    progress_records = Progress.search([
        ('enrollment_id', '=', active_enrollment.id)
    ])
    
    completed_progress = progress_records.filtered(lambda p: p.state == 'completed')
    
    print(f"\n📊 Progreso académico:")
    print(f"   Total asignaturas en plan: {len(active_enrollment.plan_id.subject_ids)}")
    print(f"   Asignaturas completadas: {len(completed_progress)}")
    print(f"   En progreso: {len(progress_records.filtered(lambda p: p.state == 'in_progress'))}")
    print(f"   Pendientes: {len(progress_records.filtered(lambda p: p.state == 'pending'))}")
    
    if student.academic_progress_percentage > 0:
        print(f"\n✅ ¡ÉXITO! Progreso calculado correctamente")
    else:
        print(f"\n⚠️ El progreso sigue en 0%. Posibles causas:")
        print(f"   - El plan no tiene asignaturas definidas")
        print(f"   - El método de cálculo del plan no está configurado")
        print(f"   - Las asignaturas completadas no están en el plan")
    
    print(f"\n" + "=" * 80)
