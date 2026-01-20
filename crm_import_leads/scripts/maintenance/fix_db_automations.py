#!/usr/bin/env python3
import psycopg2
import sys

# Leer credenciales desde odoo.conf (hardcoded según odoo.conf)
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "ailumex_be_crm"
DB_USER = "Alejo"
DB_PASSWORD = "admin"

print("Conectando a la base de datos...")
try:
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    conn.autocommit = True
    cur = conn.cursor()

    print("Buscando automatizaciones CRM...")
    # Listar todas las automatizaciones de crm.lead (evitamos castear filter_domain para no parsear JSON roto)
    cur.execute(
        """ 
        SELECT id, name, active
        FROM base_automation
        WHERE model_id = (SELECT id FROM ir_model WHERE model = 'crm.lead');
    """
    )
    rows = cur.fetchall()
    print(f"Encontradas {len(rows)} automatizaciones de crm.lead")
    for r in rows:
        print(" -", r[0], r[1], "active=" + str(r[2]))

    # Corregir/desactivar automatizaciones problemáticas por nombre
    print("Desactivando automatizaciones problemáticas...")

    # Desactivar TODAS las automatizaciones de crm.lead temporalmente
    # (esto evita el safe_eval hasta que arreglemos los filter_domain rotos)
    cur.execute(
        """ 
        UPDATE base_automation
        SET active = false
        WHERE model_id = (SELECT id FROM ir_model WHERE model = 'crm.lead');
    """
    )
    print(f"Desactivadas {cur.rowcount} automatizaciones de crm.lead")

    print("Verificando estado final...")
    cur.execute(
        """
        SELECT id, name, active
        FROM base_automation
        WHERE model_id = (SELECT id FROM ir_model WHERE model = 'crm.lead')
        ORDER BY name;
    """
    )
    for r in cur.fetchall():
        print(" >", r[0], r[1], "active=" + str(r[2]))

    cur.close()
    conn.close()
    print("Listo.")
except Exception as e:
    print("ERROR:", e)
    sys.exit(1)
