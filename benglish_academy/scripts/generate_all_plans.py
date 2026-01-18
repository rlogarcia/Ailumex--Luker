#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para generar asignaturas vinculadas a TODOS los planes
Crea 4 archivos adicionales por programa para cubrir Plus Virtual, Premium, Gold y Supreme
"""

from pathlib import Path

BASE_PATH = Path(__file__).parent.parent / "data"

# Planes a generar (Plus Mixto ya existe)
PLANS = ["plus_virtual", "premium", "gold", "supreme"]
PROGRAMS = ["benglish", "beteens"]


def generate_subjects_for_plan(program, plan):
    """Genera todas las asignaturas (B-checks, Bskills, Oral Tests) para un plan específico"""

    output = f"""<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">

        <!-- ============================================ -->
        <!-- ASIGNATURAS COMPLETAS - {program.upper()} - {plan.upper().replace('_', ' ')} -->
        <!-- ============================================ -->
        <!-- 24 B-checks + 96 Bskills + 6 Oral Tests = 126 asignaturas -->
        
        <!-- ========================================== -->
        <!-- B-CHECKS (24 unidades) -->
        <!-- ========================================== -->

"""

    # Generar 24 B-checks
    for unit in range(1, 25):
        phase_name = (
            "basic" if unit <= 8 else "intermediate" if unit <= 16 else "advanced"
        )
        phase_label = (
            "Basic" if unit <= 8 else "Intermediate" if unit <= 16 else "Advanced"
        )

        output += f"""        <record id="subject_{program}_{plan}_bcheck_unit{unit}" model="benglish.subject">
            <field name="name">{phase_label}-B Check U{unit}</field>
            <field name="alias">B-check U{unit}</field>
            <field name="code">BCHECK-U{unit}-{program.upper()}-{plan.upper()}</field>
            <field name="level_id" ref="level_{program}_{plan}_{phase_name}_unit{unit}" />
            <field name="sequence">10</field>
            <field name="subject_type">core</field>
            <field name="subject_classification">prerequisite</field>
            <field name="subject_category">bcheck</field>
            <field name="unit_number">{unit}</field>
            <field name="hours">1</field>
            <field name="credits">0</field>
            <field name="description">B-check de la Unidad {unit} - {program.upper()} - {plan.upper().replace('_', ' ')}</field>
            <field name="active" eval="True" />
        </record>

"""

    output += """        <!-- ========================================== -->
        <!-- B-SKILLS (96 unidades: 4 por UNIT) -->
        <!-- ========================================== -->

"""

    # Generar 96 Bskills (4 por unidad)
    for unit in range(1, 25):
        phase_name = (
            "basic" if unit <= 8 else "intermediate" if unit <= 16 else "advanced"
        )
        phase_label = (
            "Basic" if unit <= 8 else "Intermediate" if unit <= 16 else "Advanced"
        )

        for bskill_num in range(1, 5):
            sequence = 20 + (bskill_num - 1)

            output += f"""        <record id="subject_{program}_{plan}_bskill_u{unit}_{bskill_num}" model="benglish.subject">
            <field name="name">{phase_label}-Bskill U{unit} - {bskill_num}</field>
            <field name="alias">Bskill U{unit}-{bskill_num}</field>
            <field name="code">BSKILL-U{unit}-{bskill_num}-{program.upper()}-{plan.upper()}</field>
            <field name="level_id" ref="level_{program}_{plan}_{phase_name}_unit{unit}" />
            <field name="sequence">{sequence}</field>
            <field name="subject_type">core</field>
            <field name="subject_classification">regular</field>
            <field name="subject_category">bskills</field>
            <field name="unit_number">{unit}</field>
            <field name="bskill_number">{bskill_num}</field>
            <field name="hours">1</field>
            <field name="credits">0</field>
            <field name="description">B-skill {bskill_num} de la Unidad {unit} - {program.upper()} - {plan.upper().replace('_', ' ')}</field>
            <field name="prerequisite_ids" eval="[(6, 0, [ref('subject_{program}_{plan}_bcheck_unit{unit}')])]" />
            <field name="active" eval="True" />
        </record>

