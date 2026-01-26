/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

// Agregar botón "Ir a Mi Portal" en el backend para coaches
class CoachPortalButton extends Component {
    setup() {
        // Verificar si el usuario es coach
        this.isCoach = session.user_groups && (
            session.user_groups.includes('portal_coach.group_benglish_coach') ||
            session.user_groups.includes('portal_coach.group_portal_coach')
        );
    }

    goToPortal() {
        window.location.href = '/my/coach';
    }
}

CoachPortalButton.template = "portal_coach.CoachPortalButton";

// Registrar el componente en el systray (menú superior derecho)
registry.category("systray").add("CoachPortalButton", {
    Component: CoachPortalButton,
    isDisplayed: (env) => {
        // Mostrar solo si el usuario tiene el grupo de coach
        return env.services.user && (
            env.services.user.groups?.includes('portal_coach.group_benglish_coach') ||
            env.services.user.groups?.includes('portal_coach.group_portal_coach')
        );
    },
}, { sequence: 1 });

// Solución simple: agregar botón flotante con JavaScript puro
document.addEventListener('DOMContentLoaded', function() {
    // Solo en el backend (no en portal)
    if (window.location.pathname.startsWith('/web')) {
        // Crear botón flotante
        const button = document.createElement('a');
        button.href = '/my/coach';
        button.className = 'btn btn-primary';
        button.innerHTML = '<i class="fa fa-home"></i> Mi Portal Coach';
        button.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
            padding: 12px 20px;
            border-radius: 25px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            font-weight: bold;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 8px;
        `;
        
        // Verificar si el usuario es coach antes de agregar el botón
        if (document.body.dataset.userGroups && 
            (document.body.dataset.userGroups.includes('group_benglish_coach') ||
             document.body.dataset.userGroups.includes('group_portal_coach'))) {
            document.body.appendChild(button);
        }
    }
});
