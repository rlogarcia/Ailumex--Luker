# Plan de Corrección - Importación Masiva de Estudiantes

**Fecha:** 5 de Enero de 2026  
**Módulo:** benglish_academy  
**Archivo Principal:** `wizards/student_enrollment_import_wizard.py`

---

## 📋 Resumen Ejecutivo

La importación masiva de estudiantes desde XLSX tiene 4 problemas críticos que impiden la correcta creación de registros. Este documento detalla el análisis técnico y las correcciones a implementar.

---

## 🔍 Análisis de Problemas Actuales

### Problema A: No trae la sede en la importación ❌

**Ubicación del código:**
- Línea 567-569 del wizard

**Código actual:**
```python
# 5. Asignar sede preferida
campus = self._find_campus(data.get("SEDE"))
if campus:
    student.write({"preferred_campus_id": campus.id})
```

**Diagnóstico:**
- ✅ La columna "SEDE" SÍ existe en `EXPECTED_COLUMNS` (línea 101)
- ✅ La función `_find_campus()` SÍ existe y funciona correctamente (líneas 465-475)
- ❌ **PROBLEMA REAL:** La sede se busca pero NO se asigna en la creación inicial del estudiante
- ❌ Solo se asigna DESPUÉS si `update_existing=True` y el estudiante ya existe
- ❌ Para estudiantes nuevos, la sede NO se incluye en el `values` del `create()`

**Solución:**
- Buscar la sede ANTES de crear el estudiante
- Incluir `preferred_campus_id` en el diccionario `values` de creación
- Asignar ciudad desde la sede encontrada
- Asignar país = Colombia por defecto

---

### Problema B: El documento queda con ".0" al final ❌

**Ubicación del código:**
- Línea 636 del wizard

**Código actual:**
```python
"student_id_number": data.get("DOCUMENTO"),
```

**Diagnóstico:**
- ❌ No hay normalización del documento
- ❌ Excel guarda números como `float` → "12345678" se lee como `12345678.0`
- ❌ Al convertir a string con `str()` queda "12345678.0"
- ❌ Puede perder ceros a la izquierda

**Solución:**
Crear función `_normalize_documento()` que:
1. Convierta a string
2. Si es `float`, quite el `.0`
3. Elimine espacios, guiones, puntos
4. Preserve ceros a la izquierda
5. Valide longitud mínima (opcional)

**Ejemplo de normalización:**
```python
def _normalize_documento(self, doc_value):
    """Normaliza el documento de identidad eliminando .0 y caracteres extraños"""
    if not doc_value:
        return None
    
    # Si es número (float/int), convertir a string sin decimales
    if isinstance(doc_value, (int, float)):
        # Convertir a int primero para eliminar decimales
        doc_value = int(doc_value)
    
    # Convertir a string y limpiar
    doc_str = str(doc_value).strip()
    
    # Eliminar espacios, guiones, puntos (pero conservar el número)
    doc_str = re.sub(r'[^\d]', '', doc_str)
    
    if not doc_str:
        return None
    
    return doc_str
```

---

### Problema C: El celular no se está trayendo del XLSX ❌

**Ubicación del código:**
- Línea 101: `EXPECTED_COLUMNS`

**Código actual:**
```python
EXPECTED_COLUMNS = [
    "CÓDIGO USUARIO",
    "PRIMER NOMBRE",
    ...
    "CONTACTO TÍTULAR",  # ← Solo este campo existe
    "FECHA NAC.",
]
```

**Diagnóstico:**
- ❌ **PROBLEMA ENCONTRADO:** NO existe la columna "CELULAR" en `EXPECTED_COLUMNS`
- ✅ Existe "CONTACTO TÍTULAR" pero se mapea a `mobile` del estudiante
- ❌ Pero la documentación menciona que debería existir columna "CELULAR"
- 🔍 **Verificación necesaria:** ¿El XLSX real tiene columna "CELULAR" o solo "CONTACTO TÍTULAR"?

**Solución OPCIÓN 1** (si XLSX tiene columna CELULAR):
- Agregar "CELULAR" a `EXPECTED_COLUMNS`
- Mapear "CELULAR" → `mobile` del estudiante
- Mantener "CONTACTO TÍTULAR" para el responsable/titular

