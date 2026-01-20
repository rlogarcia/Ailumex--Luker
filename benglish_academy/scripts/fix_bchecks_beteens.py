"""
Script para regenerar el archivo subjects_bchecks_beteens.xml
Elimina atributos en múltiples líneas y caracteres extraños
"""

import os

# Datos de los 24 B-checks para BETEENS Plus Mixto
bchecks = []

# BASIC - 8 unidades
for i in range(1, 9):
    bchecks.append(
        {
            "id": f"subject_beteens_bcheck_unit{i}",
            "name": f"Basic-B Check U{i}",
            "alias": f"B-check U{i}",
            "code": f"BCHECK-U{i}-BETEENS",
            "level_ref": f"level_beteens_plus_mixto_basic_unit{i}",
            "unit": i,
            "description": f"B-check de la Unidad {i} - BETEENS",
        }
    )

# ELEMENTARY - 8 unidades
for i in range(1, 9):
    bchecks.append(
        {
            "id": f"subject_beteens_bcheck_unit{i+8}",
            "name": f"Elementary-B Check U{i}",
            "alias": f"B-check U{i}",
            "code": f"BCHECK-U{i}-BETEENS",
            "level_ref": f"level_beteens_plus_mixto_elementary_unit{i}",
            "unit": i,
            "description": f"B-check de la Unidad {i} - BETEENS",
        }
    )

# PRE-INTERMEDIATE - 8 unidades
for i in range(1, 9):
    bchecks.append(
        {
            "id": f"subject_beteens_bcheck_unit{i+16}",
            "name": f"Pre-Intermediate-B Check U{i}",
            "alias": f"B-check U{i}",
            "code": f"BCHECK-U{i}-BETEENS",
            "level_ref": f"level_beteens_plus_mixto_preintermediate_unit{i}",
            "unit": i,
            "description": f"B-check de la Unidad {i} - BETEENS",
        }
    )

# Generar XML
xml_content = """<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">

        <!-- ============================================ -->
        <!-- ASIGNATURAS B-CHECKS - BETEENS -->
        <!-- ============================================ -->
        <!-- 24 B-checks (uno por unidad) para programa BETEENS -->

"""

for bcheck in bchecks:
    xml_content += f"""        <record id="{bcheck['id']}" model="benglish.subject">
            <field name="name">{bcheck['name']}</field>
            <field name="alias">{bcheck['alias']}</field>
            <field name="code">{bcheck['code']}</field>
            <field name="level_id" ref="{bcheck['level_ref']}" />
            <field name="sequence">10</field>
            <field name="subject_type">core</field>
            <field name="subject_classification">prerequisite</field>
            <field name="subject_category">bcheck</field>
            <field name="unit_number">{bcheck['unit']}</field>
            <field name="hours">1</field>
            <field name="credits">0</field>
            <field name="description">{bcheck['description']}</field>
            <field name="active" eval="True" />
        </record>

"""

xml_content += """    </data>
</odoo>
"""

# Escribir archivo
output_file = os.path.join(
    os.path.dirname(__file__), "..", "data", "subjects_bchecks_beteens.xml"
)
with open(output_file, "w", encoding="utf-8") as f:
    f.write(xml_content)

print(f"✅ Archivo regenerado: {output_file}")
print(f"📊 Total de B-checks: {len(bchecks)}")
print("🔍 Estructura:")
print("   - BASIC: 8 B-checks (unidades 1-8)")
print("   - ELEMENTARY: 8 B-checks (unidades 1-8)")
print("   - PRE-INTERMEDIATE: 8 B-checks (unidades 1-8)")
