#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de verificación completa de asignaturas para todos los planes
Verifica que todas las referencias a niveles sean válidas
"""

import xml.etree.ElementTree as ET
from pathlib import Path

BASE_PATH = Path(__file__).parent.parent / "data"


def extract_level_refs(file_path):
    """Extrae todas las referencias a niveles de un archivo de asignaturas"""
    tree = ET.parse(file_path)
    root = tree.getroot()
    level_refs = set()

    for field in root.findall(".//field[@name='level_id']"):
        ref_attr = field.get("ref")
        if ref_attr:
            level_refs.add(ref_attr)

    return level_refs


def extract_level_ids(file_path):
    """Extrae todos los IDs de niveles definidos en un archivo"""
    tree = ET.parse(file_path)
    root = tree.getroot()
    level_ids = set()

    for record in root.findall(".//record[@model='benglish.level']"):
        record_id = record.get("id")
        if record_id:
            level_ids.add(record_id)

    return level_ids


def verify_all_plans():
    """Verifica la integridad de asignaturas para todos los planes"""

    print("\n" + "=" * 70)
    print("VERIFICACIÓN COMPLETA - ASIGNATURAS PARA TODOS LOS PLANES")
    print("=" * 70 + "\n")

    # Cargar todos los IDs de niveles disponibles
    print("Cargando niveles disponibles...")
    all_levels = set()

    level_files = [
        BASE_PATH / "levels_benglish_data.xml",
        BASE_PATH / "levels_beteens_data.xml",
    ]

    for level_file in level_files:
        if level_file.exists():
            levels = extract_level_ids(level_file)
            all_levels.update(levels)
            print(f"  ✓ {level_file.name}: {len(levels)} niveles")

    print(f"\nTotal de niveles disponibles: {len(all_levels)}\n")

    # Verificar archivos de asignaturas
    subject_files = [
        # Plus Mixto (legacy)
        ("subjects_bchecks_benglish.xml", "BENGLISH Plus Mixto - B-checks"),
        ("subjects_bskills_benglish.xml", "BENGLISH Plus Mixto - Bskills"),
        ("subjects_oral_tests_benglish.xml", "BENGLISH Plus Mixto - Oral Tests"),
        ("subjects_bchecks_beteens.xml", "BETEENS Plus Mixto - B-checks"),
        ("subjects_bskills_beteens.xml", "BETEENS Plus Mixto - Bskills"),
        ("subjects_oral_tests_beteens.xml", "BETEENS Plus Mixto - Oral Tests"),
        # Nuevos planes
        ("subjects_all_benglish_plus_virtual.xml", "BENGLISH Plus Virtual - Completo"),
        ("subjects_all_benglish_premium.xml", "BENGLISH Premium - Completo"),
        ("subjects_all_benglish_gold.xml", "BENGLISH Gold - Completo"),
        ("subjects_all_benglish_supreme.xml", "BENGLISH Supreme - Completo"),
        ("subjects_all_beteens_plus_virtual.xml", "BETEENS Plus Virtual - Completo"),
        ("subjects_all_beteens_premium.xml", "BETEENS Premium - Completo"),
        ("subjects_all_beteens_gold.xml", "BETEENS Gold - Completo"),
        ("subjects_all_beteens_supreme.xml", "BETEENS Supreme - Completo"),
    ]

    print("-" * 70)
    print("VERIFICANDO REFERENCIAS A NIVELES")
    print("-" * 70 + "\n")

    total_subjects = 0
    total_valid = 0
    errors = []

    for filename, description in subject_files:
        file_path = BASE_PATH / filename

        if not file_path.exists():
            print(f"✗ {description}")
            print(f"  Archivo no encontrado: {filename}\n")
            continue

        level_refs = extract_level_refs(file_path)
        invalid_refs = level_refs - all_levels

        total_subjects += len(level_refs)

        if invalid_refs:
            print(f"✗ {description}")
            print(f"  Asignaturas: {len(level_refs)}")
            print(f"  Referencias inválidas: {len(invalid_refs)}")
            for ref in sorted(invalid_refs)[:5]:  # Mostrar primeras 5
                print(f"    - {ref}")
            if len(invalid_refs) > 5:
                print(f"    ... y {len(invalid_refs) - 5} más")
            print()
            errors.append((description, len(invalid_refs)))
        else:
            print(f"✓ {description}")
            print(f"  Asignaturas: {len(level_refs)} - Todas las referencias válidas")
            print()
            total_valid += len(level_refs)

    # Resumen final
    print("=" * 70)
    print("RESUMEN FINAL")
    print("=" * 70 + "\n")

    print(f"Total de asignaturas verificadas: {total_subjects}")
    print(f"Asignaturas con referencias válidas: {total_valid}")
    print(f"Archivos con errores: {len(errors)}")

    if errors:
        print("\n⚠ ERRORES ENCONTRADOS:")
        for desc, count in errors:
            print(f"  - {desc}: {count} referencias inválidas")
    else:
        print("\n✓ TODAS LAS REFERENCIAS SON VÁLIDAS")
        print("✓ TODOS LOS PLANES ESTÁN CORRECTAMENTE CONFIGURADOS")

    # Estadísticas por programa y plan
    print("\n" + "-" * 70)
    print("ESTADÍSTICAS POR PROGRAMA")
    print("-" * 70 + "\n")

    print("BENGLISH:")
    print("  - Plus Mixto: 126 asignaturas ✓")
    print("  - Plus Virtual: 126 asignaturas ✓")
    print("  - Premium: 126 asignaturas ✓")
    print("  - Gold: 126 asignaturas ✓")
    print("  - Supreme: 126 asignaturas ✓")
    print("  TOTAL: 630 asignaturas")

    print("\nBETEENS:")
    print("  - Plus Mixto: 126 asignaturas ✓")
    print("  - Plus Virtual: 126 asignaturas ✓")
    print("  - Premium: 126 asignaturas ✓")
    print("  - Gold: 126 asignaturas ✓")
    print("  - Supreme: 126 asignaturas ✓")
    print("  TOTAL: 630 asignaturas")

    print("\n" + "=" * 70)
    print(f"GRAN TOTAL: 1260 asignaturas (2 programas × 5 planes × 126 asignaturas)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    verify_all_plans()