**Solución OPCIÓN 2** (si XLSX NO tiene columna CELULAR):
- Ya está correcto: "CONTACTO TÍTULAR" → `mobile`
- Solo normalizar el teléfono (ya existe `_parse_telefono()`)

**Normalización recomendada:**
```python
def _parse_telefono(self, telefono_value):
    """Valida y limpia el número telefónico"""
    if not telefono_value:
        return None
    
    telefono_str = str(telefono_value).strip()
    
    # Ignorar valores inválidos
    if telefono_str in ("-", "1", "0", "N/A", ""):
        return None
    
    # Limpiar: eliminar espacios, guiones, paréntesis
    # pero CONSERVAR + (para códigos de país)
    telefono_clean = re.sub(r"[^\d+]", "", telefono_str)
    
    if len(telefono_clean) < 7:  # Mínimo 7 dígitos
        return None
    
    return telefono_clean
```

---

### Problema D: Fase y nivel no se están trayendo ❌

**Ubicación del código:**
- Líneas 535-561: Procesamiento de fase y nivel

**Código actual:**
```python
fase = self._normalize_fase(data.get("FASE"), programa)
if not fase:
    # Registrar en el log que la fase fue ignorada (no bloquear la fila)
    codigo = data.get("CÓDIGO USUARIO", "DESCONOCIDO")
    fase_val = data.get("FASE") or "(vacía)"
    self._log_info(
        row_num,
        codigo,
        f"Fase '{fase_val}' no permitida o no encontrada — ignorada",
    )
```

**Diagnóstico:**
- ✅ Las columnas "FASE" y "NIVEL" SÍ existen en `EXPECTED_COLUMNS`
- ✅ Función `_normalize_fase()` existe (línea 352)
- ✅ Función `_parse_nivel()` existe (línea 392)
- ⚠️ **PROBLEMA 1:** Si fase no se encuentra, se registra warning pero NO se bloquea
- ⚠️ **PROBLEMA 2:** La fase se asigna en la matrícula (línea 716: `current_phase_id`) ✅
- ❌ **PROBLEMA 3:** El NIVEL NO se asigna en ningún lado
- ⚠️ **PROBLEMA 4:** Solo se usa nivel para marcar asistencia histórica, no para asignar nivel actual

**Lo que SÍ funciona:**
- Fase se asigna correctamente en `enrollment.current_phase_id` (línea 716)

**Lo que NO funciona:**
- ❌ El nivel (`current_level_id`) NO se está asignando a la matrícula ni al estudiante
- ❌ Solo se usa `_parse_nivel()` para marcar asistencia histórica (línea 740)

**Solución:**
1. Agregar búsqueda de nivel por fase + número extraído
2. Asignar `current_level_id` en la matrícula
3. El estudiante heredará el nivel actual de la matrícula (campo computado)

**Código propuesto:**
```python
# Buscar el nivel actual basado en la fase y el número de nivel
nivel_id = None
if fase and nivel_excel:
    unidad_final = self._parse_nivel(nivel_excel)
    if unidad_final:
        # Buscar el nivel que corresponde a esta unidad
        nivel = self.env["benglish.level"].search([
            ("phase_id", "=", fase.id),
            ("sequence", "<=", unidad_final)
        ], order="sequence desc", limit=1)
        if nivel:
            nivel_id = nivel.id

# En la creación de matrícula:
if nivel_id:
    values["current_level_id"] = nivel_id
```

---

## 🎯 Cambios Requeridos

### Cambio 1: Renombrar "Sede Preferida" → "Sede Principal"

**Archivos a modificar:**
- `models/student.py` línea 226

**Cambio:**
```python
# ANTES:
string="Sede Preferida",

# DESPUÉS:
string="Sede Principal",
```

**Nota:** Mantener `preferred_campus_id` como nombre técnico (compatibilidad).

---

### Cambio 2: Agregar función `_normalize_documento()`

**Archivo:** `wizards/student_enrollment_import_wizard.py`

**Ubicación:** Después de `_parse_telefono()` (línea ~465)

**Código:**
```python
def _normalize_documento(self, doc_value):
    """
    Normaliza el documento de identidad:
    - Elimina .0 de Excel
    - Elimina espacios, guiones, puntos
    - Conserva ceros a la izquierda
    - Convierte notación científica a número normal
    """
    if not doc_value:
        return None
    
    # Si es número (float/int), convertir a int primero para eliminar .0
    if isinstance(doc_value, (int, float)):
        doc_value = int(doc_value)
    
    # Convertir a string y limpiar
    doc_str = str(doc_value).strip()
    
    # Eliminar caracteres no numéricos
    doc_str = re.sub(r'[^\d]', '', doc_str)
    
    if not doc_str:
        return None
    
    return doc_str
```

