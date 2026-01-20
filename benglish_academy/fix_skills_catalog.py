#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script MEJORADO para gestionar skills extras del catálogo.

CONCEPTO ACLARADO:
- Las 6-7 skills son un CATÁLOGO de opciones
- Para cada unidad, el administrador ELIGE cuáles 4 usar
- El problema: historial retroactivo genera TODAS las skills activas (6-7) en lugar de solo las configuradas (4)

SOLUCIÓN:
- MANTENER las skills 5-6-7 en el catálogo (active=True) para que el admin pueda elegirlas
- AGREGAR campo "is_configured_for_curriculum" para marcar las 4 que se usan
- MODIFICAR wizard de historial retroactivo para filtrar por "is_configured_for_curriculum"

USO:
    python odoo-bin shell -c odoo.conf -d odoo_db
    >>> exec(open('/path/to/fix_skills_catalog.py').read())
"""

import logging

_logger = logging.getLogger(__name__)


def analyze_skills_catalog(env):
    """
    Analiza el estado actual del catálogo de skills.
    """
    Subject = env['benglish.subject'].sudo()
    
    print("\n" + "=" * 80)
    print("ANÁLISIS DEL CATÁLOGO DE SKILLS")
    print("=" * 80)
    
    # Buscar TODAS las skills (activas e inactivas)
    all_skills = Subject.search([
        ('subject_category', '=', 'bskills')
    ], order='program_id, unit_number, bskill_number')
    
    # Agrupar por programa y unidad
    by_program_unit = {}
    for skill in all_skills:
        prog_name = skill.program_id.name if skill.program_id else 'Sin programa'
        if prog_name not in by_program_unit:
            by_program_unit[prog_name] = {}
        
        unit = skill.unit_number or 0
        if unit not in by_program_unit[prog_name]:
            by_program_unit[prog_name][unit] = []
        
        by_program_unit[prog_name][unit].append(skill)
    
    # Mostrar estadísticas
    print("\n📊 RESUMEN POR PROGRAMA:")
    print("-" * 80)
    
    for prog_name, units in sorted(by_program_unit.items()):
        print(f"\n{prog_name}:")
        
        # Contar por unit
        for unit in sorted(units.keys())[:3]:  # Mostrar solo primeras 3 units
            skills = units[unit]
            active_skills = [s for s in skills if s.active]
            inactive_skills = [s for s in skills if not s.active]
            
            print(f"  Unit {unit}: {len(active_skills)} activas, {len(inactive_skills)} inactivas")
            for skill in sorted(skills, key=lambda s: s.bskill_number):
                status = "✅ ACTIVA" if skill.active else "❌ INACTIVA"
                print(f"    bskill_{skill.bskill_number}: {skill.name[:35]:35} {status}")
        
        # Total
        total_skills = sum(len(units[u]) for u in units)
        total_active = sum(len([s for s in units[u] if s.active]) for u in units)
        total_inactive = total_skills - total_active
        
        print(f"\n  📋 TOTAL: {total_skills} skills ({total_active} activas, {total_inactive} inactivas)")
        print(f"  📐 Promedio por unidad: {total_active / len(units):.1f} skills activas")
    
    return by_program_unit


def check_field_exists(env):
    """
    Verifica si existe el campo is_configured_for_curriculum.
    """
    Subject = env['benglish.subject']
    
    # Verificar si el campo existe
    if hasattr(Subject, 'is_configured_for_curriculum'):
        print("\n✅ El campo 'is_configured_for_curriculum' YA EXISTE")
        return True
    else:
        print("\n❌ El campo 'is_configured_for_curriculum' NO EXISTE")
        print("   → Necesita agregarse al modelo benglish.subject")
        return False


def proposed_solution(env):
    """
    Muestra la solución propuesta.
    """
    print("\n" + "=" * 80)
    print("💡 SOLUCIÓN PROPUESTA")
    print("=" * 80)
    
    print("""
🎯 ENFOQUE CORRECTO:

1. MANTENER catálogo completo (6-7 skills activas)
   → Permite al admin elegir cuáles usar

2. AGREGAR campo "is_configured_for_curriculum"
   → Marca las 4 skills configuradas para cada unidad
   
3. MODIFICAR wizard de historial retroactivo
   → Filtrar por: active=True AND is_configured_for_curriculum=True
   
4. PORTAL ya está correcto
   → El método _is_optional_bskill() ya identifica skills > 4
   → Las skills 5-6-7 ya se marcan como "opcionales" en el portal

📋 ARCHIVOS A MODIFICAR:

1. models/subject.py
   → Agregar campo: is_configured_for_curriculum = fields.Boolean(default=False)
   
2. wizards/generate_historical_progress_wizard.py
   → Cambiar línea 139:
     DE:   ('active', '=', True),
     A:    ('active', '=', True), ('is_configured_for_curriculum', '=', True),
   
3. data/subjects_bskills_beteens.xml (skills 1-4)
   → Agregar: <field name="is_configured_for_curriculum" eval="True" />
   
4. data/subjects_bskills_extra_beteens.xml (skills 5-6-7)
   → Agregar: <field name="is_configured_for_curriculum" eval="False" />
   
5. Mismo para subjects_bskills.xml y subjects_bskills_extra.xml

⚠️ ALTERNATIVA MÁS SIMPLE (sin modificar código):

Si NO quieres agregar campo nuevo, puedes:
→ Marcar skills 5-6-7 como active=False TEMPORALMENTE
→ Cuando el admin quiera reemplazar una skill:
   1. Desactivar la skill actual (ej: skill 2 → active=False)
   2. Activar la skill extra (ej: skill 5 → active=True)
→ El historial retroactivo solo generará las activas

¿Cuál enfoque prefieres?
    """)


if __name__ == '__main__':
    # Ejecutar análisis
    by_program_unit = analyze_skills_catalog(env)
    
    # Verificar campo
    field_exists = check_field_exists(env)
    
    # Mostrar solución
    proposed_solution(env)
    
    print("\n" + "=" * 80)
    print("🤔 ¿QUÉ HACER AHORA?")
    print("=" * 80)
    print("""
OPCIÓN A (Recomendada - Con nuevo campo):
  → Requiere modificar código (agregar campo is_configured_for_curriculum)
  → Mantiene catálogo completo visible
  → Más flexible para el futuro
  
OPCIÓN B (Rápida - Sin modificar código):
  → Desactivar skills 5-6-7 YA (active=False)
  → Cuando quieras reemplazar, intercambiar active
  → Funciona CON EL CÓDIGO ACTUAL
  
Si eliges OPCIÓN B, ejecuta:
>>> skills_extras = env['benglish.subject'].search([
...     ('subject_category', '=', 'bskills'),
...     ('bskill_number', '>', 4)
... ])
>>> skills_extras.write({'active': False})
>>> env.cr.commit()
    """)
