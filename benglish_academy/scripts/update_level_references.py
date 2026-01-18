# -*- coding: utf-8 -*-
"""
Script para actualizar referencias de niveles antiguos a niveles compartidos.
Ejecutar desde la raíz del módulo benglish_academy
"""

import os
import re

# Mapeo de IDs antiguos a nuevos (B teens)
BETEENS_LEVEL_MAPPING = {
    # BASIC
    "level_beteens_plus_mixto_basic_unit1": "level_beteens_basic_unit1",
    "level_beteens_plus_mixto_basic_unit2": "level_beteens_basic_unit2",
    "level_beteens_plus_mixto_basic_unit3": "level_beteens_basic_unit3",
    "level_beteens_plus_mixto_basic_unit4": "level_beteens_basic_unit4",
    "level_beteens_plus_mixto_basic_unit5": "level_beteens_basic_unit5",
    "level_beteens_plus_mixto_basic_unit6": "level_beteens_basic_unit6",
    "level_beteens_plus_mixto_basic_unit7": "level_beteens_basic_unit7",
    "level_beteens_plus_mixto_basic_unit8": "level_beteens_basic_unit8",
    # INTERMEDIATE
    "level_beteens_plus_mixto_intermediate_unit9": "level_beteens_intermediate_unit9",
    "level_beteens_plus_mixto_intermediate_unit10": "level_beteens_intermediate_unit10",
    "level_beteens_plus_mixto_intermediate_unit11": "level_beteens_intermediate_unit11",
    "level_beteens_plus_mixto_intermediate_unit12": "level_beteens_intermediate_unit12",
    "level_beteens_plus_mixto_intermediate_unit13": "level_beteens_intermediate_unit13",
    "level_beteens_plus_mixto_intermediate_unit14": "level_beteens_intermediate_unit14",
    "level_beteens_plus_mixto_intermediate_unit15": "level_beteens_intermediate_unit15",
    "level_beteens_plus_mixto_intermediate_unit16": "level_beteens_intermediate_unit16",
    # ADVANCED
    "level_beteens_plus_mixto_advanced_unit17": "level_beteens_advanced_unit17",
    "level_beteens_plus_mixto_advanced_unit18": "level_beteens_advanced_unit18",
    "level_beteens_plus_mixto_advanced_unit19": "level_beteens_advanced_unit19",
    "level_beteens_plus_mixto_advanced_unit20": "level_beteens_advanced_unit20",
    "level_beteens_plus_mixto_advanced_unit21": "level_beteens_advanced_unit21",
    "level_beteens_plus_mixto_advanced_unit22": "level_beteens_advanced_unit22",
    "level_beteens_plus_mixto_advanced_unit23": "level_beteens_advanced_unit23",
    "level_beteens_plus_mixto_advanced_unit24": "level_beteens_advanced_unit24",
}

# Mapeo para niveles de ORAL TEST
BETEENS_ORAL_TEST_MAPPING = {
    "level_beteens_plus_mixto_basic_oral_test_1_4": "level_beteens_basic_oral_test_1_4",
    "level_beteens_plus_mixto_basic_oral_test_5_8": "level_beteens_basic_oral_test_5_8",
    "level_beteens_plus_mixto_intermediate_oral_test_9_12": "level_beteens_intermediate_oral_test_9_12",
    "level_beteens_plus_mixto_intermediate_oral_test_13_16": "level_beteens_intermediate_oral_test_13_16",
    "level_beteens_plus_mixto_advanced_oral_test_17_20": "level_beteens_advanced_oral_test_17_20",
    "level_beteens_plus_mixto_advanced_oral_test_21_24": "level_beteens_advanced_oral_test_21_24",
}

# Combinar todos los mapeos de B teens
BETEENS_ALL_MAPPING = {**BETEENS_LEVEL_MAPPING, **BETEENS_ORAL_TEST_MAPPING}

