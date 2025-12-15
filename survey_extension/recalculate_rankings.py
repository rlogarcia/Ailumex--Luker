#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para recalcular manualmente todos los rankings de encuestas.
Ejecutar desde el shell de Odoo o directamente con odoo shell.

Uso desde terminal:
    python "C:\Program Files\Odoo 18.0.20251001\server\odoo-bin" shell -d mateo --addons-path="C:\Program Files\Odoo 18.0.20251001\server\odoo\addons,C:\ModulosOdoo18" -c "C:\Program Files\Odoo 18.0.20251001\server\odoo.conf"
    
Luego ejecutar:
    exec(open(r'C:\ModulosOdoo18\survey_extension\recalculate_rankings.py').read())
"""

import logging

_logger = logging.getLogger(__name__)

def recalculate_all_rankings():
    """Recalcula todos los rankings de todas las encuestas."""
    
    print("=" * 80)
    print("🔄 RECALCULANDO RANKINGS DE ENCUESTAS")
    print("=" * 80)
    
    try:
        # Buscar todas las encuestas que tienen participaciones
        surveys_with_inputs = env['survey.survey'].sudo().search([
            ('user_input_ids', '!=', False)
        ])

        if not surveys_with_inputs:
            print("\n⚠️  No se encontraron encuestas con participaciones.")
            return

        print(f"\n📊 Encontradas {len(surveys_with_inputs)} encuestas con participaciones\n")
        
        total_inputs = 0
        
        for idx, survey in enumerate(surveys_with_inputs, 1):
            print(f"\n[{idx}/{len(surveys_with_inputs)}] Procesando: {survey.title}")
            print("-" * 80)
            
            # Buscar todas las participaciones de esta encuesta
            all_inputs = env['survey.user_input'].sudo().search([
                ('survey_id', '=', survey.id)
            ])
            
            completed = all_inputs.filtered(lambda r: r.state == 'done')
            
            print(f"   Total participaciones: {len(all_inputs)}")
            print(f"   Completadas: {len(completed)}")
            
            if all_inputs:
                # Invalidar cache para forzar recálculo
                all_inputs.invalidate_recordset([
                    'x_ranking_position', 
                    'x_ranking_total',
                    'x_ranking_percentile', 
                    'x_ranking_medal'
                ])
                
                # Aplicar el ranking usando el método directo
                all_inputs._apply_ranking_metrics_to_survey(survey)
                
                # Commit para asegurar que se guarden los cambios
                env.cr.commit()
                
                # Verificar el resultado
                if completed:
                    first_three = completed.sorted(lambda r: r.x_ranking_position)[:3]
                    print(f"\n   🏆 Top 3 Rankings:")
                    for rec in first_three:
                        medal_emoji = {
                            'gold': '🥇',
                            'silver': '🥈', 
                            'bronze': '🥉',
                            'participant': '🎖️'
                        }.get(rec.x_ranking_medal, '❓')
                        
                        name = rec.partner_id.name if rec.partner_id else rec.email
                        print(f"      {medal_emoji} Pos. {rec.x_ranking_position}: {name} - {rec.scoring_percentage:.2f}%")
                
                total_inputs += len(all_inputs)
                print(f"   ✅ Rankings actualizados correctamente")
        
        print("\n" + "=" * 80)
        print(f"✅ PROCESO COMPLETADO EXITOSAMENTE")
        print(f"📈 Total de participaciones procesadas: {total_inputs}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


# Ejecutar automáticamente si se carga en el shell
if __name__ == '__main__' or 'env' in dir():
    recalculate_all_rankings()