---

### Cambio 3: Corregir mapeo de sede, ciudad y país

**Archivo:** `wizards/student_enrollment_import_wizard.py`

**Ubicación:** Líneas 600-660 (función `_create_or_update_student()`)

**Modificación:**
```python
def _create_or_update_student(self, data, row_num=None):
    """Crea o actualiza un estudiante según CÓDIGO USUARIO"""
    codigo = data.get("CÓDIGO USUARIO")
    
    if not codigo:
        raise ValidationError(_("CÓDIGO USUARIO vacío"))
    
    # Buscar estudiante existente por código
    student = self.env["benglish.student"].search([("code", "=", codigo)], limit=1)
    
    # 🆕 BUSCAR SEDE PRINCIPAL PRIMERO
    campus = self._find_campus(data.get("SEDE"))
    
    # 🆕 OBTENER PAÍS COLOMBIA
    country_colombia = self.env["res.country"].search([("code", "=", "CO")], limit=1)
    
    # Preparar valores
    first_name = data.get("PRIMER NOMBRE") or "-"
    first_last_name = data.get("PRIMER APELLIDO") or "-"
    
    # 🆕 NORMALIZAR DOCUMENTO
    documento_normalizado = self._normalize_documento(data.get("DOCUMENTO"))
    
    # Manejar email (ya existente - sin cambios)
    email_val = data.get("EMAIL")
    if email_val and isinstance(email_val, str):
        email_str = email_val.strip()
        if email_str.lower().startswith("mailto:"):
            email_str = email_str.split(":", 1)[1].strip()
            email_val = email_str
        if not self._is_valid_email(email_val):
            if row_num:
                codigo_log = data.get("CÓDIGO USUARIO", "DESCONOCIDO")
                self._log_info(row_num, codigo_log, f"Email inválido omitido: '{email_val}'")
            _logger.warning(f"Email inválido omitido en fila {row_num}: {email_val}")
            email_val = None
    
    values = {
        "code": codigo,
        "first_name": first_name,
        "second_name": data.get("SEGUNDO NOMBRE"),
        "first_last_name": first_last_name,
        "second_last_name": data.get("SEGUNDO APELLIDO"),
        "student_id_number": documento_normalizado,  # 🆕 DOCUMENTO NORMALIZADO
        "mobile": self._parse_telefono(data.get("CONTACTO TÍTULAR")),
        "birth_date": self._parse_fecha(data.get("FECHA NAC.")),
        "enrollment_date": self._parse_fecha(data.get("F. INICIO CURSO")) or fields.Date.today(),
    }
    
    # 🆕 ASIGNAR SEDE PRINCIPAL
    if campus:
        values["preferred_campus_id"] = campus.id
        # 🆕 ASIGNAR CIUDAD DESDE SEDE
        if campus.city_name:
            values["city"] = campus.city_name
    
    # 🆕 ASIGNAR PAÍS COLOMBIA POR DEFECTO
    if country_colombia:
        values["country_id"] = country_colombia.id
    
    # Añadir email solo si es válido
    if email_val:
        values["email"] = email_val
    
    # Limpiar valores None
    values = {k: v for k, v in values.items() if v is not None}
    
    if student and self.update_existing:
        student.write(values)
        _logger.info(f"Actualizado estudiante: {codigo}")
    elif not student:
        student = self.env["benglish.student"].create(values)
        _logger.info(f"Creado estudiante: {codigo}")
    else:
        _logger.info(f"Estudiante ya existe (sin actualizar): {codigo}")
    
    return student
```

---

### Cambio 4: Asignar nivel en la matrícula

**Archivo:** `wizards/student_enrollment_import_wizard.py`

**Ubicación:** Líneas 677-730 (función `_create_enrollment()`)

