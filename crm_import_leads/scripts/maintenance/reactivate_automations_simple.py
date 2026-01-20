#!/usr/bin/env python3
"""
Script simple para verificar y reactivar automatizaciones CRM.
Usa psycopg2 directo sin cargar todo el registry de Odoo.
"""
import psycopg2
import sys

# Configuración DB
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "ailumex_be_crm"
DB_USER = "Alejo"
DB_PASSWORD = "admin"


def main():
    print("=" * 70)
    print("VERIFICACIÓN Y REACTIVACIÓN DE AUTOMATIZACIONES CRM")
    print("=" * 70)

    try:
        # Conectar a DB
        print(f"\n1. Conectando a base de datos: {DB_NAME}...")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )
        conn.autocommit = False
        cur = conn.cursor()
        print("   ✓ Conexión exitosa")

        # Paso 1: Listar todas las automatizaciones de crm.lead
        print("\n2. Buscando automatizaciones de crm.lead...")
        cur.execute(
            """
            SELECT ba.id, ba.name, ba.active, ba.filter_domain
            FROM base_automation ba
            JOIN ir_model im ON ba.model_id = im.id
            WHERE im.model = 'crm.lead'
            ORDER BY ba.name;
        """
        )

        automations = cur.fetchall()
        print(f"   Encontradas {len(automations)} automatizaciones:\n")

        valid_ids = []
        invalid_ids = []
        inactive_valid_ids = []

        for auto_id, name, active, filter_domain in automations:
            # Verificar si tiene saltos de línea en filter_domain
            has_newline = (
                filter_domain and "\n" in filter_domain if filter_domain else False
            )

            status_icon = "✗" if has_newline else "✓"
            active_text = "ACTIVA" if active else "INACTIVA"

            print(f"   [{auto_id}] {status_icon} {name}")
            print(f"        Estado: {active_text}")

            if filter_domain:
                # Mostrar primeros 80 caracteres del domain
                domain_preview = repr(filter_domain[:80])
                print(f"        Domain: {domain_preview}...")

                if has_newline:
                    print(f"        ⚠ PROBLEMA: Contiene saltos de línea")
                    invalid_ids.append(auto_id)
                else:
                    valid_ids.append(auto_id)
                    if not active:
                        inactive_valid_ids.append(auto_id)
            else:
                print(f"        Domain: (sin filtro)")
                valid_ids.append(auto_id)
                if not active:
                    inactive_valid_ids.append(auto_id)

            print()

        # Paso 2: Reactivar automatizaciones válidas que están inactivas
        print("\n3. Reactivando automatizaciones válidas...")

        if inactive_valid_ids:
            print(f"   Reactivando {len(inactive_valid_ids)} automatizaciones:")

            for auto_id in inactive_valid_ids:
                cur.execute(
                    """
                    UPDATE base_automation
                    SET active = true
                    WHERE id = %s
                    RETURNING name;
                """,
                    (auto_id,),
                )

                name_result = cur.fetchone()
                if name_result:
                    print(f"   ✓ [{auto_id}] {name_result[0]}")

            conn.commit()
            print(
                f"\n   ✓ {len(inactive_valid_ids)} automatizaciones reactivadas exitosamente"
            )
        else:
            print("   ℹ No hay automatizaciones válidas inactivas para reactivar")

        # Paso 3: Reportar automatizaciones problemáticas
        if invalid_ids:
            print(
                f"\n⚠ ADVERTENCIA: {len(invalid_ids)} automatización(es) con filter_domain inválido:"
            )
            print("   Estas permanecen INACTIVAS hasta corregir manualmente.\n")

            for auto_id in invalid_ids:
                cur.execute(
                    """
                    SELECT name, filter_domain
                    FROM base_automation
                    WHERE id = %s;
                """,
                    (auto_id,),
                )

                name, domain = cur.fetchone()
                print(f"   [{auto_id}] {name}")
                print(f"        Domain problemático: {repr(domain[:100])}...")
                print()

        # Paso 4: Resumen final
        cur.execute(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN active THEN 1 ELSE 0 END) as activas
            FROM base_automation ba
            JOIN ir_model im ON ba.model_id = im.id
            WHERE im.model = 'crm.lead';
        """
        )

        total, activas = cur.fetchone()

        print("\n" + "=" * 70)
        print("RESUMEN FINAL")
        print("=" * 70)
        print(f"Total automatizaciones crm.lead: {total}")
        print(f"Activas:                          {activas}")
        print(f"Inactivas:                        {total - activas}")
        print(f"Con filter_domain válido:         {len(valid_ids)}")
        print(f"Con filter_domain inválido:       {len(invalid_ids)}")
        print(f"Reactivadas en esta ejecución:    {len(inactive_valid_ids)}")
        print("=" * 70)

        cur.close()
        conn.close()

        return len(invalid_ids) == 0

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = main()
        if success:
            print(
                "\n✓ Script completado exitosamente - Todas las automatizaciones están OK"
            )
            sys.exit(0)
        else:
            print(
                "\n⚠ Script completado con advertencias - Hay automatizaciones inválidas"
            )
            sys.exit(
                0
            )  # Exit 0 porque la operación fue exitosa (las válidas se reactivaron)
    except Exception as e:
        print(f"\n✗ Error fatal: {e}")
        sys.exit(1)
