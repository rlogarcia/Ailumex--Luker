#!/usr/bin/env python3
"""
Script para generar todos los archivos XML completos de la estructura académica
"""


def generate_bchecks_beteens():
    """Genera 24 B-checks para BETEENS"""

    unit_mapping = {
        **{
            i: ("Basic", f"level_beteens_plus_mixto_basic_unit{i}") for i in range(1, 9)
        },
        **{
            i: ("Intermediate", f"level_beteens_plus_mixto_intermediate_unit{i}")
            for i in range(9, 17)
        },
        **{
            i: ("Advanced", f"level_beteens_plus_mixto_advanced_unit{i}")
            for i in range(17, 25)
        },
    }

    xml = []
    xml.append('<?xml version="1.0" encoding="utf-8"?>')
    xml.append("<odoo>")
    xml.append('    <data noupdate="1">')
    xml.append("")
    xml.append("        <!-- ============================================ -->")
    xml.append("        <!-- ASIGNATURAS B-CHECKS - BETEENS -->")
    xml.append("        <!-- ============================================ -->")
    xml.append("        <!-- 24 B-checks (uno por unidad) para programa BETEENS -->")
    xml.append("        -->")
    xml.append("")

    for unit in range(1, 25):
        phase, level_id = unit_mapping[unit]

        record_id = f"subject_beteens_bcheck_unit{unit}"
        name = f"{phase}-B Check U{unit}"
        alias = f"B-check U{unit}"
        code = f"BCHECK-U{unit}-BETEENS"
        sequence = 10

        xml.append(f'        <record id="{record_id}" model="benglish.subject">')
        xml.append(f'            <field name="name">{name}</field>')
        xml.append(f'            <field name="alias">{alias}</field>')
        xml.append(f'            <field name="code">{code}</field>')
        xml.append(f'            <field name="level_id" ref="{level_id}" />')
        xml.append(f'            <field name="sequence">{sequence}</field>')
        xml.append(f'            <field name="subject_type">core</field>')
        xml.append(f'            <field name="subject_classification">regular</field>')
        xml.append(f'            <field name="subject_category">bcheck</field>')
        xml.append(f'            <field name="unit_number">{unit}</field>')
        xml.append(f'            <field name="hours">1</field>')
        xml.append(f'            <field name="credits">0</field>')
        xml.append(
            f'            <field name="description">B-check de la Unidad {unit} - BETEENS</field>'
        )
        xml.append(f'            <field name="active" eval="True" />')
        xml.append(f"        </record>")
        xml.append("")

    xml.append("    </data>")
    xml.append("</odoo>")

    return "\n".join(xml)


def generate_bskills_beteens():
    """Genera 96 Bskills para BETEENS"""

    unit_mapping = {
        **{
            i: ("Basic", f"level_beteens_plus_mixto_basic_unit{i}") for i in range(1, 9)
        },
        **{
            i: ("Intermediate", f"level_beteens_plus_mixto_intermediate_unit{i}")
            for i in range(9, 17)
        },
        **{
            i: ("Advanced", f"level_beteens_plus_mixto_advanced_unit{i}")
            for i in range(17, 25)
        },
    }

    xml = []
    xml.append('<?xml version="1.0" encoding="utf-8"?>')
    xml.append("<odoo>")
    xml.append('    <data noupdate="1">')
    xml.append("")
    xml.append("        <!-- ============================================ -->")
    xml.append("        <!-- ASIGNATURAS B-SKILLS - BETEENS - COMPLETO -->")
    xml.append("        <!-- ============================================ -->")
    xml.append("        <!-- 96 Bskills (4 por unidad × 24 unidades) para BETEENS -->")
    xml.append("        -->")
    xml.append("")

    for unit in range(1, 25):
        phase, level_id = unit_mapping[unit]

        xml.append(f"        <!-- {phase.upper()} - UNIT {unit} -->")
        xml.append("")

        for bskill_num in range(1, 5):
            record_id = f"subject_beteens_bskill_u{unit}_{bskill_num}"
            name = f"{phase}-Bskill U{unit} - {bskill_num}"
            alias = f"Bskill U{unit}-{bskill_num}"
            code = f"BSKILL-U{unit}-{bskill_num}-BETEENS"
            sequence = 19 + bskill_num
            bcheck_ref = f"subject_beteens_bcheck_unit{unit}"

            xml.append(f'        <record id="{record_id}" model="benglish.subject">')
            xml.append(f'            <field name="name">{name}</field>')
            xml.append(f'            <field name="alias">{alias}</field>')
            xml.append(f'            <field name="code">{code}</field>')
            xml.append(f'            <field name="level_id" ref="{level_id}" />')
            xml.append(f'            <field name="sequence">{sequence}</field>')
            xml.append(f'            <field name="subject_type">core</field>')
            xml.append(
                f'            <field name="subject_classification">regular</field>'
            )
            xml.append(f'            <field name="subject_category">bskills</field>')
            xml.append(f'            <field name="unit_number">{unit}</field>')
            xml.append(f'            <field name="bskill_number">{bskill_num}</field>')
            xml.append(f'            <field name="hours">1</field>')
            xml.append(f'            <field name="credits">0</field>')
            xml.append(
                f'            <field name="description">B-skill {bskill_num} de la Unidad {unit} - BETEENS</field>'
            )
            xml.append(
                f'            <field name="prerequisite_ids" eval="[(6, 0, [ref(\'{bcheck_ref}\')])]" />'
            )
            xml.append(f'            <field name="active" eval="True" />')
            xml.append(f"        </record>")
            xml.append("")

    xml.append("    </data>")
    xml.append("</odoo>")

    return "\n".join(xml)


