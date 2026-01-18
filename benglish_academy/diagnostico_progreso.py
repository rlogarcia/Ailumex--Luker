#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Diagnóstico y Corrección de Progreso de Estudiantes
===============================================================

PROBLEMAS IDENTIFICADOS:
1. Historial retroactivo generó más skills de las debidas (6-7 en lugar de 4)
2. max_unit_completed puede estar mal calculado
3. B-checks no aparecen a estudiantes que deberían verlos

SOLUCIÓN:
- Diagnostica el historial académico del estudiante
- Identifica asignaturas duplicadas o extras (skills 5-6)
- Recalcula max_unit_completed correctamente
- Propone limpieza de historial si es necesario
"""

import sys
import os

# Agregar path de Odoo
sys.path.append('/opt/odoo')  # Ajustar según instalación

def diagnose_student_progress(env, student_code):
    """
    Diagnostica el progreso de un estudiante específico.
    """
    Student = env['benglish.student']
    History = env['benglish.academic.history']
    
    student = Student.search([('code', '=', student_code)], limit=1)
    if not student:
        print(f"❌ Estudiante {student_code} no encontrado")
        return
    
    print(f"\n{'='*80}")
    print(f"DIAGNÓSTICO DE PROGRESO: {student.name} ({student.code})")
    print(f"{'='*80}\n")
    
    # 1. Información básica
    print(f"📋 INFORMACIÓN BÁSICA:")
    print(f"  • Programa: {student.program_id.name if student.program_id else 'N/A'}")
    print(f"  • Nivel actual: {student.current_level_id.name if student.current_level_id else 'N/A'}")
    print(f"  • Max unit del nivel: {student.current_level_id.max_unit if student.current_level_id else 'N/A'}")
    print(f"  • max_unit_completed: {student.max_unit_completed}")
    print(f"  • Unidad siguiente: {student.max_unit_completed + 1}\n")
    
    # 2. Historial académico completo
    history = History.search([
        ('student_id', '=', student.id),
        ('attendance_status', '=', 'attended')
    ], order='subject_id')
    
    print(f"📚 HISTORIAL ACADÉMICO ({len(history)} clases completadas):\n")
    
    # Agrupar por unidad
    by_unit = {}
    for h in history:
        subject = h.subject_id
        if not subject:
            continue
        
        unit = subject.unit_number or 0
        if unit not in by_unit:
            by_unit[unit] = {
                'bcheck': [],
                'skills': [],
                'oral_test': []
            }
        
        if subject.subject_category == 'bcheck':
            by_unit[unit]['bcheck'].append(subject)
        elif subject.subject_category == 'bskills':
            by_unit[unit]['skills'].append(subject)
        elif subject.subject_category == 'oral_test':
            by_unit[unit]['oral_test'].append(subject)
    
    # Análisis por unidad
    print(f"{'Unit':<6} {'B-check':<10} {'Skills':<30} {'Problemas'}")
    print(f"{'-'*80}")
    
    problems = []
    for unit in sorted(by_unit.keys()):
        if unit == 0:
            continue
        
        data = by_unit[unit]
        bcheck_count = len(data['bcheck'])
        skills_count = len(data['skills'])
        
        # Identificar skills por número
        skill_numbers = sorted([s.bskill_number for s in data['skills'] if s.bskill_number])
        skill_str = ','.join(str(n) for n in skill_numbers) if skill_numbers else '-'
        
        # Detectar problemas
        problem = []
        if bcheck_count > 1:
            problem.append(f"⚠️ {bcheck_count} B-checks (debería ser 1)")
        elif bcheck_count == 0:
            problem.append(f"⚠️ Sin B-check")
        
        if skills_count > 4:
            problem.append(f"⚠️ {skills_count} skills (debería ser 4)")
            # Identificar cuáles son extras
            extras = [n for n in skill_numbers if n > 4]
            if extras:
                problem.append(f"   Skills extras: {extras}")
        elif skills_count < 4:
            problem.append(f"⚠️ {skills_count} skills (incompleto)")
        
        if problem:
            problems.append((unit, problem))
        
        problem_str = ' | '.join(problem) if problem else '✅ OK'
        print(f"U{unit:<5} {bcheck_count:<10} [{skill_str}] ({skills_count} total)  {problem_str}")
    
    # 3. Resumen de problemas
    print(f"\n{'='*80}")
    print(f"RESUMEN DE PROBLEMAS:")
    print(f"{'='*80}\n")
    
    if not problems:
        print("✅ No se detectaron problemas en el historial")
    else:
        print(f"❌ Se detectaron {len(problems)} unidades con problemas:\n")
        for unit, probs in problems:
            print(f"  • Unidad {unit}:")
            for p in probs:
                print(f"    {p}")
    
    # 4. Verificar max_unit_completed
    print(f"\n{'='*80}")
    print(f"VERIFICACIÓN DE max_unit_completed:")
    print(f"{'='*80}\n")
    
    completed_units = [u for u in by_unit.keys() if u > 0]
    if completed_units:
        real_max = max(completed_units)
        current_max = student.max_unit_completed
        
        print(f"  • max_unit_completed actual: {current_max}")
        print(f"  • max_unit_completed real (según historial): {real_max}")
        
        if current_max != real_max:
            print(f"\n  ⚠️ INCONSISTENCIA DETECTADA:")
            print(f"     El valor actual ({current_max}) no coincide con el historial ({real_max})")
            print(f"     Sugerencia: Ejecutar student._compute_max_unit_from_history()")
        else:
            print(f"\n  ✅ max_unit_completed es correcto")
    
    # 5. Recomendaciones
    print(f"\n{'='*80}")
    print(f"RECOMENDACIONES:")
    print(f"{'='*80}\n")
    
    if problems:
        print(f"🔧 ACCIONES RECOMENDADAS:\n")
        
        # Contar skills extras
        total_extras = 0
        for unit, probs in problems:
            for skill in by_unit.get(unit, {}).get('skills', []):
                if skill.bskill_number and skill.bskill_number > 4:
                    total_extras += 1
        
        if total_extras > 0:
            print(f"  1. ELIMINAR SKILLS EXTRAS (bskill_number > 4):")
            print(f"     • Total de skills extras: {total_extras}")
            print(f"     • Ejecutar: python limpiar_skills_extras.py {student.code}")
        
        # Verificar B-checks faltantes
        missing_bchecks = [unit for unit, probs in problems 
                          if any('Sin B-check' in str(p) for p in probs)]
        if missing_bchecks:
            print(f"\n  2. B-CHECKS FALTANTES:")
            print(f"     • Unidades sin B-check: {missing_bchecks}")
            print(f"     • Verificar si el estudiante realmente tomó esas clases")
        
        print(f"\n  3. RECALCULAR PROGRESO:")
        print(f"     • Después de limpiar, ejecutar:")
        print(f"       student._compute_max_unit_from_history()")
    
    return student, history, problems


def clean_extra_skills(env, student_code, dry_run=True):
    """
    Elimina skills extras (bskill_number > 4) del historial.
    
    Args:
        dry_run: Si es True, solo muestra qué se eliminaría sin hacerlo
    """
    Student = env['benglish.student']
    History = env['benglish.academic.history']
    
    student = Student.search([('code', '=', student_code)], limit=1)
    if not student:
        print(f"❌ Estudiante {student_code} no encontrado")
        return
    
    # Buscar historial con skills extras
    extra_skills_history = History.search([
        ('student_id', '=', student.id),
        ('subject_id.subject_category', '=', 'bskills'),
        ('subject_id.bskill_number', '>', 4)
    ])
    
    print(f"\n{'='*80}")
    print(f"LIMPIEZA DE SKILLS EXTRAS: {student.name} ({student.code})")
    print(f"{'='*80}\n")
    
    if not extra_skills_history:
        print("✅ No se encontraron skills extras en el historial")
        return
    
    print(f"📋 Skills extras encontrados: {len(extra_skills_history)}\n")
    
    for h in extra_skills_history:
        subject = h.subject_id
        print(f"  • Unit {subject.unit_number} - Skill {subject.bskill_number} - {subject.name}")
        print(f"    Fecha: {h.session_date} | ID: {h.id}")
    
    if dry_run:
        print(f"\n⚠️ MODO DRY-RUN: No se eliminará nada")
        print(f"   Para eliminar realmente, ejecutar con dry_run=False")
    else:
        print(f"\n❌ ELIMINANDO {len(extra_skills_history)} registros...")
        extra_skills_history.unlink()
        print(f"✅ Historial limpiado")
        
        # Recalcular progreso
        print(f"\n🔄 Recalculando progreso...")
        student._compute_max_unit_from_history()
        print(f"✅ max_unit_completed actualizado: {student.max_unit_completed}")


def main():
    """
    Función principal para ejecutar desde línea de comandos.
    """
    import odoo
    from odoo import api
    
    # Inicializar Odoo
    odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf'])
    
    with api.Environment.manage():
        registry = odoo.registry(odoo.tools.config['db_name'])
        with registry.cursor() as cr:
            env = api.Environment(cr, odoo.SUPERUSER_ID, {})
            
            if len(sys.argv) < 2:
                print("Uso: python diagnostico_progreso.py <codigo_estudiante> [--clean]")
                sys.exit(1)
            
            student_code = sys.argv[1]
            do_clean = '--clean' in sys.argv
            
            # Diagnóstico
            student, history, problems = diagnose_student_progress(env, student_code)
            
            # Limpieza si se solicita
            if do_clean and problems:
                print(f"\n{'='*80}")
                dry_run = '--dry-run' not in sys.argv
                clean_extra_skills(env, student_code, dry_run=dry_run)
                
                if not dry_run:
                    cr.commit()
                    print(f"\n✅ Cambios guardados en la base de datos")


if __name__ == '__main__':
    main()
