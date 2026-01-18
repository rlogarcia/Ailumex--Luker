#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificar todos los archivos XML de asignaturas"""

import xml.etree.ElementTree as ET
from pathlib import Path

data_path = Path(__file__).parent.parent / "data"

files_to_check = [
    "subjects_bchecks_benglish.xml",
    "subjects_bskills_benglish.xml",
    "subjects_oral_tests_benglish.xml",
    "subjects_bchecks_beteens.xml",
    "subjects_bskills_beteens.xml",
    "subjects_oral_tests_beteens.xml",
    "subjects_all_benglish_plus_virtual.xml",
    "subjects_all_benglish_premium.xml",
    "subjects_all_benglish_gold.xml",
    "subjects_all_benglish_supreme.xml",
    "subjects_all_beteens_plus_virtual.xml",
    "subjects_all_beteens_premium.xml",
    "subjects_all_beteens_gold.xml",
    "subjects_all_beteens_supreme.xml",
]

print("\n" + "=" * 60)
print("VERIFICACIÓN DE ARCHIVOS XML")
print("=" * 60 + "\n")

all_ok = True

for filename in files_to_check:
    filepath = data_path / filename
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        records = root.findall(".//record")
        print(f"✓ {filename:50s} {len(records)} records")
    except Exception as e:
        print(f"✗ {filename:50s} ERROR: {e}")
        all_ok = False

print("\n" + "=" * 60)
if all_ok:
    print("✅ TODOS LOS ARCHIVOS SON VÁLIDOS")
else:
    print("❌ HAY ERRORES EN ALGUNOS ARCHIVOS")
print("=" * 60 + "\n")
