# SOLUCIÓN RÁPIDA: Campos de Evaluación no válidos

## Problema

Los campos de evaluación no aparecen en la interfaz de Odoo:

- Fecha de Evaluación
- Hora de Evaluación
- Modalidad de Evaluación

## Causa

El módulo `crm_import_leads` no se ha actualizado en la base de datos después de agregar los campos.

---

## SOLUCIÓN 1: Actualización por Interfaz Web (MÁS FÁCIL)

1. **Acceder a Odoo:**

   - Ir a http://localhost:8069
   - Iniciar sesión como administrador

2. **Activar Modo Desarrollador:**

   - Ir a: Configuración → Activar el modo de desarrollador

3. **Actualizar el Módulo:**

   - Ir a: Aplicaciones
   - Quitar el filtro "Aplicaciones" (clic en la X)
   - Buscar: `crm_import_leads`
   - Clic en el módulo
   - Clic en "Actualizar" (botón verde)
   - Esperar a que complete
   - Refrescar la página (F5)

4. **Verificar:**
   - Ir a CRM → Leads
   - Abrir cualquier lead
   - Debe aparecer una nueva pestaña "Evaluación"

---

## SOLUCIÓN 2: Actualización por Línea de Comandos

### Opción A: Usando Python de Odoo

```powershell
# 1. Detener el servicio de Odoo
Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Stop-Process -Force

# 2. Ejecutar actualización
cd "c:\Program Files\Odoo 18.0.20251128\python"

.\python.exe ..\server\odoo-bin `
    -c ..\server\odoo.conf `
    -d ailumex_be_crm `
    -u crm_import_leads `
    --stop-after-init

# 3. Reiniciar Odoo
# (reiniciar el servicio o ejecutar odoo-bin normalmente)
```

### Opción B: Usando el script Python

```powershell
cd "d:\AiLumex\CRM\crm_import_leads"

"c:\Program Files\Odoo 18.0.20251128\python\python.exe" actualizar_campos.py
```

---

## SOLUCIÓN 3: Verificación Manual de Base de Datos

Si las soluciones anteriores no funcionan, verificar directamente en PostgreSQL:

```powershell
# 1. Conectar a PostgreSQL
psql -U odoo -d ailumex_be_crm

# 2. Ejecutar el script de verificación
\i d:/AiLumex/CRM/crm_import_leads/verificar_campos.sql

# 3. Si los campos NO existen, actualizar desde Odoo forzosamente
```

---

## VERIFICACIÓN POST-ACTUALIZACIÓN

Después de actualizar, verificar que funciona:

1. **Abrir un Lead:**

   - CRM → Leads → Abrir cualquier lead

2. **Buscar pestaña "Evaluación":**

   - Debe aparecer después de las pestañas existentes
   - Dentro debe haber campos:
     - Fecha de Evaluación
     - Hora de Evaluación (formato HH:MM)
     - Modalidad de Evaluación (dropdown)
     - Link de Evaluación (si modalidad es Virtual)
     - Dirección de Evaluación (si modalidad es Presencial)

3. **Probar programar evaluación:**
   - Completar los campos requeridos
   - Clic en "Confirmar y Crear Evento en Calendario"
   - Debe crear un evento en el calendario
   - Debe crear una actividad automática

---

## TROUBLESHOOTING

### Error: "Campos no válidos" persiste

**Posible causa 1:** Caché del navegador

- Solución: Presionar Ctrl+Shift+R (recarga forzada)

**Posible causa 2:** Módulo no actualizado correctamente

- Solución: Desinstalar y reinstalar el módulo
  ```
  Aplicaciones → crm_import_leads → Desinstalar
  Aplicaciones → crm_import_leads → Instalar
  ```

**Posible causa 3:** Error en el código Python

- Verificar log de Odoo: `c:\Program Files\Odoo 18.0.20251128\server\odoo.log`
- Buscar errores relacionados con `evaluation`

### Error: "Field does not exist"

Ejecutar SQL manualmente:

```sql
ALTER TABLE crm_lead ADD COLUMN IF NOT EXISTS evaluation_date date;
ALTER TABLE crm_lead ADD COLUMN IF NOT EXISTS evaluation_time varchar;
ALTER TABLE crm_lead ADD COLUMN IF NOT EXISTS evaluation_modality varchar;
ALTER TABLE crm_lead ADD COLUMN IF NOT EXISTS evaluation_link varchar;
ALTER TABLE crm_lead ADD COLUMN IF NOT EXISTS evaluation_address text;
ALTER TABLE crm_lead ADD COLUMN IF NOT EXISTS calendar_event_id integer REFERENCES calendar_event(id) ON DELETE SET NULL;
```

Luego actualizar el módulo desde la interfaz.

---

## CONFIRMACIÓN DE ÉXITO

✅ Los campos deben aparecer en:

1. Vista de formulario de Lead (pestaña Evaluación)
2. Filtros avanzados (Con Evaluación Programada)
3. Vista de lista (pueden agregarse como columnas)

✅ Las automatizaciones deben funcionar:

1. Al crear lead → Actividad "Llamar inmediato"
2. Al programar evaluación → Actividad de reunión
3. Al confirmar evaluación → Evento en calendario

---

## RECOMENDACIÓN

**Use la SOLUCIÓN 1** (interfaz web) - Es la más confiable y muestra mensajes de error claros si algo falla.
