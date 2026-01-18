# Instrucciones de Actualización: Bitácora Académica

**Fecha:** 16 de enero de 2026  
**Módulo:** `benglish_academy`  
**Versión:** Odoo 18

---

## 📋 Resumen de Cambios

Se han corregido dos problemas críticos en la Bitácora Académica:

1. ✅ **Problema de registros únicos:** Ahora la bitácora muestra TODOS los registros históricos
2. ✅ **Problema de renderizado HTML:** El campo de asistencia se muestra como checkbox estándar

---

## 🚀 Pasos para Aplicar la Actualización

### Opción A: Actualización Estándar (Recomendada)

```powershell
# 1. Detener el servicio de Odoo (si está corriendo como servicio)
Stop-Service OdooService

# 2. Navegar al directorio de Odoo
cd "C:\Program Files\Odoo 18.0.20250614\server"

# 3. Actualizar el módulo benglish_academy
.\python\python.exe odoo-bin -c odoo.conf -u benglish_academy -d nombre_de_tu_base_de_datos --stop-after-init

# 4. Reiniciar el servicio de Odoo
Start-Service OdooService
```

### Opción B: Actualización en Modo Desarrollo

```powershell
# 1. Si Odoo está corriendo, detenerlo (Ctrl+C en la terminal)

# 2. Actualizar el módulo y arrancar en modo desarrollo
cd "C:\Program Files\Odoo 18.0.20250614\server"
.\python\python.exe odoo-bin -c odoo.conf -u benglish_academy -d nombre_de_tu_base_de_datos

# 3. Una vez que arranque, acceder en el navegador con modo debug
# http://localhost:8069/web?debug=1
```

### Opción C: Actualización desde la Interfaz de Odoo

1. **Ir a Aplicaciones**
2. **Activar el modo desarrollador:**
   - Menú → Configuración → Activar el modo desarrollador
3. **Buscar "Benglish Academy"**
4. **Hacer clic en el botón "Actualizar"**
5. **Esperar a que complete**
6. **Refrescar el navegador (F5 o Ctrl+F5)**

---

## 🧪 Verificación Post-Actualización

### 1. Verificar que los cambios se aplicaron

```powershell
# Abrir PowerShell y ejecutar
cd "C:\Program Files\TrabajoOdoo\Odoo18\Proyecto-Be\benglish_academy"

# Verificar los archivos modificados
git status
# O
git diff views/academic_history_views.xml
git diff views/student_views.xml
```

### 2. Probar la Bitácora Académica en el Backend

1. **Iniciar sesión en Odoo**
2. **Ir a: Gestión Académica → Bitácora Académica**
3. **Verificar que se muestren TODOS los registros** (no solo uno)
4. **Verificar que el campo "Asistió" muestre checkboxes** (no código HTML)

### 3. Ejecutar el Script de Diagnóstico

```python
# Opción 1: Desde odoo-bin shell
cd "C:\Program Files\Odoo 18.0.20250614\server"
.\python\python.exe odoo-bin shell -c odoo.conf -d nombre_de_tu_base_de_datos

# Una vez en el shell, ejecutar:
exec(open('C:/Program Files/TrabajoOdoo/Odoo18/Proyecto-Be/benglish_academy/scripts/diagnostic_bitacora.py').read())

# Opción 2: Copiar y pegar en el shell de Odoo
# (Ver contenido del script en scripts/diagnostic_bitacora.py)
```

### 4. Crear Registro de Prueba

1. **Ir a: Gestión Académica → Planificación Académica → Sesiones**
2. **Seleccionar una sesión en estado "Iniciada"**
3. **Hacer clic en "Marcar como Dictada"**
4. **Verificar que se creen registros en la Bitácora**
5. **Ir a Bitácora Académica y confirmar que el nuevo registro aparece**
6. **Crear otro registro y verificar que ambos aparecen**

---

## 🔧 Solución de Problemas

### Problema: "No puedo actualizar el módulo"

**Error:**
```
Module benglish_academy not found
```

**Solución:**
```powershell
# Verificar que el módulo esté en la ruta correcta
dir "C:\Program Files\TrabajoOdoo\Odoo18\Proyecto-Be\benglish_academy"

# Verificar que Odoo tenga acceso a esa ruta en odoo.conf
notepad "C:\Program Files\Odoo 18.0.20250614\server\odoo.conf"

# Buscar la línea addons_path y verificar que incluya:
# addons_path = ..., C:\Program Files\TrabajoOdoo\Odoo18\Proyecto-Be
```

### Problema: "Sigue mostrando código HTML en el campo Asistió"

**Causa:** El navegador tiene cache de la vista antigua.

