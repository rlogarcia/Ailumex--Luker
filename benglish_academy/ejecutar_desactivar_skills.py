#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script EJECUTABLE para desactivar skills extras del catálogo.

Este script SE EJECUTARÁ AUTOMÁTICAMENTE y desactivará las skills 5-6-7.
"""

import sys
import os

# Configurar paths
sys.path.insert(0, r'C:\Program Files\Odoo 18.0.20250614\server')
os.chdir(r'C:\Program Files\Odoo 18.0.20250614\server')

# Importar Odoo
import odoo
from odoo import api

# Configurar
odoo.tools.config.parse_config(['-c', r'C:\Program Files\Odoo 18.0.20250614\server\odoo.conf', '--stop-after-init'])

# Obtener registry y environment
registry = odoo.registry('BenglishV1')
with registry.cursor() as cr:
    env = api.Environment(cr, 1, {})
    
    Subject = env['benglish.subject'].sudo()
    
    print("\n" + "=" * 80)
    print("DESACTIVACIÓN DE SKILLS EXTRAS (5-6-7)")
    print("=" * 80)
    
    # Buscar skills extras ACTIVAS
    skills_extras = Subject.search([
        ('subject_category', '=', 'bskills'),
        ('bskill_number', '>', 4),
        ('active', '=', True)
    ])
    
    if not skills_extras:
        print("\n✅ No hay skills extras activas. El catálogo ya está correcto.")
    else:
        print(f"\n📋 Skills extras encontradas: {len(skills_extras)}")
        print("-" * 80)
        
        # Agrupar por programa
        by_program = {}
        for skill in skills_extras:
            prog_name = skill.program_id.name if skill.program_id else 'Sin programa'
            if prog_name not in by_program:
                by_program[prog_name] = []
            by_program[prog_name].append(skill)
        
        for prog_name, skills in sorted(by_program.items()):
            print(f"\n{prog_name}: {len(skills)} skills")
            # Mostrar solo primeras 3 como muestra
            for skill in sorted(skills, key=lambda s: (s.unit_number, s.bskill_number))[:3]:
                print(f"  Unit {skill.unit_number} bskill_{skill.bskill_number}: {skill.name[:40]}")
            if len(skills) > 3:
                print(f"  ... y {len(skills) - 3} más")
        
        print("\n" + "-" * 80)
        print(f"TOTAL: {len(skills_extras)} skills que serán desactivadas")
        print("-" * 80)
        
        # DESACTIVAR
        print("\n🔄 Desactivando skills extras...")
        
        try:
            skills_extras.write({'active': False})
            cr.commit()
            
            print(f"\n✅ ¡ÉXITO! {len(skills_extras)} skills extras desactivadas")
            
            # Verificar
            remaining = Subject.search([
                ('subject_category', '=', 'bskills'),
                ('bskill_number', '>', 4),
                ('active', '=', True)
            ])
            
            if remaining:
                print(f"\n⚠️ ADVERTENCIA: Aún quedan {len(remaining)} skills extras activas")
            else:
                print("\n✅ Verificado: Todas las skills extras (5-6-7) están desactivadas")
            
            # Mostrar ejemplo de Unit 1
            print("\n" + "=" * 80)
            print("VERIFICACIÓN: Skills de Unit 1")
            print("=" * 80)
            
            unit1_skills = Subject.search([
                ('subject_category', '=', 'bskills'),
                ('unit_number', '=', 1)
            ], order='bskill_number')
            
            for skill in unit1_skills:
                status = "✅ ACTIVA" if skill.active else "❌ INACTIVA"
                print(f"  bskill_{skill.bskill_number}: {skill.name[:40]:40} {status}")
            
            active_count = len([s for s in unit1_skills if s.active])
            print(f"\nUnit 1: {active_count} skills activas (esperado: 4)")
            
            if active_count == 4:
                print("✅ ¡PERFECTO! Solo 4 skills activas por unidad")
            else:
                print(f"⚠️ Esperado 4, encontrado {active_count}")
            
        except Exception as e:
            cr.rollback()
            print(f"\n❌ ERROR: {e}")
            sys.exit(1)
    
    print("\n" + "=" * 80)
    print("✅ PROCESO COMPLETADO")
    print("=" * 80)
    print("""
📝 PRÓXIMOS PASOS:

1. ✅ Catálogo corregido (skills 5-6-7 desactivadas)
2. 🗑️ Eliminar estudiante de prueba desde Odoo UI
3. ➕ Recrear estudiante con mismos datos
4. 🔄 Ejecutar historial retroactivo
5. ✔️ Verificar: 4 skills por unidad (no 6-7)
6. 🌐 Verificar portal: progreso correcto

⚠️ NOTA IMPORTANTE:
Las skills 5-6-7 están DESACTIVADAS pero siguen en la base de datos.
Si en el futuro quieres reemplazar una skill:
1. Desactivar la skill actual (ej: skill 2 → active=False)
2. Activar la skill extra (ej: skill 5 → active=True)
    """)
