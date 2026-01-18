"""
Script para regenerar el archivo subjects_bskills_beteens.xml
Elimina atributos en múltiples líneas y el --> huérfano
"""

import os

# Datos de los 96 Bskills para BETEENS
bskills = []

unit_mapping = {
    **{i: ("Basic", f"level_beteens_basic_unit{i}") for i in range(1, 9)},
    **{
        i: ("Intermediate", f"level_beteens_intermediate_unit{i}")
        for i in range(9, 17)
    },
    **{i: ("Advanced", f"level_beteens_advanced_unit{i}") for i in range(17, 25)},
}
skill_map = {
    1: "GRAMMAR",
    2: "VOCABULARY",
    3: "SPEAKING",
    4: "LISTENING",
}
skill_label_map = {
    1: "Grammar",
    2: "Vocabulary",
    3: "Speaking",
    4: "Listening",
}

for unit in range(1, 25):
    phase, level_ref = unit_mapping[unit]
    for skill_num in range(1, 5):
        skill_name = skill_map[skill_num]
        skill_label = skill_label_map[skill_num]
        bskills.append(
            {
                "id": f"subject_beteens_bskill_u{unit}_{skill_num}",
                "name": f"{phase}-{skill_name}-U{unit}",
                "alias": "skill",
                "code": f"BSKILL-U{unit}-{skill_num}-BETEENS",
                "level_ref": level_ref,
                "bcheck_ref": f"subject_beteens_bcheck_unit{unit}",
                "unit": unit,
                "skill_num": skill_num,
                "sequence": 19 + skill_num,
                "description": f"B-skill {skill_label} de la Unidad {unit} - BETEENS",
            }
        )

# Generar XML
xml_content = """<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">

        <!-- ============================================ -->
        <!-- ASIGNATURAS B-SKILLS - BETEENS -->
        <!-- ============================================ -->
        <!-- 96 Bskills (4 por unidad × 24 unidades) para BETEENS -->

"""

for bskill in bskills:
    xml_content += f"""        <record id="{bskill['id']}" model="benglish.subject">
            <field name="name">{bskill['name']}</field>
            <field name="alias">{bskill['alias']}</field>
            <field name="code">{bskill['code']}</field>
            <field name="level_id" ref="{bskill['level_ref']}" />
            <field name="sequence">{bskill['sequence']}</field>
            <field name="subject_type">core</field>
            <field name="subject_classification">regular</field>
            <field name="subject_category">bskills</field>
            <field name="unit_number">{bskill['unit']}</field>
            <field name="bskill_number">{bskill['skill_num']}</field>
            <field name="hours">1</field>
            <field name="credits">0</field>
            <field name="description">{bskill['description']}</field>
            <field name="prerequisite_ids" eval="[(6, 0, [ref('{bskill['bcheck_ref']}')])]" />
            <field name="active" eval="True" />
        </record>

"""

xml_content += """    </data>
</odoo>
"""

# Escribir archivo
output_file = os.path.join(
    os.path.dirname(__file__), "..", "data", "subjects_bskills_beteens.xml"
)
with open(output_file, "w", encoding="utf-8") as f:
    f.write(xml_content)

print(f"✅ Archivo regenerado: {output_file}")
print(f"📊 Total de Bskills: {len(bskills)}")
print("🔍 Estructura:")
print("   - BASIC: 32 Bskills (8 unidades × 4 skills)")
print("   - INTERMEDIATE: 32 Bskills (8 unidades × 4 skills)")
print("   - ADVANCED: 32 Bskills (8 unidades × 4 skills)")
