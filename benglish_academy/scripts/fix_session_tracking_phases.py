# -*- coding: utf-8 -*-
"""
Script para actualizar phase_id en registros de session_tracking existentes.

Uso desde Odoo shell:
    cd "C:\Program Files\Odoo 18.0.20251128\python"
    .\python.exe ..\server\odoo-bin shell -c ..\server\odoo.conf -d benglish_db

    exec(open('d:/AiLumex/Ailumex--Be/benglish_academy/scripts/fix_session_tracking_phases.py').read())
"""


def fix_session_tracking_phases():
    """Actualiza el campo phase_id en todos los registros de session_tracking"""

    Tracking = env["benglish.subject.session.tracking"]

    # Buscar todos los registros
    all_tracking = Tracking.search([])

    print(f"\n{'='*60}")
    print(f"Encontrados {len(all_tracking)} registros de session_tracking")
    print(f"{'='*60}\n")

    # FORZAR RECÁLCULO de los campos compute
    print("Forzando recálculo de jerarquía...")
    all_tracking._compute_hierarchy()

    updated = 0
    missing_phase = []

    for tracking in all_tracking:
        phase_name = tracking.phase_id.name if tracking.phase_id else "SIN FASE"
        subject_code = (
            tracking.subject_id.code if tracking.subject_id else "SIN ASIGNATURA"
        )

        if tracking.phase_id:
            print(f"✓ {subject_code} -> {phase_name}")
            updated += 1
        else:
            missing_phase.append(tracking)
            print(f"⚠ {subject_code} -> {phase_name}")

    print(f"\n{'='*60}")
    print(f"Con fase: {updated}")
    print(f"Sin fase: {len(missing_phase)}")
    print(f"{'='*60}\n")

    # Verificar distribución por fase
    basic = Tracking.search_count([("phase_id.name", "=", "Basic")])
    intermediate = Tracking.search_count([("phase_id.name", "=", "Intermediate")])
    advanced = Tracking.search_count([("phase_id.name", "=", "Advanced")])
    sin_fase = Tracking.search_count([("phase_id", "=", False)])

    print("\nDistribución por fase:")
    print(f"  📘 Basic: {basic}")
    print(f"  📗 Intermediate: {intermediate}")
    print(f"  📕 Advanced: {advanced}")
    print(f"  ⚠ Sin fase: {sin_fase}")
    print()

    return updated, missing_phase


if __name__ == "__main__":
    updated, missing = fix_session_tracking_phases()
