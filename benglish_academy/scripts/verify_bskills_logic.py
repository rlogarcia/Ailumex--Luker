#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICACIÓN DETALLADA: Lógica de Bskills por Plan
Confirma que TODOS los planes tienen 4 Bskills disponibles
y documenta cómo se maneja la diferencia de requisitos
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

BASE_PATH = Path(__file__).parent.parent / "data"


def analyze_bskills_in_file(file_path):
    """Analiza Bskills en un archivo XML y retorna estadísticas detalladas"""
    tree = ET.parse(file_path)
    root = tree.getroot()

    bskills_by_unit = defaultdict(list)
    total_bskills = 0

    for record in root.findall(".//record[@model='benglish.subject']"):
        # Verificar si es Bskill
        category_field = record.find(".//field[@name='subject_category']")
        if category_field is not None and category_field.text == "bskills":
            total_bskills += 1

            # Obtener unit_number
            unit_field = record.find(".//field[@name='unit_number']")
            bskill_field = record.find(".//field[@name='bskill_number']")

            if unit_field is not None and bskill_field is not None:
                unit_num = int(unit_field.text)
                bskill_num = int(bskill_field.text)
                bskills_by_unit[unit_num].append(bskill_num)

    return {"total": total_bskills, "by_unit": dict(bskills_by_unit)}


def main():
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DETALLADA: LÓGICA DE BSKILLS POR PLAN")
    print("=" * 80 + "\n")

    # Archivos a verificar
    files_to_check = {
        "BENGLISH": {
            "Plus Mixto": "subjects_bskills_benglish.xml",
            "Plus Virtual": "subjects_all_benglish_plus_virtual.xml",
            "Premium": "subjects_all_benglish_premium.xml",
            "Gold": "subjects_all_benglish_gold.xml",
            "Supreme": "subjects_all_benglish_supreme.xml",
        },
        "BETEENS": {
            "Plus Mixto": "subjects_bskills_beteens.xml",
            "Plus Virtual": "subjects_all_beteens_plus_virtual.xml",
            "Premium": "subjects_all_beteens_premium.xml",
            "Gold": "subjects_all_beteens_gold.xml",
            "Supreme": "subjects_all_beteens_supreme.xml",
        },
    }

    all_correct = True
    summary = []

    for program, plans in files_to_check.items():
        print(f"\n{'='*80}")
        print(f"{program}")
        print(f"{'='*80}\n")

        for plan_name, filename in plans.items():
            file_path = BASE_PATH / filename

            if not file_path.exists():
                print(f"✗ {plan_name}: Archivo no encontrado - {filename}")
                all_correct = False
                continue

            stats = analyze_bskills_in_file(file_path)

            # Verificar que tenga 96 Bskills (24 unidades × 4 Bskills)
            expected_total = 96

            # Verificar que cada unidad tenga exactamente 4 Bskills
            units_with_4_bskills = sum(
                1
                for unit, bskills in stats["by_unit"].items()
                if len(bskills) == 4 and set(bskills) == {1, 2, 3, 4}
            )

            if stats["total"] == expected_total and units_with_4_bskills == 24:
                status = "✓"
                color = "CORRECTO"
            else:
                status = "✗"
                color = "ERROR"
                all_correct = False

            print(f"{status} {plan_name}:")
            print(f"    Total Bskills: {stats['total']}/{expected_total}")
            print(f"    Unidades con 4 Bskills: {units_with_4_bskills}/24")

            # Verificar algunas unidades específicas
            sample_units = [1, 12, 24]
            for unit in sample_units:
                if unit in stats["by_unit"]:
                    bskills = sorted(stats["by_unit"][unit])
                    print(f"    Unidad {unit}: Bskills {bskills}")

            summary.append(
                {
                    "program": program,
                    "plan": plan_name,
                    "total": stats["total"],
                    "correct": stats["total"] == expected_total
                    and units_with_4_bskills == 24,
                }
            )
            print()

    # Resumen final
    print("\n" + "=" * 80)
    print("RESUMEN FINAL")
    print("=" * 80 + "\n")

    print("📊 ESTADO POR PLAN:\n")
    for item in summary:
        status = "✓" if item["correct"] else "✗"
        print(
            f"{status} {item['program']:8s} - {item['plan']:15s}: {item['total']} Bskills"
        )

    print("\n" + "-" * 80)
    print("ANÁLISIS DE LÓGICA DE NEGOCIO")
    print("-" * 80 + "\n")

    if all_correct:
        print("✅ TODOS LOS PLANES TIENEN 4 BSKILLS DISPONIBLES POR UNIDAD")
        print()
        print("📋 LÓGICA IMPLEMENTADA (CORRECTA):")
        print()
        print("1. BACKEND (Base de Datos - Odoo):")
        print("   • Plus Virtual:    4 Bskills disponibles por unidad ✓")
        print("   • Plus Mixto:      4 Bskills disponibles por unidad ✓")
        print("   • Premium:         4 Bskills disponibles por unidad ✓")
        print("   • Gold:            4 Bskills disponibles por unidad ✓")
        print("   • Supreme:         4 Bskills disponibles por unidad ✓")
        print()
        print("2. VALIDACIÓN (Portal/Frontend - A IMPLEMENTAR):")
        print("   • Plus Virtual:    Validar mínimo 2 Bskills completados")
        print("   • Otros planes:    Validar 4 Bskills completados")
        print()
        print("3. LÓGICA DE PROGRESO:")
        print("   • Estudiante Plus Virtual puede avanzar completando 2 de 4 Bskills")
        print("   • Estudiante otros planes debe completar las 4 Bskills")
        print("   • Backend ofrece flexibilidad: tiene las 4 disponibles")
        print("   • Portal aplica reglas de negocio según plan del estudiante")
        print()
        print("✅ VENTAJAS DE ESTA IMPLEMENTACIÓN:")
        print("   ✓ Flexibilidad: Fácil cambiar requisitos sin tocar datos")
        print("   ✓ Escalabilidad: Agregar nuevos planes con diferentes requisitos")
        print("   ✓ Consistencia: Misma estructura de datos para todos")
        print("   ✓ Auditoría: Se puede ver qué Bskills completó cada estudiante")
        print()
        print("📝 EJEMPLO DE USO EN PORTAL:")
        print()
        print("   # Obtener Bskills de unidad 5 para estudiante Plus Virtual")
        print("   bskills = env['benglish.subject'].search([")
        print("       ('subject_category', '=', 'bskills'),")
        print("       ('unit_number', '=', 5),")
        print("       ('level_id.phase_id.plan_id', '=', student.plan_id.id)")
        print("   ])")
        print("   # Retorna: 4 Bskills (U5-1, U5-2, U5-3, U5-4)")
        print()
        print("   # Verificar si puede avanzar (Plus Virtual: mínimo 2)")
        print("   completed = len([b for b in bskills if b.is_completed_by(student)])")
        print("   min_required = 2 if student.plan_id.code == 'PLUS_VIRTUAL' else 4")
        print("   can_advance = completed >= min_required")
        print()
    else:
        print("❌ ERRORES ENCONTRADOS")
        print("    Algunos planes no tienen la estructura correcta.")
        print("    Revisa los detalles arriba.")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
