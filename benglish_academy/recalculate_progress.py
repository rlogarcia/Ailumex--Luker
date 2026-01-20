#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para recalcular el progreso académico de todos los estudiantes.
"""

import sys
import os

# Configuración de conexión Odoo
ODOO_BIN = r"C:\Program Files\Odoo 18.0.20250614\server\odoo-bin"
CONFIG_FILE = r"C:\Program Files\Odoo 18.0.20250614\server\odoo.conf"
DATABASE = "BenglishV1"

# Agregar el path de Odoo al PYTHONPATH
sys.path.insert(0, os.path.dirname(ODOO_BIN))

try:
    import odoo
    from odoo import api, SUPERUSER_ID
    from odoo.tools import config
except ImportError:
    print("❌ Error: No se pudo importar Odoo. Verifica las rutas.")
    sys.exit(1)


def recalculate_progress():
    """Recalcula el progreso académico de todos los estudiantes."""
    
    # Inicializar Odoo
    config.parse_config(["-c", CONFIG_FILE, "-d", DATABASE])
    odoo.cli.server.report_configuration()
    
    # Obtener registry y cursor
    registry = odoo.registry(DATABASE)
    
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Buscar todos los estudiantes con plan
        students = env["benglish.student"].search([
            ("plan_id", "!=", False),
        ])
        
        print(f"\n{'='*80}")
        print(f"RECALCULANDO PROGRESO ACADÉMICO")
        print(f"{'='*80}\n")
        print(f"Total de estudiantes con plan: {len(students)}\n")
        
        updated_count = 0
        with_progress_count = 0
        
        for student in students:
            # Invalidar caché y forzar recálculo
            student.invalidate_recordset([
                "academic_progress_percentage", 
                "completed_hours",
                "enrollment_ids",
                "active_enrollment_ids"
            ])
            student._compute_academic_progress()
            
            # Re-leer el estudiante
            student = env["benglish.student"].browse(student.id)
            
            progress = student.academic_progress_percentage
            
            if progress > 0:
                print(f"✅ {student.code} - {student.name}: {progress:.1f}%")
                with_progress_count += 1
            else:
                print(f"⚠️  {student.code} - {student.name}: 0%")
            
            updated_count += 1
        
        # Commit
        cr.commit()
        
        print(f"\n{'='*80}")
        print(f"RESUMEN:")
        print(f"  ✅ Con progreso > 0%: {with_progress_count}")
        print(f"  ⚠️  Sin progreso (0%): {updated_count - with_progress_count}")
        print(f"  📊 Total procesados: {updated_count}")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    try:
        recalculate_progress()
        print("✅ Recálculo completado")
    except Exception as e:
        print(f"❌ Error ejecutando el script: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
