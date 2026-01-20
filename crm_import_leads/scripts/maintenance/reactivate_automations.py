#!/usr/bin/env python3
"""
Script para reactivar automatizaciones de CRM después de corregir filter_domain.
Actualiza el módulo y reactiva las automatizaciones desactivadas.
"""
import sys
import os

# Agregar path de Odoo
odoo_path = r"C:\Program Files\Odoo 18.0.20251128\server"
sys.path.insert(0, odoo_path)

import odoo
from odoo import api, SUPERUSER_ID

# Configuración
DB_NAME = "ailumex_be_crm"
CONFIG_FILE = r"C:\Program Files\Odoo 18.0.20251128\server\odoo.conf"


def main():
    print("=" * 60)
    print("REACTIVACIÓN DE AUTOMATIZACIONES CRM")
    print("=" * 60)

    # Cargar configuración
    odoo.tools.config.parse_config(["-c", CONFIG_FILE])

    # Inicializar registry
    print(f"\n1. Conectando a base de datos: {DB_NAME}...")
    registry = odoo.registry(DB_NAME)

    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        # Paso 1: Actualizar el módulo
        print("\n2. Actualizando módulo crm_import_leads...")
        try:
            module = env["ir.module.module"].search([("name", "=", "crm_import_leads")])
            if module:
                print(f"   - Estado actual: {module.state}")
                module.button_immediate_upgrade()
                cr.commit()
                print("   ✓ Módulo actualizado correctamente")
            else:
                print("   ✗ Módulo no encontrado")
                return
        except Exception as e:
            print(f"   ✗ Error al actualizar módulo: {e}")
            cr.rollback()
            return

        # Paso 2: Verificar automatizaciones
        print("\n3. Verificando automatizaciones de crm.lead...")
        automations = env["base.automation"].search(
            [("model_id.model", "=", "crm.lead")], order="name"
        )

        print(f"   Encontradas {len(automations)} automatizaciones:\n")

        for auto in automations:
            # Verificar filter_domain
            has_newline = False
            if auto.filter_domain:
                has_newline = "\n" in auto.filter_domain

            status = "✗ INVÁLIDO (salto línea)" if has_newline else "✓ VÁLIDO"
            active_status = "ACTIVA" if auto.active else "INACTIVA"

            print(f"   [{auto.id}] {auto.name}")
            print(f"        Estado: {active_status}")
            print(f"        Filter: {status}")
            if auto.filter_domain and len(auto.filter_domain) < 200:
                print(f"        Domain: {auto.filter_domain[:100]}...")
            print()

        # Paso 3: Reactivar automatizaciones válidas
        print("\n4. Reactivando automatizaciones...")

        # Filtrar solo las que tienen filter_domain válido (sin saltos de línea)
        valid_automations = automations.filtered(
            lambda a: not a.filter_domain or "\n" not in a.filter_domain
        )

        # Reactivar las válidas que estén inactivas
        to_activate = valid_automations.filtered(lambda a: not a.active)

        if to_activate:
            print(f"   Reactivando {len(to_activate)} automatizaciones:")
            for auto in to_activate:
                print(f"   - {auto.name}")
                auto.write({"active": True})
            cr.commit()
            print(f"\n   ✓ {len(to_activate)} automatizaciones reactivadas")
        else:
            print("   ℹ No hay automatizaciones inactivas válidas para reactivar")

        # Paso 4: Reportar automatizaciones problemáticas
        invalid_automations = automations.filtered(
            lambda a: a.filter_domain and "\n" in a.filter_domain
        )

        if invalid_automations:
            print(
                f"\n⚠ ADVERTENCIA: {len(invalid_automations)} automatizaciones con filter_domain inválido:"
            )
            for auto in invalid_automations:
                print(f"   - [{auto.id}] {auto.name}")
                print(f"     Domain: {repr(auto.filter_domain[:100])}")
            print(
                "\n   Estas permanecerán INACTIVAS hasta que se corrija el filter_domain."
            )

        # Resumen final
        print("\n" + "=" * 60)
        print("RESUMEN")
        print("=" * 60)
        active_count = len(automations.filtered(lambda a: a.active))
        print(f"Total automatizaciones: {len(automations)}")
        print(f"Activas: {active_count}")
        print(f"Inactivas: {len(automations) - active_count}")
        print(f"Con filter_domain inválido: {len(invalid_automations)}")
        print("=" * 60)


if __name__ == "__main__":
    try:
        main()
        print("\n✓ Script completado exitosamente")
    except Exception as e:
        print(f"\n✗ Error fatal: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
