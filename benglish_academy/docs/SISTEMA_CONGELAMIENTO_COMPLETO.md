# Sistema de Congelamiento de Matrículas - Documentación Completa


## 📋 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Modelos Principales](#modelos-principales)
4. [Flujo de Trabajo](#flujo-de-trabajo)
5. [Configuración Inicial](#configuración-inicial)
6. [Uso del Sistema](#uso-del-sistema)
7. [Seguridad y Permisos](#seguridad-y-permisos)
8. [Validaciones y Reglas](#validaciones-y-reglas)
9. [Vistas e Interfaces](#vistas-e-interfaces)
10. [Casos de Uso](#casos-de-uso)

---

## 🎯 Introducción

### ¿Qué es el Sistema de Congelamiento?

El sistema de congelamiento permite a los estudiantes pausar temporalmente sus matrículas bajo ciertas condiciones y políticas institucionales. El sistema controla:

- ✅ Motivos válidos de congelamiento
- ✅ Días permitidos según el plan del estudiante
- ✅ Documentación requerida por tipo de motivo
- ✅ Estado de cartera del estudiante
- ✅ Flujo de aprobación coordinado
- ✅ Ajuste automático de fechas de matrícula

### Historias de Usuario Implementadas

- **HU-GA-CONG-01**: Configuración de políticas de congelamiento por plan
- **HU-GA-CONG-02**: Congelamientos especiales (excepciones)
- **T-GA-CONG-01**: Validación de política del plan
- **T-GA-CONG-02**: Registro y cálculo de días
- **T-GA-CONG-03**: Ajuste automático de fechas
- **T-GA-CONG-04**: Validación de estado de cartera

---

## 🏗️ Arquitectura del Sistema

### Diagrama de Capas

```
┌─────────────────────────────────────────────────────────┐
│  CAPA 1: CATÁLOGO DE MOTIVOS                            │
│  benglish.freeze.reason                                 │
│  Rol: Define opciones para el usuario                  │
│  - 11 motivos predefinidos                             │
│  - Control de documentación por motivo                 │
│  - Días sugeridos por tipo                             │
└─────────────────────────────────────────────────────────┘
                          ↓ guía al usuario
┌─────────────────────────────────────────────────────────┐
│  CAPA 2: POLÍTICAS INSTITUCIONALES                      │
│  benglish.plan.freeze.config                            │
│  Rol: Reglas DURAS por plan                            │
│  - Límites min/max por solicitud                       │
│  - Máximo acumulado durante vigencia                   │
│  - Restricciones de cartera                            │
└─────────────────────────────────────────────────────────┘
                          ↓ valida según
┌─────────────────────────────────────────────────────────┐
│  CAPA 3: SOLICITUDES DE CONGELAMIENTO                   │
│  benglish.student.freeze.period                         │
│  Rol: Registro de solicitud concreta                   │
│  - Estados del flujo (borrador → aprobado)             │
│  - Documentos adjuntos                                 │
│  - Auditoría de cambios                                │
└─────────────────────────────────────────────────────────┘
                          ↓ se crea mediante
┌─────────────────────────────────────────────────────────┐
│  CAPA 4: INTERFAZ DE USUARIO                            │
│  benglish.freeze.request.wizard                         │
│  Rol: UX guiada para crear solicitudes                 │
│  - Validaciones en tiempo real                         │
│  - Cálculo automático de días                          │
│  - Alertas de documentación                            │
└─────────────────────────────────────────────────────────┘
```

### Flujo de Datos

```
Estudiante → Wizard → Validación → Solicitud → Aprobación → Ajuste Fechas
    ↓           ↓          ↓            ↓           ↓            ↓
  Perfil    Motivo    Política      Registro   Coordinador   Matrícula
```

---

## 📦 Modelos Principales

### 1. `benglish.freeze.reason` (Catálogo de Motivos)

**Archivo:** `models/freeze_reason.py` (173 líneas)

#### Propósito
Catálogo predefinido de motivos que los estudiantes pueden seleccionar al solicitar un congelamiento.

#### Campos Principales

```python
# Identificación
name = fields.Char('Motivo')                    # ej: "Motivo Médico"
code = fields.Char('Código')                    # ej: "MEDICO"
sequence = fields.Integer('Secuencia')          # Orden de visualización
description = fields.Text('Descripción')        # Detalles del motivo

# Configuración
requiere_documentacion = fields.Boolean()       # Si requiere docs
tipos_documentos = fields.Text()                # Qué documentos adjuntar
dias_maximos_sugeridos = fields.Integer()       # Sugerencia de días
es_especial = fields.Boolean()                  # Solo para coordinación

# Estadísticas
freeze_count = fields.Integer()                 # Cuántas veces se usó
```

#### Motivos Predefinidos (11)

| Código | Nombre | Documentos | Días Sugeridos |
|--------|--------|------------|----------------|
| MEDICO | Motivo Médico | Certificado médico | 90 |
| VIAJE | Viaje al Exterior | Boletos de avión | 60 |
| LABORAL | Razones Laborales | Carta de trabajo | 60 |
| FAMILIAR | Situación Familiar | No | 45 |
| ECONOMICO | Dificultades Económicas | No | 60 |
| ACADEMICO | Razones Académicas | Horario académico | 30 |
| MUDANZA | Mudanza o Cambio Ciudad | No | 45 |
| PERSONAL | Motivos Personales | No | 30 |
| MATERNIDAD | Embarazo/Maternidad | Certificado médico | 120 |
| ESPECIAL_COORD | Acuerdo Especial | No | 0 (especial) |
| ESPECIAL_CART | Excepción Cartera | No | 0 (especial) |

#### Métodos Importantes

```python
def action_view_freeze_periods(self):
    """Abre vista de todos los congelamientos que usan este motivo"""
    return {
        'type': 'ir.actions.act_window',
        'res_model': 'benglish.student.freeze.period',
        'domain': [('freeze_reason_id', '=', self.id)]
    }
```

#### SQL Constraints

```python
_sql_constraints = [
    ('code_unique', 'UNIQUE(code, company_id)', 
     'El código del motivo debe ser único')
]
```

---

### 2. `benglish.plan.freeze.config` (Políticas por Plan)

**Archivo:** `models/plan_freeze_config.py` (428 líneas)

#### Propósito
Define las reglas y restricciones de congelamiento específicas para cada plan de estudio.

#### Campos Principales

```python
# Relación
plan_id = fields.Many2one('benglish.plan')      # Plan al que aplica

# Habilitación
permite_congelamiento = fields.Boolean()        # ¿Permite congelar?

# Límites de Días
min_dias_congelamiento = fields.Integer()       # Mínimo: 15 días
max_dias_congelamiento = fields.Integer()       # Máximo por solicitud: 60
max_dias_acumulados = fields.Integer()          # Máximo total: 90

# Restricciones
requiere_pago_al_dia = fields.Boolean()         # ¿Requiere estar al día?
dias_minimos_cursados = fields.Integer()        # Días mínimos antes de congelar
max_congelamientos_por_ciclo = fields.Integer() # Límite de solicitudes
```

#### Ejemplos de Configuración

**Plan Plus:**
```python
permite_congelamiento = True
min_dias = 15
max_dias = 60
max_acumulados = 90
requiere_pago_al_dia = True
```

**Plan Supreme:**
```python
permite_congelamiento = True
min_dias = 30
max_dias = 120
max_acumulados = 180
requiere_pago_al_dia = True
```

**Plan Cortesía:**
```python
permite_congelamiento = False  # No permite congelamiento
```

#### Métodos Importantes

```python
def get_config_for_plan(self, plan_id):
    """Obtiene la configuración de un plan específico"""
    return self.search([
        ('plan_id', '=', plan_id),
        ('active', '=', True)
    ], limit=1)

def can_request_freeze(self, dias_solicitados, dias_ya_usados):
    """Valida si se puede solicitar un congelamiento"""
    if not self.permite_congelamiento:
        return (False, "Este plan no permite congelamiento")
    
    if dias_solicitados < self.min_dias_congelamiento:
        return (False, f"Mínimo: {self.min_dias_congelamiento} días")
    
    if dias_solicitados > self.max_dias_congelamiento:
        return (False, f"Máximo: {self.max_dias_congelamiento} días")
    
    dias_totales = dias_ya_usados + dias_solicitados
    if dias_totales > self.max_dias_acumulados:
        return (False, f"Excede máximo acumulado: {self.max_dias_acumulados}")
    
    return (True, "Solicitud válida")
```

#### SQL Constraints

```python
_sql_constraints = [
    ('plan_unique', 'UNIQUE(plan_id, company_id)', 
     'Ya existe configuración para este plan'),
    ('min_menor_max', 'CHECK(min_dias <= max_dias)', 
     'Mínimo no puede ser mayor al máximo'),
]
```

---

### 3. `benglish.student.freeze.period` (Solicitudes)

**Archivo:** `models/student_freeze_period.py` (990 líneas)

#### Propósito
Registra las solicitudes concretas de congelamiento de los estudiantes con todo su ciclo de vida.

#### Campos Principales

```python
# Relaciones
student_id = fields.Many2one('benglish.student')
enrollment_id = fields.Many2one('benglish.enrollment')
plan_id = fields.Many2one(related='enrollment_id.plan_id')
freeze_config_id = fields.Many2one(computed)

# Motivo (REDISEÑADO v1.3.0)
freeze_reason_id = fields.Many2one('benglish.freeze.reason')  # Selector
motivo_detalle = fields.Text()                                 # Detalles adicionales
motivo = fields.Text(computed)                                 # Legacy combinado

# Fechas
fecha_solicitud = fields.Date()
fecha_inicio = fields.Date()
fecha_fin = fields.Date()
fecha_aprobacion = fields.Datetime()

# Días
dias = fields.Integer(computed)                # Días del periodo
dias_restantes = fields.Integer(computed)      # Días que faltan

# Estado
estado = fields.Selection([
    ('borrador', 'Borrador'),
    ('pendiente', 'Pendiente de Aprobación'),
    ('aprobado', 'Aprobado'),
    ('rechazado', 'Rechazado'),
    ('cancelado', 'Cancelado'),
    ('finalizado', 'Finalizado'),
])

# Documentación
requiere_documentacion = fields.Boolean(related)
tipos_documentos_requeridos = fields.Text(related)
documento_soporte_ids = fields.Many2many('ir.attachment')
documentacion_completa = fields.Boolean(computed)

# Cartera
estudiante_al_dia = fields.Boolean(computed)
excepcion_cartera = fields.Boolean()
motivo_excepcion_cartera = fields.Text()

# Congelamiento Especial
es_especial = fields.Boolean()
tipo_especial = fields.Selection()
motivo_especial = fields.Text()

# Aprobación
aprobado_por_id = fields.Many2one('res.users')
rechazado_por_id = fields.Many2one('res.users')
motivo_rechazo = fields.Text()

# Auditoría (ajuste de fechas)
fecha_fin_original_enrollment = fields.Date()
fecha_fin_nueva_enrollment = fields.Date()
ajuste_aplicado = fields.Boolean()

# UX
mensaje_validacion = fields.Html(computed)
puede_aprobar = fields.Boolean(computed)
visible_portal = fields.Boolean(computed)
```

#### Estados del Flujo

```
┌──────────┐   enviar   ┌──────────┐   aprobar   ┌──────────┐
│ Borrador │  ────────> │ Pendiente │  ────────>  │ Aprobado │
└──────────┘            └──────────┘             └──────────┘
                             │  rechazar              │
                             v                        v
                        ┌──────────┐            ┌────────────┐
                        │ Rechazado│            │ Finalizado │
                        └──────────┘            └────────────┘
```

#### Métodos Principales

```python
@api.depends('freeze_reason_id', 'motivo_detalle')
def _compute_motivo(self):
    """Combina motivo seleccionado + detalles"""
    for record in self:
        if record.freeze_reason_id:
            motivo = f"[{record.freeze_reason_id.name}]"
            if record.motivo_detalle:
                motivo += f"\n\n{record.motivo_detalle}"
            record.motivo = motivo

@api.depends('fecha_inicio', 'fecha_fin')
def _compute_dias(self):
    """Calcula días del periodo"""
    for record in self:
        if record.fecha_inicio and record.fecha_fin:
            delta = record.fecha_fin - record.fecha_inicio
            record.dias = delta.days + 1

@api.depends('requiere_documentacion', 'documento_soporte_ids')
def _compute_documentacion_completa(self):
    """Verifica si adjuntó documentos"""
    for record in self:
        if record.requiere_documentacion:
            record.documentacion_completa = len(record.documento_soporte_ids) > 0
        else:
            record.documentacion_completa = True

def action_enviar_aprobacion(self):
    """Envía solicitud a aprobación"""
    self.ensure_one()
    self._validar_antes_enviar()
    self.estado = 'pendiente'
    self.message_post(body="Solicitud enviada a aprobación")

def action_aprobar(self):
    """Aprueba y ajusta fechas de matrícula"""
    self.ensure_one()
    self._validar_antes_aprobar()
    
    # Ajustar fecha fin de enrollment
    if self.enrollment_id:
        self.fecha_fin_original_enrollment = self.enrollment_id.end_date
        nueva_fecha = self.enrollment_id.end_date + timedelta(days=self.dias)
        self.enrollment_id.end_date = nueva_fecha
        self.fecha_fin_nueva_enrollment = nueva_fecha
        self.ajuste_aplicado = True
    
    self.estado = 'aprobado'
    self.fecha_aprobacion = fields.Datetime.now()
    self.aprobado_por_id = self.env.user.id

def action_rechazar(self, motivo):
    """Rechaza solicitud con motivo"""
    self.ensure_one()
    self.estado = 'rechazado'
    self.motivo_rechazo = motivo
    self.rechazado_por_id = self.env.user.id
```

#### Validaciones

```python
@api.constrains('fecha_inicio', 'fecha_fin')
def _check_fechas(self):
    """Valida coherencia de fechas"""
    for record in self:
        if record.fecha_fin < record.fecha_inicio:
            raise ValidationError("Fecha fin debe ser posterior")

@api.constrains('dias')
def _check_dias_disponibles(self):
    """Valida contra política del plan"""
    for record in self:
        if record.es_especial:
            continue
        
        config = record.freeze_config_id
        if not config:
            continue
        
        dias_usados = record._get_dias_usados_estudiante()
        puede, mensaje = config.can_request_freeze(record.dias, dias_usados)
        
        if not puede:
            raise ValidationError(mensaje)
```

---

### 4. `benglish.freeze.request.wizard` (Wizard de Solicitud)

**Archivo:** `wizards/freeze_request_wizard.py` (346 líneas)

#### Propósito
Interfaz amigable paso a paso para que estudiantes o administrativos creen solicitudes de congelamiento con validaciones en tiempo real.

#### Campos del Wizard

```python
# Estudiante
student_id = fields.Many2one('benglish.student')
enrollment_id = fields.Many2one('benglish.enrollment')
plan_id = fields.Many2one(related)

# Motivo
freeze_reason_id = fields.Many2one('benglish.freeze.reason')
motivo_detalle = fields.Text()

# Fechas
fecha_inicio = fields.Date(default=hoy + 7 días)
fecha_fin = fields.Date()
dias_solicitados = fields.Integer(computed)

# Disponibilidad
dias_usados = fields.Integer(computed)
dias_disponibles = fields.Integer(computed)
dias_maximos_plan = fields.Integer(computed)

# Validación
puede_solicitar = fields.Boolean(computed)
mensaje_validacion = fields.Html(computed)
estudiante_al_dia = fields.Boolean(related)
```

#### Flujo del Wizard

```
1. Selección Estudiante + Matrícula
   ↓
2. Muestra Disponibilidad (días usados/disponibles)
   ↓
3. Selecciona Motivo del catálogo
   ↓
4. Sistema sugiere fechas según motivo
   ↓
5. Usuario ajusta fechas
   ↓
6. Proporciona detalles adicionales
   ↓
7. Panel de validación en tiempo real
   ↓
8. Crear Solicitud (si cumple requisitos)
```

#### Validaciones en Tiempo Real

```python
@api.depends('dias_solicitados', 'dias_disponibles', 'estudiante_al_dia', ...)
def _compute_puede_solicitar(self):
    """Valida en tiempo real"""
    for wizard in self:
        errores = []
        advertencias = []
        
        # Validación 1: Fecha de inicio
        if wizard.fecha_inicio < today:
            errores.append('❌ Fecha no puede ser en el pasado')
        
        # Validación 2: Días disponibles
        if wizard.dias_solicitados > wizard.dias_disponibles:
            errores.append(f'❌ Solo tiene {wizard.dias_disponibles} días')
        
        # Validación 3: Estado de cartera
        if config.requiere_pago_al_dia and not wizard.estudiante_al_dia:
            advertencias.append('⚠ Tiene pagos pendientes')
        
        # Validación 4: Documentación
        if wizard.requiere_documentacion:
            advertencias.append(f'📎 Debe adjuntar: {wizard.tipos_documentos}')
        
        wizard.puede_solicitar = len(errores) == 0
        wizard.mensaje_validacion = self._generar_html(errores, advertencias)
```

#### Método de Creación

```python
def action_create_request(self):
    """Crea la solicitud de congelamiento"""
    self.ensure_one()
    
    if not self.puede_solicitar:
        raise ValidationError("Corrija los errores antes de crear")
    
    freeze_period = self.env['benglish.student.freeze.period'].create({
        'student_id': self.student_id.id,
        'enrollment_id': self.enrollment_id.id,
        'freeze_reason_id': self.freeze_reason_id.id,
        'motivo_detalle': self.motivo_detalle,
        'fecha_inicio': self.fecha_inicio,
        'fecha_fin': self.fecha_fin,
        'estado': 'borrador',
    })
    
    return {
        'type': 'ir.actions.act_window',
        'res_model': 'benglish.student.freeze.period',
        'res_id': freeze_period.id,
        'view_mode': 'form',
    }
```

---

## 🔄 Flujo de Trabajo Completo

### Flujo Normal (Usuario Final)

```
1. ESTUDIANTE
   - Va a menú Estudiantes
   - Abre su ficha
   - Clic en "Solicitar Congelamiento"
   
2. WIZARD (validación en tiempo real)
   - Selecciona matrícula
   - Ve días disponibles: 60/90 usados
   - Selecciona "Motivo Médico" del catálogo
   - Sistema sugiere fechas (90 días)
   - Ajusta a 45 días
   - Proporciona detalles
   - Ve panel: "✅ Todo correcto"
   - Clic "Crear Solicitud"
   
3. SOLICITUD CREADA
   - Estado: Borrador
   - Puede adjuntar documentos
   - Puede editar detalles
   - Clic "Enviar a Aprobación"
   
4. COORDINACIÓN
   - Ve en menú "Pendientes de Aprobación"
   - Abre solicitud
   - Revisa:
     * Días solicitados vs disponibles
     * Documentación adjunta
     * Estado de cartera
     * Motivo y justificación
   - Decide: Aprobar o Rechazar
   
5. APROBACIÓN
   - Sistema ajusta automáticamente:
     * Fecha fin de matrícula + 45 días
     * Registra auditoría
     * Notifica al estudiante
   - Estado: Aprobado
   
6. FINALIZACIÓN
   - Al llegar fecha_fin, estado → Finalizado
   - Días se suman a días_usados del estudiante
```

### Flujo Especial (Coordinación)

```
1. COORDINACIÓN crea solicitud especial
   - Marca "Es Especial" = True
   - No valida contra política del plan
   - Puede exceder límites normales
   - Requiere justificación especial
   
2. Ejemplos de uso:
   - Acuerdo comercial especial
   - Excepción de cartera
   - Caso médico grave > 90 días
   - Situación humanitaria
```

---

## ⚙️ Configuración Inicial

### Paso 1: Crear Motivos de Congelamiento

**Menú:** Congelamiento > Configuración > Motivos de Congelamiento

Ya vienen 11 motivos predefinidos en `data/demo_freeze_reasons.xml`:

```xml
<record id="freeze_reason_medico" model="benglish.freeze.reason">
    <field name="name">Motivo Médico</field>
    <field name="code">MEDICO</field>
    <field name="sequence">10</field>
    <field name="requiere_documentacion">True</field>
    <field name="tipos_documentos">Certificado médico, Historia clínica</field>
    <field name="dias_maximos_sugeridos">90</field>
</record>
```

**Puedes agregar más:**
1. Clic "Nuevo"
2. Nombre: ej. "Viaje Largo"
3. Código: VIAJE_LARGO
4. Requiere documentación: Sí/No
5. Tipos documentos: "Boletos, Visa"
6. Días sugeridos: 120
7. Guardar

### Paso 2: Configurar Políticas por Plan

**Menú:** Congelamiento > Configuración > Políticas por Plan

**Para cada plan:**

```
Plan: Plus
├─ Permite Congelamiento: ✓
├─ Mínimo de días: 15
├─ Máximo por solicitud: 60
├─ Máximo acumulado: 90
├─ Requiere pagos al día: ✓
└─ Días mínimos cursados: 30
```

### Paso 3: Verificar Grupos de Seguridad

Los siguientes grupos deben existir:
- `group_academic_user` → Solo lectura
- `group_academic_assistant` → Crear solicitudes
- `group_academic_coordinator` → Aprobar/Rechazar
- `group_academic_manager` → Todo + Especiales

---

## 👥 Seguridad y Permisos

### Matriz de Permisos

| Modelo | User | Teacher | Assistant | Coordinator | Manager |
|--------|------|---------|-----------|-------------|---------|
| **freeze.reason** | R | R | R | CRUD | CRUD |
| **plan.freeze.config** | R | R | R | CRUD | CRUD |
| **student.freeze.period** | R | R | RWC | CRUD | CRUD |
| **freeze.request.wizard** | RWC | - | RWC | RWC | RWC |

**Leyenda:**
- R = Read
- W = Write
- C = Create
- D = Delete

### Reglas de Dominio (Record Rules)

```python
# Los estudiantes solo ven sus propios congelamientos
<record id="rule_freeze_period_student" model="ir.rule">
    <field name="domain_force">
        [('student_id.user_id', '=', user.id)]
    </field>
    <field name="groups" eval="[(4, ref('base.group_portal'))]"/>
</record>

# Coordinadores ven todos
<record id="rule_freeze_period_coordinator" model="ir.rule">
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('group_academic_coordinator'))]"/>
</record>
```

### Vistas con Grupos

```xml
<!-- Solo coordinadores pueden aprobar -->
<button name="action_aprobar" type="object"
    groups="benglish_academy.group_academic_coordinator"/>

<!-- Solo managers ven congelamientos especiales -->
<field name="es_especial" 
    invisible="not context.get('show_special')"
    groups="benglish_academy.group_academic_manager"/>
```

---

## ✅ Validaciones y Reglas

### Validaciones del Sistema

#### 1. Validación de Disponibilidad

```python
def _validar_dias_disponibles(self):
    """Verifica que no exceda límite del plan"""
    config = self.freeze_config_id
    dias_usados = self.student_id.dias_congelamiento_usados
    
    if dias_usados + self.dias > config.max_dias_acumulados:
        raise ValidationError(
            f"Excede máximo acumulado. "
            f"Usados: {dias_usados}, "
            f"Disponibles: {config.max_dias_acumulados - dias_usados}"
        )
```

#### 2. Validación de Cartera

```python
def _validar_estado_cartera(self):
    """Verifica pagos al día si el plan lo requiere"""
    config = self.freeze_config_id
    
    if config.requiere_pago_al_dia:
        if not self.estudiante_al_dia and not self.excepcion_cartera:
            raise ValidationError(
                "El estudiante tiene pagos pendientes. "
                "Requiere excepción de cartera para aprobar."
            )
```

#### 3. Validación de Documentación

```python
def _validar_documentacion(self):
    """Verifica documentos adjuntos si se requieren"""
    if self.requiere_documentacion:
        if not self.documentacion_completa:
            raise UserError(
                f"Debe adjuntar: {self.tipos_documentos_requeridos}"
            )
```

#### 4. Validación de Fechas

```python
@api.constrains('fecha_inicio', 'fecha_fin')
def _check_fechas_coherentes(self):
    """Valida coherencia de fechas"""
    for record in self:
        if record.fecha_fin < record.fecha_inicio:
            raise ValidationError("Fecha fin debe ser posterior a inicio")
        
        if record.fecha_inicio < fields.Date.today():
            raise ValidationError("No puede congelar en el pasado")
```

### Reglas de Negocio

#### Matriz de Reglas

| Condición | Acción | Quién |
|-----------|--------|-------|
| Plan no permite | Bloquear solicitud | Sistema |
| Días < mínimo | Rechazar | Sistema |
| Días > máximo | Rechazar | Sistema |
| Excede acumulado | Rechazar | Sistema |
| Sin pagos al día | Requiere excepción | Coordinador |
| Sin documentos | Bloquear envío | Sistema |
| Especial | Solo coordinación | Sistema |

---

## 🖥️ Vistas e Interfaces

### Vista Lista de Solicitudes

**Archivo:** `views/student_freeze_period_views.xml`

```xml
<list decoration-success="estado == 'aprobado'"
      decoration-warning="estado == 'pendiente'"
      decoration-danger="estado == 'rechazado'"
      decoration-muted="estado in ('cancelado', 'finalizado')">
    <field name="student_id"/>
    <field name="freeze_reason_id"/>
    <field name="fecha_inicio"/>
    <field name="fecha_fin"/>
    <field name="dias"/>
    <field name="estado" widget="badge"/>
</list>
```

### Vista Formulario de Solicitud

**Secciones:**

1. **Header** (Ribbons y Botones)
```xml
<header>
    <button name="action_enviar_aprobacion" 
        string="Enviar a Aprobación"
        invisible="estado != 'borrador'"/>
    
    <button name="action_aprobar" 
        string="✅ Aprobar"
        groups="group_academic_coordinator"
        invisible="estado != 'pendiente'"/>
    
    <field name="estado" widget="statusbar"/>
</header>
```

2. **Información de Matrícula**
```xml
<group string="📋 Información de la Matrícula">
    <field name="student_id"/>
    <field name="enrollment_id"/>
    <field name="plan_id"/>
</group>
```

3. **Periodo de Congelamiento**
```xml
<group string="📅 Periodo de Congelamiento">
    <field name="fecha_inicio"/>
    <field name="fecha_fin"/>
    <field name="dias" string="Días Solicitados"/>
</group>
```

4. **Motivo**
```xml
<group string="📝 Motivo del Congelamiento">
    <field name="freeze_reason_id" 
        placeholder="Seleccione el motivo..."/>
    <field name="motivo_detalle" 
        placeholder="Explique su situación..."/>
</group>
```

5. **Documentos** (condicional)
```xml
<group string="📎 Documentos de Soporte" 
    invisible="not requiere_documentacion">
    <field name="documento_soporte_ids" widget="many2many_binary"/>
    <field name="documentacion_completa" widget="boolean"/>
</group>
```

6. **Panel de Validación**
```xml
<separator string="✅ Estado de Validación"/>
<field name="mensaje_validacion" nolabel="1"/>
```

### Vista Wizard

**Archivo:** `views/freeze_request_wizard_views.xml`

```xml
<form string="Solicitar Congelamiento">
    <sheet>
        <div class="oe_title">
            <h1>🗓️ Solicitar Congelamiento de Matrícula</h1>
        </div>
        
        <!-- Disponibilidad -->
        <group string="📊 Información de Congelamiento">
            <field name="dias_usados"/>
            <field name="dias_disponibles" 
                decoration-danger="dias_disponibles &lt; 15"/>
        </group>
        
        <!-- Motivo -->
        <field name="freeze_reason_id"/>
        
        <!-- Alerta de documentos -->
        <div class="alert alert-warning" 
            invisible="not requiere_documentacion">
            📎 Este motivo requiere: 
            <field name="tipos_documentos_requeridos"/>
        </div>
        
        <!-- Fechas -->
        <group string="📅 Fechas">
            <field name="fecha_inicio"/>
            <field name="fecha_fin"/>
            <field name="dias_solicitados"/>
        </group>
        
        <!-- Validación -->
        <field name="mensaje_validacion"/>
    </sheet>
    
    <footer>
        <button name="action_create_request" 
            string="✅ Crear Solicitud"
            invisible="not puede_solicitar"/>
        <button string="Cancelar" special="cancel"/>
    </footer>
</form>
```

### Vista Kanban (Dashboard)

```xml
<kanban>
    <field name="estado"/>
    <field name="dias"/>
    <field name="color"/>
    <templates>
        <t t-name="kanban-box">
            <div t-attf-class="oe_kanban_card">
                <div class="oe_kanban_content">
                    <strong><field name="student_id"/></strong>
                    <div><field name="freeze_reason_id"/></div>
                    <div>
                        <field name="dias"/> días
                        (<field name="fecha_inicio"/> - 
                         <field name="fecha_fin"/>)
                    </div>
                </div>
                <div class="oe_kanban_footer">
                    <field name="estado" widget="label_selection"/>
                </div>
            </div>
        </t>
    </templates>
</kanban>
```

---

## 📝 Casos de Uso

### Caso 1: Congelamiento Médico Normal

**Escenario:**
- Estudiante Juan (Plan Plus)
- Tiene una cirugía programada
- Necesita 60 días de congelamiento

**Pasos:**

1. Juan abre su ficha de estudiante
2. Clic "Solicitar Congelamiento"
3. Wizard muestra:
   - Días usados: 0
   - Días disponibles: 90
   - Días máximos: 90
4. Selecciona: "Motivo Médico"
5. Sistema pre-llena: 90 días (sugeridos)
6. Juan ajusta a: 60 días
7. Fechas: 01/12/2025 - 30/01/2026
8. Agrega detalles: "Cirugía de rodilla programada"
9. Validación: ✅ Todo correcto
10. Clic "Crear Solicitud"
11. Estado: Borrador
12. Juan adjunta: Certificado médico (PDF)
13. Clic "Enviar a Aprobación"
14. Estado: Pendiente
15. Coordinadora María revisa:
    - ✅ Está al día en pagos
    - ✅ Tiene documento adjunto
    - ✅ Días dentro del límite
16. María clic "Aprobar"
17. Sistema:
    - Ajusta fecha fin matrícula: +60 días
    - Registra auditoría
    - Estado: Aprobado
18. Al 30/01/2026:
    - Estado: Finalizado
    - Días usados de Juan: 60/90

### Caso 2: Solicitud Rechazada (Sin Pagos)

**Escenario:**
- Estudiante Ana (Plan Plus)
- Tiene pagos atrasados
- Solicita 30 días

**Pasos:**

1. Ana crea solicitud
2. Wizard muestra:
   - ⚠ Tiene pagos pendientes
3. Ana continúa y envía
4. Coordinador ve:
   - ❌ No está al día
   - Sin excepción de cartera
5. Coordinador clic "Rechazar"
6. Motivo: "Debe regularizar pagos primero"
7. Estado: Rechazado
8. Ana recibe notificación

### Caso 3: Congelamiento Especial

**Escenario:**
- Estudiante Carlos (Plan Plus)
- Necesita 150 días (excede límite de 90)
- Acuerdo comercial especial

**Pasos:**

1. Coordinador abre "Congelamiento > Todos"
2. Clic "Nuevo"
3. Selecciona: Carlos
4. Marca: "Es Especial" ✓
5. Tipo: "Acuerdo Especial"
6. Días: 150
7. Justificación: "Acuerdo con gerencia por..."
8. No valida contra política del plan
9. Clic "Aprobar" directamente
10. Estado: Aprobado
11. Días usados de Carlos: 150 (no cuenta para límite normal)

### Caso 4: Sin Documentos Requeridos

**Escenario:**
- Estudiante Laura
- Selecciona "Motivo Médico" (requiere docs)
- Intenta enviar sin adjuntar

**Pasos:**

1. Laura crea solicitud
2. Motivo: Médico
3. Wizard alerta: 📎 Debe adjuntar certificado
4. Laura clic "Crear"
5. Solicitud creada (Borrador)
6. Laura clic "Enviar a Aprobación"
7. Sistema valida:
   - ❌ Falta documentación
   - Error: "Debe adjuntar: Certificado médico"
8. Laura adjunta documento
9. Validación: ✅ Documentación completa
10. Ahora puede enviar

---

## 🔧 Mantenimiento y Extensiones

### Agregar Nuevo Motivo

```python
# En data/custom_freeze_reasons.xml
<record id="freeze_reason_custom" model="benglish.freeze.reason">
    <field name="name">Mi Motivo Personalizado</field>
    <field name="code">CUSTOM</field>
    <field name="sequence">100</field>
    <field name="requiere_documentacion">True</field>
    <field name="tipos_documentos">Documento específico</field>
    <field name="dias_maximos_sugeridos">45</field>
</record>
```

### Modificar Política de Plan

```python
# Buscar configuración existente
config = env['benglish.plan.freeze.config'].search([
    ('plan_id', '=', plan_plus.id)
])

# Actualizar
config.write({
    'max_dias_congelamiento': 90,  # Aumentar de 60 a 90
    'max_dias_acumulados': 120,    # Aumentar de 90 a 120
})
```

### Agregar Validación Personalizada

```python
# En student_freeze_period.py
@api.constrains('dias')
def _check_custom_rule(self):
    """Mi validación personalizada"""
    for record in self:
        if record.dias > 30 and not record.documentacion_completa:
            raise ValidationError(
                "Congelamientos mayores a 30 días "
                "requieren documentación obligatoria"
            )
```

---

## 📊 Reportes y Estadísticas

### Días de Congelamiento por Estudiante

```python
# En benglish.student
dias_congelamiento_usados = fields.Integer(
    compute='_compute_freeze_statistics'
)
dias_congelamiento_disponibles = fields.Integer(
    compute='_compute_freeze_statistics'
)

@api.depends('freeze_period_ids', 'plan_id')
def _compute_freeze_statistics(self):
    for student in self:
        # Días usados (solo aprobados y finalizados)
        usados = sum(student.freeze_period_ids.filtered(
            lambda f: f.estado in ('aprobado', 'finalizado')
        ).mapped('dias'))
        
        student.dias_congelamiento_usados = usados
        
        # Días disponibles
        config = env['benglish.plan.freeze.config'].get_config_for_plan(
            student.plan_id
        )
        if config:
            student.dias_congelamiento_disponibles = (
                config.max_dias_acumulados - usados
            )
```

### Uso de Motivos

```python
# En benglish.freeze.reason
freeze_count = fields.Integer(
    compute='_compute_freeze_count'
)

@api.depends()
def _compute_freeze_count(self):
    for reason in self:
        reason.freeze_count = env['benglish.student.freeze.period'].search_count([
            ('freeze_reason_id', '=', reason.id)
        ])
```

### Dashboard en Kanban

Vista agrupada por estado:
- Pendientes: 15
- Aprobados: 45
- Finalizados: 120
- Rechazados: 8

---

## 🚀 Mejoras Futuras

### Corto Plazo
- [ ] Notificaciones automáticas por email
- [ ] Recordatorio X días antes de finalización
- [ ] Exportar reporte Excel de congelamientos
- [ ] Dashboard gráfico (Chart.js)

### Mediano Plazo
- [ ] Aprobación multinivel (asistente → coordinador → manager)
- [ ] Integración con portal estudiante
- [ ] Firma digital de documentos
- [ ] Workflow configurable por tipo de motivo

### Largo Plazo
- [ ] Machine Learning para predecir aprobación
- [ ] Análisis de patrones de congelamiento
- [ ] Sugerencias automáticas de fechas
- [ ] Integración con sistema de pagos

---

## 📞 Soporte

### Contacto
- **Email:** soporte@benglish.com
- **Teléfono:** +123456789
- **Horario:** Lunes a Viernes 8am-6pm

### Recursos
- [Manual de Usuario](./MANUAL_USUARIO_CONGELAMIENTO.pdf)
- [Video Tutorial](https://youtube.com/...)
- [FAQ](./FAQ_CONGELAMIENTO.md)

---

## 📜 Historial de Cambios

### v18.0.1.3.0 (27/11/2025)
- ✅ Rediseño completo de congelamiento
- ✅ Catálogo de motivos predefinidos
- ✅ Wizard guiado con validaciones
- ✅ Panel HTML de validación
- ✅ Documentación completa

### v18.0.1.2.0 (20/11/2025)
- ✅ Implementación inicial HU-GA-CONG
- ✅ Estados de perfil
- ✅ Flujo de aprobación

