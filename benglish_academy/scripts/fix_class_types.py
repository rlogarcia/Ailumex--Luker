#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para regenerar class_types_structured.xml sin campos inválidos
"""


def generate_class_types_xml():
    output = """<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">

        <!-- ============================================ -->
        <!-- TIPOS DE CLASE CON ESTRUCTURA COMPLETA -->
        <!-- ============================================ -->
        <!-- 24 B-checks + 1 Bskills + 6 Oral Tests = 31 tipos -->

        <!-- ========================================== -->
        <!-- CLASS TYPES - B-CHECKS (24 unidades) -->
        <!-- ========================================== -->

"""

    # Generar 24 B-check types
    for unit in range(1, 25):
        phase = "Basic" if unit <= 8 else "Intermediate" if unit <= 16 else "Advanced"
        output += f"""        <record id="class_type_bcheck_unit_{unit}" model="benglish.class.type">
            <field name="name">{phase} - B Check U{unit}</field>
            <field name="code">BCHECK_U{unit}</field>
            <field name="category">bcheck</field>
            <field name="bcheck_subcategory">unit_{unit}</field>
            <field name="unit_number">{unit}</field>
            <field name="is_prerequisite" eval="True" />
            <field name="active" eval="True" />
        </record>

"""

    # Generar Bskills type
    output += """        <!-- ========================================== -->
        <!-- CLASS TYPE - BSKILLS (genérico) -->
        <!-- ========================================== -->

        <record id="class_type_bskills" model="benglish.class.type">
            <field name="name">B Skills</field>
            <field name="code">BSKILLS</field>
            <field name="category">bskills</field>
            <field name="active" eval="True" />
        </record>

        <!-- ========================================== -->
        <!-- CLASS TYPES - ORAL TESTS (6 bloques) -->
        <!-- ========================================== -->

"""

    # Generar 6 Oral Test types
    blocks = [
        (1, 4, "Basic"),
        (5, 8, "Basic"),
        (9, 12, "Intermediate"),
        (13, 16, "Intermediate"),
        (17, 20, "Advanced"),
        (21, 24, "Advanced"),
    ]

    for start, end, phase in blocks:
        output += f"""        <record id="class_type_oral_test_u{start}_{end}" model="benglish.class.type">
            <field name="name">{phase} - Oral Test U{start}-{end}</field>
            <field name="code">ORAL_TEST_U{start}_{end}</field>
            <field name="category">oral_test</field>
            <field name="unit_block_start">{start}</field>
            <field name="unit_block_end">{end}</field>
            <field name="is_prerequisite" eval="False" />
            <field name="active" eval="True" />
        </record>

"""

    output += """    </data>
</odoo>"""

    return output


if __name__ == "__main__":
    xml_content = generate_class_types_xml()

    output_file = (
        r"d:\AiLumex\Ailumex--Be\benglish_academy\data\class_types_structured.xml"
    )
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(xml_content)

    print("✓ class_types_structured.xml regenerado (31 registros)")
    print("  - 24 B-check types")
    print("  - 1 Bskills type")
    print("  - 6 Oral Test types")
    print("\nCampos eliminados (no existen en el modelo):")
    print("  - allows_enroll_multiple_students")
    print("  - max_students")
