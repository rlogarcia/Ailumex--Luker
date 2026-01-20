# -*- coding: utf-8 -*-

from odoo import models, fields, api, osv
from datetime import datetime, timedelta, date, time
from odoo.exceptions import AccessError, UserError, ValidationError



class ResPartnerExt(models.Model):

    _inherit = 'res.partner'

    primer_nombre = fields.Char('Primer nombre')
    otros_nombres = fields.Char('Otros nombres')
    primer_apellido = fields.Char('Primer apellido')
    segundo_apellido = fields.Char('Segundo apellido')
    fecha_nacimiento = fields.Date('Fecha de nacimiento')
    barrio_ciudad = fields.Char('Barrio ciudad')
    dev_ref = fields.Integer(compute='_compute_dev_ref', size=1, string='Digito Verificación', store=True)
    city_id = fields.Many2one('res.city', string='Ciudad', domain="[('state_id','=',state_id)]")
    mes_nacimiento = fields.Char(compute='_compute_mes_nacimiento', size=20, string='Mes Cumpleaños', store=True)
    edad = fields.Char(compute='_compute_edad', size=2, string='Edad')
    lugar_trabajo = fields.Char('Lugar de trabajo')
    genero = fields.Selection([('masculino', 'Masculino'), ('femenino', 'Femenino')], string='Genero')
    profesion_id = fields.Many2one('res.partner.profesion', string='Profesión')
    is_contact_customer = fields.Boolean('Es contacto')
    felec_email = fields.Char('Email facturacion electronica', default='@')
    plazo_pago_proveedor = fields.Many2one('account.payment.term', string='Plazo pago proveedor')
    email_alter_1 = fields.Char('Email alternativo 1')
    email_alter_2 = fields.Char('Email alternativo 2')
    ref = fields.Char(string='Identificacion', index=True, required=True)
    state_id = fields.Many2one(domain="[('country_id','=',country_id)]")
    pricelist_def_id = fields.Many2one('product.pricelist', string='Lista precios por defecto')
    city_exp_ref_id = fields.Many2one('res.city', string='Lugar de expedicion')
    dias_pago_servicio = fields.Integer(size=2, string='Días pago servicio')
    nombre_comercial = fields.Char('Nombre comercial')
    representante_legal_id = fields.Many2one('res.partner', string='Representante legal')
    economic_act_ids =  fields.Many2many('res.partner.economic.activity', string='Actividad Economica')
    society_type_id =  fields.Many2one('res.partner.society', string='Tipo sociedad')
    sag_pep = fields.Boolean('Persona Expuesta Publicamente')
    sag_tav = fields.Boolean('Transacciones con activos virtuales')
    sag_tme = fields.Boolean('Transacciones en moneda extranjera')
    sag_alto_riesgo = fields.Boolean('Opera en jurisdicción de alto riesgo o país no cooperante LA/FT/FPADM')
    tipo_contacto = fields.Selection([('Contacto', 'Contacto'), ('Referencia Personal', 'Referencia Personal'), ('Referencia Familiar', 'Referencia Familiar'), ('Referencia Comercial', 'Referencia Comercial'), ('Sede', 'Sede')], string='Tipo de contacto')
    regimen_fiscal = fields.Selection([('48', 'Responsable de IVA'), 
                                    ('49', 'No Responsable de IVA')], string='Regimen tributario', required=False, default='49')
    
    # NUEVOS CAMPOS - Información Personal Adicional
    sexo_biologico = fields.Selection([
        ('femenino', 'Femenino'),
        ('masculino', 'Masculino')
    ], string='Sexo Biológico')
    
    sexo_identificacion = fields.Selection([
        ('masculino', 'Masculino'),
        ('femenino', 'Femenino'),
        ('no_binario', 'No binario'),
        ('prefiero_no_decir', 'Prefiero no decir'),
        ('otro', 'Otro')
    ], string='Sexo de Identificación')
    
    pais_nacimiento = fields.Many2one('res.country', string='País de Nacimiento')
    
    estado_civil = fields.Selection([
        ('soltero', 'Soltero (a)'),
        ('casado', 'Casado (a)'),
        ('viudo', 'Viudo (a)'),
        ('separado', 'Separado (a)'),
        ('union_libre', 'Union Libre')
    ], string='Estado civil')
    
    direccion_residencia = fields.Char('Dirección de residencia')
    
    # NUEVOS CAMPOS - Información de Salud/EPS
    municipio_eps = fields.Many2one('res.city', string='Municipio cobertura EPS')
    
    zona = fields.Selection([
        ('rural', 'Rural'),
        ('urbana', 'Urbana')
    ], string='Zona')
    
    ips_cotizante = fields.Selection([
        ('sanitas', 'EPS Sanitas'),
        ('sura', 'EPS Sura'),
        ('compensar', 'Compensar EPS'),
        ('nueva_eps', 'Nueva EPS'),
        ('salud_total', 'Salud Total EPS'),
        ('famisanar', 'Famisanar EPS'),
        ('coomeva', 'Coomeva EPS'),
        ('medimas', 'Medimás EPS'),
        ('mutual_ser', 'Mutual SER EPS'),
        ('cruz_blanca', 'Cruz Blanca EPS'),
        ('capital_salud', 'Capital Salud EPS'),
        ('aliansalud', 'Aliansalud EPS'),
        ('servicio_occidental', 'Servicio Occidental de Salud'),
        ('sos_eps', 'SOS EPS'),
        ('coosalud', 'Coosalud EPS'),
        ('comfenalco_valle', 'Comfenalco Valle EPS'),
        ('comfamiliar_nariño', 'Comfamiliar Nariño'),
        ('otra', 'Otra IPS')
    ], string='IPS cotizante')
    
    # NUEVOS CAMPOS - Información Laboral/Pensiones
    fondo_pensiones = fields.Selection([
        ('porvenir', 'Porvenir'),
        ('proteccion', 'Protección'),
        ('colfondos', 'Colfondos'),
        ('skandia', 'Skandia'),
        ('colpensiones', 'Colpensiones (Régimen Público)'),
        ('bbva_horizonte', 'BBVA Horizonte'),
        ('old_mutual', 'Old Mutual (Inactivo)')
    ], string='Fondo de pensiones')

    _sql_constraints = [
        ('ref_partner_check', 'CHECK (ref IS NOT NULL)', 'Tercero debe tener identificación!'),
        ('ref_partner_unique', 'UNIQUE (ref, l10n_latam_identification_type_id)', 'El número de identificación no puede ser repetido para el tipo de identificación seleccionado.!'),
    ]

    def action_create_employee(self):
        for record in self:
            employee = self.env['hr.employee']
            employee_exist = self.env['hr.employee'].search([('work_contact_id','=',record.id)])
            if not employee_exist:
                vals = {
                    'name': record.name,
                    'work_contact_id': record.id,
                }
                employee.create(vals)


    @api.model
    @api.depends('fecha_nacimiento')
    def _compute_mes_nacimiento(self):
        for reg in self:
            if reg.fecha_nacimiento:
                formato_fecha = '%Y-%m-%d'
                fecha = str(reg.fecha_nacimiento)
                fecha_formato = datetime.strptime(fecha, formato_fecha)
                months = ("Sin Mes", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre")
                reg.mes_nacimiento = "{m}".format(m = months[fecha_formato.month])

    @api.model
    @api.depends('fecha_nacimiento')
    def _compute_edad(self):
        for reg in self:
            if reg.fecha_nacimiento:
                formato_fecha = '%Y-%m-%d'
                fecha = str(reg.fecha_nacimiento)
                fecha_formato = datetime.strptime(fecha, formato_fecha)
                fecha_nac = date(fecha_formato.year, fecha_formato.month, fecha_formato.day)
                diferencia_fechas = date.today() - fecha_nac
                diferencia_fechas_dias = diferencia_fechas.days
                edad_numerica = diferencia_fechas_dias / 365.2425
                reg.edad = int(edad_numerica) 
            else:
                reg.edad = int(0) 


    @api.onchange('primer_nombre', 'otros_nombres', 'primer_apellido', 'segundo_apellido')
    def _onchange_nombre_persona(self):
        for reg in self:
            if reg.company_type == 'person':
                reg.primer_nombre = str(reg.primer_nombre).upper()
                reg.otros_nombres = str(reg.otros_nombres).upper()
                reg.primer_apellido = str(reg.primer_apellido).upper()
                reg.segundo_apellido = str(reg.segundo_apellido).upper()

                if reg.primer_nombre == 'FALSE':
                    reg.primer_nombre = ''
                if reg.otros_nombres == 'FALSE':
                    reg.otros_nombres = ''
                if reg.primer_apellido == 'FALSE':
                    reg.primer_apellido = ''
                if reg.segundo_apellido == 'FALSE':
                    reg.segundo_apellido = ''

                reg.name = str((reg.primer_nombre and reg.primer_nombre + " " or '') + (reg.otros_nombres and reg.otros_nombres + " " or '') + (reg.primer_apellido and reg.primer_apellido + " " or '') + (reg.segundo_apellido and reg.segundo_apellido + " " or '')).upper()
            else:
                self.primer_nombre = ''
                self.otros_nombres = ''
                self.primer_apellido = ''
                self.segundo_apellido = ''
                reg.name = str(reg.name).upper()

    @api.onchange('street')
    def _onchange_direccion(self):
        if self.street:
            self.street = str(self.street).upper()

    @api.onchange('company_type')
    def _onchange_company_type(self):

        nit = self.env['l10n_latam.identification.type'].search([('name','=','NIT')])
        cc = self.env['l10n_latam.identification.type'].search([('name','=','Cédula de ciudadanía')])

        if self.company_type == 'person':
            self.l10n_latam_identification_type_id = cc
        else:
            self.l10n_latam_identification_type_id = nit

    @api.onchange('email')
    def _onchange_email(self):
        if self.email:
            self.email = str(self.email).lower()
            self.felec_email = str(self.email).lower()

    @api.onchange('name')
    def _onchange_nombre_compania(self):
        if self.is_contact_customer == False:
            if self.company_type == 'person':
                self.name = str((self.primer_nombre and self.primer_nombre + " " or '') + (self.otros_nombres and self.otros_nombres + " " or '') + (self.primer_apellido and self.primer_apellido + " " or '') + (self.segundo_apellido and self.segundo_apellido + " " or '')).upper()
            else:
                self.primer_nombre = ''
                self.otros_nombres = ''
                self.primer_apellido = ''
                self.segundo_apellido = ''
                if self.name:
                    self.name = self.name.upper()
        else:
            milliseconds = int(datetime.now().timestamp())

            if self.tipo_contacto == 'Sede':
                ti = self.env['l10n_latam.identification.type'].search([('name','=','Sede')])
                self.ref = 'SD' + str(milliseconds)

                if ti:
                    self.l10n_latam_identification_type_id = ti
            else:
                self.ref = 'CT' + str(milliseconds)

    #Cálcular el digito de verificación para los terceros.
    @api.model
    @api.depends('ref')
    def _compute_dev_ref(self):
        for reg in self:
            iPrimos = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
            partner = reg
            iChequeo = iResiduo = DigitoNIT = 0
            sTMP = sTmp1 = sTMP2  = ''
            if partner.ref:
                try:
                    dev_ref = partner.ref.strip()
                    for i in range(0, len(dev_ref)):
                        sTMP = dev_ref[len(dev_ref)-(i +1)]
                        iChequeo = iChequeo + (int(sTMP) * iPrimos[i])
                    iResiduo = iChequeo % 11
                    if iResiduo <= 1:
                        if iResiduo == 0:
                            DigitoNIT = 0
                        if iResiduo == 1:
                            DigitoNIT = 1
                    else:
                        DigitoNIT = 11 - iResiduo
                except:
                    pass
            reg.dev_ref = str(DigitoNIT)

    def _compute_display_name(self):
        for partner in self:
            # Construye el nombre personalizado usando los campos propios
            if partner.company_type == 'person':
                nombre = ' '.join(filter(None, [
                    partner.primer_nombre,
                    partner.otros_nombres,
                    partner.primer_apellido,
                    partner.segundo_apellido
                ]))
                partner.display_name = nombre.strip() if nombre else partner.name
            else:
                partner.display_name = partner.name

class StreetModelWizard(models.TransientModel):
    _name = 'street.model.wizard'
    _description = 'Wizard para direccion de tercero'

    f1 = fields.Selection([('AC', 'Avenida Calle'), ('AK', 'Avenida Carrera'),('CL', 'Calle'), ('CR', 'Carrera'), ('AU', 'Autopista'), ('AV', 'Avenida'), ('BL', 'Bulevar'), ('CT', 'Carretera'), ('CQ', 'Circular'), ('CV', 'Circunvalar'), ('DG', 'Diagonal'), ('TV', 'Transversal'), ('VT', 'Variante'), ('VI', 'Vía'), ('TC', 'Troncal'), ('VRD', 'Vereda') ], default='CL')
    f2 = fields.Char('')
    f3 = fields.Selection([('A', 'A'), ('B', 'B'),('C', 'C'), ('D', 'D'),('E', 'E'), ('F', 'F'),('G', 'G'), ('H', 'H'),('I', 'I'), ('J', 'J'),('K', 'K'), ('L', 'L'),('M', 'M'), ('N', 'N'),('O', 'O'), ('P', 'P'),('Q', 'Q'), ('R', 'R'),('S', 'S'), ('T', 'T'),('U', 'U'), ('V', 'V'),('W', 'W'), ('X', 'X'),('Y', 'Y'), ('Z', 'Z'), ('AA', 'AA'), ('AB', 'AB'), ('AC', 'AC'), ('AD', 'AD'), ('AE', 'AE'), ('AF', 'AF')])
    f4 = fields.Boolean('BIS?')
    f5 = fields.Selection([('A', 'A'), ('B', 'B'),('C', 'C'), ('D', 'D'),('E', 'E'), ('F', 'F'),('G', 'G'), ('H', 'H'),('I', 'I'), ('J', 'J'),('K', 'K'), ('L', 'L'),('M', 'M'), ('N', 'N'),('O', 'O'), ('P', 'P'),('Q', 'Q'), ('R', 'R'),('S', 'S'), ('T', 'T'),('U', 'U'), ('V', 'V'),('W', 'W'), ('X', 'X'),('Y', 'Y'), ('Z', 'Z'), ('AA', 'AA'), ('AB', 'AB'), ('AC', 'AC'), ('AD', 'AD'), ('AE', 'AE'), ('AF', 'AF')])
    f6 = fields.Selection([('Norte', 'Norte'), ('Oeste', 'Oeste'),('Este', 'Este'), ('Sur', 'Sur')])
    f7 = fields.Char('')
    f8 = fields.Selection([('A', 'A'), ('B', 'B'),('C', 'C'), ('D', 'D'),('E', 'E'), ('F', 'F'),('G', 'G'), ('H', 'H'),('I', 'I'), ('J', 'J'),('K', 'K'), ('L', 'L'),('M', 'M'), ('N', 'N'),('O', 'O'), ('P', 'P'),('Q', 'Q'), ('R', 'R'),('S', 'S'), ('T', 'T'),('U', 'U'), ('V', 'V'),('W', 'W'), ('X', 'X'),('Y', 'Y'), ('Z', 'Z'), ('AA', 'AA'), ('AB', 'AB'), ('AC', 'AC'), ('AD', 'AD'), ('AE', 'AE'), ('AF', 'AF')])
    f9 = fields.Char('')
    f10 = fields.Selection([('Norte', 'Norte'), ('Oeste', 'Oeste'),('Este', 'Este'), ('Sur', 'Sur')])
    f11 = fields.Selection([('AP', 'Apartamento'), ('AG', 'Agrupación'),('BR', 'Barrio'), ('CA', 'Casa'), ('LC', 'Local')])
    f12 = fields.Char('', help='Referencia')
    f13 = fields.Selection([('A', 'A'), ('B', 'B'),('C', 'C'), ('D', 'D'),('E', 'E'), ('F', 'F'),('G', 'G'), ('H', 'H'),('I', 'I'), ('J', 'J'),('K', 'K'), ('L', 'L'),('M', 'M'), ('N', 'N'),('O', 'O'), ('P', 'P'),('Q', 'Q'), ('R', 'R'),('S', 'S'), ('T', 'T'),('U', 'U'), ('V', 'V'),('W', 'W'), ('X', 'X'),('Y', 'Y'), ('Z', 'Z'), ('AA', 'AA'), ('AB', 'AB'), ('AC', 'AC'), ('AD', 'AD'), ('AE', 'AE'), ('AF', 'AF')])
    f14 = fields.Selection([('A', 'A'), ('B', 'B'),('C', 'C'), ('D', 'D'),('E', 'E'), ('F', 'F'),('G', 'G'), ('H', 'H'),('I', 'I'), ('J', 'J'),('K', 'K'), ('L', 'L'),('M', 'M'), ('N', 'N'),('O', 'O'), ('P', 'P'),('Q', 'Q'), ('R', 'R'),('S', 'S'), ('T', 'T'),('U', 'U'), ('V', 'V'),('W', 'W'), ('X', 'X'),('Y', 'Y'), ('Z', 'Z'), ('AA', 'AA'), ('AB', 'AB'), ('AC', 'AC'), ('AD', 'AD'), ('AE', 'AE'), ('AF', 'AF')])
    f15 = fields.Selection([('A', 'A'), ('B', 'B'),('C', 'C'), ('D', 'D'),('E', 'E'), ('F', 'F'),('G', 'G'), ('H', 'H'),('I', 'I'), ('J', 'J'),('K', 'K'), ('L', 'L'),('M', 'M'), ('N', 'N'),('O', 'O'), ('P', 'P'),('Q', 'Q'), ('R', 'R'),('S', 'S'), ('T', 'T'),('U', 'U'), ('V', 'V'),('W', 'W'), ('X', 'X'),('Y', 'Y'), ('Z', 'Z'), ('AA', 'AA'), ('AB', 'AB'), ('AC', 'AC'), ('AD', 'AD'), ('AE', 'AE'), ('AF', 'AF')])
    f16 = fields.Selection([('A', 'A'), ('B', 'B'),('C', 'C'), ('D', 'D'),('E', 'E'), ('F', 'F'),('G', 'G'), ('H', 'H'),('I', 'I'), ('J', 'J'),('K', 'K'), ('L', 'L'),('M', 'M'), ('N', 'N'),('O', 'O'), ('P', 'P'),('Q', 'Q'), ('R', 'R'),('S', 'S'), ('T', 'T'),('U', 'U'), ('V', 'V'),('W', 'W'), ('X', 'X'),('Y', 'Y'), ('Z', 'Z'), ('AA', 'AA'), ('AB', 'AB'), ('AC', 'AC'), ('AD', 'AD'), ('AE', 'AE'), ('AF', 'AF')])
    street_sug = fields.Char('Direccion sugerida')

    @api.model
    @api.onchange('f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12', 'f13', 'f14', 'f15', 'f16')
    def _calcular_componente_street(self):
        
        bis = ''
        v1 = v2 = v3 = v13 = v4 = v5 = v6 = v7 = v8 = v9 = v10 = v11 = v12 = v14 = v15 = v16 = ''

        if self.f1 is not False:
            v1 = str(self.f1)
        if self.f2 is not False:
            v2 = str(self.f2)
        if self.f3 is not False:
            v3 = str(self.f3)
        if self.f13 is not False:
            v13 = str(self.f13)
        if self.f4 is not False:
            v4 = 'BIS'
        if self.f5 is not False:
            v5 = str(self.f5)
        if self.f6 is not False:
            v6 = str(self.f6)
        if self.f7 is not False:
            v7 = str(self.f7)
        if self.f8 is not False:
            v8 = str(self.f8)
        if self.f9 is not False:
            v9 = str(self.f9)
        if self.f10 is not False:
            v10 = str(self.f10)
        if self.f11 is not False:
            v11 = str(self.f11)
        if self.f12 is not False:
            v12 = str(self.f12)

        self.street_sug = v1 + ' ' + v2 + ' ' + v3 + v13 + ' ' + v4 + ' ' + v5 + ' ' + v6 + ' ' + v7 + ' ' + v8 + v14 + ' ' + v10 + ' ' + v9 + ' ' + v15 + v16 + ' ' + v11 + ' ' + v12

    def action_add_street(self):
        
        bis = ''
        v1 = v2 = v3 = v13 = v4 = v5 = v6 = v7 = v8 = v9 = v10 = v11 = v12 = v14 = v15 = v16 = ''

        if self.f1 is not False:
            v1 = str(self.f1)
        if self.f2 is not False:
            v2 = str(self.f2)
        if self.f3 is not False:
            v3 = str(self.f3)
        if self.f13 is not False:
            v13 = str(self.f13)
        if self.f4 is not False:
            v4 = 'BIS'
        if self.f5 is not False:
            v5 = str(self.f5)
        if self.f6 is not False:
            v6 = str(self.f6)
        if self.f7 is not False:
            v7 = str(self.f7)
        if self.f8 is not False:
            v8 = str(self.f8)
        if self.f9 is not False:
            v9 = str(self.f9)
        if self.f10 is not False:
            v10 = str(self.f10)
        if self.f11 is not False:
            v11 = str(self.f11)
        if self.f12 is not False:
            v12 = str(self.f12)
        if self.f14 is not False:
            v14 = str(self.f14)
        if self.f15 is not False:
            v15 = str(self.f15)
        if self.f16 is not False:
            v16 = str(self.f16)

        direccion = v1 + ' ' + v2 + ' ' + v3 + v13 + ' ' + v4 + ' ' + v5 + ' ' + v6 + ' ' + v7 + ' ' + v8 + v14 + ' ' + v10 + ' ' + v9 + ' ' + v15 + v16 + ' ' + v11 + ' ' + v12

        partner_id = self.env['res.partner'].search([('id', '=', self.env.context['active_id'])])
        partner_id.write({'street': direccion})
        return {'type': 'ir.actions.act_window_close'}

class ProfesionTercero(models.Model):

    _name = 'res.partner.profesion'
    _description = 'Profesión de tercero'
    
    name = fields.Char('Nombre profesión')