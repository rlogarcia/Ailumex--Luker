#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para regenerar subjects_oral_tests_benglish.xml limpio"""

content = """<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">

        <!-- ============================================ -->
        <!-- ASIGNATURAS ORAL TESTS - BENGLISH -->
        <!-- ============================================ -->
        <!-- 6 Oral Tests (uno por bloque de 4 unidades) -->
        <!-- Cada uno requiere TODAS las 16 Bskills de su bloque -->

        <record id="subject_benglish_oral_test_u1_4" model="benglish.subject">
            <field name="name">Basic-Oral Test U1-4</field>
            <field name="alias">Oral Test U1-4</field>
            <field name="code">ORAL-TEST-U1-4</field>
            <field name="level_id" ref="level_benglish_plus_mixto_basic_unit4" />
            <field name="sequence">30</field>
            <field name="subject_type">core</field>
            <field name="subject_classification">evaluation</field>
            <field name="subject_category">oral_test</field>
            <field name="unit_block_start">1</field>
            <field name="unit_block_end">4</field>
            <field name="hours">1</field>
            <field name="credits">0</field>
            <field name="description">Oral Test de las unidades 1 a 4</field>
            <field name="prerequisite_ids" eval="[(6, 0, [ref('subject_benglish_bskill_u1_1'), ref('subject_benglish_bskill_u1_2'), ref('subject_benglish_bskill_u1_3'), ref('subject_benglish_bskill_u1_4'), ref('subject_benglish_bskill_u2_1'), ref('subject_benglish_bskill_u2_2'), ref('subject_benglish_bskill_u2_3'), ref('subject_benglish_bskill_u2_4'), ref('subject_benglish_bskill_u3_1'), ref('subject_benglish_bskill_u3_2'), ref('subject_benglish_bskill_u3_3'), ref('subject_benglish_bskill_u3_4'), ref('subject_benglish_bskill_u4_1'), ref('subject_benglish_bskill_u4_2'), ref('subject_benglish_bskill_u4_3'), ref('subject_benglish_bskill_u4_4')])]" />
            <field name="active" eval="True" />
        </record>

        <record id="subject_benglish_oral_test_u5_8" model="benglish.subject">
            <field name="name">Basic-Oral Test U5-8</field>
            <field name="alias">Oral Test U5-8</field>
            <field name="code">ORAL-TEST-U5-8</field>
            <field name="level_id" ref="level_benglish_plus_mixto_basic_unit8" />
            <field name="sequence">30</field>
            <field name="subject_type">core</field>
            <field name="subject_classification">evaluation</field>
            <field name="subject_category">oral_test</field>
            <field name="unit_block_start">5</field>
            <field name="unit_block_end">8</field>
            <field name="hours">1</field>
            <field name="credits">0</field>
            <field name="description">Oral Test de las unidades 5 a 8</field>
            <field name="prerequisite_ids" eval="[(6, 0, [ref('subject_benglish_bskill_u5_1'), ref('subject_benglish_bskill_u5_2'), ref('subject_benglish_bskill_u5_3'), ref('subject_benglish_bskill_u5_4'), ref('subject_benglish_bskill_u6_1'), ref('subject_benglish_bskill_u6_2'), ref('subject_benglish_bskill_u6_3'), ref('subject_benglish_bskill_u6_4'), ref('subject_benglish_bskill_u7_1'), ref('subject_benglish_bskill_u7_2'), ref('subject_benglish_bskill_u7_3'), ref('subject_benglish_bskill_u7_4'), ref('subject_benglish_bskill_u8_1'), ref('subject_benglish_bskill_u8_2'), ref('subject_benglish_bskill_u8_3'), ref('subject_benglish_bskill_u8_4')])]" />
            <field name="active" eval="True" />
        </record>

        <record id="subject_benglish_oral_test_u9_12" model="benglish.subject">
            <field name="name">Intermediate-Oral Test U9-12</field>
            <field name="alias">Oral Test U9-12</field>
            <field name="code">ORAL-TEST-U9-12</field>
            <field name="level_id" ref="level_benglish_plus_mixto_intermediate_unit12" />
            <field name="sequence">30</field>
            <field name="subject_type">core</field>
            <field name="subject_classification">evaluation</field>
            <field name="subject_category">oral_test</field>
            <field name="unit_block_start">9</field>
            <field name="unit_block_end">12</field>
            <field name="hours">1</field>
            <field name="credits">0</field>
            <field name="description">Oral Test de las unidades 9 a 12</field>
            <field name="prerequisite_ids" eval="[(6, 0, [ref('subject_benglish_bskill_u9_1'), ref('subject_benglish_bskill_u9_2'), ref('subject_benglish_bskill_u9_3'), ref('subject_benglish_bskill_u9_4'), ref('subject_benglish_bskill_u10_1'), ref('subject_benglish_bskill_u10_2'), ref('subject_benglish_bskill_u10_3'), ref('subject_benglish_bskill_u10_4'), ref('subject_benglish_bskill_u11_1'), ref('subject_benglish_bskill_u11_2'), ref('subject_benglish_bskill_u11_3'), ref('subject_benglish_bskill_u11_4'), ref('subject_benglish_bskill_u12_1'), ref('subject_benglish_bskill_u12_2'), ref('subject_benglish_bskill_u12_3'), ref('subject_benglish_bskill_u12_4')])]" />
            <field name="active" eval="True" />
        </record>

        <record id="subject_benglish_oral_test_u13_16" model="benglish.subject">
            <field name="name">Intermediate-Oral Test U13-16</field>
            <field name="alias">Oral Test U13-16</field>
            <field name="code">ORAL-TEST-U13-16</field>
            <field name="level_id" ref="level_benglish_plus_mixto_intermediate_unit16" />
            <field name="sequence">30</field>
            <field name="subject_type">core</field>
            <field name="subject_classification">evaluation</field>
            <field name="subject_category">oral_test</field>
            <field name="unit_block_start">13</field>
            <field name="unit_block_end">16</field>
            <field name="hours">1</field>
            <field name="credits">0</field>
            <field name="description">Oral Test de las unidades 13 a 16</field>
            <field name="prerequisite_ids" eval="[(6, 0, [ref('subject_benglish_bskill_u13_1'), ref('subject_benglish_bskill_u13_2'), ref('subject_benglish_bskill_u13_3'), ref('subject_benglish_bskill_u13_4'), ref('subject_benglish_bskill_u14_1'), ref('subject_benglish_bskill_u14_2'), ref('subject_benglish_bskill_u14_3'), ref('subject_benglish_bskill_u14_4'), ref('subject_benglish_bskill_u15_1'), ref('subject_benglish_bskill_u15_2'), ref('subject_benglish_bskill_u15_3'), ref('subject_benglish_bskill_u15_4'), ref('subject_benglish_bskill_u16_1'), ref('subject_benglish_bskill_u16_2'), ref('subject_benglish_bskill_u16_3'), ref('subject_benglish_bskill_u16_4')])]" />
            <field name="active" eval="True" />
        </record>

        <record id="subject_benglish_oral_test_u17_20" model="benglish.subject">
            <field name="name">Advanced-Oral Test U17-20</field>
            <field name="alias">Oral Test U17-20</field>
            <field name="code">ORAL-TEST-U17-20</field>
            <field name="level_id" ref="level_benglish_plus_mixto_advanced_unit20" />
            <field name="sequence">30</field>
            <field name="subject_type">core</field>
            <field name="subject_classification">evaluation</field>
            <field name="subject_category">oral_test</field>
            <field name="unit_block_start">17</field>
            <field name="unit_block_end">20</field>
            <field name="hours">1</field>
            <field name="credits">0</field>
            <field name="description">Oral Test de las unidades 17 a 20</field>
            <field name="prerequisite_ids" eval="[(6, 0, [ref('subject_benglish_bskill_u17_1'), ref('subject_benglish_bskill_u17_2'), ref('subject_benglish_bskill_u17_3'), ref('subject_benglish_bskill_u17_4'), ref('subject_benglish_bskill_u18_1'), ref('subject_benglish_bskill_u18_2'), ref('subject_benglish_bskill_u18_3'), ref('subject_benglish_bskill_u18_4'), ref('subject_benglish_bskill_u19_1'), ref('subject_benglish_bskill_u19_2'), ref('subject_benglish_bskill_u19_3'), ref('subject_benglish_bskill_u19_4'), ref('subject_benglish_bskill_u20_1'), ref('subject_benglish_bskill_u20_2'), ref('subject_benglish_bskill_u20_3'), ref('subject_benglish_bskill_u20_4')])]" />
            <field name="active" eval="True" />
        </record>

        <record id="subject_benglish_oral_test_u21_24" model="benglish.subject">
            <field name="name">Advanced-Oral Test U21-24</field>
            <field name="alias">Oral Test U21-24</field>
            <field name="code">ORAL-TEST-U21-24</field>
            <field name="level_id" ref="level_benglish_plus_mixto_advanced_unit24" />
            <field name="sequence">30</field>
            <field name="subject_type">core</field>
            <field name="subject_classification">evaluation</field>
            <field name="subject_category">oral_test</field>
            <field name="unit_block_start">21</field>
            <field name="unit_block_end">24</field>
            <field name="hours">1</field>
            <field name="credits">0</field>
            <field name="description">Oral Test de las unidades 21 a 24</field>
            <field name="prerequisite_ids" eval="[(6, 0, [ref('subject_benglish_bskill_u21_1'), ref('subject_benglish_bskill_u21_2'), ref('subject_benglish_bskill_u21_3'), ref('subject_benglish_bskill_u21_4'), ref('subject_benglish_bskill_u22_1'), ref('subject_benglish_bskill_u22_2'), ref('subject_benglish_bskill_u22_3'), ref('subject_benglish_bskill_u22_4'), ref('subject_benglish_bskill_u23_1'), ref('subject_benglish_bskill_u23_2'), ref('subject_benglish_bskill_u23_3'), ref('subject_benglish_bskill_u23_4'), ref('subject_benglish_bskill_u24_1'), ref('subject_benglish_bskill_u24_2'), ref('subject_benglish_bskill_u24_3'), ref('subject_benglish_bskill_u24_4')])]" />
            <field name="active" eval="True" />
        </record>

    </data>
</odoo>
"""

output_file = "../data/subjects_oral_tests_benglish.xml"

with open(output_file, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print(f"✓ Archivo regenerado: {output_file}")
print("✓ Todos los prerequisite_ids en una sola línea")
print("✓ 6 Oral Tests con classification=evaluation")
