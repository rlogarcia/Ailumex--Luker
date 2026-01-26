# 📋 PLANTILLA EXCEL - IMPORTACIÓN DE ESTUDIANTES

Yo desarrolle el modulo Benglish Academy y documente este archivo para su operacion en produccion.


## 📥 COLUMNAS SOPORTADAS

### ✅ OBLIGATORIAS

| Columna               | Tipo  | Descripción                           | Ejemplo                |
| --------------------- | ----- | ------------------------------------- | ---------------------- |
| `documento_identidad` | Texto | Documento de identidad del estudiante | `1234567890`           |
| `primer_nombre`       | Texto | Primer nombre                         | `Juan`                 |
| `primer_apellido`     | Texto | Primer apellido                       | `Pérez`                |
| `email`               | Email | Correo electrónico principal          | `juan.perez@email.com` |
| `telefono`            | Texto | Teléfono principal                    | `3001234567`           |

### 📝 OPCIONALES - DATOS PERSONALES

| Columna            | Tipo  | Descripción                      | Ejemplo                     |
| ------------------ | ----- | -------------------------------- | --------------------------- |
| `segundo_nombre`   | Texto | Segundo nombre (opcional)        | `Carlos`                    |
| `segundo_apellido` | Texto | Segundo apellido (opcional)      | `García`                    |
| `celular`          | Texto | Número de celular                | `3009876543`                |
| `fecha_nacimiento` | Fecha | Fecha de nacimiento              | `1995-03-15` o `15/03/1995` |
| `genero`           | Texto | Género (Masculino/Femenino/Otro) | `Masculino` o `M`           |
| `codigo`           | Texto | Código de estudiante (si existe) | `EST-2025-001`              |

### 🏠 OPCIONALES - DIRECCIÓN

| Columna     | Tipo  | Descripción             | Ejemplo             |
| ----------- | ----- | ----------------------- | ------------------- |
| `direccion` | Texto | Dirección de residencia | `Calle 123 # 45-67` |
| `ciudad`    | Texto | Ciudad de residencia    | `Bogotá`            |
| `pais`      | Texto | País de residencia      | `Colombia` o `CO`   |

### 🎓 OPCIONALES - ACADÉMICO

| Columna     | Tipo  | Descripción                                      | Ejemplo          |
| ----------- | ----- | ------------------------------------------------ | ---------------- |
| `programa`  | Texto | Nombre del programa académico                    | `Inglés General` |
| `plan`      | Texto | Nombre del plan de estudio                       | `Plan 2025`      |
| `fase`      | Texto | Nombre de la fase académica                      | `Básico`         |
| `nivel`     | Texto | Nombre del nivel                                 | `A1`             |
| `sede`      | Texto | Nombre de la sede principal                      | `Sede Centro`    |
| `modalidad` | Texto | Modalidad preferida (Presencial/Virtual/Híbrido) | `Presencial`     |

### 📝 OPCIONALES - CONTRATO ACADÉMICO

| Columna                      | Tipo   | Descripción                     | Ejemplo                         |
| ---------------------------- | ------ | ------------------------------- | ------------------------------- |
| `categoria`                  | Texto  | Categoría académica o comercial | `Regular` / `Intensivo` / `VIP` |
| `fecha_inicio_curso`         | Fecha  | Fecha de inicio del curso       | `2025-02-01`                    |
| `fecha_fin_curso`            | Fecha  | Fecha de fin del curso          | `2025-06-30`                    |
| `fecha_maxima_congelamiento` | Fecha  | Fecha límite para congelar      | `2025-05-15`                    |
| `dias_curso`                 | Número | Duración del curso en días      | `150`                           |

### 👥 OPCIONALES - TITULAR

| Columna            | Tipo  | Descripción                             | Ejemplo        |
| ------------------ | ----- | --------------------------------------- | -------------- |
| `contacto_titular` | Texto | Nombre completo del titular/responsable | `María García` |

### 🔄 OPCIONALES - ESTADO

| Columna            | Tipo  | Descripción           | Ejemplo                  |
| ------------------ | ----- | --------------------- | ------------------------ |
| `estado_academico` | Texto | Estado del estudiante | `Activo` / `Matriculado` |

---

## 📌 ALIASES DE COLUMNAS SOPORTADOS

El sistema reconoce múltiples variantes de nombres de columna:

### Documento de Identidad

- `documento_identidad`, `documento`, `documentoidentidad`, `id`, `identificacion`

### Nombres

