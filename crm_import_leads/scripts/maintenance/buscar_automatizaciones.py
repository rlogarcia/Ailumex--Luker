#!/usr/bin/env python3
import psycopg2

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "ailumex_be_crm"
DB_USER = "Alejo"
DB_PASSWORD = "admin"

conn = psycopg2.connect(
    host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
)
cur = conn.cursor()

# Buscar todas las automatizaciones de CRM
cur.execute(
    """
    SELECT id, name::text, state, code::text
    FROM ir_act_server
    WHERE name::text ILIKE '%CRM%' OR name::text ILIKE '%lead%' OR name::text ILIKE '%Llamar%'
    ORDER BY id;
"""
)

print("Automatizaciones (ir.actions.server) encontradas:\n")
for row in cur.fetchall():
    print(f"ID: {row[0]}")
    print(f"Name: {row[1]}")
    print(f"State: {row[2]}")
    if row[3] and "fields.Date" in row[3]:
        print(f"⚠️  TIENE EL ERROR: fields.Date.today()")
    print("-" * 80)

cur.close()
conn.close()
