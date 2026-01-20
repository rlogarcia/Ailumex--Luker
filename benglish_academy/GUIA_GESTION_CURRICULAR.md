# 📚 Guía de Gestión Curricular desde Odoo

## 🎯 Objetivo

Este documento explica cómo gestionar el diseño curricular de Benglish Academy directamente desde la interfaz de Odoo, siguiendo buenas prácticas de desarrollo.

---

## ✅ Cambios Implementados

### 1. **Datos Editables** 
- ✅ Todos los archivos XML de datos ahora tienen `noupdate="0"`
- ✅ Esto permite actualizar registros existentes desde Odoo
- ✅ Los cambios en la interfaz se mantienen entre actualizaciones

### 2. **Vistas Habilitadas para Creación**
- ✅ Se eliminó `create="false"` de vistas de Niveles y Asignaturas
- ✅ Ahora puedes crear nuevos registros desde la interfaz
- ✅ Programas, Planes y Fases ya permitían creación

### 3. **Campos Editables**
- ✅ Los campos `code` (código) ahora son editables
- ✅ Se pueden ingresar manualmente o generar automáticamente
- ✅ Mantienen la validación de unicidad

---

## 📋 Estructura Académica

### Jerarquía de Entidades

```
PROGRAMA (Benglish / B-TEENS)
├── Planes de Estudio (Plus, Premium, Gold, Supreme, Plus Mixto)
│   └── Configuración (duración, modalidad, método de progreso)
│
├── Fases (Basic, Intermediate, Advanced) [COMPARTIDAS]
│   └── Niveles (Units 1-24 + Oral Tests) [COMPARTIDOS]
│       └── Asignaturas (B-Checks, B-Skills, Oral Tests) [COMPARTIDAS]
```

**Principio Fundamental:** Las asignaturas pertenecen al PROGRAMA, NO al plan. Los planes solo definen CÓMO se cursa el programa.

---

## 🛠️ Guía de Gestión

### 1️⃣ Gestionar Programas

**Ubicación:** Menú → Académico → Configuración → Programas

**Crear nuevo programa:**
1. Click en "Crear"
2. Completa:
   - Nombre del Programa
   - Tipo de Programa (Bekids, B-TEENS, Benglish, Otro)
   - Código (se genera automáticamente, o ingresa uno manual)
   - Descripción
3. Guardar

**Editar programa existente:**
- Abre el programa
- Modifica los campos necesarios
- Guarda los cambios

---

### 2️⃣ Gestionar Planes de Estudio

**Ubicación:** Menú → Académico → Configuración → Planes de Estudio

**Crear nuevo plan:**
1. Click en "Crear"
2. Completa:
   - Nombre del Plan (ej: Plan GOLD)
   - Programa al que pertenece
   - Código (se genera automáticamente)
   - Duración en meses
   - Total de horas
   - Método de cálculo de progreso
   - Versión (importante para versionamiento)
3. Guardar

**Buenas prácticas:**
- ✅ Usa versionamiento para cambios importantes (v1.0, v1.1, v2.0)
- ✅ Define fechas de vigencia para planes históricos
- ✅ Marca solo una versión como "Versión Actual"

---

### 3️⃣ Gestionar Fases

**Ubicación:** Menú → Académico → Configuración → Fases

**Crear nueva fase:**
1. Click en "Crear"
2. Completa:
   - Nombre de la Fase (ej: Basic, Intermediate, Advanced)
   - Programa al que pertenece
   - Código (se genera automáticamente)
   - Secuencia (orden de presentación: 10, 20, 30)
   - Duración en meses
3. Guardar

**Importante:**
- Las fases son COMPARTIDAS por todos los planes del mismo programa
- Define una secuencia clara para ordenarlas correctamente

---

### 4️⃣ Gestionar Niveles

**Ubicación:** Menú → Académico → Configuración → Niveles

**Crear nuevo nivel:**
1. Click en "Crear"
2. Completa:
   - Nombre del Nivel (ej: UNIT 1, UNIT 2, ORAL TEST (1-4))
   - Fase a la que pertenece
   - Código (se genera automáticamente según el programa)
   - Secuencia (orden dentro de la fase)
   - Duración en semanas
   - Total de horas
   - Unidad máxima (max_unit: 1, 2, 3... 24)
