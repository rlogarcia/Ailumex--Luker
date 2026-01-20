# Sincronización Estudiante → Contacto (res.partner)

## 📋 Objetivo

Garantizar que toda la información del estudiante se capture correctamente y se sincronice con Contactos (`res.partner`) al momento de crear o habilitar el acceso al portal, usando únicamente los campos existentes de los módulos **OX / 1xResPartnerCall** y **Benglish Academy**.

## ✅ Cambios Implementados

### 1️⃣ Campo Tipo de Documento en Vista de Estudiante

**Archivo modificado:** `views/student_views.xml`

Se agregó el campo `id_type_id` (Tipo de Documento) en el formulario del estudiante, ubicado **antes** del campo `student_id_number` (Documento de Identidad).

```xml
<field name="id_type_id" string="Tipo de Documento"
    options="{'no_open': True, 'no_create': True}"
    placeholder="Cédula, Tarjeta de Identidad, etc." />
<field name="student_id_number" />
```

**Resultado:**

- El usuario ahora puede seleccionar el tipo de documento del estudiante desde el catálogo existente en Odoo (`l10n_latam.identification.type`)
- Opciones disponibles: Cédula de Ciudadanía, Tarjeta de Identidad, NIT, etc.

---

### 2️⃣ Sincronización Completa al Crear Acceso al Portal

**Archivo modificado:** `models/student.py` → Método `_create_single_portal_user()`

Se actualizó la lógica para copiar **todos los campos disponibles** del estudiante al contacto:

#### Campos sincronizados:

**Información Personal:**

- ✅ `first_name` → `primer_nombre` (OX)
- ✅ `second_name` → `otros_nombres` (OX)
- ✅ `first_last_name` → `primer_apellido` (OX)
- ✅ `second_last_name` → `segundo_apellido` (OX)
- ✅ `birth_date` → `fecha_nacimiento` (OX) **[NUEVO]**
- ✅ `gender` → `genero` (OX) **[NUEVO]** (con mapeo: male→masculino, female→femenino)

**Documento de Identidad:**

- ✅ `id_type_id` → `l10n_latam_identification_type_id` **[NUEVO - PRIORIDAD]**
  - Si el estudiante tiene tipo de documento seleccionado, se usa ese
  - Si no, se calcula automáticamente según la edad (fallback):
    - ≥18 años → Cédula de Ciudadanía
    - <18 años → Tarjeta de Identidad
- ✅ `student_id_number` → `ref` (campo estándar) **[NUEVO]**
- ✅ `student_id_number` → `vat` (campo NIT/VAT)

**Información de Contacto:**

- ✅ `email` → `email`
- ✅ `phone` → `phone`
- ✅ `mobile` → `mobile`
- ✅ `address` → `street`
- ✅ `city` → `city`
- ✅ `country_id` → `country_id`

**Otros:**

- ✅ `image_1920` → `image_1920` (foto del estudiante)
- ✅ Marcado como estudiante: `is_student = True`
- ✅ Tipo de persona: `company_type = 'person'`

---

### 3️⃣ Sincronización al Crear Estudiante

**Archivo modificado:** `models/student.py` → Método `create()`

Se aplicaron los **mismos cambios** al método `create()` para que cuando se cree un estudiante, el contacto asociado se genere automáticamente con **toda la información completa**.

**Lógica implementada:**

- Si se proporciona `id_type_id` en vals, se usa ese valor
- Si no hay `id_type_id` pero hay `birth_date`, se calcula según edad
- Se mapea el género correctamente (male/female/other → masculino/femenino)
- Se copian **todos** los campos disponibles

---

### 4️⃣ Método Manual de Sincronización

**Archivo modificado:** `models/student.py` → Nuevo método `action_sync_to_partner()`

Se agregó un método para **sincronizar manualmente** la información del estudiante a un contacto existente.

**Uso:**

- Para actualizar contactos existentes que fueron creados antes de esta mejora
- Para forzar sincronización después de editar datos del estudiante
- Útil para corrección masiva de datos

**Archivo modificado:** `views/student_views.xml` → Nuevo botón en header

```xml
<button name="action_sync_to_partner"
    type="object"
    string="Sincronizar a Contacto"
    class="btn-info"
    invisible="not partner_id"
    groups="benglish_academy.group_academic_assistant,base.group_system"
    help="Actualiza el contacto con toda la información del estudiante" />
```

**Resultado:**

- Botón visible solo si el estudiante tiene un contacto asociado
- Solo para Asistentes Académicos y Administradores
- Copia **todos** los datos del estudiante al contacto
- Muestra notificación de éxito

---

## 🔍 Campos del Módulo OX Utilizados

El módulo **OX / 1xResPartnerCall** (`ox_res_partner_ext_co`) extiende `res.partner` con los siguientes campos relevantes:

```python
# Nombres desagregados
primer_nombre = fields.Char('Primer nombre')
otros_nombres = fields.Char('Otros nombres')
primer_apellido = fields.Char('Primer apellido')
segundo_apellido = fields.Char('Segundo apellido')

# Información personal
fecha_nacimiento = fields.Date('Fecha de nacimiento')
genero = fields.Selection([
    ('masculino', 'Masculino'),
    ('femenino', 'Femenino')
], string='Genero')

# Documento (heredado de l10n_latam_base)
l10n_latam_identification_type_id = fields.Many2one(...)
ref = fields.Char(string='Identificacion')

# Ubicación
city_id = fields.Many2one('res.city', string='Ciudad')
barrio_ciudad = fields.Char('Barrio ciudad')

# Otros campos disponibles pero NO utilizados actualmente:
# - sexo_biologico
# - sexo_identificacion
# - pais_nacimiento
# - estado_civil
# - direccion_residencia
# - municipio_eps
# - zona
# - ips_cotizante
# - fondo_pensiones
```

