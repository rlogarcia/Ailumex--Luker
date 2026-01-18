# 📦 Sistema de Importación Masiva de Estudiantes y Matrículas

## 🎯 Resumen Ejecutivo

Se ha implementado un sistema completo de importación masiva de estudiantes y matrículas desde Excel, siguiendo una especificación técnica detallada que garantiza coherencia total con el modelo académico de Benglish.

## ✨ Características Implementadas

### 1. ✅ Validación y Filtrado Automático

- **Filtro por categoría**: Solo importa "B teens" y "ADULTOS"
- **Normalización automática**:
  - Categoría → Programa (ADULTOS → Benglish, B teens → B teens)
  - Plan con prefijo (GOLD → PLAN GOLD)
  - Fase (case-insensitive)
- **Validaciones bloqueantes**: Plan inexistente, fase inválida, nivel no parseable

### 2. ✅ Gestión Inteligente de Estudiantes

- **Búsqueda por código único**: CÓDIGO USUARIO es el identificador maestro
- **Creación o actualización**: Modo configurable
- **Campos desagregados**: Nombres y apellidos separados
- **Datos opcionales**: Email, documento, teléfono, fecha nacimiento
- **Manejo de duplicados**: Emails y documentos pueden repetirse

### 3. ✅ Matrículas Coherentes

- **Modelo correcto**: Matrícula al PLAN completo (no a asignatura individual)
- **Jerarquía académica**: Programa → Plan → Fase
- **Fechas**: Inicio, fin real, fin con congelamiento
- **Estado inicial**: enrolled

### 4. ✅ Asistencia Histórica Automática

- **Parseo inteligente de NIVEL**: Extrae el número mayor ("11 - 12" → 12)
- **Marcado automático**:
  - Unidades ≤ nivel → attended = True, state = in_progress/registered
  - Unidades > nivel → attended = False, state = pending
- **Caso especial FINALIZADO**: Marca TODAS las unidades como completadas

### 5. ✅ Congelamientos

- **Procesamiento automático**: Si DÍAS CONG. > 0
- **Estado histórico**: Congelamientos ya aprobados
- **Fechas coherentes**: Basadas en inicio y días
- **Ajuste de contadores**: Días usados y disponibles

### 6. ✅ Estados Académicos Finales

| Excel      | Estudiante | Matrícula | Efecto     |
| ---------- | ---------- | --------- | ---------- |
| ACTIVO     | active     | enrolled  | Normal     |
| SUSPENDIDO | inactive   | frozen    | Bloqueado  |
| FINALIZADO | graduated  | completed | Graduado   |
| N/A        | inactive   | frozen    | Sin agenda |

### 7. ✅ Logging y Trazabilidad

- **Log detallado por fila**: Éxito (verde), Error (rojo), Info (gris)
- **Estadísticas completas**: Total, éxitos, errores, omitidos
- **Modo tolerante a errores**: Configurable

## 📁 Archivos Creados

```
benglish_academy/
├── wizards/
│   └── student_enrollment_import_wizard.py  (661 líneas)
├── views/
│   └── student_enrollment_import_wizard_views.xml  (150 líneas)
├── docs/
│   ├── IMPORTACION_MASIVA.md  (Documentación completa)
│   └── PLANTILLA_IMPORTACION.md  (Guía de plantilla Excel)
├── scripts/
│   └── validate_import_wizard.py  (Script de validación)
├── security/
│   └── ir.model.access.csv  (Permisos agregados)
└── __manifest__.py  (Vista agregada)
```

## 🔐 Seguridad

**Grupos con acceso:**

- Coordinador Académico (`group_academic_coordinator`)
- Gerente Académico (`group_academic_manager`)

**Modelos protegidos:**

- `benglish.student.enrollment.import.wizard` (CRUD completo)
- `benglish.student.enrollment.import.log` (CRUD completo)

## 🚀 Uso

### Interfaz de Usuario

1. **Menú**: Gestión Académica → Matrícula → **Importación Masiva**
2. **Cargar Excel** (.xlsx)
3. **Configurar opciones**:
   - ☑️ Actualizar existentes
   - ☑️ Omitir errores
4. **Clic en Importar**
5. **Revisar resultados**

### Configuración Recomendada

- ✅ **Actualizar existentes**: ON (para reimportaciones)
- ✅ **Omitir errores**: ON (para archivos grandes)

## 📊 Columnas del Excel

18 columnas requeridas (orden no importa):

