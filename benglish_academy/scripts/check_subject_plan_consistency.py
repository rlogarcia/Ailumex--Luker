#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar la consistencia entre asignaturas, niveles, fases y planes.
Detecta asignaturas que puedan estar mal relacionadas.
"""

import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def check_subject_plan_consistency(env):
    """
    Verifica que todas las asignaturas estén correctamente relacionadas con sus planes.
    """
    Subject = env['benglish.subject']
    Plan = env['benglish.plan']
    
    print("\n" + "="*80)
    print("VERIFICACIÓN DE CONSISTENCIA: ASIGNATURAS vs PLANES")
    print("="*80 + "\n")
    
    # Obtener todos los planes
    plans = Plan.search([])
    
    for plan in plans:
        print(f"\n📋 PLAN: {plan.name} ({plan.code})")
        print(f"   Programa: {plan.program_id.name}")
        print(f"   Fases: {len(plan.phase_ids)}")
        print(f"   Niveles: {len(plan.level_ids)}")
        
        # Método 1: A través del campo calculado plan_id
        subjects_by_field = plan.subject_ids
        print(f"   Asignaturas (campo plan_id): {len(subjects_by_field)}")
        
        # Método 2: Buscar a través de los niveles (más confiable)
        subjects_by_levels = Subject.search([
            ('level_id', 'in', plan.level_ids.ids)
        ])
        print(f"   Asignaturas (vía niveles): {len(subjects_by_levels)}")
        
        # Detectar inconsistencias
        if len(subjects_by_field) != len(subjects_by_levels):
            print(f"\n   ⚠️  INCONSISTENCIA DETECTADA!")
            print(f"   Diferencia: {len(subjects_by_levels) - len(subjects_by_field)} asignaturas")
            
            # Encontrar asignaturas que faltan
            missing_subjects = subjects_by_levels - subjects_by_field
            if missing_subjects:
                print(f"\n   ❌ Asignaturas que NO aparecen en plan.subject_ids pero SÍ en niveles:")
                for subj in missing_subjects[:5]:  # Mostrar primeras 5
                    print(f"      - {subj.name} (ID: {subj.id})")
                    print(f"        Nivel: {subj.level_id.name}")
                    print(f"        Fase: {subj.phase_id.name if subj.phase_id else 'N/A'}")
                    print(f"        Plan calculado: {subj.plan_id.name if subj.plan_id else 'N/A'}")
        else:
            print(f"   ✅ Consistencia OK")
        
        # Verificar que todas las asignaturas tengan el plan_id correcto
        wrong_plan_subjects = []
        for subject in subjects_by_levels:
            if subject.plan_id != plan:
                wrong_plan_subjects.append(subject)
        
        if wrong_plan_subjects:
            print(f"\n   ❌ Asignaturas con plan_id INCORRECTO:")
            for subj in wrong_plan_subjects[:5]:
                print(f"      - {subj.name} (ID: {subj.id})")
                print(f"        Plan esperado: {plan.name}")
                print(f"        Plan actual: {subj.plan_id.name if subj.plan_id else 'None'}")
    
    print("\n" + "="*80)
    print("VERIFICACIÓN COMPLETA")
    print("="*80 + "\n")


def fix_subject_plan_field(env):
    """
    Recalcula el campo plan_id para todas las asignaturas.
    """
    Subject = env['benglish.subject']
    
    print("\n" + "="*80)
    print("RECALCULANDO CAMPO plan_id EN ASIGNATURAS")
    print("="*80 + "\n")
    
    subjects = Subject.search([])
    print(f"Total de asignaturas a procesar: {len(subjects)}")
    
    updated = 0
    for subject in subjects:
        old_plan = subject.plan_id
        # Forzar recálculo
        subject._compute_plan_id() if hasattr(subject, '_compute_plan_id') else None
        new_plan = subject.plan_id
        
        if old_plan != new_plan:
            updated += 1
            print(f"  Actualizada: {subject.name}")
            print(f"    Plan anterior: {old_plan.name if old_plan else 'None'}")
            print(f"    Plan nuevo: {new_plan.name if new_plan else 'None'}")
    
    print(f"\n✅ Asignaturas actualizadas: {updated}/{len(subjects)}")
    print("="*80 + "\n")


def run_diagnosis(env):
    """Ejecuta el diagnóstico completo"""
    check_subject_plan_consistency(env)
    
    print("\n¿Desea recalcular los campos plan_id? (s/n): ", end='')
    # En contexto de script, siempre hacemos el diagnóstico solamente
    print("Diagnóstico completado. Para recalcular, ejecute fix_subject_plan_field()")


# Para ejecutar desde shell de Odoo:
# env = api.Environment(cr, SUPERUSER_ID, {})
# from benglish_academy.scripts.check_subject_plan_consistency import run_diagnosis
# run_diagnosis(env)
