# Sistema de Notificaciones del Portal del Estudiante

## 📋 Descripción General

El sistema de notificaciones permite a los estudiantes recibir alertas en tiempo real sobre nuevas clases publicadas. Incluye un contador visual (badge rojo) que muestra el número de notificaciones no vistas.

## ✨ Características Principales

### 1. **Badge Visual Super Visible**
- Badge rojo brillante con animación de pulso
- Contador que muestra el número de notificaciones no vistas
- Muestra hasta 99+para grandes cantidades
- Desaparece automáticamente cuando todas las notificaciones han sido vistas

### 2. **Sistema Inteligente de Marcado**
- Las notificaciones se marcan como vistas cuando el estudiante abre el dropdown
- El badge se oculta inmediatamente al abrir (mejor UX)
- Persistencia temporal con localStorage para evitar parpadeos
- Actualización automática del contador cada 30 segundos

### 3. **Panel de Notificaciones Mejorado**
- Muestra las últimas 10 clases publicadas
- Notificaciones no vistas destacadas visualmente con:
  - Fondo de color rojo suave
  - Borde izquierdo rojo
  - Icono pulsante
  - Punto rojo animado en el título
- Información completa: asignatura, fecha/hora, tiempo relativo

### 4. **Responsive Design**
- Adaptado para móviles, tablets y desktop
- En móviles pequeños, el panel ocupa toda la pantalla
- Scrollbar personalizado

## 🔧 Componentes Técnicos

### Backend (Python)

#### **Modelo: portal.notification.view**
Ubicación: `models/portal_notification.py`

Registra qué notificaciones ha visto cada usuario:
- `user_id`: Usuario que vio la notificación
- `session_id`: Sesión académica vista
- `viewed_at`: Timestamp de cuándo se vio

#### **Endpoints JSON-RPC**

1. **GET /my/student/notifications_count**
   - Obtiene el contador de notificaciones no vistas
   - Respuesta: `{success: true, unseen_count: 5, total_notifications: 10}`
   - Usado para actualización periódica del badge

2. **POST /my/student/mark_notifications_viewed**
   - Marca notificaciones como vistas
   - Parámetros: `{session_ids: [1, 2, 3]}`
   - Respuesta: `{success: true, viewed_count: 3, created: 3}`
   - Llamado cuando el estudiante abre el dropdown

3. **GET /my/student/notifications_debug**
   - Endpoint de diagnóstico para debugging
   - Retorna estado completo del sistema de notificaciones

### Frontend (JavaScript)

Ubicación: `static/src/js/portal_student.js`

#### **Métodos Principales**

1. **_initNotificationSystem()**
   - Inicializa el sistema al cargar la página
   - Verifica estado del badge
   - Inicia el polling automático

2. **_startNotificationPolling()**
   - Actualiza el contador cada 30 segundos
   - Mantiene el badge sincronizado con el servidor

3. **_updateNotificationCount()**
   - Llama al endpoint `/notifications_count`
   - Actualiza el badge visual
   - Crea el badge si no existe

4. **_markNotificationsAsViewed()**
   - Marca las notificaciones como vistas cuando se abre el dropdown
   - Actualiza visual inmediatamente (optimistic update)
   - Sincroniza con el servidor
   - Maneja errores restaurando el estado previo

5. **_restoreUnseenState()**
   - Restaura el estado visual si hay error en el servidor
   - Asegura consistencia de datos

### Frontend (QWeb Template)

Ubicación: `views/portal_student_templates.xml`

#### **Variables del Template**
```xml
<t t-set="notif_list" t-value="request.env['benglish.academic.session'].sudo().search([('is_published','=',True)], order='create_date desc', limit=10)"/>
<t t-set="viewed_ids" t-value="request.env['portal.notification.view'].sudo().search([('user_id','=',request.env.user.id)]).mapped('session_id').ids"/>
<t t-set="unseen_count" t-value="len([n for n in notif_list if n.id not in viewed_ids])"/>
```

### Estilos (CSS)

Ubicación: `static/src/css/portal_student.css`

#### **Clases CSS Principales**

- `.ps-notif-badge`: Badge contador con animación de pulso
- `.ps-notif-badge-hidden`: Oculta el badge con transición suave
- `.ps-notif-unseen`: Estilo para notificaciones no vistas
- `.ps-notif-unread-dot`: Punto pulsante en notificaciones nuevas
- `.ps-notif-icon`: Icono circular para cada notificación
- `.ps-notif-dropdown`: Panel desplegable de notificaciones

#### **Animaciones**
```css
@keyframes ps-badge-pulse {
    /* Pulso suave del badge cada 2 segundos */
}

@keyframes ps-dot-blink {
    /* Parpadeo del punto de notificación no leída */
}
```

## 🚀 Flujo de Funcionamiento

### Carga Inicial
1. El template renderiza el badge con el contador inicial
2. JavaScript inicializa el sistema de notificaciones
3. Se inicia el polling automático cada 30 segundos

### Nueva Notificación (Nueva Clase Publicada)
1. Admin publica una nueva clase (sesión académica)
2. El sistema detecta que es nueva (no está en `portal.notification.view`)
3. En la siguiente actualización (máx 30 seg), el badge se actualiza
4. El badge aparece/incrementa mostrando el nuevo contador

### Estudiante Abre las Notificaciones
1. Click en el botón de notificaciones (campana)
2. Se abre el dropdown con la lista de notificaciones
3. JavaScript detecta las notificaciones no vistas
4. Badge se oculta inmediatamente (mejor UX)
5. Se envía petición al servidor para marcar como vistas
6. Servidor crea registros en `portal.notification.view`
7. Respuesta exitosa: notificaciones quedan marcadas
8. En caso de error: se restaura el estado visual previo