"""

    output += """        <!-- ========================================== -->
        <!-- ORAL TESTS (6 bloques de 4 unidades) -->
        <!-- ========================================== -->

"""

    # Generar 6 Oral Tests
    oral_test_blocks = [
        (1, 4, "basic"),
        (5, 8, "basic"),
        (9, 12, "intermediate"),
        (13, 16, "intermediate"),
        (17, 20, "advanced"),
        (21, 24, "advanced"),
    ]

    for start, end, phase_name in oral_test_blocks:
        phase_label = phase_name.capitalize()

        # Generar lista de prerrequisitos (16 Bskills del bloque)
        prereq_refs = []
        for unit in range(start, end + 1):
            for bskill_num in range(1, 5):
                prereq_refs.append(
                    f"ref('subject_{program}_{plan}_bskill_u{unit}_{bskill_num}')"
                )

        prereqs_str = ", ".join(prereq_refs)

        # Determinar el nivel correcto para el oral test (última unidad del bloque)
        output += f"""        <record id="subject_{program}_{plan}_oral_test_u{start}_{end}" model="benglish.subject">
            <field name="name">{phase_label}-Oral Test U{start}-{end}</field>
            <field name="alias">Oral Test U{start}-{end}</field>
            <field name="code">ORAL-TEST-U{start}-{end}-{program.upper()}-{plan.upper()}</field>
            <field name="level_id" ref="level_{program}_{plan}_{phase_name}_unit{end}" />
            <field name="sequence">30</field>
            <field name="subject_type">core</field>
            <field name="subject_classification">evaluation</field>
            <field name="subject_category">oral_test</field>
            <field name="unit_block_start">{start}</field>
            <field name="unit_block_end">{end}</field>
            <field name="hours">1</field>
            <field name="credits">0</field>
            <field name="description">Oral Test de las unidades {start} a {end} - {program.upper()} - {plan.upper().replace('_', ' ')}</field>
            <field name="prerequisite_ids" eval="[(6, 0, [{prereqs_str}])]" />
            <field name="active" eval="True" />
        </record>

"""

    output += """    </data>
</odoo>"""

    return output


def main():
    """Genera todos los archivos de asignaturas para todos los planes"""

    print("\n" + "=" * 60)
    print("GENERANDO ASIGNATURAS PARA TODOS LOS PLANES")
    print("=" * 60 + "\n")

    files_generated = []

    for program in PROGRAMS:
        for plan in PLANS:
            print(f"Generando: {program.upper()} - {plan.upper().replace('_', ' ')}")

            xml_content = generate_subjects_for_plan(program, plan)

            filename = f"subjects_all_{program}_{plan}.xml"
            output_file = BASE_PATH / filename

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(xml_content)

            files_generated.append(filename)
            print(f"  ✓ {filename} (126 asignaturas)")

    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"\nArchivos generados: {len(files_generated)}")
    for fname in files_generated:
        print(f"  - {fname}")

    print(
        f"\nTotal de asignaturas por archivo: 126 (24 B-checks + 96 Bskills + 6 Oral Tests)"
    )
    print(f"Total de asignaturas generadas: {len(files_generated) * 126}")
    print(f"\nAsignaturas previas (Plus Mixto): 252 (126 BENGLISH + 126 BETEENS)")
    print(f"Asignaturas nuevas: {len(files_generated) * 126}")
    print(f"TOTAL ASIGNATURAS: {252 + len(files_generated) * 126}")

    print("\n" + "=" * 60)
    print("SIGUIENTE PASO")
    print("=" * 60)
    print("\nActualizar __manifest__.py agregando estos archivos en 'data':")
    for fname in files_generated:
        print(f'        "data/{fname}",')

    print("\n")


if __name__ == "__main__":
    main()
