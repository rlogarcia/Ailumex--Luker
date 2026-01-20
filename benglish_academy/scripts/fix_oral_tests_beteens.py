"""
Script para regenerar el archivo subjects_oral_tests_beteens.xml
Elimina atributos en múltiples líneas y el --> huérfano
"""

import os

# Datos de los 6 Oral Tests para BETEENS Plus Mixto
oral_tests = []

# BASIC - 2 Oral Tests (U1-4, U5-8)
oral_tests.append(
    {
        "id": "subject_beteens_oral_test_u1_4",
        "name": "Basic-Oral Test U1-4",
        "alias": "Oral Test U1-4",
        "code": "ORAL-TEST-U1-4-BETEENS",
        "level_ref": "level_beteens_plus_mixto_basic_unit4",
        "unit_start": 1,
        "unit_end": 4,
        "description": "Oral Test de las unidades 1 a 4 - BETEENS",
        "bskills": [
            f"subject_beteens_bskill_u{u}_{s}" for u in range(1, 5) for s in range(1, 5)
        ],
    }
)

oral_tests.append(
    {
        "id": "subject_beteens_oral_test_u5_8",
        "name": "Basic-Oral Test U5-8",
        "alias": "Oral Test U5-8",
        "code": "ORAL-TEST-U5-8-BETEENS",
        "level_ref": "level_beteens_plus_mixto_basic_unit8",
        "unit_start": 5,
        "unit_end": 8,
        "description": "Oral Test de las unidades 5 a 8 - BETEENS",
        "bskills": [
            f"subject_beteens_bskill_u{u}_{s}" for u in range(5, 9) for s in range(1, 5)
        ],
    }
)

# ELEMENTARY - 2 Oral Tests (U1-4, U5-8)
oral_tests.append(
    {
        "id": "subject_beteens_oral_test_u9_12",
        "name": "Elementary-Oral Test U1-4",
        "alias": "Oral Test U1-4",
        "code": "ORAL-TEST-U1-4-BETEENS",
        "level_ref": "level_beteens_plus_mixto_elementary_unit4",
        "unit_start": 1,
        "unit_end": 4,
        "description": "Oral Test de las unidades 1 a 4 - BETEENS",
        "bskills": [
            f"subject_beteens_bskill_u{u}_{s}"
            for u in range(9, 13)
            for s in range(1, 5)
        ],
    }
)

oral_tests.append(
    {
        "id": "subject_beteens_oral_test_u13_16",
        "name": "Elementary-Oral Test U5-8",
        "alias": "Oral Test U5-8",
        "code": "ORAL-TEST-U5-8-BETEENS",
        "level_ref": "level_beteens_plus_mixto_elementary_unit8",
        "unit_start": 5,
        "unit_end": 8,
        "description": "Oral Test de las unidades 5 a 8 - BETEENS",
        "bskills": [
            f"subject_beteens_bskill_u{u}_{s}"
            for u in range(13, 17)
            for s in range(1, 5)
        ],
    }
)

# PRE-INTERMEDIATE - 2 Oral Tests (U1-4, U5-8)
oral_tests.append(
    {
        "id": "subject_beteens_oral_test_u17_20",
        "name": "Pre-Intermediate-Oral Test U1-4",
        "alias": "Oral Test U1-4",
        "code": "ORAL-TEST-U1-4-BETEENS",
        "level_ref": "level_beteens_plus_mixto_preintermediate_unit4",
        "unit_start": 1,
        "unit_end": 4,
        "description": "Oral Test de las unidades 1 a 4 - BETEENS",
        "bskills": [
            f"subject_beteens_bskill_u{u}_{s}"
            for u in range(17, 21)
            for s in range(1, 5)
        ],
    }
)

oral_tests.append(
    {
        "id": "subject_beteens_oral_test_u21_24",
        "name": "Pre-Intermediate-Oral Test U5-8",
        "alias": "Oral Test U5-8",
        "code": "ORAL-TEST-U5-8-BETEENS",
        "level_ref": "level_beteens_plus_mixto_preintermediate_unit8",
        "unit_start": 5,
        "unit_end": 8,
        "description": "Oral Test de las unidades 5 a 8 - BETEENS",
        "bskills": [
            f"subject_beteens_bskill_u{u}_{s}"
            for u in range(21, 25)
            for s in range(1, 5)
        ],
    }
)

# Generar XML
xml_content = """<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">

        <!-- ============================================ -->
        <!-- ASIGNATURAS ORAL TESTS - BETEENS -->
        <!-- ============================================ -->
        <!-- 6 Oral Tests (uno por bloque de 4 unidades) -->
        <!-- Cada uno requiere TODAS las 16 Bskills de su bloque -->

"""

for test in oral_tests:
    # Construir prerequisite_ids en una sola línea
    prereq_refs = ", ".join([f"ref('{bskill}')" for bskill in test["bskills"]])

    xml_content += f"""        <record id="{test['id']}" model="benglish.subject">
            <field name="name">{test['name']}</field>
            <field name="alias">{test['alias']}</field>
            <field name="code">{test['code']}</field>
            <field name="level_id" ref="{test['level_ref']}" />
            <field name="sequence">30</field>
            <field name="subject_type">core</field>
            <field name="subject_classification">evaluation</field>
            <field name="subject_category">oral_test</field>
            <field name="unit_block_start">{test['unit_start']}</field>
            <field name="unit_block_end">{test['unit_end']}</field>
            <field name="hours">1</field>
            <field name="credits">0</field>
            <field name="description">{test['description']}</field>
            <field name="prerequisite_ids" eval="[(6, 0, [{prereq_refs}])]" />
            <field name="active" eval="True" />
        </record>

"""

xml_content += """    </data>
</odoo>
"""

# Escribir archivo
output_file = os.path.join(
    os.path.dirname(__file__), "..", "data", "subjects_oral_tests_beteens.xml"
)
with open(output_file, "w", encoding="utf-8") as f:
    f.write(xml_content)

print(f"✅ Archivo regenerado: {output_file}")
print(f"📊 Total de Oral Tests: {len(oral_tests)}")
print("🔍 Estructura:")
print("   - BASIC: 2 Oral Tests (U1-4, U5-8)")
print("   - ELEMENTARY: 2 Oral Tests (U1-4, U5-8)")
print("   - PRE-INTERMEDIATE: 2 Oral Tests (U1-4, U5-8)")
print("   - Cada Oral Test requiere 16 Bskills")
