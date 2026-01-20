#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Buscar automatizaciones que contengan 'fields.Date' en su código
"""

import psycopg2

# Conectar a la base de datos
conn = psycopg2.connect(
    host="localhost", port=5432, dbname="ailumex_be_crm", user="Alejo", password="admin"
)

cur = conn.cursor()

# Buscar por código que contenga 'fields.Date'
cur.execute(
    """
    SELECT id, name::text, state, code::text
    FROM ir_act_server
    WHERE code::text LIKE %s
    ORDER BY id;
""",
    ("%fields.Date%",),
)

print("Automatizaciones con 'fields.Date' en el código:\n")
for row in cur.fetchall():
    print(f"ID: {row[0]}")
    print(f"Nombre: {row[1]}")
    print(f"Estado: {row[2]}")
    print(f"Código (primeros 200 caracteres):\n{row[3][:200]}...")
    print("-" * 80)

cur.close()
conn.close()