def generate_oral_tests_beteens():
    """Genera 6 Oral Tests para BETEENS con todos los prerrequisitos"""

    # Define los bloques de Oral Tests
    blocks = [
        (1, 4, "level_beteens_plus_mixto_basic_unit4"),
        (5, 8, "level_beteens_plus_mixto_basic_unit8"),
        (9, 12, "level_beteens_plus_mixto_intermediate_unit12"),
        (13, 16, "level_beteens_plus_mixto_intermediate_unit16"),
        (17, 20, "level_beteens_plus_mixto_advanced_unit20"),
        (21, 24, "level_beteens_plus_mixto_advanced_unit24"),
    ]

    xml = []
    xml.append('<?xml version="1.0" encoding="utf-8"?>')
    xml.append("<odoo>")
    xml.append('    <data noupdate="1">')
    xml.append("")
    xml.append("        <!-- ============================================ -->")
    xml.append("        <!-- ASIGNATURAS ORAL TESTS - BETEENS -->")
    xml.append("        <!-- ============================================ -->")
    xml.append("        <!-- 6 Oral Tests (uno por bloque de 4 unidades) -->")
    xml.append("        <!-- Cada uno requiere TODAS las 16 Bskills de su bloque -->")
    xml.append("        -->")
    xml.append("")

    for start_unit, end_unit, level_id in blocks:
        # Determinar la fase
        if start_unit <= 8:
            phase = "Basic"
        elif start_unit <= 16:
            phase = "Intermediate"
        else:
            phase = "Advanced"

        record_id = f"subject_beteens_oral_test_u{start_unit}_{end_unit}"
        name = f"{phase}-Oral Test U{start_unit}-{end_unit}"
        alias = f"Oral Test U{start_unit}-{end_unit}"
        code = f"ORAL-TEST-U{start_unit}-{end_unit}-BETEENS"
        sequence = 30

        # Generar referencias a todas las Bskills del bloque (4 unidades × 4 bskills = 16)
        bskill_refs = []
        for unit in range(start_unit, end_unit + 1):
            for bskill_num in range(1, 5):
                bskill_refs.append(
                    f"ref('subject_beteens_bskill_u{unit}_{bskill_num}')"
                )

        prereq_eval = f"[(6, 0, [{', '.join(bskill_refs)}])]"

        xml.append(f'        <record id="{record_id}" model="benglish.subject">')
        xml.append(f'            <field name="name">{name}</field>')
        xml.append(f'            <field name="alias">{alias}</field>')
        xml.append(f'            <field name="code">{code}</field>')
        xml.append(f'            <field name="level_id" ref="{level_id}" />')
        xml.append(f'            <field name="sequence">{sequence}</field>')
        xml.append(f'            <field name="subject_type">core</field>')
        xml.append(f'            <field name="subject_classification">regular</field>')
        xml.append(f'            <field name="subject_category">oral_test</field>')
        xml.append(f'            <field name="unit_block_start">{start_unit}</field>')
        xml.append(f'            <field name="unit_block_end">{end_unit}</field>')
        xml.append(f'            <field name="hours">1</field>')
        xml.append(f'            <field name="credits">0</field>')
        xml.append(
            f'            <field name="description">Oral Test de las unidades {start_unit} a {end_unit} - BETEENS</field>'
        )
        xml.append(
            f'            <field name="prerequisite_ids" eval="{prereq_eval}" />'
        )
        xml.append(f'            <field name="active" eval="True" />')
        xml.append(f"        </record>")
        xml.append("")

    xml.append("    </data>")
    xml.append("</odoo>")

    return "\n".join(xml)


