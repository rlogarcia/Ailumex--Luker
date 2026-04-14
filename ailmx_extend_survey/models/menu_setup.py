# -*- coding: utf-8 -*-


def _rename_menus(env):
    """
    Renombra los menús nativos del módulo survey para SISPAR.
    Se llama tanto en instalación como en actualización.
    """

    # Encuestas → Instrumentos
    menu_surveys = env.ref('survey.menu_survey_form', raise_if_not_found=False)
    if menu_surveys:
        menu_surveys.sudo().write({'name': 'Instrumentos'})

    # Participaciones → Participantes
    menu_participantes = env.ref('survey.menu_survey_type_form1', raise_if_not_found=False)
    if menu_participantes:
        menu_participantes.sudo().write({'name': 'Participantes'})

    # Preguntas y respuestas → Aplicaciones
    menu_questions = env.ref('survey.survey_menu_questions', raise_if_not_found=False)
    if menu_questions:
        menu_questions.sudo().write({'name': 'Aplicaciones'})


def post_init_hook(env):
    """
    Se ejecuta una sola vez al instalar el módulo por primera vez.
    """
    _rename_menus(env)


def post_migrate(env, version_from, version_to):
    """
    Se ejecuta cada vez que el módulo se actualiza con -u.
    Garantiza que los renombres se apliquen aunque el módulo
    ya estuviera instalado antes de agregar esta lógica.
    """
    _rename_menus(env)