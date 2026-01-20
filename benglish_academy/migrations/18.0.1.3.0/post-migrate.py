"""
Script de migración para actualizar subject_classification de asignaturas existentes
Este script debe ejecutarse una sola vez para actualizar los datos
"""


def migrate(cr, version):
    """
    Actualiza subject_classification basándose en subject_category
    - B-checks (bcheck) → prerequisite
    - Bskills (bskills) → regular
    - Oral Tests (oral_test) → evaluation
    """

    # Actualizar B-checks a 'prerequisite'
    cr.execute(
        """
        UPDATE benglish_subject
        SET subject_classification = 'prerequisite'
        WHERE subject_category = 'bcheck'
        AND subject_classification != 'prerequisite'
    """
    )
    bchecks_updated = cr.rowcount

    # Actualizar Bskills a 'regular'
    cr.execute(
        """
        UPDATE benglish_subject
        SET subject_classification = 'regular'
        WHERE subject_category = 'bskills'
        AND subject_classification != 'regular'
    """
    )
    bskills_updated = cr.rowcount

    # Actualizar Oral Tests a 'evaluation'
    cr.execute(
        """
        UPDATE benglish_subject
        SET subject_classification = 'evaluation'
        WHERE subject_category = 'oral_test'
        AND subject_classification != 'evaluation'
    """
    )
    oral_tests_updated = cr.rowcount

    # Log de resultados
    from odoo.tools import config
    import logging

    _logger = logging.getLogger(__name__)

    _logger.info("=" * 80)
    _logger.info("MIGRACIÓN DE CLASIFICACIONES COMPLETADA")
    _logger.info("=" * 80)
    _logger.info(f"B-checks actualizados: {bchecks_updated}")
    _logger.info(f"Bskills actualizados: {bskills_updated}")
    _logger.info(f"Oral Tests actualizados: {oral_tests_updated}")
    _logger.info(
        f"TOTAL: {bchecks_updated + bskills_updated + oral_tests_updated} registros actualizados"
    )
    _logger.info("=" * 80)