def generate_oral_tests_benglish_complete():
    """Genera 6 Oral Tests para BENGLISH con TODOS los prerrequisitos"""

    blocks = [
        (1, 4, "level_benglish_plus_mixto_basic_unit4"),
        (5, 8, "level_benglish_plus_mixto_basic_unit8"),
        (9, 12, "level_benglish_plus_mixto_intermediate_unit12"),
        (13, 16, "level_benglish_plus_mixto_intermediate_unit16"),
        (17, 20, "level_benglish_plus_mixto_advanced_unit20"),
        (21, 24, "level_benglish_plus_mixto_advanced_unit24"),
    ]

    xml = []
    xml.append('<?xml version="1.0" encoding="utf-8"?>')
    xml.append("<odoo>")
    xml.append('    <data noupdate="1">')
    xml.append("")
    xml.append("        <!-- ============================================ -->")
    xml.append("        <!-- ASIGNATURAS ORAL TESTS - BENGLISH -->")
    xml.append("        <!-- ============================================ -->")
    xml.append("        <!-- 6 Oral Tests (uno por bloque de 4 unidades) -->")
    xml.append("        <!-- Cada uno requiere TODAS las 16 Bskills de su bloque -->")
    xml.append("        -->")
    xml.append("")

    for start_unit, end_unit, level_id in blocks:
        if start_unit <= 8:
            phase = "Basic"
        elif start_unit <= 16:
            phase = "Intermediate"
        else:
            phase = "Advanced"

        record_id = f"subject_benglish_oral_test_u{start_unit}_{end_unit}"
        name = f"{phase}-Oral Test U{start_unit}-{end_unit}"
        alias = f"Oral Test U{start_unit}-{end_unit}"
        code = f"ORAL-TEST-U{start_unit}-{end_unit}"
        sequence = 30

        bskill_refs = []
        for unit in range(start_unit, end_unit + 1):
            for bskill_num in range(1, 5):
                bskill_refs.append(
                    f"ref('subject_benglish_bskill_u{unit}_{bskill_num}')"
                )

        prereq_eval = f"[(6, 0, [{', '.join(bskill_refs)}])]"

        xml.append(f'        <record id="{record_id}" model="benglish.subject">')
        xml.append(f'            <field name="name">{name}</field>')
        xml.append(f'            <field name="alias">{alias}</field>')
        xml.append(f'            <field name="code">{code}</field>')
        xml.append(f'            <field name="level_id" ref="{level_id}" />')
        xml.append(f'            <field name="sequence">{sequence}</field>')
        xml.append(f'            <field name="subject_type">core</field>')
        xml.append(f'            <field name="subject_classification">regular</field>')
        xml.append(f'            <field name="subject_category">oral_test</field>')
        xml.append(f'            <field name="unit_block_start">{start_unit}</field>')
        xml.append(f'            <field name="unit_block_end">{end_unit}</field>')
        xml.append(f'            <field name="hours">1</field>')
        xml.append(f'            <field name="credits">0</field>')
        xml.append(
            f'            <field name="description">Oral Test de las unidades {start_unit} a {end_unit}</field>'
        )
        xml.append(
            f'            <field name="prerequisite_ids" eval="{prereq_eval}" />'
        )
        xml.append(f'            <field name="active" eval="True" />')
        xml.append(f"        </record>")
        xml.append("")

    xml.append("    </data>")
    xml.append("</odoo>")

    return "\n".join(xml)


