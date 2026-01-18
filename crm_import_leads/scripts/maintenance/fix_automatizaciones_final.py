#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corregir las automatizaciones que usan fields.Date.today()
Reemplaza por datetime.date.today()
"""

import psycopg2

# IDs de las automatizaciones a corregir
IDS_A_CORREGIR = [624, 626, 627, 628]

# Conectar a la base de datos
conn = psycopg2.connect(
    host="localhost", port=5432, dbname="ailumex_be_crm", user="Alejo", password="admin"
)

cur = conn.cursor()

print("=== CORRECCIÓN DE AUTOMATIZACIONES ===\n")

for automation_id in IDS_A_CORREGIR:
    # Leer código actual
    cur.execute("SELECT code FROM ir_act_server WHERE id = %s", (automation_id,))
    result = cur.fetchone()

    if not result:
        print(f"⚠️  ID {automation_id}: No encontrado")
        continue

    codigo_actual = result[0]

    # Reemplazar fields.Date.today() por date.today()
    # y agregar el import al inicio si no existe
    codigo_nuevo = codigo_actual.replace("fields.Date.today()", "date.today()")

    # Agregar import si no existe
    if "from datetime import date" not in codigo_nuevo:
        codigo_nuevo = "from datetime import date\n" + codigo_nuevo

    # Actualizar
    cur.execute(
        "UPDATE ir_act_server SET code = %s WHERE id = %s",
        (codigo_nuevo, automation_id),
    )

    print(f"✅ ID {automation_id}: Corregido")
    print(f"   Cambios: fields.Date.today() → date.today()")
    print(f"   Import agregado: from datetime import date\n")

# Confirmar cambios
conn.commit()

print("=== RESUMEN ===")
print(f"✅ {len(IDS_A_CORREGIR)} automatizaciones corregidas")
print("\nVerifica creando un nuevo lead.")

cur.close()
conn.close()
