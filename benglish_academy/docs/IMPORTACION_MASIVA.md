# Importación Masiva de Estudiantes y Matrículas

Yo desarrolle el modulo Benglish Academy y documente este archivo para su operacion en produccion.


## 📋 Descripción

Este módulo implementa un sistema de importación masiva de estudiantes y matrículas desde archivos Excel siguiendo una especificación técnica detallada.

## 🎯 Características Principales

- ✅ Importación desde Excel con validación de columnas
- ✅ Creación/actualización de estudiantes por código único
- ✅ Generación de matrículas coherentes con el modelo académico
- ✅ Asignación automática de programa según categoría
- ✅ Normalización automática de planes (ej: GOLD → PLAN GOLD)
- ✅ Asistencia histórica según niveles completados
- ✅ Procesamiento de congelamientos
- ✅ Aplicación de estados académicos finales
- ✅ Log detallado de importación con éxitos/errores

## 📊 Columnas del Excel

El archivo Excel **debe** tener exactamente estas columnas (orden no importa):

1. **CÓDIGO USUARIO** - Identificador único del estudiante
2. **PRIMER NOMBRE**
3. **SEGUNDO NOMBRE** (opcional)
4. **PRIMER APELLIDO**
5. **SEGUNDO APELLIDO** (opcional)
6. **EMAIL**
7. **DOCUMENTO** - Número de identificación
8. **CATEGORÍA** - B teens o ADULTOS
9. **PLAN** - GOLD, PLUS, PREMIUM, SUPREME, etc.
10. **SEDE** - Nombre de la sede principal (se asigna ciudad y país automáticamente)
11. **F. INICIO CURSO** - Fecha de inicio (DD/MM/YYYY)
12. **DÍAS CONG.** - Días de congelamiento (número o vacío)
13. **FECHA FIN CURSO MÁS CONG.** - Fecha fin real
14. **FASE** - BASIC, INTERMEDIATE o ADVANCED
15. **NIVEL** - Formato "1 - 2", "11 - 12", etc. (se asigna fase y nivel en matrícula)
16. **ESTADO** - ACTIVO, SUSPENDIDO, FINALIZADO, N/A
17. **CONTACTO TÍTULAR** - Teléfono/Celular del estudiante
18. **FECHA NAC.** - Fecha nacimiento (DD/MM/YYYY)

## 🔄 Proceso de Importación

### 0. Normalización de Datos

#### Documento de Identidad
- Se eliminan automáticamente los `.0` que genera Excel en celdas numéricas
- Se eliminan espacios, guiones y puntos
- **Se conservan ceros a la izquierda** (ej: `0012345` se mantiene)
- Ejemplo: `12345678.0` → `12345678`

#### Celular/Teléfono
- Se eliminan espacios, guiones, paréntesis
- Se conserva el prefijo `+` si existe (ej: `+57`)
- Longitud mínima: 7 dígitos
- Ejemplo: `(+57) 300-123-4567` → `+573001234567`

#### Sede Principal y Ciudad
- La sede se busca por nombre (case-insensitive)
- **La ciudad se asigna automáticamente desde la sede**
- **El país por defecto es Colombia**
- Si la sede no existe, se registra advertencia pero NO bloquea la importación

### 1. Filtrado por Categoría (CRÍTICO)

Solo se importan registros con categoría:

- **B teens** → Programa: B teens
- **ADULTOS** → Programa: Benglish

⛔ Cualquier otro valor se omite (no genera error).

### 2. Normalización de Plan

El sistema agrega automáticamente el prefijo "PLAN":

- Excel: `GOLD` → Sistema: `PLAN GOLD`
- Excel: `PLUS` → Sistema: `PLAN PLUS`
- Excel: `PREMIUM` → Sistema: `PLAN PREMIUM`

⚠️ Si el plan no existe en el sistema → Se omite la fila (registra en log)

### 3. Asignación de Fase y Nivel

**Fase:**
- Valores permitidos: BASIC, INTERMEDIATE, ADVANCED
- Se asigna en `enrollment.current_phase_id`
- Si la fase no existe o no es válida → se registra advertencia y continúa

**Nivel:**
- Del campo NIVEL se extrae el **número mayor**: `"11 - 12"` → 12
- Se busca el nivel dentro de la fase que contiene esa unidad
- Se asigna en `enrollment.current_level_id`
- El estudiante hereda fase y nivel de la matrícula activa (campos computados)

### 4. Procesamiento de Niveles y Asistencia Histórica

Del campo NIVEL se extrae el **número mayor**:

- `"1 - 2"` → última unidad asistida = 2
- `"11 - 12"` → última unidad asistida = 12
- `"23 - 24"` → última unidad asistida = 24

El sistema marca automáticamente:

- Unidades con `sequence ≤ número_extraído` → **Asistidas**
- Unidades con `sequence > número_extraído` → **Pendientes**

### 5. Estados Académicos

| Excel      | Estado Estudiante | Estado Matrícula | Lógica                       |
| ---------- | ----------------- | ---------------- | ---------------------------- |
| ACTIVO     | active            | enrolled         | Matrícula normal             |
| SUSPENDIDO | inactive          | frozen           | Bloqueado                    |
| FINALIZADO | graduated         | completed        | Todas las unidades asistidas |
| N/A        | inactive          | frozen           | Sin agenda                   |
| (vacío)    | inactive          | frozen           | Sin agenda                   |

**Caso Especial:** Si estado es **FINALIZADO**, se marcan **TODAS** las unidades como completadas, independientemente del campo NIVEL.

### 6. Congelamientos

Si `DÍAS CONG. > 0`:

- Se crea un registro de congelamiento
- Estado: Aprobado (es histórico)
- Fecha inicio: F. INICIO CURSO
- Fecha fin: inicio + días de congelamiento

## 🚀 Uso

### Desde la Interfaz

1. Ir a: **Gestión Académica → Matrícula → Importación Masiva**
2. Cargar archivo Excel (.xlsx)
3. Configurar opciones:
   - ✅ **Actualizar Existentes**: Actualiza datos de estudiantes que ya existen
   - ✅ **Omitir Errores**: Continúa aunque haya errores en algunas filas
4. Clic en **Importar**
5. RCÓDIGO USUARIO vacío

### Advertencias (se registran pero no bloquean)

- ⚠️ Plan no existe (se omite la fila)
- ⚠️ Fase inválida (se registra y continúa sin fase)
- ⚠️ Sede no encontrada (no se asigna sede principal)
- ⚠️ Fecha de nacimiento inválida (no se asigna)
- ⚠️ Teléfono inválido (no se asigna)
- ⚠️ Documento duplicado (permitido)
- ⚠️ Email duplicado (permitido)
- ⚠️ Email inválido (se omite pero continúaa importación)

- ❌ Plan no existe en el sistema
- ❌ Fase inválida (no es BASIC, INTERMEDIATE o ADVANCED)
- ❌ NIVEL no contiene números parseables
- ❌ CÓDIGO USUARIO vacío

### Advertencias (se registran pero no bloquean)

- ⚠️ Sede no encontrada (no se asigna preferencia)
- ⚠️ Fecha de nacimiento inválida (no se asigna)
- ⚠️ Teléfono inválido (no se asigna)
- ⚠️ Email duplicado (permitido)
- ⚠️ Documento duplicado (permitido)

## 📊 Estadísticas de Importación

Al finalizar, se muestran:

- **Total Filas**: Registros procesados
- **Importados Exitosamente**: Estudiantes creados/actualizados
- **Errores**: Filas con errores
- **Omitidos**: Filas con categoría no permitida

## 🔍 Log Detallado

Cada fila procesada genera una entrada de log con:

- Número de fila
- Código de estudiante
- Tipo: Éxito (verde), Error (rojo), Info (gris)
- Mensaje descriptivo

## ⚙️ Configuración Técnica

### Modelos Creados

- `benglish.student.enrollment.import.wizard` - Wizard principal
- `benglish.student.enrollment.import.log` - Log de importación

### Archivos

```
wizards/
  └── student_enrollment_import_wizard.py

views/
  └── student_enrollment_import_wizard_views.xml

security/
  └── ir.model.access.csv (permisos agregados)
```

### Dependencias

- Python: `openpyxl` (para lectura de Excel)
- Odoo: versión 18.0

## 🐛 Troubleshooting

### Error: "openpyxl no está instalado"

Solución:

```bash
pip install openpyxl
```

### Error: "Plan 'GOLD' no existe"

Verificar que en el sistema exista un plan llamado exactamente: `PLAN GOLD`

### Categoría omitida silenciosamente

Revisar que la categoría sea exactamente `B teens` o `ADULTOS` (case-insensitive)

### Fechas no se importan

Formatos soportados:

- DD/MM/YYYY
- DD-MM-YYYY
- YYYY-MM-DD
- DD/MM/YY
- DD-MM-YY

## 📈 Mejoras Futuras

- [ ] Validación previa sin importar (modo dry-run)
- [ ] Importación asíncrona para archivos grandes
- [ ] Exportación de plantilla Excel vacía
- [ ] Mapeo flexible de columnas
- [ ] Importación de notas y asistencia detallada

## 📞 Soporte

Para reportar problemas o solicitar mejoras, contactar al equipo de desarrollo de Ailumex.

---

**Versión:** 1.0.0  
**Última actualización:** Enero 2026  
**Módulo:** benglish_academy