3. Guardar

**Ejemplo de secuenciación:**
```
Basic (Fase 1)
├── UNIT 1 (seq: 10, max_unit: 1)
├── UNIT 2 (seq: 20, max_unit: 2)
├── UNIT 3 (seq: 30, max_unit: 3)
└── UNIT 4 (seq: 40, max_unit: 4)
```

---

### 5️⃣ Gestionar Asignaturas

**Ubicación:** Menú → Académico → Configuración → Asignaturas

**Crear nueva asignatura:**
1. Click en "Crear"
2. Completa:
   - Nombre de la Asignatura (ej: Basic-GRAMMAR-U1)
   - Alias (ej: Skill, Check, Oral Test)
   - Nivel al que pertenece
   - Código (se genera automáticamente o ingresa manual)
   - Tipo de Asignatura:
     - `Núcleo/Obligatoria`: asignatura principal
     - `Electiva`: asignatura opcional
     - `Complementaria`: asignatura adicional
   - Clasificación:
     - `Asignatura Regular`: contenido académico normal
     - `Prerrequisito`: requerida para otras
     - `Evaluación`: examen/prueba
   - Categoría de asignatura (para lógica de negocio):
     - `bskills`: B-Skills
     - `bchecks`: B-Checks
     - `oral_tests`: Oral Tests
     - `placement_test`: Placement Test
   - ¿Es evaluable?: Si tiene nota/calificación
   - Horas académicas
   - Créditos
3. Configurar prerrequisitos (si aplica)
4. Guardar

**Tipos de asignaturas actuales:**

| Categoría | Cantidad | Descripción |
|-----------|----------|-------------|
| B-Checks | 24 | Evaluaciones por unidad (1 por UNIT) |
| B-Skills | 96 | Habilidades por unidad (4 por UNIT) |
| Oral Tests | 6 | Evaluaciones orales por fase (2 por fase) |
| Placement Test | 1 | Evaluación inicial |

---

### 6️⃣ Configurar Prerrequisitos

**Desde la asignatura:**
1. Abre la asignatura
2. Ve a la pestaña "Prerrequisitos"
3. Agrega asignaturas requeridas
4. Guarda

**Ejemplo de uso:**
```
Oral Test (5-8) requiere:
├── B-Check UNIT 5
├── B-Check UNIT 6
├── B-Check UNIT 7
└── B-Check UNIT 8
```

---

## ⚠️ Consideraciones Importantes

### Códigos de Secuencia

Los códigos se generan automáticamente según el programa:

| Tipo | Programa | Prefijo | Ejemplo |
|------|----------|---------|---------|
| Programa | B-TEENS | BT-PROG | BT-PROG |
| Programa | BENGLISH | BE-PROG | BE-PROG |
| Plan | B-TEENS | BT-P | BT-P-001 |
| Plan | BENGLISH | BE-P | BE-P-001 |
| Fase | B-TEENS | BT-F | BT-F-001 |
| Fase | BENGLISH | BE-F | BE-F-001 |
| Nivel | B-TEENS | BT-L | BT-L-001 |
| Nivel | BENGLISH | BE-L | BE-L-001 |
| Asignatura | B-TEENS | BT-S | BT-S-001 |
| Asignatura | BENGLISH | BE-S | BE-S-001 |

### Validaciones del Sistema

✅ **Códigos únicos:** No puede haber códigos duplicados
✅ **Secuencias únicas:** Dentro de cada contenedor (fase/programa)
✅ **Relaciones obligatorias:** Plan → Programa, Fase → Programa, Nivel → Fase, Asignatura → Nivel

---

## 🔄 Migración de Datos Existentes

### Si necesitas actualizar datos existentes:

1. **Desde Odoo (Recomendado):**
   - Navega al registro
   - Edita los campos necesarios
   - Guarda

2. **Desde archivos XML (Avanzado):**
   - Modifica el archivo XML correspondiente
   - Actualiza el módulo:
     ```bash
     odoo-bin -u benglish_academy -d tu_base_datos
     ```

**Importante:** Con `noupdate="0"`, los cambios en XML sobrescribirán los cambios manuales.

---

## 📊 Método de Progreso por Plan

Cada plan puede calcular el progreso de diferente forma:

| Método | Descripción | Uso recomendado |
|--------|-------------|-----------------|
| Por Asignaturas | Cuenta asignaturas completadas | Planes estándar |
| Por Horas | Calcula horas acumuladas | Planes personalizados |
| Mixto | 50% asignaturas + 50% horas | Planes híbridos |

**Configurar:** Plan → Método de Progreso

---

## 🎨 Categorías de Asignaturas

### B-Skills (`subject_category = 'bskills'`)
- 4 skills por UNIT
- Clasificación: `regular`
- Evaluable: No
- Total: 96 (24 units × 4 skills)

### B-Checks (`subject_category = 'bchecks'`)
- 1 check por UNIT
- Clasificación: `evaluation`
- Evaluable: Sí
- Total: 24 (24 units × 1 check)

### Oral Tests (`subject_category = 'oral_tests'`)
- 2 oral tests por fase
- Clasificación: `evaluation`
- Evaluable: Sí
- Total: 6 (3 fases × 2 tests)

### Placement Test (`subject_category = 'placement_test'`)
- Evaluación inicial
- Clasificación: `prerequisite`
- Evaluable: Sí
- Total: 1

---

## 🔐 Permisos de Usuario

Para gestionar el diseño curricular, el usuario necesita:

✅ Grupo: `Administrador Académico` o `Gestor Académico`
✅ Acceso a: Programas, Planes, Fases, Niveles, Asignaturas

**Configurar permisos:**
Ajustes → Usuarios → Seleccionar usuario → Pestaña "Grupos de acceso"

---

## 📝 Buenas Prácticas

### ✅ Hacer

1. **Versionamiento de Planes:**
   - Crea nuevas versiones en lugar de modificar planes existentes con estudiantes
   - Marca la versión actual con el campo `is_current_version`

2. **Secuencias Consistentes:**
   - Usa múltiplos de 10 (10, 20, 30...) para permitir inserciones futuras
   - Mantén el orden lógico del currículo

3. **Nomenclatura Clara:**
   - Usa nombres descriptivos
   - Mantén consistencia en la nomenclatura

4. **Prerrequisitos Lógicos:**
   - Define dependencias claras
   - Evita dependencias circulares

5. **Documentación:**
   - Completa el campo `description` en todos los registros
   - Explica el propósito y contenido

### ❌ Evitar

1. ❌ Modificar códigos de registros con matrículas activas
2. ❌ Eliminar registros con dependencias
3. ❌ Duplicar códigos manualmente
4. ❌ Cambiar tipos de programa en registros existentes
5. ❌ Desactivar registros con estudiantes activos sin análisis

---

## 🆘 Solución de Problemas

### Problema: No puedo editar un registro

**Solución:**
1. Verifica que tienes permisos de Gestor/Administrador Académico
2. Verifica que el registro no esté en uso por estudiantes activos
3. Si es necesario, duplica el registro en lugar de editarlo

### Problema: El código no se genera automáticamente

**Solución:**
1. Verifica que las secuencias estén configuradas correctamente
2. Navega a: Ajustes → Técnico → Secuencias → Busca "benglish"
3. Si no existe, recrea el módulo

### Problema: Error de código duplicado

**Solución:**
1. Cambia el código manualmente a uno único
2. Verifica que no haya conflictos con registros existentes
3. Usa la nomenclatura estándar del programa

### Problema: Los cambios no se reflejan

**Solución:**
1. Refresca el navegador (Ctrl + R o Cmd + R)
2. Verifica que hayas guardado los cambios
3. Si editaste XML, actualiza el módulo

---

## 📖 Recursos Adicionales

- [ACADEMIC_STRUCTURE.md](docs/ACADEMIC_STRUCTURE.md) - Documentación técnica completa
- Menú Ayuda en Odoo → Documentación técnica
- Contacta al equipo de desarrollo para soporte técnico

---

## 🎓 Conclusión

Ahora puedes gestionar completamente el diseño curricular de Benglish Academy desde Odoo, sin necesidad de modificar código. Esto permite:

✅ Mayor agilidad en cambios curriculares
✅ Mejor control de versiones de planes
✅ Gestión descentralizada (gestores académicos)
✅ Menor dependencia de desarrolladores
✅ Auditoría completa de cambios (tracking)

**¡Buenas prácticas implementadas con éxito!** 🎉