---

## 🚀 Flujo de Sincronización

### Caso 1: Crear nuevo estudiante

1. Usuario completa formulario del estudiante
2. Usuario selecciona **Tipo de Documento** (opcional)
3. Al guardar, método `create()` ejecuta:
   - Genera código automático si no existe
   - Calcula tipo de documento (usa el seleccionado o calcula por edad)
   - Crea `res.partner` con **todos los datos**
   - Vincula `partner_id` al estudiante

### Caso 2: Crear acceso al portal

1. Usuario hace clic en **"Crear Usuario Portal"**
2. Método `_create_single_portal_user()` ejecuta:
   - Valida email y documento
   - Calcula tipo de documento (prioriza el del estudiante)
   - Si NO existe `partner_id`:
     - Crea nuevo contacto con **todos los datos**
   - Si YA existe `partner_id`:
     - **Actualiza** el contacto con **todos los datos**
   - Crea usuario de portal
   - Asigna contraseña = documento de identidad

### Caso 3: Sincronización manual

1. Usuario edita datos del estudiante
2. Usuario hace clic en **"Sincronizar a Contacto"**
3. Método `action_sync_to_partner()` ejecuta:
   - Toma **todos** los datos actuales del estudiante
   - Sobrescribe el `res.partner` vinculado
   - Muestra notificación de éxito

---

## ⚠️ Consideraciones Importantes

### Mapeo de Género

El estudiante usa valores diferentes a OX:

- Estudiante: `male` / `female` / `other`
- Partner OX: `masculino` / `femenino`

**Solución implementada:**

```python
genero_partner = False
if self.gender == 'male':
    genero_partner = 'masculino'
elif self.gender == 'female':
    genero_partner = 'femenino'
# 'other' → se deja vacío (no hay equivalente en OX)
```

### Tipo de Documento

**Lógica de prioridad:**

1. Si el estudiante tiene `id_type_id` seleccionado → **usar ese**
2. Si no tiene tipo pero tiene `birth_date` → calcular por edad
3. Si no tiene ninguno → dejar vacío

### Campo `ref` (Identificación)

El módulo OX tiene una **constraint unique** en `ref`:

```python
_sql_constraints = [
    ('ref_partner_unique', 'UNIQUE (ref, l10n_latam_identification_type_id)',
     'El número de identificación no puede ser repetido para el tipo de identificación seleccionado.!')
]
```

**Implicación:** No pueden haber dos contactos con el mismo número de documento Y tipo de documento.

---

## 📊 Testing Recomendado

### Test 1: Crear estudiante con tipo de documento

1. Crear nuevo estudiante
2. Seleccionar "Cédula de Ciudadanía" en Tipo de Documento
3. Completar documento: `1234567890`
4. Guardar
5. ✅ Verificar que se creó `res.partner` con `l10n_latam_identification_type_id` = Cédula

### Test 2: Crear acceso al portal

1. Crear estudiante con todos los datos completos
2. Clic en "Crear Usuario Portal"
3. ✅ Verificar contacto tiene: nombres, documento, tipo doc, fecha nacimiento, género, dirección, ciudad, país

### Test 3: Actualizar estudiante existente

1. Abrir estudiante con contacto ya creado
2. Cambiar fecha de nacimiento, género, dirección
3. Clic en "Sincronizar a Contacto"
4. ✅ Verificar que `res.partner` se actualizó correctamente

### Test 4: Estudiante sin tipo de documento

1. Crear estudiante sin seleccionar tipo de documento
2. Poner fecha de nacimiento de 15 años
3. Crear acceso al portal
4. ✅ Verificar que se asignó automáticamente "Tarjeta de Identidad"

---

## 🔧 Archivos Modificados

```
benglish_academy/
├── models/
│   └── student.py
│       ├── _create_single_portal_user()    [MODIFICADO]
│       ├── create()                        [MODIFICADO]
│       └── action_sync_to_partner()        [NUEVO]
└── views/
    └── student_views.xml
        ├── Campo id_type_id                [AGREGADO]
        └── Botón "Sincronizar a Contacto"  [AGREGADO]
```

---

## ✅ Resultado Final

### Antes

- ❌ Tipo de documento se calculaba solo por edad (no era seleccionable)
- ❌ Fecha de nacimiento NO se copiaba al contacto
- ❌ Género NO se copiaba al contacto
- ❌ Campo `ref` no se llenaba

### Después

- ✅ **Tipo de documento seleccionable** en el formulario del estudiante
- ✅ **Prioridad al tipo seleccionado**, fallback a cálculo por edad
- ✅ **Fecha de nacimiento sincronizada** (`fecha_nacimiento` en OX)
- ✅ **Género sincronizado** con mapeo correcto (`genero` en OX)
- ✅ **Campo `ref` llenado** con el documento de identidad
- ✅ **Sincronización completa** en creación y portal
- ✅ **Botón manual** para actualizar contactos existentes

---

## 📝 Notas Finales

1. **No se crearon campos nuevos** - solo se usaron los existentes
2. **No se modificaron catálogos** - se reutilizó `l10n_latam.identification.type`
3. **No se cambiaron validaciones existentes** - solo se completó el mapeo
4. **Compatibilidad total** con módulo OX y estructura actual de Benglish Academy
5. **Reversible** - si hay problemas, solo revertir los cambios en estos archivos

---

**Fecha de implementación:** Enero 2026  
**Desarrollador:** GitHub Copilot  
**Revisión:** Pendiente por usuario
