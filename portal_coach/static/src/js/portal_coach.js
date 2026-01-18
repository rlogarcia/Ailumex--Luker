/** @odoo-module **/

// Portal Coach JavaScript
// Funcionalidad adicional para el portal del coach

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.PortalCoach = publicWidget.Widget.extend({
    selector: '.o_portal_coach',

    /**
     * @override
     */
    start: function () {
        return this._super.apply(this, arguments);
    },
});

export default publicWidget.registry.PortalCoach;
