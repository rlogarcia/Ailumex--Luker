#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar que las clasificaciones de asignaturas sean correctas:
- B-checks → prerequisite
- Bskills → regular
- Oral Tests → evaluation
"""

import re
from pathlib import Path

BASE_PATH = Path(__file__).parent.parent / "data"

# Archivos a verificar
FILES_TO_CHECK = [
    # Legacy files
    "subjects_bchecks_benglish.xml",
    "subjects_bchecks_beteens.xml",
    "subjects_bskills_benglish.xml",
    "subjects_bskills_beteens.xml",
    "subjects_oral_tests_benglish.xml",
    "subjects_oral_tests_beteens.xml",
    # Generated files - BENGLISH
    "subjects_all_benglish_plus_virtual.xml",
    "subjects_all_benglish_premium.xml",
    "subjects_all_benglish_gold.xml",
    "subjects_all_benglish_supreme.xml",
    # Generated files - BETEENS
    "subjects_all_beteens_plus_virtual.xml",
    "subjects_all_beteens_premium.xml",
    "subjects_all_beteens_gold.xml",
    "subjects_all_beteens_supreme.xml",
]

# Reglas de clasificación esperadas
EXPECTED_CLASSIFICATIONS = {
    "bcheck": "prerequisite",
    "bskills": "regular",
    "oral_test": "evaluation",
}


def extract_records(xml_content):
    """Extrae todos los records de asignaturas del XML"""
    pattern = r'<record id="([^"]+)"[^>]*>(.+?)</record>'
    return re.findall(pattern, xml_content, re.DOTALL)


def get_field_value(record_content, field_name):
    """Extrae el valor de un campo específico del record"""
    pattern = rf'<field name="{field_name}">([^<]+)</field>'
    match = re.search(pattern, record_content)
    return match.group(1) if match else None


def verify_file(filepath):
    """Verifica un archivo XML y retorna estadísticas"""

    if not filepath.exists():
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    records = extract_records(content)

    stats = {
        "total": len(records),
        "bchecks": {"count": 0, "correct": 0, "incorrect": []},
        "bskills": {"count": 0, "correct": 0, "incorrect": []},
        "oral_tests": {"count": 0, "correct": 0, "incorrect": []},
    }

    for record_id, record_content in records:
        category = get_field_value(record_content, "subject_category")
        classification = get_field_value(record_content, "subject_classification")

        if not category or not classification:
            continue

        # Mapear categoría
        if category == "bcheck":
            key = "bchecks"
        elif category == "bskills":
            key = "bskills"
        elif category == "oral_test":
            key = "oral_tests"
        else:
            continue

        stats[key]["count"] += 1

        expected = EXPECTED_CLASSIFICATIONS[category]
        if classification == expected:
            stats[key]["correct"] += 1
        else:
            stats[key]["incorrect"].append(
                {"id": record_id, "expected": expected, "found": classification}
            )

    return stats


def print_file_results(filename, stats):
    """Imprime los resultados de verificación de un archivo"""

    if stats is None:
        print(f"  ⚠️  Archivo no encontrado")
        return False

    all_correct = True

    for key, label in [
        ("bchecks", "B-checks"),
        ("bskills", "Bskills"),
        ("oral_tests", "Oral Tests"),
    ]:
        data = stats[key]
        if data["count"] == 0:
            continue

        if data["correct"] == data["count"]:
            print(f"  ✓ {label}: {data['count']} correctos")
        else:
            all_correct = False
            print(f"  ✗ {label}: {data['correct']}/{data['count']} correctos")
            for error in data["incorrect"]:
                print(
                    f"    - {error['id']}: esperado '{error['expected']}', encontrado '{error['found']}'"
                )

    return all_correct


def main():
    """Ejecuta la verificación completa"""

    print("\n" + "=" * 70)
    print("VERIFICACIÓN DE CLASIFICACIONES DE ASIGNATURAS")
    print("=" * 70 + "\n")

    print("Reglas esperadas:")
    print("  • B-checks → prerequisite")
    print("  • Bskills → regular")
    print("  • Oral Tests → evaluation\n")

    print("=" * 70 + "\n")

    all_files_correct = True
    total_stats = {
        "bchecks": {"count": 0, "correct": 0},
        "bskills": {"count": 0, "correct": 0},
        "oral_tests": {"count": 0, "correct": 0},
    }

    for filename in FILES_TO_CHECK:
        filepath = BASE_PATH / filename
        print(f"📄 {filename}")

        stats = verify_file(filepath)
        file_correct = print_file_results(filename, stats)

        if stats:
            for key in ["bchecks", "bskills", "oral_tests"]:
                total_stats[key]["count"] += stats[key]["count"]
                total_stats[key]["correct"] += stats[key]["correct"]

        if not file_correct:
            all_files_correct = False

        print()

    # Resumen final
    print("=" * 70)
    print("RESUMEN TOTAL")
    print("=" * 70 + "\n")

    for key, label in [
        ("bchecks", "B-checks"),
        ("bskills", "Bskills"),
        ("oral_tests", "Oral Tests"),
    ]:
        data = total_stats[key]
        if data["count"] > 0:
            status = "✓" if data["correct"] == data["count"] else "✗"
            print(f"{status} {label}: {data['correct']}/{data['count']} correctos")

    print("\n" + "=" * 70)

    if all_files_correct:
        print("✅ TODAS LAS CLASIFICACIONES SON CORRECTAS")
    else:
        print("❌ EXISTEN CLASIFICACIONES INCORRECTAS")

    print("=" * 70 + "\n")

    return 0 if all_files_correct else 1


if __name__ == "__main__":
    exit(main())
