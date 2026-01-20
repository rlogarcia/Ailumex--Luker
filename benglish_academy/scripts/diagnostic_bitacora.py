#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Diagnóstico: Bitácora Académica

Ejecutar desde odoo-bin shell:
    odoo-bin shell -d tu_base_de_datos --load=web,benglish_academy
    >>> exec(open('scripts/diagnostic_bitacora.py').read())

O copiar y pegar en el shell de Odoo.
"""

import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

def diagnostic_bitacora_academica(env):
    """
    Ejecuta un diagnóstico completo de la Bitácora Académica.
    
    Args:
        env: Entorno de Odoo (odoo.api.Environment)
    
    Returns:
        dict: Resultados del diagnóstico
    """
    print("\n" + "="*80)
    print("🔍 DIAGNÓSTICO: BITÁCORA ACADÉMICA")
    print("="*80 + "\n")
    
    History = env['benglish.academic.history'].sudo()
    Session = env['benglish.academic.session'].sudo()
    
    # ========================================
    # 1. CONTEO GENERAL DE REGISTROS
    # ========================================
    print("📊 1. ESTADÍSTICAS GENERALES")
    print("-" * 40)
    
    total_history = History.search_count([])
    print(f"   Total de registros en bitácora: {total_history}")
    
    if total_history == 0:
        print("   ⚠️  No hay registros en la bitácora.")
        print("   💡 Posibles causas:")
        print("      - No se han dictado clases (sesiones en estado 'done')")
        print("      - Problema en la creación automática de registros")
        print("      - Base de datos recién inicializada")
        return {"success": False, "error": "no_records"}
    
    # Registros por estado de asistencia
    attended = History.search_count([('attendance_status', '=', 'attended')])
    absent = History.search_count([('attendance_status', '=', 'absent')])
    pending = History.search_count([('attendance_status', '=', 'pending')])
    
    print(f"   ✅ Asistió: {attended} ({attended/total_history*100:.1f}%)")
    print(f"   ❌ Ausente: {absent} ({absent/total_history*100:.1f}%)")
    print(f"   ⏳ Pendiente: {pending} ({pending/total_history*100:.1f}%)")
    
    # Registros con y sin sesión
    with_session = History.search_count([('session_id', '!=', False)])
    without_session = History.search_count([('session_id', '=', False)])
    
    print(f"\n   📅 Con sesión asociada: {with_session}")
    print(f"   ⚠️  Sin sesión asociada: {without_session}")
    
    if without_session > 0:
        print(f"      💡 Hay {without_session} registros sin sesión (posiblemente retroactivos)")
    
    print()
    
    # ========================================
    # 2. DISTRIBUCIÓN POR ESTUDIANTE
    # ========================================
    print("👥 2. DISTRIBUCIÓN POR ESTUDIANTE")
    print("-" * 40)
    
    students_with_history = History.read_group(
        domain=[],
        fields=['student_id'],
        groupby=['student_id']
    )
    
    print(f"   Estudiantes con registros: {len(students_with_history)}")
    
    # Top 5 estudiantes con más registros
    top_students = sorted(
        students_with_history,
        key=lambda x: x['student_id_count'],
        reverse=True
    )[:5]
    
    print(f"\n   🏆 Top 5 estudiantes con más clases:")
    for i, student in enumerate(top_students, 1):
        student_name = student['student_id'][1] if student['student_id'] else 'Sin nombre'
        count = student['student_id_count']
        print(f"      {i}. {student_name}: {count} clases")
    
    print()
    
    # ========================================
    # 3. DISTRIBUCIÓN POR PROGRAMA Y NIVEL
    # ========================================
    print("📚 3. DISTRIBUCIÓN POR PROGRAMA Y NIVEL")
    print("-" * 40)
    
    programs = History.read_group(
        domain=[],
        fields=['program_id'],
        groupby=['program_id']
    )
    
    print(f"   Programas con registros: {len(programs)}")
    for program in programs:
        program_name = program['program_id'][1] if program['program_id'] else 'Sin programa'
        count = program['program_id_count']
        print(f"      • {program_name}: {count} registros")
    
    print()
    
    # ========================================
    # 4. REGISTROS RECIENTES (ÚLTIMOS 30 DÍAS)
    # ========================================
    print("📅 4. REGISTROS RECIENTES (ÚLTIMOS 30 DÍAS)")
    print("-" * 40)
    
    thirty_days_ago = (datetime.now() - timedelta(days=30)).date()
    recent_history = History.search([
        ('session_date', '>=', thirty_days_ago)
    ], order='session_date desc')
    
    print(f"   Registros de los últimos 30 días: {len(recent_history)}")
    
    if len(recent_history) > 0:
        print(f"\n   📝 Últimos 10 registros:")
        for rec in recent_history[:10]:
            student_name = rec.student_id.name[:30] if rec.student_id else "Sin estudiante"
            subject_name = rec.subject_id.name[:20] if rec.subject_id else "Sin asignatura"
            status_emoji = {
                'attended': '✅',
                'absent': '❌',
                'pending': '⏳'
            }.get(rec.attendance_status, '❓')
            
            print(f"      {rec.session_date} | {status_emoji} | {student_name} | {subject_name}")
    else:
        print("   ⚠️  No hay registros recientes")
        print("   💡 Posibles causas:")
        print("      - No se han dictado clases en el último mes")
        print("      - Las clases no se están marcando como 'done'")
    
    print()
    
    # ========================================
    # 5. VERIFICAR SESIONES TERMINADAS
    # ========================================
    print("🎓 5. SESIONES TERMINADAS VS REGISTROS DE HISTORIAL")
    print("-" * 40)
    
    sessions_done = Session.search([('state', '=', 'done')])
    print(f"   Sesiones en estado 'done': {len(sessions_done)}")
    
    # Contar inscripciones en sesiones terminadas
    total_enrollments_done = sum(len(s.enrollment_ids) for s in sessions_done)
    print(f"   Total de inscripciones en sesiones terminadas: {total_enrollments_done}")
    
    # Comparar con registros de historial
    history_with_session_done = History.search([
        ('session_id', '!=', False),
        ('session_id.state', '=', 'done')
    ])
    
    print(f"   Registros de historial con sesión 'done': {len(history_with_session_done)}")
    
    if total_enrollments_done != len(history_with_session_done):
        diff = total_enrollments_done - len(history_with_session_done)
        print(f"\n   ⚠️  DISCREPANCIA DETECTADA: {abs(diff)} registros")
        if diff > 0:
            print(f"      💡 Faltan {diff} registros de historial")
            print(f"      🔧 Posible solución: Volver a marcar sesiones como 'done'")
        else:
            print(f"      💡 Hay {abs(diff)} registros de más")
            print(f"      🔧 Posible causa: Registros duplicados o retroactivos")
    else:
        print(f"   ✅ Sincronización correcta: sesiones terminadas = registros de historial")
    
    print()
    
    # ========================================
    # 6. VERIFICAR INTEGRIDAD DE DATOS
    # ========================================
    print("🔍 6. VERIFICACIÓN DE INTEGRIDAD DE DATOS")
    print("-" * 40)
    
    # Registros sin estudiante
    no_student = History.search_count([('student_id', '=', False)])
    print(f"   Registros sin estudiante: {no_student}")
    if no_student > 0:
        print(f"      ⚠️  Revisar: estos registros pueden ser inválidos")
    
    # Registros sin asignatura
    no_subject = History.search_count([('subject_id', '=', False)])
    print(f"   Registros sin asignatura: {no_subject}")
    if no_subject > 0:
        print(f"      ⚠️  Revisar: estos registros pueden ser inválidos")
    
    # Registros sin fecha
    no_date = History.search_count([('session_date', '=', False)])
    print(f"   Registros sin fecha: {no_date}")
    if no_date > 0:
        print(f"      ⚠️  Revisar: estos registros pueden ser inválidos")
    
    # Buscar posibles duplicados (mismo estudiante + misma sesión)
    duplicates = env.cr.execute("""
        SELECT student_id, session_id, COUNT(*) as count
        FROM benglish_academic_history
        WHERE student_id IS NOT NULL AND session_id IS NOT NULL
        GROUP BY student_id, session_id
        HAVING COUNT(*) > 1
    """)
    duplicate_count = len(env.cr.fetchall())
    
    print(f"   Registros duplicados (mismo estudiante + sesión): {duplicate_count}")
    if duplicate_count > 0:
        print(f"      ⚠️  PROBLEMA CRÍTICO: Hay registros duplicados")
        print(f"      🔧 Solución: Ejecutar limpieza de duplicados")
    
    print()
    
    # ========================================
    # 7. VERIFICAR CONSTRAINT SQL
    # ========================================
    print("🔒 7. VERIFICACIÓN DE CONSTRAINT SQL")
    print("-" * 40)
    
    # Verificar que el constraint UNIQUE(student_id, session_id) existe
    env.cr.execute("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'benglish_academic_history'
        AND constraint_type = 'UNIQUE'
    """)
    constraints = env.cr.fetchall()
    
    has_unique_constraint = any('unique_student_session' in str(c) for c in constraints)
    
    if has_unique_constraint:
        print(f"   ✅ Constraint UNIQUE(student_id, session_id) está activo")
    else:
        print(f"   ⚠️  Constraint UNIQUE(student_id, session_id) NO encontrado")
        print(f"      🔧 Solución: Actualizar el módulo con 'odoo-bin -u benglish_academy'")
    
    print()
    
    # ========================================
    # 8. RESUMEN Y RECOMENDACIONES
    # ========================================
    print("="*80)
    print("📋 RESUMEN Y RECOMENDACIONES")
    print("="*80 + "\n")
    
    issues = []
    
    if total_history == 0:
        issues.append("❌ No hay registros en la bitácora")
    
    if without_session > total_history * 0.5:
        issues.append(f"⚠️  Más del 50% de registros sin sesión asociada ({without_session}/{total_history})")
    
    if pending > total_history * 0.3:
        issues.append(f"⚠️  Más del 30% de asistencias están pendientes ({pending}/{total_history})")
    
    if total_enrollments_done != len(history_with_session_done):
        issues.append("⚠️  Discrepancia entre sesiones terminadas y registros de historial")
    
    if duplicate_count > 0:
        issues.append("❌ CRÍTICO: Hay registros duplicados")
    
    if not has_unique_constraint:
        issues.append("❌ CRÍTICO: Constraint SQL no está activo")
    
    if issues:
        print("🚨 PROBLEMAS DETECTADOS:\n")
        for issue in issues:
            print(f"   {issue}")
        
        print("\n💡 ACCIONES RECOMENDADAS:\n")
        print("   1. Actualizar el módulo: odoo-bin -u benglish_academy")
        print("   2. Verificar que las sesiones se marquen como 'done' correctamente")
        print("   3. Si hay duplicados, ejecutar script de limpieza")
        print("   4. Revisar logs de Odoo para errores relacionados con [ACADEMIC HISTORY]")
    else:
        print("✅ TODAS LAS VERIFICACIONES PASARON")
        print("\n   La Bitácora Académica está funcionando correctamente.")
        print("   No se detectaron problemas de integridad o sincronización.")
    
    print("\n" + "="*80 + "\n")
    
    return {
        "success": True,
        "total_records": total_history,
        "attended": attended,
        "absent": absent,
        "pending": pending,
        "students_count": len(students_with_history),
        "sessions_done": len(sessions_done),
        "issues": issues
    }


# ========================================
# EJECUTAR DIAGNÓSTICO
# ========================================
if __name__ == '__main__':
    # Si se ejecuta desde odoo-bin shell, 'env' ya está disponible
    try:
        result = diagnostic_bitacora_academica(env)
        print("\n✅ Diagnóstico completado exitosamente\n")
    except NameError:
        print("\n⚠️  Este script debe ejecutarse desde odoo-bin shell")
        print("   Ejemplo: odoo-bin shell -d tu_base_de_datos")
        print("   >>> exec(open('scripts/diagnostic_bitacora.py').read())\n")
