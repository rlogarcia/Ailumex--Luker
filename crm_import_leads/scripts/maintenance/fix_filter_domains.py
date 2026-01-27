#!/usr/bin/env python3
"""
Script para corregir filter_domain rotos en automatizaciones CRM.
Reemplaza los filter_domain con saltos de línea por versiones corregidas.
"""
import psycopg2
import sys

# Configuración DB
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "ailumex_be_crm"
DB_USER = "Alejo"
DB_PASSWORD = "admin"

# Mapeo de correcciones: id -> filter_domain corregido
CORRECTIONS = {
    22: "[('evaluation_date', '!=', False), ('evaluation_time', '!=', False)]",
    23: "[('stage_id.name', 'in', ['Reprobado', 'Matriculado', 'Pago parcial'])]",
    27: "[('stage_id.name', '=', 'Matriculado'), ('active', '=', True)]",
    28: "[('stage_id.name', '=', 'Rechazado'), ('team_id.name', '=', 'Pipeline Comercial')]",
    26: "[('team_id.name', '=', 'Pipeline Comercial'), ('type', '=', 'lead')]",
}


def main():
    print("=" * 70)
    print("CORRECCIÓN DE FILTER_DOMAIN EN AUTOMATIZACIONES CRM")
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

        # Mostrar estado actual
        print("\n2. Verificando automatizaciones a corregir...")
        for auto_id in CORRECTIONS.keys():
            cur.execute(
                """
                SELECT name, filter_domain, active
                FROM base_automation
                WHERE id = %s;
            """,
                (auto_id,),
            )

            result = cur.fetchone()
            if result:
                name, domain, active = result
                has_newline = "\n" in domain if domain else False
                status = "✗ CON SALTOS DE LÍNEA" if has_newline else "✓ OK"
                print(f"\n   [{auto_id}] {name}")
                print(f"        Estado: {status}")
                print(f"        Activa: {active}")
                if has_newline:
                    print(f"        Domain actual: {repr(domain[:80])}...")

        # Aplicar correcciones
        print("\n3. Aplicando correcciones...")
        corrected_count = 0

        for auto_id, new_domain in CORRECTIONS.items():
            # Verificar que la automatización existe
            cur.execute("SELECT name FROM base_automation WHERE id = %s;", (auto_id,))
            result = cur.fetchone()

            if not result:
                print(f"   ⚠ [{auto_id}] No encontrada - omitiendo")
                continue

            name = result[0]

            # Actualizar filter_domain
            cur.execute(
                """
                UPDATE base_automation
                SET filter_domain = %s
                WHERE id = %s;
            """,
                (new_domain, auto_id),
            )

            print(f"   ✓ [{auto_id}] {name}")
            print(f"        Nuevo domain: {new_domain}")
            corrected_count += 1

        # Commit de las correcciones
        conn.commit()
        print(f"\n   ✓ {corrected_count} automatizaciones corregidas")

        # Reactivar las automatizaciones corregidas
        print("\n4. Reactivando automatizaciones corregidas...")
        reactivated_count = 0

        for auto_id in CORRECTIONS.keys():
            cur.execute(
                """
                UPDATE base_automation
                SET active = true
                WHERE id = %s
                RETURNING name;
            """,
                (auto_id,),
            )

            result = cur.fetchone()
            if result:
                print(f"   ✓ [{auto_id}] {result[0]} - REACTIVADA")
                reactivated_count += 1

        conn.commit()
        print(f"\n   ✓ {reactivated_count} automatizaciones reactivadas")

        # Verificación final
        print("\n5. Verificación final...")
        cur.execute(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN active THEN 1 ELSE 0 END) as activas,
                SUM(CASE WHEN filter_domain IS NOT NULL AND position(E'\\n' in filter_domain::text) > 0 THEN 1 ELSE 0 END) as con_newline
            FROM base_automation ba
            JOIN ir_model im ON ba.model_id = im.id
            WHERE im.model = 'crm.lead';
        """
        )

        total, activas, con_newline = cur.fetchone()

        print("\n" + "=" * 70)
        print("RESUMEN FINAL")
        print("=" * 70)
        print(f"Total automatizaciones crm.lead:     {total}")
        print(f"Activas:                              {activas}")
        print(f"Inactivas:                            {total - activas}")
        print(f"Con saltos de línea (inválidas):      {con_newline}")
        print(f"Corregidas en esta ejecución:         {corrected_count}")
        print(f"Reactivadas en esta ejecución:        {reactivated_count}")
        print("=" * 70)

        cur.close()
        conn.close()

        if con_newline == 0:
            print("\n✓ ÉXITO: Todas las automatizaciones tienen filter_domain válido")
            return True
        else:
            print(
                f"\n⚠ ADVERTENCIA: Aún quedan {con_newline} automatizaciones con problemas"
            )
            return False

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        if "conn" in locals():
            conn.rollback()
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error fatal: {e}")
        sys.exit(1)