# Mapeo de IDs antiguos a nuevos (Benglish)
BENGLISH_LEVEL_MAPPING = {
    # BASIC
    "level_benglish_plus_mixto_basic_unit1": "level_benglish_basic_unit1",
    "level_benglish_plus_mixto_basic_unit2": "level_benglish_basic_unit2",
    "level_benglish_plus_mixto_basic_unit3": "level_benglish_basic_unit3",
    "level_benglish_plus_mixto_basic_unit4": "level_benglish_basic_unit4",
    "level_benglish_plus_mixto_basic_unit5": "level_benglish_basic_unit5",
    "level_benglish_plus_mixto_basic_unit6": "level_benglish_basic_unit6",
    "level_benglish_plus_mixto_basic_unit7": "level_benglish_basic_unit7",
    "level_benglish_plus_mixto_basic_unit8": "level_benglish_basic_unit8",
    # INTERMEDIATE
    "level_benglish_plus_mixto_intermediate_unit9": "level_benglish_intermediate_unit9",
    "level_benglish_plus_mixto_intermediate_unit10": "level_benglish_intermediate_unit10",
    "level_benglish_plus_mixto_intermediate_unit11": "level_benglish_intermediate_unit11",
    "level_benglish_plus_mixto_intermediate_unit12": "level_benglish_intermediate_unit12",
    "level_benglish_plus_mixto_intermediate_unit13": "level_benglish_intermediate_unit13",
    "level_benglish_plus_mixto_intermediate_unit14": "level_benglish_intermediate_unit14",
    "level_benglish_plus_mixto_intermediate_unit15": "level_benglish_intermediate_unit15",
    "level_benglish_plus_mixto_intermediate_unit16": "level_benglish_intermediate_unit16",
    # ADVANCED
    "level_benglish_plus_mixto_advanced_unit17": "level_benglish_advanced_unit17",
    "level_benglish_plus_mixto_advanced_unit18": "level_benglish_advanced_unit18",
    "level_benglish_plus_mixto_advanced_unit19": "level_benglish_advanced_unit19",
    "level_benglish_plus_mixto_advanced_unit20": "level_benglish_advanced_unit20",
    "level_benglish_plus_mixto_advanced_unit21": "level_benglish_advanced_unit21",
    "level_benglish_plus_mixto_advanced_unit22": "level_benglish_advanced_unit22",
    "level_benglish_plus_mixto_advanced_unit23": "level_benglish_advanced_unit23",
    "level_benglish_plus_mixto_advanced_unit24": "level_benglish_advanced_unit24",
}

# Mapeo para niveles de ORAL TEST
BENGLISH_ORAL_TEST_MAPPING = {
    "level_benglish_plus_mixto_basic_oral_test_1_4": "level_benglish_basic_oral_test_1_4",
    "level_benglish_plus_mixto_basic_oral_test_5_8": "level_benglish_basic_oral_test_5_8",
    "level_benglish_plus_mixto_intermediate_oral_test_9_12": "level_benglish_intermediate_oral_test_9_12",
    "level_benglish_plus_mixto_intermediate_oral_test_13_16": "level_benglish_intermediate_oral_test_13_16",
    "level_benglish_plus_mixto_advanced_oral_test_17_20": "level_benglish_advanced_oral_test_17_20",
    "level_benglish_plus_mixto_advanced_oral_test_21_24": "level_benglish_advanced_oral_test_21_24",
}

# Combinar todos los mapeos de Benglish
BENGLISH_ALL_MAPPING = {**BENGLISH_LEVEL_MAPPING, **BENGLISH_ORAL_TEST_MAPPING}


def update_file(file_path, mapping):
    """Actualiza un archivo XML reemplazando las referencias antiguas por las nuevas."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        replacements_made = 0

        for old_id, new_id in mapping.items():
            pattern = f'ref="{old_id}"'
            replacement = f'ref="{new_id}"'
            if pattern in content:
                content = content.replace(pattern, replacement)
                count = original_content.count(pattern)
                replacements_made += count
                print(f"  - Reemplazado '{old_id}' → '{new_id}' ({count} veces)")

        if replacements_made > 0:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(
                f"✅ Archivo actualizado: {file_path} ({replacements_made} reemplazos)"
            )
        else:
            print(f"⚠️  Sin cambios: {file_path}")

        return replacements_made
    except Exception as e:
        print(f"❌ Error procesando {file_path}: {e}")
        return 0


def main():
    """Función principal para actualizar todos los archivos de asignaturas."""
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")

    # Archivos de asignaturas de B teens
    beteens_files = [
        "subjects_bchecks_beteens.xml",
        "subjects_bskills_beteens.xml",
        "subjects_oral_tests_beteens.xml",
    ]

    # Archivos de asignaturas de Benglish
    benglish_files = [
        "subjects_bchecks_benglish.xml",
        "subjects_bskills_benglish.xml",
        "subjects_oral_tests_benglish.xml",
    ]

    print("=" * 70)
    print("ACTUALIZACIÓN DE REFERENCIAS DE NIVELES A ESTRUCTURA COMPARTIDA")
    print("=" * 70)
    print()

    total_replacements = 0

    print("📄 Actualizando archivos de B TEENS...")
    print("-" * 70)
    for filename in beteens_files:
        file_path = os.path.join(data_dir, filename)
        if os.path.exists(file_path):
            print(f"\nProcesando: {filename}")
            replacements = update_file(file_path, BETEENS_ALL_MAPPING)
            total_replacements += replacements
        else:
            print(f"⚠️  Archivo no encontrado: {filename}")

    print()
    print("📄 Actualizando archivos de BENGLISH...")
    print("-" * 70)
    for filename in benglish_files:
        file_path = os.path.join(data_dir, filename)
        if os.path.exists(file_path):
            print(f"\nProcesando: {filename}")
            replacements = update_file(file_path, BENGLISH_ALL_MAPPING)
            total_replacements += replacements
        else:
            print(f"⚠️  Archivo no encontrado: {filename}")

    print()
    print("=" * 70)
    print(f"✅ COMPLETADO: {total_replacements} reemplazos totales")
    print("=" * 70)


if __name__ == "__main__":
    main()
