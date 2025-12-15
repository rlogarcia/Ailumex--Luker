# -*- coding: utf-8 -*-
"""
Archivo de inicialización del módulo survey_extension

Este archivo se ejecuta cuando Odoo carga el módulo.
Su función principal es importar las carpetas que contienen código Python.

¿Por qué existe este archivo?
-----------------------------
En Python, para que una carpeta sea reconocida como un "paquete" (módulo),
debe contener un archivo __init__.py. Este archivo puede estar vacío o
puede importar otros módulos internos.

¿Qué hace?
----------
Importa la carpeta 'models' que contiene todos los archivos Python con
la lógica de negocio del módulo (modelos, campos, métodos, etc.)
"""

# Importar las carpetas con código Python para que Odoo cargue toda la lógica
from . import models
from . import controllers
from . import wizard
from .hooks import assign_survey_codes  # post-init: completa códigos faltantes

