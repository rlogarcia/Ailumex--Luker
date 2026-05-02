# -*- coding: utf-8 -*-

from odoo import models, fields

class DataElement(models.Model): # Odoo va a crear la tabla en PostgreSQL
    _name = 'luker.data.element' 
    _description = 'Catálogo de elementos de dato DAMA'
    _order = 'nam_element asc' # Ordenar los registros por nombre
    _rec_name = 'nam_element' # Campo que se muestra en la interfaz de Odoo

    nam_element = fields.Char(
        string = 'Nombre del elemento',
        required = True,
        help = 'Nombre del elemento de dato'
    )

    des_element = fields.Text (
        string = 'Descripción',
        help = 'Descripción del propósito y uso del dato'
    )
    
    nam_data_domain = fields.Char (
        string = 'Dominio del dato',
        help = 'Área temática a la que pertenece.'
    )

    nam_sensitivity = fields.Char (
        string = 'Sensibilidad',
        help = 'Nivel de sensibilidad: publico, interno, confidencial, restringido'
    )

    des_retention_policy = fields.Char (
        string = 'Política de retención',
        help = 'Tiempo de conservación del dato. Ejemplo: 5 años, permanente'
    )

    nam_owner = fields.Char (
        string = 'Propietario',
        help = 'Área o persona responsable de la definición del dato'
    )

    nam_steward = fields.Char (
        string = 'Custodio',
        help = 'Responsable operativo de la calidad del dato'
    )

    activo = fields.Boolean (
        string = 'Activo',
        default = True
    )