**Solución:**
1. **Limpiar cache del navegador:**
   - Chrome: Ctrl+Shift+Delete → Borrar imágenes y archivos en caché
   - Firefox: Ctrl+Shift+Delete → Cache
2. **Hacer hard refresh:**
   - Ctrl+F5 o Ctrl+Shift+R
3. **Si persiste, regenerar vistas:**
   ```python
   # En odoo-bin shell
   env['ir.ui.view'].clear_caches()
   env.cr.commit()
   ```

### Problema: "Solo aparece un registro en la Bitácora"

**Diagnóstico:**
1. **Verificar cuántos registros hay en la base de datos:**
   ```python
   # En odoo-bin shell
   History = env['benglish.academic.history']
   total = History.search_count([])
   print(f"Total de registros: {total}")
   ```

2. **Si total > 1 pero solo ves 1 en la vista:**
   - **Verificar filtros activos** en la búsqueda (limpiar filtros)
   - **Verificar que no haya filtros personalizados guardados**
   - **Desactivar modo debug** y volver a entrar

3. **Si total == 1:**
   - **No es un problema de la vista, sino de datos**
   - **Verificar que las sesiones se marquen como 'done':**
     ```python
     Session = env['benglish.academic.session']
     sessions_done = Session.search_count([('state', '=', 'done')])
     print(f"Sesiones terminadas: {sessions_done}")
     ```
   - **Si sessions_done == 0:** Las clases no se están marcando como dictadas

### Problema: "Error al actualizar: psycopg2.errors.UniqueViolation"

**Causa:** Hay registros duplicados que violan el constraint SQL.

**Solución:**
```sql
-- Conectar a PostgreSQL y ejecutar:
SELECT student_id, session_id, COUNT(*) as count
FROM benglish_academic_history
WHERE student_id IS NOT NULL AND session_id IS NOT NULL
GROUP BY student_id, session_id
HAVING COUNT(*) > 1;

-- Eliminar duplicados (conservar el más antiguo):
DELETE FROM benglish_academic_history
WHERE id NOT IN (
    SELECT MIN(id)
    FROM benglish_academic_history
    WHERE student_id IS NOT NULL AND session_id IS NOT NULL
    GROUP BY student_id, session_id
);

-- Luego actualizar el módulo normalmente
```

---

## 📊 Verificación de Éxito

Después de la actualización, debes ver:

### ✅ En la Vista de Lista (Bitácora Académica)

```
Fecha         | Clase           | Asistió | Nota | Docente
------------- | --------------- | ------- | ---- | --------
16/01/2026    | Benglish Basic  |   ☑     | 8.5  | Carlos
15/01/2026    | Benglish Inter  |   ☐     | 0.0  | María
14/01/2026    | Benglish Adv    |   ☑     | 9.0  | Carlos
13/01/2026    | B-Check Unit 1  |   ☑     | 7.5  | Ana
...
```

**NO** debe mostrar:
```html
<div class="o-checkbox-inline-block me-2">
  <input type="checkbox" ...
```

### ✅ En la Estadística

```
📊 Total de registros en bitácora: 150
✅ Asistió: 120 (80.0%)
❌ Ausente: 20 (13.3%)
⏳ Pendiente: 10 (6.7%)
```

Si los números son > 1, la actualización fue exitosa.

---

## 🔄 Rollback (Solo en caso de emergencia)

Si después de la actualización hay problemas críticos:

```powershell
# 1. Restaurar archivos anteriores
cd "C:\Program Files\TrabajoOdoo\Odoo18\Proyecto-Be\benglish_academy"
git checkout HEAD~1 views/academic_history_views.xml
git checkout HEAD~1 views/student_views.xml

# 2. Actualizar módulo con versión anterior
cd "C:\Program Files\Odoo 18.0.20250614\server"
.\python\python.exe odoo-bin -c odoo.conf -u benglish_academy -d nombre_de_tu_base_de_datos --stop-after-init

# 3. Reportar el problema con logs y detalles
```

---

## 📞 Contacto y Soporte

Si tienes problemas durante la actualización:

1. **Revisar logs de Odoo:**
   ```
   C:\Program Files\Odoo 18.0.20250614\server\odoo.log
   ```

2. **Buscar errores relacionados con:**
   - `[ACADEMIC HISTORY]`
   - `benglish.academic.history`
   - `UniqueViolation`
   - `view_benglish_academic_history`

3. **Ejecutar el script de diagnóstico** para más detalles

4. **Documentar el problema con:**
   - Mensaje de error completo
   - Pasos para reproducir
   - Salida del script de diagnóstico

---

**Última actualización:** 2026-01-16  
**Tiempo estimado de actualización:** 2-5 minutos  
**Requiere detener Odoo:** Sí
