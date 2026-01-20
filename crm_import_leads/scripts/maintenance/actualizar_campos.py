#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para actualizar el módulo crm_import_leads
Agrega los campos de evaluación si no existen
"""

import sys
import os

# Configuración
ODOO_PATH = r"c:\Program Files\Odoo 18.0.20251128\server"
DATABASE = "ailumex_be_crm"
MODULE = "crm_import_leads"

# Agregar ruta de Odoo al path
sys.path.insert(0, ODOO_PATH)

try:
    import odoo
    from odoo import api, SUPERUSER_ID

    print("=" * 60)
    print("ACTUALIZACIÓN MÓDULO CRM - Campos de Evaluación")
    print("=" * 60)
    print()

    # Configurar Odoo
    odoo.tools.config.parse_config(
        [
            "--database",
            DATABASE,
            "--db_host",
            "localhost",
            "--db_port",
            "5432",
        ]
    )

    # Conectar a la base de datos
    print(f"Conectando a base de datos: {DATABASE}")
    registry = odoo.registry(DATABASE)

    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        print(f"Actualizando módulo: {MODULE}")

        # Verificar si el módulo está instalado
        module = env["ir.module.module"].search(
            [("name", "=", MODULE), ("state", "=", "installed")]
        )

        if not module:
            print(f"ERROR: El módulo {MODULE} no está instalado")
            sys.exit(1)

        print(f"Módulo encontrado: {module.name} (v{module.latest_version})")

        # Forzar actualización
        print("Forzando actualización del módulo...")
        module.button_immediate_upgrade()

        cr.commit()

        # Verificar campos
        print("\nVerificando campos de evaluación:")
        Lead = env["crm.lead"]

        campos_evaluacion = [
            "evaluation_date",
            "evaluation_time",
            "evaluation_modality",
            "evaluation_link",
            "evaluation_address",
            "calendar_event_id",
        ]

        for campo in campos_evaluacion:
            if campo in Lead._fields:
                field = Lead._fields[campo]
                print(f"  ✓ {campo}: {field.string} ({field.type})")
            else:
                print(f"  ✗ {campo}: NO ENCONTRADO")

        print()
        print("=" * 60)
        print("ACTUALIZACIÓN COMPLETADA")
        print("=" * 60)
        print()
        print("Próximos pasos:")
        print("1. Reiniciar el servicio de Odoo")
        print("2. Verificar que los campos aparezcan en la interfaz")
        print("3. Si persiste el error, revisar el log de Odoo")

except ImportError as e:
    print(f"ERROR: No se pudo importar Odoo: {e}")
    print("Verifique que la ruta de Odoo sea correcta")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
