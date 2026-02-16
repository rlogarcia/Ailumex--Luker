# Migración 18.0.1.10.0 - Plan Comercial: Fix validación de intervalo de niveles

## Problema resuelto

Al configurar líneas de plan comercial con modo de cálculo "Por Nivel" o "Total Fijo",
se producía un error de validación:

```
¡Ups!
No se puede completar la operación: El intervalo de niveles debe ser mayor a cero.
```

## Causa

La restricción SQL `interval_positive` validaba que el campo `levels_interval > 0`
**siempre**, incluso cuando el modo de cálculo no requería ese campo.

## Solución

### 1. Modelo (`commercial_plan_line.py`)

- **Eliminada** la restricción SQL `interval_positive`
- **Agregada** validación Python con `@api.constrains` que solo valida cuando
  `calculation_mode == 'per_x_levels'`
- **Mejorado** el `@api.onchange` para mantener `levels_interval` con valor válido
  (≥ 4) incluso cuando no se usa, evitando inconsistencias

### 2. Vista (`commercial_plan_views.xml`)

- **Eliminado** el atributo `sum="Total General"` que causaba que apareciera "0"
  seguido del total real
- **Mejorada** la presentación del "TOTAL ASIGNATURAS DEL PLAN" con mejor formato
  y estilos

### 3. Migración

Los scripts de migración (`pre-migrate.py` y `post-migrate.py`):

- Eliminan la restricción SQL antigua de la base de datos
- Actualizan registros existentes que tengan `levels_interval = 0` cuando no usan
  el modo "Cada X Niveles"
- Verifican que no queden configuraciones inválidas
- Generan estadísticas de la migración

## Cómo aplicar

1. Actualizar el módulo a versión `18.0.1.10.0`
2. Los scripts de migración se ejecutarán automáticamente
3. La restricción SQL se eliminará y los datos se corregirán

## Comportamiento esperado

- **Por Nivel**: `levels_interval` puede ser cualquier valor (se mantiene en 4 por defecto)
- **Cada X Niveles**: `levels_interval` debe ser > 0 (validado por Python)
- **Total Fijo**: `levels_interval` puede ser cualquier valor (se mantiene en 4 por defecto)

El resumen de totales ahora muestra correctamente el total sin duplicados.