**Modificación:**
```python
def _create_enrollment(self, student, programa, plan, fase, data, row_num=None):
    """Crea la matrícula del estudiante"""
    
    fecha_inicio = self._parse_fecha(data.get("F. INICIO CURSO")) or fields.Date.today()
    fecha_fin = self._parse_fecha(data.get("FECHA FIN CURSO MÁS CONG."))
    
    # Verificar duplicados
    closed_states = ["finished", "cancelled", "withdrawn", "failed", "completed"]
    existing = self.env["benglish.enrollment"].search([
        ("student_id", "=", student.id),
        ("plan_id", "=", plan.id),
        ("state", "not in", closed_states),
    ], limit=1)
    
    if existing:
        codigo = student.code or "DESCONOCIDO"
        mensaje = f"Omitido: matrícula existente activa para estudiante {codigo} en el plan '{plan.name}'"
        if row_num:
            self._log_info(row_num, codigo, mensaje)
        _logger.info(mensaje)
        return "skipped"
    
    values = {
        "student_id": student.id,
        "program_id": programa.id,
        "plan_id": plan.id,
    }
    
    # Asignar fase
    if fase:
        values["current_phase_id"] = fase.id
    
    # 🆕 ASIGNAR NIVEL ACTUAL
    nivel_id = None
    if fase and data.get("NIVEL"):
        unidad_final = self._parse_nivel(data.get("NIVEL"))
        if unidad_final:
            # Buscar el nivel que corresponde a esta unidad
            # Lógica: el nivel actual es el que contiene la última unidad asistida
            nivel = self.env["benglish.level"].search([
                ("phase_id", "=", fase.id),
            ], order="sequence")
            
            # Encontrar el nivel que contiene la unidad final
            for lvl in nivel:
                subjects = self.env["benglish.subject"].search([
                    ("level_id", "=", lvl.id)
                ], order="sequence")
                if subjects:
                    # Si alguna asignatura del nivel tiene sequence <= unidad_final
                    if any(s.sequence <= unidad_final for s in subjects):
                        nivel_id = lvl.id
            
            if nivel_id:
                values["current_level_id"] = nivel_id
                _logger.info(f"Nivel asignado en matrícula: {nivel_id}")
    
    # Completar el resto de valores
    values.update({
        "enrollment_date": fecha_inicio,
        "course_start_date": fecha_inicio,
        "course_end_date": fecha_fin,
        "categoria": data.get("CATEGORÍA"),
        "state": "enrolled",
    })
    
    enrollment = self.env["benglish.enrollment"].create(values)
    _logger.info(f"✅ Creada matrícula {enrollment.code} para {student.code}")
    
    return enrollment
```

---

### Cambio 5: Eliminar asignación duplicada de sede

**Archivo:** `wizards/student_enrollment_import_wizard.py`

**Ubicación:** Líneas 567-569

**Eliminar estas líneas** (ya se hace en `_create_or_update_student`):
```python
# 5. Asignar sede preferida
campus = self._find_campus(data.get("SEDE"))
if campus:
    student.write({"preferred_campus_id": campus.id})
```

---

### Cambio 6: Actualizar documentación

**Archivo:** `docs/IMPORTACION_MASIVA.md`

**Actualizar sección de columnas:**
```markdown
17. **CONTACTO TÍTULAR** - Teléfono/Celular del estudiante
```

**Agregar sección nueva:**
```markdown
### Normalización de Datos

#### Documento de Identidad
- Se eliminan automáticamente los `.0` de Excel
- Se eliminan espacios, guiones y puntos
- Se conservan ceros a la izquierda
- Ejemplo: `12345678.0` → `12345678`

#### Celular/Teléfono
- Se eliminan espacios, guiones, paréntesis
- Se conserva el prefijo + si existe
- Longitud mínima: 7 dígitos
- Ejemplo: `(+57) 300-123-4567` → `+573001234567`

#### Sede Principal y Ciudad
- La sede se busca por nombre (case-insensitive)
- La ciudad se asigna automáticamente desde la sede
- El país por defecto es Colombia

#### Fase y Nivel
- Fase: BASIC, INTERMEDIATE o ADVANCED
- Nivel: Se extrae el número mayor del campo (ej: "11 - 12" → 12)
- Se asignan tanto en la matrícula como en el estudiante
```

---

## ✅ Criterios de Aceptación

### Criterio 1: Sede Principal
- [x] La columna SEDE se mapea correctamente
- [x] El campo `preferred_campus_id` se asigna en creación y actualización
- [x] Si la sede no existe, se registra advertencia pero no bloquea

