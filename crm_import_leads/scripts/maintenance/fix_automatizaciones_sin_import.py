#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corregir las automatizaciones sin usar imports
Odoo provee 'datetime' en el contexto de safe_eval
"""

import psycopg2

# IDs de las automatizaciones a corregir
IDS_A_CORREGIR = [624, 626, 627, 628]

# Conectar a la base de datos
conn = psycopg2.connect(
    host="localhost", port=5432, dbname="ailumex_be_crm", user="Alejo", password="admin"
)

cur = conn.cursor()

print("=== CORRECCIÓN DE AUTOMATIZACIONES (SIN IMPORTS) ===\n")

for automation_id in IDS_A_CORREGIR:
    # Leer código actual
    cur.execute("SELECT code FROM ir_act_server WHERE id = %s", (automation_id,))
    result = cur.fetchone()

    if not result:
        print(f"⚠️  ID {automation_id}: No encontrado")
        continue

    codigo_actual = result[0]

    # Remover el import que agregamos
    codigo_nuevo = codigo_actual.replace("from datetime import date\n", "")
    codigo_nuevo = codigo_nuevo.replace("from datetime import date", "")

    # Reemplazar date.today() por datetime.date.today()
    # datetime ya está disponible en el contexto de safe_eval
    codigo_nuevo = codigo_nuevo.replace("date.today()", "datetime.date.today()")

    # Actualizar
    cur.execute(
        "UPDATE ir_act_server SET code = %s WHERE id = %s",
        (codigo_nuevo, automation_id),
    )

    print(f"✅ ID {automation_id}: Corregido")
    print(f"   Cambio: date.today() → datetime.date.today()")
    print(f"   (datetime ya está en contexto de Odoo)\n")

# Confirmar cambios
conn.commit()

print("=== RESUMEN ===")
print(f"✅ {len(IDS_A_CORREGIR)} automatizaciones corregidas")
print("\nVerifica creando un nuevo lead.")

cur.close()
conn.close()
