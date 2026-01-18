#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para forzar el recálculo de los niveles de estudiantes.
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


def force_recompute_levels():
    """Fuerza el recálculo de los niveles de todos los estudiantes."""
    
    # Inicializar Odoo
    config.parse_config(["-c", CONFIG_FILE, "-d", DATABASE])
    odoo.cli.server.report_configuration()
    
    # Obtener registry y cursor
    registry = odoo.registry(DATABASE)
    
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Buscar todos los estudiantes con matrículas activas
        students = env["benglish.student"].search([
            ("state", "in", ["active", "enrolled"]),
        ])
        
        print(f"\n{'='*80}")
        print(f"FORZANDO RECÁLCULO DE NIVELES")
        print(f"{'='*80}\n")
        print(f"Total de estudiantes a procesar: {len(students)}\n")
        
        updated_count = 0
        
        for student in students:
            # Invalidar caché y forzar recálculo
            student.invalidate_recordset(["current_level_id", "current_phase_id", "active_enrollment_ids", "enrollment_ids"])
            student._compute_current_academic_info()
            
            # Re-leer el estudiante
            student = env["benglish.student"].browse(student.id)
            
            if student.current_level_id:
                print(f"✅ {student.code} - {student.name}: {student.current_level_id.name} ({student.current_phase_id.name if student.current_phase_id else 'N/A'})")
                updated_count += 1
            else:
                print(f"⚠️  {student.code} - {student.name}: Sin nivel computado")
        
        # Commit
        cr.commit()
        
        print(f"\n{'='*80}")
        print(f"RESUMEN:")
        print(f"  ✅ Con nivel: {updated_count}")
        print(f"  ⚠️  Sin nivel: {len(students) - updated_count}")
        print(f"  📊 Total: {len(students)}")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    try:
        force_recompute_levels()
        print("✅ Recálculo completado")
    except Exception as e:
        print(f"❌ Error ejecutando el script: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