def generate_class_types_complete():
    """Genera TODOS los class types necesarios"""

    xml = []
    xml.append('<?xml version="1.0" encoding="utf-8"?>')
    xml.append("<odoo>")
    xml.append('    <data noupdate="1">')
    xml.append("")
    xml.append("        <!-- ============================================ -->")
    xml.append("        <!-- TIPOS DE CLASE CON ESTRUCTURA COMPLETA -->")
    xml.append("        <!-- ============================================ -->")
    xml.append("        <!-- 24 B-checks + 1 Bskills + 6 Oral Tests = 31 tipos -->")
    xml.append("        -->")
    xml.append("")

    # 24 B-checks (uno por unidad)
    xml.append("        <!-- ========================================== -->")
    xml.append("        <!-- CLASS TYPES - B-CHECKS (24 unidades) -->")
    xml.append("        <!-- ========================================== -->")
    xml.append("")

    for unit in range(1, 25):
        if unit <= 8:
            phase = "Basic"
        elif unit <= 16:
            phase = "Intermediate"
        else:
            phase = "Advanced"

        record_id = f"class_type_bcheck_unit_{unit}"
        name = f"{phase} - B Check U{unit}"
        code = f"BCHECK_U{unit}"

        xml.append(f'        <record id="{record_id}" model="benglish.class.type">')
        xml.append(f'            <field name="name">{name}</field>')
        xml.append(f'            <field name="code">{code}</field>')
        xml.append(f'            <field name="category">bcheck</field>')
        xml.append(f'            <field name="bcheck_subcategory">unit_{unit}</field>')
        xml.append(f'            <field name="unit_number">{unit}</field>')
        xml.append(f'            <field name="is_prerequisite" eval="True" />')
        xml.append(
            f'            <field name="allows_enroll_multiple_students" eval="True" />'
        )
        xml.append(f'            <field name="max_students">20</field>')
        xml.append(f'            <field name="active" eval="True" />')
        xml.append(f"        </record>")
        xml.append("")

    # 1 Bskills genérico
    xml.append("        <!-- ========================================== -->")
    xml.append("        <!-- CLASS TYPE - BSKILLS (genérico) -->")
    xml.append("        <!-- ========================================== -->")
    xml.append("")
    xml.append('        <record id="class_type_bskills" model="benglish.class.type">')
    xml.append('            <field name="name">B-Skills</field>')
    xml.append('            <field name="code">BSKILLS</field>')
    xml.append('            <field name="category">bskills</field>')
    xml.append('            <field name="is_prerequisite" eval="False" />')
    xml.append(
        '            <field name="allows_enroll_multiple_students" eval="True" />'
    )
    xml.append('            <field name="max_students">20</field>')
    xml.append('            <field name="active" eval="True" />')
    xml.append("        </record>")
    xml.append("")

    # 6 Oral Tests
    xml.append("        <!-- ========================================== -->")
    xml.append("        <!-- CLASS TYPES - ORAL TESTS (6 bloques) -->")
    xml.append("        <!-- ========================================== -->")
    xml.append("")

    blocks = [
        (1, 4, "Basic"),
        (5, 8, "Basic"),
        (9, 12, "Intermediate"),
        (13, 16, "Intermediate"),
        (17, 20, "Advanced"),
        (21, 24, "Advanced"),
    ]

    for start_unit, end_unit, phase in blocks:
        record_id = f"class_type_oral_test_u{start_unit}_{end_unit}"
        name = f"{phase} - Oral Test U{start_unit}-{end_unit}"
        code = f"ORAL_TEST_U{start_unit}_{end_unit}"

        xml.append(f'        <record id="{record_id}" model="benglish.class.type">')
        xml.append(f'            <field name="name">{name}</field>')
        xml.append(f'            <field name="code">{code}</field>')
        xml.append(f'            <field name="category">oral_test</field>')
        xml.append(f'            <field name="unit_block_start">{start_unit}</field>')
        xml.append(f'            <field name="unit_block_end">{end_unit}</field>')
        xml.append(f'            <field name="is_prerequisite" eval="False" />')
        xml.append(
            f'            <field name="allows_enroll_multiple_students" eval="True" />'
        )
        xml.append(f'            <field name="max_students">20</field>')
        xml.append(f'            <field name="active" eval="True" />')
        xml.append(f"        </record>")
        xml.append("")

    xml.append("    </data>")
    xml.append("</odoo>")

    return "\n".join(xml)


if __name__ == "__main__":
    import os

    base_path = "../data/"

    files = [
        ("subjects_bchecks_beteens.xml", generate_bchecks_beteens()),
        ("subjects_bskills_beteens.xml", generate_bskills_beteens()),
        ("subjects_oral_tests_beteens.xml", generate_oral_tests_beteens()),
        ("subjects_oral_tests_benglish.xml", generate_oral_tests_benglish_complete()),
        ("class_types_structured.xml", generate_class_types_complete()),
    ]

    for filename, content in files:
        filepath = os.path.join(base_path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✓ {filename}")

    print("\n=== RESUMEN ===")
    print("BENGLISH:")
    print("  - 24 B-checks ✓")
    print("  - 96 Bskills ✓")
    print("  - 6 Oral Tests (con 16 prerrequisitos cada uno) ✓")
    print("\nBETEENS:")
    print("  - 24 B-checks ✓")
    print("  - 96 Bskills ✓")
    print("  - 6 Oral Tests (con 16 prerrequisitos cada uno) ✓")
    print("\nCLASS TYPES:")
    print("  - 24 B-check types ✓")
    print("  - 1 Bskills type ✓")
    print("  - 6 Oral Test types ✓")
    print("  - TOTAL: 31 class types")