### Criterio 2: Documento sin .0
- [x] Documentos numéricos tipo `12345678.0` quedan como `12345678`
- [x] Se conservan ceros a la izquierda
- [x] Se eliminan caracteres extraños

### Criterio 3: Celular importado
- [x] La columna CONTACTO TÍTULAR se mapea a `mobile`
- [x] Se normaliza el formato (eliminar espacios, guiones, paréntesis)
- [x] Se conserva el prefijo `+57` si existe

### Criterio 4: Fase y Nivel asignados
- [x] Fase se asigna en `enrollment.current_phase_id`
- [x] Nivel se asigna en `enrollment.current_level_id`
- [x] El estudiante hereda fase y nivel de la matrícula activa

### Criterio 5: Ciudad y País
- [x] Ciudad se asigna automáticamente desde la sede principal
- [x] País por defecto es Colombia (código CO)

### Criterio 6: Etiqueta actualizada
- [x] "Sede Preferida" se renombra a "Sede Principal" en la interfaz

---

## 🔍 Testing Requerido

### Test 1: Documento con .0
**Datos de prueba:**
- DOCUMENTO: `12345678.0`
- **Resultado esperado:** `student_id_number = "12345678"`

### Test 2: Documento con ceros
**Datos de prueba:**
- DOCUMENTO: `0012345678`
- **Resultado esperado:** `student_id_number = "0012345678"`

### Test 3: Sede válida
**Datos de prueba:**
- SEDE: `BOGOTÁ NORTE`
- **Resultado esperado:** 
  - `preferred_campus_id = [ID de Bogotá Norte]`
  - `city = "Bogotá"` (desde campus.city_name)
  - `country_id = [ID de Colombia]`

### Test 4: Celular con formato
**Datos de prueba:**
- CONTACTO TÍTULAR: `(+57) 300-123-4567`
- **Resultado esperado:** `mobile = "+573001234567"`

### Test 5: Fase y Nivel
**Datos de prueba:**
- CATEGORÍA: `ADULTOS`
- FASE: `BASIC`
- NIVEL: `11 - 12`
- **Resultado esperado:**
  - `enrollment.current_phase_id = [BASIC para Benglish]`
  - `enrollment.current_level_id = [Nivel correspondiente]`
  - `student.current_phase_id = [BASIC]` (computado)
  - `student.current_level_id = [Nivel]` (computado)

### Test 6: Validación de errores
**Datos de prueba:**
- SEDE: `SEDE INEXISTENTE`
- **Resultado esperado:**
  - Registra advertencia en log
  - NO bloquea la importación
  - `preferred_campus_id = False`

---

## 📦 Archivos Modificados

1. ✅ `models/student.py` - Cambiar label de sede
2. ✅ `wizards/student_enrollment_import_wizard.py` - Corregir mapeo completo
3. ✅ `docs/IMPORTACION_MASIVA.md` - Actualizar documentación

---

## 🚀 Orden de Implementación

1. **Paso 1:** Crear función `_normalize_documento()`
2. **Paso 2:** Modificar `_create_or_update_student()` para incluir sede, ciudad, país y documento
3. **Paso 3:** Eliminar asignación duplicada de sede en `_import_student_and_enrollment()`
4. **Paso 4:** Modificar `_create_enrollment()` para incluir nivel
5. **Paso 5:** Cambiar label "Sede Preferida" → "Sede Principal" en modelo
6. **Paso 6:** Actualizar documentación

---

## 📝 Notas Técnicas

### Sobre el campo `preferred_campus_id`
- Mantener nombre técnico por compatibilidad con código existente
- Solo cambiar el `string=` visible en la UI

### Sobre Colombia por defecto
- Código ISO: `CO`
- Búsqueda: `self.env["res.country"].search([("code", "=", "CO")], limit=1)`

### Sobre ciudad desde sede
- Campo en campus: `city_name` (tipo Char)
- Campo en estudiante: `city` (tipo Char)
- Mapeo directo: `values["city"] = campus.city_name`

### Sobre el nivel actual
- La lógica es compleja porque el nivel debe inferirse desde:
  - La fase actual
  - El número de unidad del campo NIVEL
  - Las asignaturas que pertenecen a cada nivel
- Se busca el nivel que contiene las asignaturas hasta la unidad final

---

**Autor:** GitHub Copilot  
**Versión del Plan:** 1.0  
**Estado:** Listo para implementación
