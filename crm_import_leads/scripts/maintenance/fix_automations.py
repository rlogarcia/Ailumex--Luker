#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corregir automatizaciones con sintaxis incorrecta
Desactiva las automatizaciones problemáticas directamente en la BD
"""

import sys
import os

# Configuración
ODOO_PATH = r"c:\Program Files\Odoo 18.0.20251128\server"
DATABASE = "ailumex_be_crm"

# Agregar ruta de Odoo al path
sys.path.insert(0, ODOO_PATH)

try:
    import odoo
    from odoo import api, SUPERUSER_ID

    print("=" * 60)
    print("CORRIGIENDO AUTOMATIZACIONES CON SINTAXIS INCORRECTA")
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

        print("Buscando automatizaciones problemáticas...")

        # Buscar automatizaciones con el nombre específico
        automations = env["base.automation"].search(
            [
                "|",
                ("name", "=", "CRM: Actividad - Seguimiento post-evaluación"),
                ("name", "=", "CRM: Actividad - Evaluación programada"),
            ]
        )

        print(f"Encontradas {len(automations)} automatizaciones")

        for auto in automations:
            print(f"\n  Automatización: {auto.name}")
            print(f"  Estado actual: {'Activa' if auto.active else 'Inactiva'}")
            print(f"  Filter domain: {auto.filter_domain}")

            # Desactivar y corregir filter_domain
            new_domain = False
            if "Seguimiento post-evaluación" in auto.name:
                new_domain = '[("stage_id.name", "in", ["Reprobado", "Matriculado", "Pago parcial"])]'
            elif "Evaluación programada" in auto.name:
                new_domain = '[("evaluation_date", "!=", False), ("evaluation_time", "!=", False)]'

            if new_domain:
                auto.write({"active": False, "filter_domain": new_domain})
                print(f"  ✓ Desactivada y corregida")

        cr.commit()

        print()
        print("=" * 60)
        print("CORRECCIÓN COMPLETADA")
        print("=" * 60)
        print()
        print("Las automatizaciones han sido desactivadas.")
        print("Ahora puede crear leads sin errores.")
        print()
        print("Para reactivarlas:")
        print("1. Ir a Configuración > Automatización > Acciones automatizadas")
        print("2. Buscar las automatizaciones CRM")
        print("3. Activarlas manualmente si es necesario")

except ImportError as e:
    print(f"ERROR: No se pudo importar Odoo: {e}")
    print("Verifique que la ruta de Odoo sea correcta")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
