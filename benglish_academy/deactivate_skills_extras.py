#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para desactivar skills extras (bskill_number 5 y 6) del catálogo.

Este script marca como active=False todas las skills con bskill_number > 4,
para que el wizard de historial retroactivo NO las genere.

USO EN ODOO SHELL:
    python odoo-bin shell -c odoo.conf -d odoo_db
    >>> exec(open('/path/to/deactivate_skills_extras.py').read())

O EJECUTAR DIRECTAMENTE:
    python odoo-bin shell -c odoo.conf -d odoo_db < deactivate_skills_extras.py
"""

import logging

_logger = logging.getLogger(__name__)


def deactivate_skills_extras(env):
    """
    Desactiva todas las skills con bskill_number > 4 (las skills 5 y 6).
    """
    Subject = env['benglish.subject'].sudo()
    
    print("\n" + "=" * 80)
    print("DESACTIVACIÓN DE SKILLS EXTRAS (bskill_number 5 y 6)")
    print("=" * 80)
    
    # Buscar todas las skills extras
    skills_extras = Subject.search([
        ('subject_category', '=', 'bskills'),
        ('bskill_number', '>', 4),
        ('active', '=', True)  # Solo las que están activas
    ])
    
    if not skills_extras:
        print("✓ No hay skills extras activas. Todo correcto.")
        return
    
    print(f"\n📋 Skills extras encontradas: {len(skills_extras)}")
    print("-" * 80)
    
    # Agrupar por programa y unidad para mostrar
    by_program = {}
    for skill in skills_extras:
        prog_name = skill.program_id.name if skill.program_id else 'Sin programa'
        if prog_name not in by_program:
            by_program[prog_name] = {}
        
        unit = skill.unit_number or 0
        if unit not in by_program[prog_name]:
            by_program[prog_name][unit] = []
        
        by_program[prog_name][unit].append(skill)
    
    # Mostrar detalle
    for prog_name, units in sorted(by_program.items()):
        print(f"\n{prog_name}:")
        for unit, skills in sorted(units.items()):
            print(f"  Unit {unit}:")
            for skill in skills:
                print(f"    • bskill_{skill.bskill_number}: {skill.name}")
    
    print("\n" + "-" * 80)
    print(f"TOTAL: {len(skills_extras)} skills extras que serán desactivadas")
    print("-" * 80)
    
    # DESACTIVAR
    print("\n🔄 Desactivando skills extras...")
    
    try:
        skills_extras.write({'active': False})
        env.cr.commit()
        
        print(f"✅ {len(skills_extras)} skills extras desactivadas correctamente")
        print("\n📝 Ahora:")
        print("   1. El wizard de historial retroactivo solo generará skills 1-4")
        print("   2. Los students nuevos tendrán progreso correcto (4 skills por unit)")
        print("   3. Puedes eliminar y recrear el estudiante de prueba")
        
    except Exception as e:
        env.cr.rollback()
        print(f"❌ ERROR al desactivar: {e}")
        raise


if __name__ == '__main__':
    # Si se ejecuta desde odoo shell
    deactivate_skills_extras(env)