```
CÓDIGO USUARIO | PRIMER NOMBRE | SEGUNDO NOMBRE | PRIMER APELLIDO |
SEGUNDO APELLIDO | EMAIL | DOCUMENTO | CATEGORÍA | PLAN | SEDE |
F. INICIO CURSO | DÍAS CONG. | FECHA FIN CURSO MÁS CONG. | FASE |
NIVEL | ESTADO | CONTACTO TÍTULAR | FECHA NAC.
```

## ⚙️ Especificación Técnica Cumplida

### ✅ Orden de Ejecución (NO NEGOCIABLE)

1. ✅ Validar categoría
2. ✅ Normalizar programa
3. ✅ Normalizar plan
4. ✅ Crear / actualizar estudiante
5. ✅ Asignar sede principal
6. ✅ Crear matrícula
7. ✅ Asignar fase
8. ✅ Procesar niveles → asistencia histórica
9. ✅ Procesar congelamientos
10. ✅ Aplicar estado académico final

### ✅ Normalización de Datos

- **Categoría → Programa**: Mapeo exacto
- **Plan**: Prefijo "PLAN " automático
- **Fase**: Case-insensitive, validación estricta
- **Nivel**: Regex para extraer números, tomar el mayor
- **Fechas**: Múltiples formatos soportados
- **Teléfono**: Validación básica, limpieza
- **Estado**: Mapeo con casos especiales (N/A, vacío)

### ✅ Casos Especiales Manejados

- 🔹 Emails duplicados → ✅ Permitido
- 🔹 Documentos duplicados → ✅ Permitido
- 🔹 Fecha nacimiento inválida → ⚠️ Warning, continúa
- 🔹 Teléfono inválido → ⚠️ Warning, continúa
- 🔹 Sede no existe → ⚠️ Warning, continúa
- 🔹 Plan no existe → ❌ Error bloqueante
- 🔹 Fase inválida → ❌ Error bloqueante
- 🔹 Estado FINALIZADO → 🎯 Todas las unidades completadas

## 🧪 Validación

Ejecutar script de validación:

```bash
cd d:/AiLumex/Ailumex--Be/benglish_academy
python scripts/validate_import_wizard.py
```

## 📚 Documentación Adicional

- **[IMPORTACION_MASIVA.md](docs/IMPORTACION_MASIVA.md)**: Documentación completa
- **[PLANTILLA_IMPORTACION.md](docs/PLANTILLA_IMPORTACION.md)**: Guía de plantilla Excel

## 🔄 Flujo de Datos

```
Excel (.xlsx)
    ↓
[Validar Columnas]
    ↓
[Filtrar Categorías] → Omitir no válidas
    ↓
[Por cada fila]
    ↓
[Normalizar Datos] → Programa, Plan, Fase, Nivel
    ↓
[Crear/Actualizar Estudiante] → Por CÓDIGO USUARIO
    ↓
[Crear Matrícula] → Programa + Plan + Fase
    ↓
[Asistencia Histórica] → Marcar unidades según NIVEL
    ↓
[Congelamientos] → Si DÍAS CONG. > 0
    ↓
[Estado Final] → ACTIVO, SUSPENDIDO, FINALIZADO, N/A
    ↓
[Log + Estadísticas]
```

## 🎯 Principios Rectores (Cumplidos)

1. ✅ **La matrícula manda**: Todo se registra en la matrícula, no en el estudiante
2. ✅ **Matrícula al plan completo**: No a asignaturas individuales
3. ✅ **CÓDIGO USUARIO es único**: Identificador maestro
4. ✅ **Asistencia histórica coherente**: Según niveles completados
5. ✅ **Estados académicos finales**: Aplicados al estudiante y matrícula
6. ✅ **Sin pasos faltantes**: Flujo completo implementado

## 📈 Resultados Esperados

Al importar un archivo Excel:

- **Estudiantes**: Creados o actualizados
- **Matrículas**: Generadas coherentemente
- **Progreso académico**: Registrado por asignatura
- **Congelamientos**: Procesados correctamente
- **Estados**: Aplicados según especificación
- **Log**: Detallado con éxitos/errores

**Resultado final**: 100% equivalente a una matrícula manual

## 🆘 Soporte

Para problemas o consultas:

- Revisar documentación: `docs/IMPORTACION_MASIVA.md`
- Validar plantilla: `docs/PLANTILLA_IMPORTACION.md`
- Contactar: Equipo de desarrollo Ailumex

---

**Versión**: 1.0.0  
**Fecha**: Enero 2026  
**Módulo**: benglish_academy  
**Odoo**: 18.0
