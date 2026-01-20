#!/usr/bin/env python3
"""
Script para limpiar filtros guardados obsoletos que referencian plan_id
en los modelos phase, level y subject.

Ejecutar desde el shell de Odoo:
python -c "from odoo import registry, SUPERUSER_ID; from odoo.api import Environment; \
env = Environment(registry('ailu_benglish'), SUPERUSER_ID, {}); \
env.cr.execute(\"DELETE FROM ir_filters WHERE model_id IN ('benglish.phase', 'benglish.level', 'benglish.subject') AND context LIKE '%plan_id%'\"); \
env.cr.commit(); \
print('Filtros obsoletos eliminados')"

O desde el shell interactivo de Odoo:
env.cr.execute("DELETE FROM ir_filters WHERE model_id IN ('benglish.phase', 'benglish.level', 'benglish.subject') AND context LIKE '%plan_id%'")
env.cr.commit()
"""

import logging

_logger = logging.getLogger(__name__)


def clear_obsolete_filters(env):
    """Elimina filtros guardados que referencian plan_id en phase, level, subject."""

    # Buscar filtros con plan_id en el contexto
    filters = env["ir.filters"].search(
        [
            (
                "model_id",
                "in",
                ["benglish.phase", "benglish.level", "benglish.subject"],
            ),
            "|",
            "|",
            ("context", "ilike", "%plan_id%"),
            ("domain", "ilike", "%plan_id%"),
            ("sort", "ilike", "%plan_id%"),
        ]
    )

    if filters:
        count = len(filters)
        _logger.info(
            f"Eliminando {count} filtros obsoletos con referencias a plan_id..."
        )
        filters.unlink()
        _logger.info(f"✓ {count} filtros eliminados exitosamente")
        return count
    else:
        _logger.info("No se encontraron filtros obsoletos para eliminar")
        return 0


if __name__ == "__main__":
    # Este script debe ejecutarse desde el shell de Odoo
    print(__doc__)