- **Primer Nombre:** `primer_nombre`, `primernombre`, `nombre1`
- **Segundo Nombre:** `segundo_nombre`, `segundonombre`, `nombre2`
- **Primer Apellido:** `primer_apellido`, `primerapellido`, `apellido1`
- **Segundo Apellido:** `segundo_apellido`, `segundoapellido`, `apellido2`
- **Legacy:** `nombres` → mapeará a `primer_nombre`, `apellidos` → mapeará a `primer_apellido`

### Contacto

- **Email:** `email`, `correo`, `correo_electronico`
- **Teléfono:** `telefono`, `telefono_principal`
- **Celular:** `celular`, `movil`

### Fechas

- **Nacimiento:** `fecha_nacimiento`, `nacimiento`
- **Inicio Curso:** `fecha_inicio_curso`, `fecha_inicio`
- **Fin Curso:** `fecha_fin_curso`, `fecha_fin`
- **Congelamiento:** `fecha_maxima_congelamiento`, `fecha_max_congelamiento`

### Género

- `genero`, `sexo`
- **Valores aceptados:** `Masculino`/`M`/`male`, `Femenino`/`F`/`female`, `Otro`/`O`/`other`

### Estado Académico

- `estado_academico`, `estado`
- **Valores:** `Prospecto`, `Matriculado`, `Activo`, `Inactivo`, `Graduado`, `Retirado`

---

## 🎯 EJEMPLO DE EXCEL

| documento_identidad | primer_nombre | segundo_nombre | primer_apellido | segundo_apellido | email                | telefono   | celular    | fecha_nacimiento | genero    | ciudad   | pais     | programa       | plan      | fase   | nivel | sede        | modalidad  | categoria | fecha_inicio_curso | fecha_fin_curso | dias_curso | contacto_titular | estado_academico |
| ------------------- | ------------- | -------------- | --------------- | ---------------- | -------------------- | ---------- | ---------- | ---------------- | --------- | -------- | -------- | -------------- | --------- | ------ | ----- | ----------- | ---------- | --------- | ------------------ | --------------- | ---------- | ---------------- | ---------------- |
| 1234567890          | Juan          | Carlos         | Pérez           | García           | juan.perez@email.com | 3001234567 | 3009876543 | 1995-03-15       | Masculino | Bogotá   | Colombia | Inglés General | Plan 2025 | Básico | A1    | Sede Centro | Presencial | Regular   | 2025-02-01         | 2025-06-30      | 150        | María García     | Activo           |
| 9876543210          | Ana           | María          | López           |                  | ana.lopez@email.com  | 3112223333 |            | 1998-07-22       | Femenino  | Medellín | CO       | Inglés General | Plan 2025 | Básico | A1    | Sede Norte  | Virtual    | Intensivo | 2025-02-01         | 2025-05-15      | 105        | Pedro López      | Matriculado      |

---

## 📝 FORMATOS DE FECHA SOPORTADOS

El sistema acepta múltiples formatos de fecha:

- `YYYY-MM-DD` → `2025-02-01`
- `DD/MM/YYYY` → `01/02/2025`
- `DD-MM-YYYY` → `01-02-2025`

---

## ⚠️ VALIDACIONES IMPORTANTES

### ❌ Errores (bloquean la importación):

- Documento de identidad vacío
- Primer nombre vacío
- Primer apellido vacío
- Email vacío o inválido
- Teléfono vacío
- Fechas en formato inválido

### ⚠️ Advertencias (permiten importación):

- Programa no encontrado o ambiguo
- Plan no encontrado o ambiguo
- Fase no encontrada
- Nivel no encontrado
- Sede no encontrada
- País no encontrado
- Fechas del curso inválidas
- Estado académico inválido

---

## 🔄 PROCESO DE IMPORTACIÓN

1. **Subir archivo Excel** (.xlsx)
2. **Validación automática** de columnas y datos
3. **Revisión de errores/advertencias**
4. **Decisión de duplicados** (crear/actualizar/ignorar)
5. **Importación final**
6. **Reporte de resultados**

---

## 💡 CONSEJOS

✅ **Usa la primera fila para encabezados** (nombres de columna)  
✅ **No dejes filas vacías** entre datos  
✅ **Revisa duplicados** antes de importar  
✅ **Verifica que programas/planes/sedes existan** en el sistema  
✅ **Usa formatos de fecha consistentes**  
✅ **Evita caracteres especiales** en documentos de identidad

---

## 📞 SOPORTE

Para problemas con la importación, contactar al administrador del sistema con:

- Archivo Excel original
- Reporte de errores generado
- Captura de pantalla del problema

---

**FIN DEL DOCUMENTO**
