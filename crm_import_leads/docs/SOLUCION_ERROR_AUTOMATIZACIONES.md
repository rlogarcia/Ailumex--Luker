# SOLUCIÓN INMEDIATA AL ERROR DE AUTOMATIZACIONES

## El Problema

Error al crear leads debido a automatizaciones con `filter_domain` mal formateado en la base de datos.

```
SyntaxError: unterminated string literal
[('stage_id.name', 'in', ['Reprobado', 'Matriculado', 'Pago
```

## SOLUCIÓN RÁPIDA - Por Interfaz Web

### Paso 1: Desactivar Automatizaciones Problemáticas

1. **Acceder a Odoo:**

   - http://localhost:8069
   - Iniciar sesión como administrador

2. **Activar Modo Desarrollador:**

   - Configuración → Activar el modo de desarrollador

3. **Ir a Automatizaciones:**

   - Configuración → Automatización → Acciones automatizadas

4. **Buscar y Desactivar:**

   - Buscar: `CRM: Actividad - Seguimiento post-evaluación`
   - Clic en el registro
   - Quitar el check de "Activo"
   - Guardar

   - Buscar: `CRM: Actividad - Evaluación programada`
   - Clic en el registro
   - Quitar el check de "Activo"
   - Guardar

### Paso 2: Probar Creación de Lead

1. **Ir a CRM:**

   - CRM → Leads → Nuevo

2. **Completar datos mínimos:**

   - Nombre del lead
   - Responsable (debe ser usuario comercial)

3. **Guardar:**
   - Debería guardar sin errores

---

## SOLUCIÓN ALTERNATIVA - SQL Directo

Si tienes acceso a PostgreSQL:

```sql
-- Conectar a la base de datos
psql -U odoo -d ailumex_be_crm

-- Desactivar automatizaciones problemáticas
UPDATE base_automation
SET active = false
WHERE name IN (
    'CRM: Actividad - Seguimiento post-evaluación',
    'CRM: Actividad - Evaluación programada'
);

-- Verificar
SELECT id, name, active
FROM base_automation
WHERE name LIKE 'CRM:%'
ORDER BY name;
```

---

## Verificación Final

Después de aplicar la solución:

1. **Refrescar navegador:** Ctrl + Shift + R
2. **Crear un lead de prueba**
3. **Verificar que se guarde sin errores**

---

## Notas Importantes

- Las automatizaciones están **desactivadas temporalmente**
- Los leads se crearán correctamente pero sin:
  - Actividad automática de evaluación programada
  - Seguimiento post-evaluación
- Estas automatizaciones se pueden reactivar más tarde una vez corregido el bug en la base de datos

---

## Para Reactivar las Automatizaciones

Una vez que el módulo se actualice correctamente:

1. Configuración → Automatización → Acciones automatizadas
2. Buscar las automatizaciones CRM
3. Editar cada una
4. Verificar que el "Dominio del filtro" esté correcto
5. Activar

---

## Estado Actual

✅ Archivos XML corregidos  
⚠️ Base de datos con datos antiguos  
🔧 Solución: Desactivar manual hasta próxima actualización
