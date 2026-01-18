"""
Script para actualizar clasificaciones directamente en la base de datos
Ejecutar este script UNA SOLA VEZ después de actualizar el módulo
"""

import psycopg2

# Configuración de conexión a PostgreSQL
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "odoo18",  # CAMBIAR AL NOMBRE DE TU BASE DE DATOS
    "user": "odoo",
    "password": "odoo",
}

try:
    # Conectar a la base de datos
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("=" * 80)
    print("ACTUALIZACIÓN DE CLASIFICACIONES EN BASE DE DATOS")
    print("=" * 80)

    # 1. Actualizar B-checks a 'prerequisite'
    cursor.execute(
        """
        UPDATE benglish_subject
        SET subject_classification = 'prerequisite'
        WHERE subject_category = 'bcheck'
        AND subject_classification != 'prerequisite'
    """
    )
    bchecks_updated = cursor.rowcount
    print(f"\n✅ B-checks actualizados: {bchecks_updated}")

    # 2. Actualizar Bskills a 'regular'
    cursor.execute(
        """
        UPDATE benglish_subject
        SET subject_classification = 'regular'
        WHERE subject_category = 'bskills'
        AND subject_classification != 'regular'
    """
    )
    bskills_updated = cursor.rowcount
    print(f"✅ Bskills actualizados: {bskills_updated}")

    # 3. Actualizar Oral Tests a 'evaluation'
    cursor.execute(
        """
        UPDATE benglish_subject
        SET subject_classification = 'evaluation'
        WHERE subject_category = 'oral_test'
        AND subject_classification != 'evaluation'
    """
    )
    oral_tests_updated = cursor.rowcount
    print(f"✅ Oral Tests actualizados: {oral_tests_updated}")

    # Commit de los cambios
    conn.commit()

    # Verificar resultados
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE RESULTADOS")
    print("=" * 80)

    cursor.execute(
        """
        SELECT subject_category, subject_classification, COUNT(*) as total
        FROM benglish_subject
        GROUP BY subject_category, subject_classification
        ORDER BY subject_category, subject_classification
    """
    )

    results = cursor.fetchall()
    print("\n📊 Distribución de clasificaciones:")
    for row in results:
        category, classification, count = row
        print(f"   {category:15} → {classification:15} : {count:4} asignaturas")

    # Verificar si hay clasificaciones incorrectas
    cursor.execute(
        """
        SELECT COUNT(*) FROM benglish_subject
        WHERE (subject_category = 'bcheck' AND subject_classification != 'prerequisite')
           OR (subject_category = 'bskills' AND subject_classification != 'regular')
           OR (subject_category = 'oral_test' AND subject_classification != 'evaluation')
    """
    )

    incorrect_count = cursor.fetchone()[0]

    print("\n" + "=" * 80)
    if incorrect_count == 0:
        print("✅ TODAS LAS CLASIFICACIONES SON CORRECTAS")
    else:
        print(f"⚠️  AÚN HAY {incorrect_count} CLASIFICACIONES INCORRECTAS")
    print("=" * 80)

    print(f"\n📝 RESUMEN:")
    print(
        f"   Total de registros actualizados: {bchecks_updated + bskills_updated + oral_tests_updated}"
    )

    cursor.close()
    conn.close()

except psycopg2.Error as e:
    print(f"\n❌ Error de base de datos: {e}")
    if conn:
        conn.rollback()
except Exception as e:
    print(f"\n❌ Error: {e}")
finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()

print(
    "\n💡 IMPORTANTE: Reinicia el servidor de Odoo para que los cambios se reflejen en la interfaz"
)
