#!/usr/bin/env python3
"""
Script para agregar el campo 'evaluable' a los archivos XML de asignaturas.
- Oral Tests: evaluable=True
- BChecks: evaluable=False
- BSkills: evaluable=False
"""

import re
import os

# Ruta base del proyecto
BASE_PATH = r"C:\Program Files\TrabajoOdoo\Odoo18\Proyecto-Be\benglish_academy\data"

def add_evaluable_to_file(filepath, evaluable_value):
    """
    Agrega el campo evaluable después de subject_classification
    
    Args:
        filepath: Ruta completa del archivo XML
        evaluable_value: "True" o "False"
    """
    print(f"\nProcesando: {os.path.basename(filepath)}")
    print(f"Evaluable: {evaluable_value}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Patrón para encontrar subject_classification y agregar evaluable después
    # Solo si no existe ya el campo evaluable
    pattern = r'(<field name="subject_classification">[^<]+</field>)\s*\n(\s*)(<field name="subject_category")'
    
    replacement = rf'\1\n\2<field name="evaluable" eval="{evaluable_value}" />\n\2\3'
    
    # Verificar si ya existe el campo evaluable
    if '<field name="evaluable"' in content:
        print(f"  ⚠️  El campo 'evaluable' ya existe en {os.path.basename(filepath)}")
        return False
    
    new_content, count = re.subn(pattern, replacement, content)
    
    if count > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  ✅ Actualizado {count} registros")
        return True
    else:
        print(f"  ❌ No se encontraron coincidencias")
        return False


def main():
    """Función principal"""
    print("="*60)
    print("AGREGANDO CAMPO 'evaluable' A ASIGNATURAS")
    print("="*60)
    
    # Archivos a procesar
    files_to_process = [
        # BChecks - evaluable=False
        ("subjects_bchecks_benglish.xml", "False"),
        ("subjects_bchecks_beteens.xml", "False"),
        
        # BSkills - evaluable=False
        ("subjects_bskills_benglish.xml", "False"),
        ("subjects_bskills_beteens.xml", "False"),
        
        # Oral Tests - evaluable=True (ya procesados manualmente, pero por si acaso)
        # ("subjects_oral_tests_benglish.xml", "True"),
        # ("subjects_oral_tests_beteens.xml", "True"),
    ]
    
    total_updated = 0
    for filename, evaluable_value in files_to_process:
        filepath = os.path.join(BASE_PATH, filename)
        if os.path.exists(filepath):
            if add_evaluable_to_file(filepath, evaluable_value):
                total_updated += 1
        else:
            print(f"\n❌ Archivo no encontrado: {filename}")
    
    print("\n" + "="*60)
    print(f"PROCESO COMPLETADO: {total_updated} archivos actualizados")
    print("="*60)


if __name__ == "__main__":
    main()
