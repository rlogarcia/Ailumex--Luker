#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar el historial académico de Tatiana en UNIT 24
"""

import sys
import os

# Agregar ruta de Odoo al path
odoo_path = r"C:\Program Files\Odoo 18.0.20250614\server"
if odoo_path not in sys.path:
    sys.path.insert(0, odoo_path)

import odoo
from odoo import api, SUPERUSER_ID

# Configuración de la base de datos
DB_NAME = 'odoo'
ODOO_CONF = r"C:\Program Files\Odoo 18.0.20250614\server\odoo.conf"

def check_tatiana_history():
    """Verificar historial de Tatiana en UNIT 24"""
    
    # Cargar configuración
    odoo.tools.config.parse_config(['-c', ODOO_CONF, '--db-filter', DB_NAME])
    
    # Conectar a la base de datos
    registry = odoo.registry(DB_NAME)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Buscar estudiante Tatiana
        Student = env['benglish.student']
        students = Student.search([('name', 'ilike', 'Tatiana')])
        
        if not students:
            print("❌ No se encontró estudiante con nombre Tatiana")
            return
        
        student = students[0]
        print(f"\n✅ Estudiante encontrado: {student.name} (ID: {student.id})")
        print(f"   Programa: {student.program_id.name if student.program_id else 'N/A'}")
        print(f"   Plan: {student.plan_id.name if student.plan_id else 'N/A'}")
        
        # Buscar historial en UNIT 24
        History = env['benglish.academic.history']
        Subject = env['benglish.subject']
        
        unit24_subjects = Subject.search([('code', 'ilike', 'U24')], order='sequence, code')
        
        print(f"\n📚 Asignaturas de UNIT 24 encontradas: {len(unit24_subjects)}")
        
        for subject in unit24_subjects:
            history = History.search([
                ('student_id', '=', student.id),
                ('subject_id', '=', subject.id)
            ], limit=1)
            
            if history:
                status_icon = "✅" if history.attendance_status == 'attended' else "❌"
                print(f"\n{status_icon} {subject.code} - {subject.name}")
                print(f"   Categoría: {subject.subject_category}")
                print(f"   Asistencia: {history.attendance_status}")
                print(f"   Fecha: {history.session_date}")
                print(f"   Sesión ID: {history.session_id.id if history.session_id else 'Sin sesión (retroactivo)'}")
            else:
                print(f"\n⚠️  {subject.code} - {subject.name}")
                print(f"   Categoría: {subject.subject_category}")
                print(f"   ❌ SIN HISTORIAL")

if __name__ == '__main__':
    check_tatiana_history()
