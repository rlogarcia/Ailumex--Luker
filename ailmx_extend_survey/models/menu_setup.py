# -*- coding: utf-8 -*-

def post_init_hook(env):
    # Se ejecuta automáticamente después de instalar o actualizar el módulo
    # Renombra los menús del módulo survey para SISPAR

    # Encuestas → Instrumentos
    menu_surveys = env.ref('survey.menu_survey_form', raise_if_not_found=False)
    if menu_surveys:
        menu_surveys.sudo().write({'name': 'Instrumentos'})

    # Participaciones - Participantes
    menu_surveys = env.ref('survey.menu_survey_type_form1', raise_if_not_found=False)
    if menu_surveys:
        menu_surveys.sudo().write({'name': 'Participantes'})

    # Preguntas y respuestas → Aplicaciones
    menu_questions = env.ref('survey.survey_menu_questions', raise_if_not_found=False)
    if menu_questions:
        menu_questions.sudo().write({'name': 'Aplicaciones'})