#!/usr/bin/env python3
"""
Script para generar TODAS las 96 Bskills de BENGLISH (4 por unidad x 24 unidades)
"""


def generate_bskills_benglish():
    """Genera las 96 Bskills completas para BENGLISH"""

    # Mapeo de unidades a fases y niveles
    unit_mapping = {
        # Basic: 1-8
        **{i: ("Basic", f"level_benglish_basic_unit{i}") for i in range(1, 9)},
        # Intermediate: 9-16
        **{
            i: ("Intermediate", f"level_benglish_intermediate_unit{i}")
            for i in range(9, 17)
        },
        # Advanced: 17-24
        **{i: ("Advanced", f"level_benglish_advanced_unit{i}") for i in range(17, 25)},
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

    xml_records = []
    xml_records.append('<?xml version="1.0" encoding="utf-8"?>')
    xml_records.append("<odoo>")
    xml_records.append('    <data noupdate="1">')
    xml_records.append("")
    xml_records.append("        <!-- ============================================ -->")
    xml_records.append("        <!-- ASIGNATURAS B-SKILLS - BENGLISH - COMPLETO -->")
    xml_records.append("        <!-- ============================================ -->")
    xml_records.append("        <!-- ")
    xml_records.append("        GENERADO AUTOMÁTICAMENTE")
    xml_records.append("        4 Bskills por UNIT x 24 UNITS = 96 Bskills totales")
    xml_records.append("        -->")
    xml_records.append("")

    for unit in range(1, 25):
        phase, level_id = unit_mapping[unit]

        xml_records.append("")
        xml_records.append(
            f"        <!-- ========================================== -->"
        )
        xml_records.append(f"        <!-- {phase.upper()} - UNIT {unit} -->")
        xml_records.append(
            f"        <!-- ========================================== -->"
        )
        xml_records.append("")

        for bskill_num in range(1, 5):
            skill_name = skill_map[bskill_num]
            skill_label = skill_label_map[bskill_num]
            record_id = f"subject_benglish_bskill_u{unit}_{bskill_num}"
            name = f"{phase}-{skill_name}-U{unit}"
            alias = "skill"
            code = f"BSKILL-U{unit}-{bskill_num}"
            sequence = 19 + bskill_num
            bcheck_ref = f"subject_benglish_bcheck_unit{unit}"

            xml_records.append(
                f'        <record id="{record_id}" model="benglish.subject">'
            )
            xml_records.append(f'            <field name="name">{name}</field>')
            xml_records.append(f'            <field name="alias">{alias}</field>')
            xml_records.append(f'            <field name="code">{code}</field>')
            xml_records.append(
                f'            <field name="level_id" ref="{level_id}" />'
            )
            xml_records.append(f'            <field name="sequence">{sequence}</field>')
            xml_records.append(f'            <field name="subject_type">core</field>')
            xml_records.append(
                f'            <field name="subject_classification">regular</field>'
            )
            xml_records.append(
                f'            <field name="subject_category">bskills</field>'
            )
            xml_records.append(f'            <field name="unit_number">{unit}</field>')
            xml_records.append(
                f'            <field name="bskill_number">{bskill_num}</field>'
            )
            xml_records.append(f'            <field name="hours">1</field>')
            xml_records.append(f'            <field name="credits">0</field>')
            xml_records.append(
                f'            <field name="description">B-skill {skill_label} de la Unidad {unit}</field>'
            )
            xml_records.append(
                f'            <field name="prerequisite_ids" eval="[(6, 0, [ref(\'{bcheck_ref}\')])]" />'
            )
            xml_records.append(f'            <field name="active" eval="True" />')
            xml_records.append(f"        </record>")
            xml_records.append("")

    xml_records.append("    </data>")
    xml_records.append("</odoo>")

    return "\n".join(xml_records)


if __name__ == "__main__":
    content = generate_bskills_benglish()
    output_path = "../data/subjects_bskills_benglish.xml"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✓ Archivo generado: {output_path}")
    print(f"✓ 96 Bskills completas para BENGLISH")
