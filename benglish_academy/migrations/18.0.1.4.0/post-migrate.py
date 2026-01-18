"""
Post-migration script para eliminar filtros obsoletos después de la reestructuración
de phase, level y subject para usar program_id en lugar de plan_id.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Elimina filtros guardados que referencian plan_id en phase, level, subject."""

    _logger.info("=" * 80)
    _logger.info("INICIANDO LIMPIEZA DE FILTROS OBSOLETOS")
    _logger.info("=" * 80)

    # Eliminar todos los filtros para estos modelos ya que pueden tener referencias obsoletas
    cr.execute(
        """
        DELETE FROM ir_filters 
        WHERE model_id IN ('benglish.phase', 'benglish.level', 'benglish.subject')
    """
    )

    deleted_count = cr.rowcount
    _logger.info(f"✓ Se eliminaron {deleted_count} filtros obsoletos")

    # Limpiar vistas favoritas que puedan tener contexto obsoleto
    cr.execute(
        """
        UPDATE ir_ui_view_custom 
        SET arch = NULL 
        WHERE arch LIKE '%plan_id%'
    """
    )

    updated_views = cr.rowcount
    _logger.info(f"✓ Se limpiaron {updated_views} vistas personalizadas")

    _logger.info("=" * 80)
    _logger.info("LIMPIEZA COMPLETADA - Por favor, recarga el navegador (Ctrl+F5)")
    _logger.info("=" * 80)
