# Plantilla Excel para Importación Masiva

Este documento describe la estructura del archivo Excel necesario para la importación masiva.

## Columnas Requeridas (Primera Fila - Encabezados)

```
CÓDIGO USUARIO | PRIMER NOMBRE | SEGUNDO NOMBRE | PRIMER APELLIDO | SEGUNDO APELLIDO | EMAIL | DOCUMENTO | CATEGORÍA | PLAN | SEDE | F. INICIO CURSO | DÍAS CONG. | FECHA FIN CURSO MÁS CONG. | FASE | NIVEL | ESTADO | CONTACTO TÍTULAR | FECHA NAC.
```

## Ejemplo de Datos (Filas 2 en adelante)

### Ejemplo 1: Estudiante Activo B teens

```
EST-001 | Juan | Carlos | Pérez | González | juan.perez@email.com | 1234567890 | B teens | GOLD | VIRTUAL | 15/01/2025 | 0 | 15/07/2025 | BASIC | 1 - 2 | ACTIVO | 3001234567 | 15/03/2005
```

### Ejemplo 2: Estudiante Adulto con Congelamiento

```
EST-002 | María | | López | Rodríguez | maria.lopez@email.com | 9876543210 | ADULTOS | PLUS | DUITAMA | 01/02/2025 | 15 | 01/09/2025 | INTERMEDIATE | 11 - 12 | ACTIVO | 3109876543 | 22/08/1990
```

### Ejemplo 3: Estudiante Finalizado

```
EST-003 | Pedro | José | Martínez | Silva | pedro.martinez@email.com | 5555555555 | ADULTOS | PREMIUM | ZIPAQUIRÁ | 10/01/2025 | 0 | 10/12/2025 | ADVANCED | 23 - 24 | FINALIZADO | 3205555555 | 10/05/1985
```

### Ejemplo 4: Estudiante Suspendido

```
EST-004 | Ana | María | García | Torres | ana.garcia@email.com | 1111111111 | B teens | GOLD | NIZA | 20/02/2025 | 10 | 20/08/2025 | BASIC | 5 - 6 | SUSPENDIDO | 3151111111 | 12/11/2006
```

## Notas Importantes

### Campos Obligatorios vs Opcionales

**Obligatorios:**

- CÓDIGO USUARIO
- PRIMER NOMBRE
- PRIMER APELLIDO
- CATEGORÍA
- PLAN
- F. INICIO CURSO
- FECHA FIN CURSO MÁS CONG.
- FASE
- NIVEL
- ESTADO

**Opcionales (pueden estar vacíos o con "-"):**

- SEGUNDO NOMBRE
- SEGUNDO APELLIDO
- EMAIL
- DOCUMENTO
- SEDE
- DÍAS CONG.
- CONTACTO TÍTULAR
- FECHA NAC.

### Valores Especiales

- **Vacío / "-" / "0"**: Se interpretan como NULL (sin valor)
- **DÍAS CONG. = 0**: No se crea congelamiento
- **ESTADO = N/A**: Estudiante inactivo sin agenda

### Formatos de Fecha

Soportados:

- `15/01/2025`
- `15-01-2025`
- `2025-01-15`
- `15/01/25`
- `15-01-25`

### Categorías Válidas

Solo estas categorías serán importadas:

- `B teens`
- `ADULTOS`

Cualquier otra categoría será **omitida** (no genera error, simplemente no se importa).

### Planes Disponibles (ejemplos)

El sistema buscará:

- Excel: `GOLD` → Sistema: `PLAN GOLD`
- Excel: `PLUS` → Sistema: `PLAN PLUS`
- Excel: `PREMIUM` → Sistema: `PLAN PREMIUM`
- Excel: `SUPREME` → Sistema: `PLAN SUPREME`
- Excel: `PLUS VIRTUAL` → Sistema: `PLAN PLUS VIRTUAL`

### Fases Válidas

- `BASIC`
- `INTERMEDIATE`
- `ADVANCED`

(Case-insensitive)

### Estados Válidos

- `ACTIVO`
- `SUSPENDIDO`
- `FINALIZADO`
- `N/A`

(Case-insensitive)

## Descarga de Plantilla

Para facilitar el proceso, se recomienda:

1. Crear un archivo Excel nuevo
2. Copiar los encabezados de la primera sección
3. Llenar con los datos de los estudiantes
4. Guardar como `.xlsx`
5. Importar desde: **Gestión Académica → Matrícula → Importación Masiva**

## Verificación Previa

Antes de importar, verificar:

1. ✅ Todos los CÓDIGO USUARIO son únicos
2. ✅ Las categorías son solo "B teens" o "ADULTOS"
3. ✅ Los planes existen en el sistema (con prefijo "PLAN ")
4. ✅ Las fases son BASIC, INTERMEDIATE o ADVANCED
5. ✅ Las fechas están en formato correcto
6. ✅ Los niveles tienen formato "X - Y"
7. ✅ No hay filas completamente vacías

---

**Tip:** Si tienes dudas sobre los datos, usa la opción **"Omitir Errores"** en el wizard para que continúe la importación aunque algunas filas fallen.