### Actualización Periódica
1. Cada 30 segundos, JavaScript llama a `/notifications_count`
2. Servidor calcula notificaciones no vistas
3. Badge se actualiza con el nuevo contador
4. Si hay nuevas notificaciones, el badge reaparece

## 🎨 Características Visuales

### Badge Rojo
- Color: Gradiente rojo (#ff0000 → #dc2626)
- Sombra: Múltiples capas para máxima visibilidad
- Animación: Pulso cada 2 segundos
- Borde: Blanco con sombra del tema
- Posición: Esquina superior derecha del botón

### Notificaciones No Vistas
- Fondo: Gradiente rojo muy suave
- Borde izquierdo: Rojo brillante de 4px
- Punto pulsante: Icono de círculo animado
- Icono: Fondo rojo suave en lugar de azul

### Dropdown
- Ancho: 420px en desktop, 100% en móvil
- Altura máxima: 500px con scroll
- Sombra: Profunda para destacar
- Scrollbar: Personalizado con colores del tema

## 📱 Responsive Design

### Desktop (> 768px)
- Badge tamaño normal (20x20px)
- Dropdown ancho fijo (420px)
- Notificaciones con spacing generoso

### Tablet (768px)
- Dropdown se ajusta a viewport menos margen
- Badge igual que desktop

### Móvil (< 480px)
- Dropdown ocupa toda la pantalla
- Badge más pequeño (18x18px)
- Header sticky al hacer scroll
- Sin border-radius

## 🐛 Debugging

### Consola del Navegador
El sistema registra logs detallados:
```javascript
console.log('=== Inicializando Sistema de Notificaciones ===');
console.log('Contador actualizado:', unseenCount);
console.log('=== Marcando notificaciones como vistas ===');
```

### Endpoint de Debug
Llamar desde la consola:
```javascript
odoo.define('test', function(require) {
    var ajax = require('web.ajax');
    ajax.jsonRpc('/my/student/notifications_debug', 'call', {}).then(console.log);
});
```

Retorna información completa del estado actual.

## 🔒 Seguridad

- Todos los endpoints usan autenticación de usuario (`auth='user'`)
- Las consultas usan `.sudo()` con cuidado solo para lectura
- Validación de IDs de sesión antes de crear registros
- Manejo de errores con try/catch
- Logs detallados para auditoría

## ⚙️ Configuración

### Frecuencia de Actualización
Ubicación: `portal_student.js` línea ~32
```javascript
setInterval(function() {
    self._updateNotificationCount();
}, 30000); // 30 segundos
```

### Cantidad de Notificaciones
Ubicación: Varios archivos
- Template: `limit=10`
- Endpoint count: `limit=10`
- Endpoint debug: `limit=10`

**Nota:** Mantener consistencia entre todos los límites.

### Límite del Badge
Ubicación: `portal_student_templates.xml` línea ~43
```xml
<span t-esc="unseen_count if unseen_count &lt; 100 else '99+'"></span>
```

## 🎯 Casos de Uso

### 1. Estudiante Nuevo (Primera Vez)
- Ve todas las clases publicadas como no vistas
- Badge muestra el contador total
- Al abrir, todas se marcan como vistas

### 2. Estudiante Recurrente
- Solo ve nuevas clases desde su última visita
- Badge muestra solo las nuevas
- Puede revisar historial en el dropdown

### 3. Múltiples Dispositivos
- El estado de "visto" es por usuario, no por sesión
- Si abre en PC, también se marca en móvil
- Sincronización en tiempo real (máx 30 seg)

### 4. Sin Notificaciones
- Badge oculto completamente
- Dropdown muestra mensaje amigable
- Icono diferente (bell-slash)

## 📝 Notas de Implementación

### Optimistic UI Updates
El sistema usa "optimistic updates" para mejor UX:
- El badge se oculta inmediatamente al abrir
- Las notificaciones se desmarcan visualmente de inmediato
- Si el servidor falla, se restaura el estado previo

### LocalStorage
Se usa temporalmente para evitar parpadeos:
- `ps_notif_badge_hidden`: Flag temporal cuando se oculta el badge
- Se limpia en la siguiente actualización del contador
- No es la fuente de verdad (servidor lo es)

### Prevención de Duplicados
- Constraint SQL único en `portal.notification.view`
- Verificación en Python antes de crear
- Manejo de errores silencioso si ya existe

## 🚀 Futuras Mejoras Posibles

1. **Notificaciones en Tiempo Real**
   - Implementar WebSocket o long-polling
   - Actualización instantánea sin esperar 30 segundos

2. **Tipos de Notificación**
   - Diferentes tipos: clase nueva, cambio de horario, cancelación
   - Iconos y colores diferentes por tipo
   - Filtros en el dropdown

3. **Acciones Rápidas**
   - Botón "Agendar" directamente desde la notificación
   - Link directo a la clase
   - Botón "Marcar todas como vistas"

4. **Preferencias de Usuario**
   - Activar/desactivar notificaciones
   - Elegir frecuencia de actualización
   - Sonidos o alertas visuales

5. **Historial Completo**
   - Página dedicada con todas las notificaciones
   - Búsqueda y filtros avanzados
   - Exportación de notificaciones

## 📞 Soporte

Para problemas o preguntas sobre el sistema de notificaciones:
1. Revisar logs de consola del navegador
2. Verificar logs del servidor Odoo
3. Usar endpoint de debug para diagnóstico
4. Revisar modelo `portal.notification.view` en el backend

---

**Última actualización:** Diciembre 2025  
**Versión:** 1.0  
**Autor:** Equipo de Desarrollo B English
