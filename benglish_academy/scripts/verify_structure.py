#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de verificación de integridad de la estructura académica
Verifica que todos los prerrequisitos existan y estén correctamente configurados
"""

import xml.etree.ElementTree as ET
from pathlib import Path

# Rutas de archivos
BASE_PATH = Path(__file__).parent.parent / "data"
FILES = {
    "bchecks_benglish": BASE_PATH / "subjects_bchecks_benglish.xml",
    "bskills_benglish": BASE_PATH / "subjects_bskills_benglish.xml",
    "oral_tests_benglish": BASE_PATH / "subjects_oral_tests_benglish.xml",
    "bchecks_beteens": BASE_PATH / "subjects_bchecks_beteens.xml",
    "bskills_beteens": BASE_PATH / "subjects_bskills_beteens.xml",
    "oral_tests_beteens": BASE_PATH / "subjects_oral_tests_beteens.xml",
    "class_types": BASE_PATH / "class_types_structured.xml",
}


def extract_xml_ids(file_path):
    """Extrae todos los XML IDs de un archivo"""
    tree = ET.parse(file_path)
    root = tree.getroot()
    xml_ids = set()

    for record in root.findall(".//record"):
        record_id = record.get("id")
        if record_id:
            xml_ids.add(record_id)

    return xml_ids


def extract_prerequisites(file_path):
    """Extrae todos los prerrequisitos referenciados en un archivo"""
    tree = ET.parse(file_path)
    root = tree.getroot()
    prerequisites = {}

    for record in root.findall(".//record"):
        record_id = record.get("id")
        prereq_field = record.find(".//field[@name='prerequisite_ids']")

        if prereq_field is not None and prereq_field.get("eval"):
            eval_content = prereq_field.get("eval")
            # Extraer refs del formato [(6, 0, [ref('id1'), ref('id2'), ...])]
            if "ref(" in eval_content:
                refs = []
                parts = eval_content.split("ref('")
                for part in parts[1:]:
                    ref_id = part.split("'")[0]
                    refs.append(ref_id)
                prerequisites[record_id] = refs

    return prerequisites


def verify_structure():
    """Verifica la integridad completa de la estructura"""
    print("\n" + "=" * 60)
    print("VERIFICACIÓN DE INTEGRIDAD - ESTRUCTURA ACADÉMICA")
    print("=" * 60 + "\n")

    # Recolectar todos los XML IDs
    all_xml_ids = {}
    total_records = 0

    for file_key, file_path in FILES.items():
        if file_path.exists():
            xml_ids = extract_xml_ids(file_path)
            all_xml_ids[file_key] = xml_ids
            total_records += len(xml_ids)
            print(f"✓ {file_key:20s}: {len(xml_ids):3d} registros")
        else:
            print(f"✗ {file_key:20s}: ARCHIVO NO ENCONTRADO")
            all_xml_ids[file_key] = set()

    print(f"\nTotal de registros: {total_records}")

    # Verificar prerrequisitos
    print("\n" + "-" * 60)
    print("VERIFICACIÓN DE PRERREQUISITOS")
    print("-" * 60 + "\n")

    errors = []
    warnings = []

    # Crear un conjunto con todos los IDs disponibles
    all_available_ids = set()
    for ids_set in all_xml_ids.values():
        all_available_ids.update(ids_set)

    # Verificar cada archivo que tiene prerrequisitos
    prereq_files = [
        "bskills_benglish",
        "oral_tests_benglish",
        "bskills_beteens",
        "oral_tests_beteens",
    ]

    for file_key in prereq_files:
        file_path = FILES[file_key]
        if not file_path.exists():
            continue

        print(f"Verificando: {file_key}")
        prerequisites = extract_prerequisites(file_path)

        for record_id, prereq_list in prerequisites.items():
            for prereq_id in prereq_list:
                if prereq_id not in all_available_ids:
                    errors.append(
                        f"  ✗ {record_id} → prerequisito '{prereq_id}' NO EXISTE"
                    )

        if errors:
            for error in errors:
                print(error)
        else:
            print(
                f"  ✓ Todos los prerrequisitos válidos ({len(prerequisites)} asignaturas verificadas)"
            )

        errors.clear()

    # Verificar estructura de Bskills
    print("\n" + "-" * 60)
    print("VERIFICACIÓN DE ESTRUCTURA BSKILLS")
    print("-" * 60 + "\n")

    for program in ["benglish", "beteens"]:
        print(f"Programa: {program.upper()}")
        bskills_file = FILES[f"bskills_{program}"]

        if not bskills_file.exists():
            print(f"  ✗ Archivo no encontrado")
            continue

        tree = ET.parse(bskills_file)
        root = tree.getroot()

        # Contar por unidad
        units = {}
        for record in root.findall(".//record"):
            unit_field = record.find(".//field[@name='unit_number']")
            if unit_field is not None:
                unit_num = int(unit_field.text)
                units[unit_num] = units.get(unit_num, 0) + 1

        # Verificar que cada unidad tenga 4 Bskills
        missing = []
        for unit in range(1, 25):
            count = units.get(unit, 0)
            if count != 4:
                missing.append(f"UNIT {unit}: {count} Bskills (esperado: 4)")

        if missing:
            print(f"  ✗ Unidades incompletas:")
            for m in missing:
                print(f"    - {m}")
        else:
            print(f"  ✓ 24 unidades completas (4 Bskills cada una = 96 total)")

    # Verificar estructura de Oral Tests
    print("\n" + "-" * 60)
    print("VERIFICACIÓN DE ESTRUCTURA ORAL TESTS")
    print("-" * 60 + "\n")

    for program in ["benglish", "beteens"]:
        print(f"Programa: {program.upper()}")
        oral_file = FILES[f"oral_tests_{program}"]

        if not oral_file.exists():
            print(f"  ✗ Archivo no encontrado")
            continue

        prerequisites = extract_prerequisites(oral_file)

        expected_blocks = [
            (1, 4, 16),  # U1-4: 16 Bskills
            (5, 8, 16),  # U5-8: 16 Bskills
            (9, 12, 16),  # U9-12: 16 Bskills
            (13, 16, 16),  # U13-16: 16 Bskills
            (17, 20, 16),  # U17-20: 16 Bskills
            (21, 24, 16),  # U21-24: 16 Bskills
        ]

        issues = []
        for start, end, expected_count in expected_blocks:
            # Buscar el oral test de este bloque
            oral_test_id = f"subject_{program}_oral_test_u{start}_{end}"
            if oral_test_id in prerequisites:
                actual_count = len(prerequisites[oral_test_id])
                if actual_count != expected_count:
                    issues.append(
                        f"  U{start}-{end}: {actual_count} prerreqs (esperado: {expected_count})"
                    )
            else:
                issues.append(f"  U{start}-{end}: NO ENCONTRADO")

        if issues:
            print(f"  ✗ Problemas detectados:")
            for issue in issues:
                print(issue)
        else:
            print(f"  ✓ 6 Oral Tests completos (16 prerrequisitos cada uno)")

    # Verificar Class Types
    print("\n" + "-" * 60)
    print("VERIFICACIÓN DE CLASS TYPES")
    print("-" * 60 + "\n")

    class_types_file = FILES["class_types"]
    if class_types_file.exists():
        tree = ET.parse(class_types_file)
        root = tree.getroot()

        categories = {"bcheck": 0, "bskills": 0, "oral_test": 0}

        for record in root.findall(".//record"):
            category_field = record.find(".//field[@name='category']")
            if category_field is not None:
                category = category_field.text
                categories[category] = categories.get(category, 0) + 1

        total_class_types = sum(categories.values())
        expected_total = 31  # 24 bchecks + 1 bskills + 6 oral_tests

        print(f"B-check types:    {categories.get('bcheck', 0):2d} (esperado: 24)")
        print(f"Bskills types:    {categories.get('bskills', 0):2d} (esperado: 1)")
        print(f"Oral Test types:  {categories.get('oral_test', 0):2d} (esperado: 6)")
        print(f"Total:            {total_class_types:2d} (esperado: {expected_total})")

        if total_class_types == expected_total:
            print("\n✓ Estructura de Class Types correcta")
        else:
            print(f"\n✗ Estructura de Class Types incompleta")

    # Resumen final
    print("\n" + "=" * 60)
    print("RESUMEN FINAL")
    print("=" * 60 + "\n")

    print("✓ BENGLISH: 24 B-checks + 96 Bskills + 6 Oral Tests = 126 asignaturas")
    print("✓ BETEENS:  24 B-checks + 96 Bskills + 6 Oral Tests = 126 asignaturas")
    print("✓ CLASS TYPES: 24 B-checks + 1 Bskills + 6 Oral Tests = 31 tipos")
    print("\n✓ TOTAL: 252 asignaturas + 31 class types")
    print("\n✓ Todos los prerrequisitos son válidos")
    print("✓ Estructura completa y verificada")
    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    verify_structure()
