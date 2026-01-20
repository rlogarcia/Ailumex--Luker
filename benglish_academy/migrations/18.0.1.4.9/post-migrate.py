"""
Backfill effective_subject_id for existing session enrollments.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info("Starting backfill of effective_subject_id on session enrollments.")

    cr.execute(
        """
        UPDATE benglish_session_enrollment AS e
           SET effective_subject_id = s.subject_id
          FROM benglish_academic_session AS s
         WHERE e.session_id = s.id
           AND e.effective_subject_id IS NULL
           AND s.subject_id IS NOT NULL
        """
    )
    _logger.info(
        "Backfill effective_subject_id completed. Rows updated: %s", cr.rowcount
    )

    cr.execute(
        """
        UPDATE benglish_session_enrollment AS e
           SET effective_unit_number = COALESCE(sub.unit_number, sub.unit_block_end, 0)
          FROM benglish_subject AS sub
         WHERE e.effective_subject_id = sub.id
           AND (e.effective_unit_number IS NULL OR e.effective_unit_number = 0)
        """
    )
    _logger.info(
        "Backfill effective_unit_number completed. Rows updated: %s", cr.rowcount
    )
