/** JavaScript Vanilla para Portal del Estudiante - Sin dependencias de Odoo **/

console.log("✅ portal_student.js cargado");

// ==================== SISTEMA DE NOTIFICACIONES PERSONALIZADAS ====================
function showNotification(message, type = 'success') {
    // Crear el contenedor de notificación
    const notification = document.createElement('div');
    notification.className = `ps-notification ps-notification-${type}`;
    notification.innerHTML = `
        <div class="ps-notification-content">
            <i class="fa ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
            <span class="ps-notification-message">${message}</span>
        </div>
        <button class="ps-notification-close" onclick="this.parentElement.remove()">
            <i class="fa fa-times"></i>
        </button>
    `;
    
    document.body.appendChild(notification);
    
    // Animación de entrada
    setTimeout(() => notification.classList.add('ps-notification-show'), 10);
    
    // Auto-cerrar después de 5 segundos (excepto errores)
    if (type !== 'error') {
        setTimeout(() => {
            notification.classList.remove('ps-notification-show');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }
}

// ==================== FUNCIÓN GLOBAL ====================
// Esta función usa fetch() nativo de JavaScript (sin dependencias de Odoo)
window.psMarkNotificationsAsRead = function() {
    console.log("🔵 Función psMarkNotificationsAsRead llamada");

    if (window.psMarkNotificationsInFlight) {
        console.warn("⚠️ Marcado de notificaciones en curso");
        return;
    }
    window.psMarkNotificationsInFlight = true;
    
    const notifDropdown = document.querySelector('.ps-notif-dropdown');
    if (!notifDropdown) {
        console.error('❌ No se encontró el dropdown');
        showNotification('Error: No se encontró el panel de notificaciones. Recarga la página.', 'error');
        window.psMarkNotificationsInFlight = false;
        return;
    }
    
    const unseenItems = notifDropdown.querySelectorAll('.ps-notif-item.ps-notif-unseen');
    console.log('📋 Notificaciones no vistas:', unseenItems.length);
    
    if (unseenItems.length === 0) {
        showNotification('No hay notificaciones nuevas para marcar', 'info');
        window.psMarkNotificationsInFlight = false;
        return;
    }
    
    const sessionIds = [];
    unseenItems.forEach(function(item) {
        const sessionId = parseInt(item.getAttribute('data-session-id'));
        if (sessionId) sessionIds.push(sessionId);
    });
    
    console.log('📤 Session IDs:', sessionIds);
    
    if (sessionIds.length === 0) {
        showNotification('No se encontraron IDs de sesión válidos', 'error');
        window.psMarkNotificationsInFlight = false;
        return;
    }
    
    const markButton = document.querySelector('[data-action="mark-all-read"]');
    if (markButton) {
        markButton.disabled = true;
        if (!markButton.dataset.originalLabel) {
            markButton.dataset.originalLabel = markButton.innerHTML;
        }
        markButton.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Marcando...';
    }
    
    console.log('📡 Llamando al servidor...');
    
    // Usar fetch() para hacer la petición AJAX
    const url = '/my/student/mark_notifications_viewed';
    
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "call",
            params: {
                session_ids: sessionIds
            }
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log("✅ Respuesta del servidor:", data);
        const result = data.result || data;
        
        if (result.success) {
            unseenItems.forEach(function(item) {
                item.classList.remove('ps-notif-unseen');
            });
            const badge = document.querySelector('.ps-notif-badge');
            if (badge) {
                badge.style.display = 'none';
                badge.textContent = '';
            }
            showNotification('✓ ' + result.viewed_count + ' notificación(es) marcada(s) como leída(s)', 'success');
            if (typeof updateNotificationCount === 'function') {
                updateNotificationCount();
            }
        } else {
            showNotification('Error: ' + (result.error || 'No se pudieron marcar las notificaciones'), 'error');
        }
        if (markButton) {
            markButton.disabled = false;
            markButton.innerHTML = markButton.dataset.originalLabel || '<i class="fa fa-check"></i> Marcar todas como leídas';
        }
        window.psMarkNotificationsInFlight = false;
    })
    .catch(error => {
        console.error("❌ Error en la petición:", error);
        showNotification('Error al marcar notificaciones como leídas. Ver consola para más detalles.', 'error');
        if (markButton) {
            markButton.disabled = false;
            markButton.innerHTML = markButton.dataset.originalLabel || '<i class="fa fa-check"></i> Marcar todas como leídas';
        }
        window.psMarkNotificationsInFlight = false;
    });
};

console.log("✅ Función global psMarkNotificationsAsRead definida");
console.log("✅ Tipo:", typeof window.psMarkNotificationsAsRead);

// ==================== INICIALIZACIÓN ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log("🔵 DOM cargado - Inicializando portal_student");
    
    // Configurar botón de marcar como leídas
    const button = document.querySelector('.ps-btn-mark-read');
    if (button) {
        console.log("✅ Botón encontrado, añadiendo event listener");
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log("🔵 Click detectado en botón");
            window.psMarkNotificationsAsRead();
        });
    } else {
        console.warn("⚠️ No se encontró el botón .ps-btn-mark-read");
    }
    
    // También buscar botón por atributo data-action
    const markAllButton = document.querySelector('[data-action="mark-all-read"]');
    if (markAllButton) {
        console.log("✅ Botón mark-all-read encontrado, añadiendo event listener");
        markAllButton.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log("🔵 Click detectado en botón mark-all-read");
            window.psMarkNotificationsAsRead();
        });
    }
    
    // Polling cada 30 segundos para actualizar el contador
    setInterval(function() {
        updateNotificationCount();
    }, 30000);
    
    console.log("✅ Portal Student inicializado correctamente");
});

// ==================== FUNCIÓN AUXILIAR ====================
function updateNotificationCount() {
    fetch('/my/student/notifications_count', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "call",
            params: {}
        })
    })
    .then(response => response.json())
    .then(data => {
        const result = data.result || data;
        const badge = document.querySelector('.ps-notif-badge');
        const count = (typeof result.unseen_count === 'number') ? result.unseen_count : (result.count || 0);
        
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
    })
    .catch(error => {
        console.error("❌ Error al actualizar contador:", error);
    });
}

// Mantener compatibilidad con código existente del campus modal
window.psCampusModalHandler = true;
