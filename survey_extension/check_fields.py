# -*- coding: utf-8 -*-
"""
Script para verificar campos existentes en survey.user_input
Ejecutar desde la consola de Odoo antes de actualizar
"""

def check_survey_fields(env):
    """
    Verifica qué campos de score existen en survey.user_input
    
    Uso en consola de Odoo:
    >>> exec(open('c:/ModulosOdoo18/survey_extension/check_fields.py').read())
    >>> check_survey_fields(env)
    """
    print("\n" + "="*80)
    print("VERIFICACIÓN DE CAMPOS EN survey.user_input")
    print("="*80 + "\n")
    
    model = env['survey.user_input']
    fields_dict = model.fields_get()
    
    # Campos relacionados con score
    score_fields = [
        'score_percentage',
        'scoring_percentage', 
        'score_points',
        'score_total',
        'is_passed',
        'x_score_percent',
        'x_score_obtained',
        'x_score_total',
        'x_passed',
    ]
    
    print("Campos de puntaje disponibles:")
    for field in score_fields:
        if field in fields_dict:
            print(f"  ✅ {field} - Tipo: {fields_dict[field].get('type', 'unknown')}")
        else:
            print(f"  ❌ {field} - NO EXISTE")
    
    # Campos de duración
    duration_fields = [
        'x_survey_duration',
        'x_survey_duration_display',
    ]
    
    print("\nCampos de duración disponibles:")
    for field in duration_fields:
        if field in fields_dict:
            print(f"  ✅ {field} - Tipo: {fields_dict[field].get('type', 'unknown')}")
        else:
            print(f"  ❌ {field} - NO EXISTE")
    
    # Campos de ranking
    ranking_fields = [
        'x_ranking_position',
        'x_ranking_total',
        'x_ranking_percentile',
        'x_ranking_medal',
    ]
    
    print("\nCampos de ranking disponibles:")
    for field in ranking_fields:
        if field in fields_dict:
            print(f"  ✅ {field} - Tipo: {fields_dict[field].get('type', 'unknown')}")
        else:
            print(f"  ❌ {field} - NO EXISTE")
    
    print("\n" + "="*80)
    
    # Verificar en SQL qué columnas existen realmente
    print("\nColumnas en la tabla survey_user_input (SQL):")
    env.cr.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'survey_user_input' 
        AND column_name LIKE ANY(ARRAY['%score%', '%ranking%', '%duration%'])
        ORDER BY column_name
    """)
    
    for row in env.cr.fetchall():
        print(f"  {row[0]} ({row[1]})")
    
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    print("Ejecutar desde la consola de Odoo:")
    print("exec(open('c:/ModulosOdoo18/survey_extension/check_fields.py').read())")
    print("check_survey_fields(env)")
