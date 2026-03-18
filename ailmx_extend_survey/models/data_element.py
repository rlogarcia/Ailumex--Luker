# -*- coding: utf-8 -*-

from odoo import models, fields

class DataElement(models.Model): # Odoo va a crear la tabla en PostgreSQL
    _name = 'data.element' 
    _description = 'Catálogo de elementos de dato DAMA'
    _order = 'Nam_Element asc' # Ordenar los registros por nombre
    _rec_name = 'Nam_Element' # Campo que se muestra en la interfaz de Odoo

    Id_Data_Element = fields.Integer( # Generado automáticamente
        string='ID Elemento Dato',
        readonly=True
    )

    Nam_Element = fields.Char(
        string = 'Nombre del elemento',
        required = True,
        help = 'Nombre del elemento de dato'
    )

    Des_Element = fields.Text (
        string = 'Descripción',
        help = 'Descripción del propósito y uso del dato'
    )
    
    Nam_Data_Domain = fields.Char (
        string = 'Dominio del dato',
        help = 'Área temática a la que pertenece.'
    )

    Nam_Sensitivity = fields.Char (
        string = 'Sensibilidad',
        help = 'Nivel de sensibilidad: publico, interno, confidencial, restringido'
    )

    Des_Retention_Policy = fields.Char (
        string = 'Política de retención',
        help = 'Tiempo de conservación del dato. Ejemplo: 5 años, permanente'
    )

    Nam_Owner = fields.Char (
        string = 'Propietario',
        help = 'Área o persona responsable de la definición del dato'
    )

    Nam_Steward = fields.Char (
        string = 'Custodio',
        help = 'Responsable operativo de la calidad del dato'
    )

    active = fields.Boolean (
        string = 'Activo',
        default = True
    )