# -*- coding: utf-8 -*-
"""
Script de diagnóstico para verificar la resolución de asignaturas desde Pools de Electivas.

Uso desde shell de Odoo:
    $ odoo-bin shell -d DATABASE_NAME
    >>> exec(open('d:/AiLumex/Ailumex--Be/portal_student/scripts/diagnose_elective_pools.py').read())

O desde el menú Configuración > Técnico > Scripts de servidor (si está habilitado)
"""

import logging
_logger = logging.getLogger(__name__)

def diagnose_elective_pools():
    """
    Ejecuta diagnóstico de pools de electivas y sesiones configuradas.
    """
    print("\n" + "=" * 80)
    print("🔍 DIAGNÓSTICO DE POOLS DE ELECTIVAS")
    print("=" * 80)
    
    # 1. Buscar todos los pools de electivas activos
    ElectivePool = env['benglish.elective.pool'].sudo()
    pools = ElectivePool.search([('state', '=', 'active')])
    
    print(f"\n📦 POOLS DE ELECTIVAS ACTIVOS: {len(pools)}")
    print("-" * 40)
    
    for pool in pools:
        print(f"\n  📌 {pool.display_name} (ID: {pool.id})")
        print(f"     Fase: {pool.phase_id.name if pool.phase_id else 'N/A'}")
        print(f"     Programa: {pool.program_id.name if pool.program_id else 'N/A'}")
        print(f"     Asignaturas: {len(pool.subject_ids)}")
        
        if pool.subject_ids:
            print("     Listado de asignaturas:")
            for subj in pool.subject_ids.sorted(key=lambda s: (s.sequence, s.name)):
                level_name = subj.level_id.name if subj.level_id else "Sin nivel"
                print(f"       - [{subj.code}] {subj.name} | Nivel: {level_name} | Cat: {subj.subject_category or 'N/A'}")
    
    # 2. Buscar sesiones que usan pools de electivas
    Session = env['benglish.academic.session'].sudo()
    sessions_with_pool = Session.search([
        ('elective_pool_id', '!=', False),
        ('state', 'in', ['active', 'with_enrollment'])
    ])
    
    print(f"\n\n📅 SESIONES CON POOL DE ELECTIVAS: {len(sessions_with_pool)}")
    print("-" * 40)
    
    for session in sessions_with_pool[:10]:  # Limitar a 10 para no saturar
        print(f"\n  🗓️ Sesión ID: {session.id}")
        print(f"     Nombre: {session.display_name}")
        print(f"     Fecha: {session.date}")
        print(f"     Pool: {session.elective_pool_id.display_name}")
        print(f"     Subject ID (placeholder): {session.subject_id.name if session.subject_id else 'N/A'}")
        print(f"     Tipo sesión: {session.session_type}")
        print(f"     Estado: {session.state}")
    
    if len(sessions_with_pool) > 10:
        print(f"\n  ... y {len(sessions_with_pool) - 10} sesiones más")
    
    # 3. Buscar estudiantes activos para probar
    Student = env['benglish.student'].sudo()
    students = Student.search([
        ('state', 'in', ['enrolled', 'active', 'in_progress'])
    ], limit=5)
    
    print(f"\n\n👤 ESTUDIANTES DE PRUEBA: {len(students)}")
    print("-" * 40)
    
    for student in students:
        print(f"\n  🎓 {student.name} (ID: {student.id})")
        print(f"     Programa: {student.program_id.name if student.program_id else 'N/A'}")
        print(f"     Nivel actual: {student.current_level_id.name if student.current_level_id else 'N/A'}")
        
        # Para cada pool activo, intentar resolver asignatura
        for pool in pools[:2]:  # Solo probar con 2 pools
            if pool.subject_ids:
                # Simular sesión con pool
                test_session = sessions_with_pool.filtered(
                    lambda s: s.elective_pool_id.id == pool.id
                )[:1]
                
                if test_session:
                    try:
                        result = test_session._resolve_elective_pool_subject(
                            student,
                            check_completed=True,
                            raise_on_error=False
                        )
                        if result:
                            print(f"     ✅ Pool '{pool.name}' → {result.name} (ID: {result.id})")
                        else:
                            print(f"     ⚠️ Pool '{pool.name}' → Sin asignatura disponible")
                    except Exception as e:
                        print(f"     ❌ Pool '{pool.name}' → Error: {str(e)}")
    
    # 4. Verificar historial académico para completados
    print(f"\n\n📚 VERIFICACIÓN DE HISTORIAL")
    print("-" * 40)
    
    if students and pools:
        student = students[0]
        History = env['benglish.academic.history'].sudo()
        
        for pool in pools[:2]:
            pool_subject_ids = pool.subject_ids.ids
            completed = History.search_count([
                ('student_id', '=', student.id),
                ('subject_id', 'in', pool_subject_ids),
                ('attendance_status', '=', 'attended')
            ])
            
            print(f"\n  Estudiante: {student.name}")
            print(f"  Pool: {pool.name}")
            print(f"  Asignaturas en pool: {len(pool.subject_ids)}")
            print(f"  Completadas (attended): {completed}")
            print(f"  Pendientes: {len(pool.subject_ids) - completed}")
    
    print("\n" + "=" * 80)
    print("✅ DIAGNÓSTICO COMPLETADO")
    print("=" * 80 + "\n")
    
    return {
        'pools': pools,
        'sessions_with_pool': sessions_with_pool,
        'students': students
    }

# Ejecutar diagnóstico
try:
    result = diagnose_elective_pools()
except Exception as e:
    print(f"\n❌ ERROR DURANTE DIAGNÓSTICO: {str(e)}")
    import traceback
    traceback.print_exc()
