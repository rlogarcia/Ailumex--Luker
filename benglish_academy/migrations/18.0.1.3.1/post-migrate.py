"""Normaliza subject_classification para evitar que Bskills aparezcan como prerrequisitos."""


def migrate(cr, version):
    """
    Reafirma la clasificación según categoría:
    - bcheck -> prerequisite
    - bskills -> regular
    - oral_test -> evaluation
    Esto corrige listados donde Bskills se muestran como "Prerrequisito".
    """

    cr.execute(
        """
        UPDATE benglish_subject
           SET subject_classification = 'prerequisite'
         WHERE subject_category = 'bcheck'
           AND subject_classification IS DISTINCT FROM 'prerequisite'
        """
    )
    cr.execute(
        """
        UPDATE benglish_subject
           SET subject_classification = 'regular'
         WHERE subject_category = 'bskills'
           AND subject_classification IS DISTINCT FROM 'regular'
        """
    )
    cr.execute(
        """
        UPDATE benglish_subject
           SET subject_classification = 'evaluation'
         WHERE subject_category = 'oral_test'
           AND subject_classification IS DISTINCT FROM 'evaluation'
        """
    )