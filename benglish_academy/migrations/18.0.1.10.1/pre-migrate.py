# -*- coding: utf-8 -*-
"""
Pre-migration script for version 18.0.1.10.1
Adds missing 'campus_display' column to benglish_campus table.

This fixes the error:
    psycopg2.errors.UndefinedColumn: column benglish_campus.campus_display does not exist
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Add campus_display column if it doesn't exist."""
    if not version:
        return

    _logger.info("Pre-migration 18.0.1.10.1: Checking for missing campus_display column...")

    # Check if column exists
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'benglish_campus' 
        AND column_name = 'campus_display'
    """)
    
    if not cr.fetchone():
        _logger.info("Adding missing column 'campus_display' to benglish_campus table...")
        cr.execute("""
            ALTER TABLE benglish_campus 
            ADD COLUMN campus_display VARCHAR
        """)
        _logger.info("Column 'campus_display' added successfully.")
        
        # Update existing records based on is_virtual_sede and campus_type
        cr.execute("""
            UPDATE benglish_campus
            SET campus_display = CASE
                WHEN is_virtual_sede = TRUE THEN 'Virtual'
                WHEN campus_type = 'branch' THEN 'Presencial'
                WHEN campus_type = 'online' THEN 'Virtual'
                ELSE ''
            END
        """)
        _logger.info("Updated campus_display values for existing records.")
    else:
        _logger.info("Column 'campus_display' already exists.")
