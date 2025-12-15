# -*- coding: utf-8 -*-
"""Rutinas de inicialización para completar códigos de encuestas existentes."""

import logging
from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def assign_survey_codes(cr, registry):
    """Asignar códigos faltantes o fuera de formato a encuestas previas."""

    env = api.Environment(cr, SUPERUSER_ID, {})
    env["survey.survey"]._assign_missing_codes()


def migrate_version_year_to_char(cr, registry):
    """Migra el campo version_year de Integer a Char para evitar formato con separadores."""
    
    # Verificar si la columna existe y tiene tipo numérico
    cr.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'survey_survey' 
        AND column_name = 'version_year'
    """)
    
    result = cr.fetchone()
    if result and result[1] in ('integer', 'numeric', 'bigint'):
        # Convertir valores existentes a string
        cr.execute("""
            ALTER TABLE survey_survey 
            ALTER COLUMN version_year TYPE varchar(4) 
            USING CASE 
                WHEN version_year IS NULL THEN NULL 
                ELSE version_year::varchar 
            END
        """)


def post_init_hook(env):
    """
    Post-installation hook to recalculate ranking positions and assign codes.
    """
    _logger.info("Starting post_init_hook...")
    
    # Asignar códigos a encuestas existentes
    env["survey.survey"]._assign_missing_codes()
    
    # Migrar estados de respuesta
    _migrate_response_status(env)
    
    # Recalcular rankings
    _recalculate_rankings(env)


def _migrate_response_status(env):
    """
    Migrar x_response_status para usar los nuevos valores basados en state.
    """
    try:
        _logger.info("Migrando estados de respuesta...")
        
        # Actualizar registros completados
        done_inputs = env['survey.user_input'].sudo().search([('state', '=', 'done')])
        if done_inputs:
            done_inputs.write({'x_response_status': 'done'})
            _logger.info(f"  ✓ {len(done_inputs)} registros marcados como 'Completado'")
        
        # Actualizar registros en progreso
        progress_inputs = env['survey.user_input'].sudo().search([('state', '=', 'in_progress')])
        if progress_inputs:
            progress_inputs.write({'x_response_status': 'in_progress'})
            _logger.info(f"  ✓ {len(progress_inputs)} registros marcados como 'En progreso'")
        
        # Actualizar registros sin iniciar
        new_inputs = env['survey.user_input'].sudo().search([
            '|', ('state', '=', 'new'), 
            ('state', 'not in', ['done', 'in_progress', 'new'])
        ])
        if new_inputs:
            new_inputs.write({'x_response_status': 'new'})
            _logger.info(f"  ✓ {len(new_inputs)} registros marcados como 'Sin iniciar'")
        
        env.cr.commit()
        _logger.info("✅ Estados de respuesta migrados correctamente!")
        
    except Exception as e:
        _logger.error(f"❌ Error migrando estados: {e}", exc_info=True)


def _recalculate_rankings(env):
    """
    Recalculate all ranking positions for completed survey inputs.
    """
    try:
        # Buscar todas las encuestas que tienen participaciones
        surveys_with_inputs = env['survey.survey'].sudo().search([
            ('user_input_ids', '!=', False)
        ])

        if surveys_with_inputs:
            _logger.info(f"Recalculating rankings for {len(surveys_with_inputs)} surveys...")
            
            for survey in surveys_with_inputs:
                # Buscar todas las participaciones de esta encuesta
                all_inputs = env['survey.user_input'].sudo().search([
                    ('survey_id', '=', survey.id)
                ])
                
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
                    
                    _logger.info(f"✓ Rankings recalculated for survey '{survey.title}' ({len(all_inputs)} participations)")
            
            _logger.info("✅ All ranking positions recalculated successfully!")
        else:
            _logger.info("No surveys with participations found to recalculate.")
            
    except Exception as e:
        _logger.error(f"❌ Error recalculating rankings: {e}", exc_info=True)
