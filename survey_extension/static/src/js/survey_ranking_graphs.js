/** @odoo-module **/
/**
 * ARCHIVO: survey_ranking_graphs.js
 * PROPÓSITO: Forzar solo medida "Número" en gráficos de ranking
 * FECHA: 2025-10-24
 */

import { patch } from "@web/core/utils/patch";
import { GraphModel } from "@web/views/graph/graph_model";

// Patch del modelo de gráficos
patch(GraphModel.prototype, {
    /**
     * Sobrescribir la carga de datos para forzar __count
     */
    async load(params) {
        const result = await super.load(params);
        
        // Si es survey.user_input, filtrar medidas
        if (this.metaData.resModel === 'survey.user_input') {
            // Forzar solo __count
            this.metaData.measure = '__count';
            
            // Filtrar measures para dejar solo __count
            const measures = this.metaData.measures || {};
            this.metaData.measures = {};
            
            if (measures['__count']) {
                this.metaData.measures['__count'] = measures['__count'];
            } else {
                this.metaData.measures['__count'] = {
                    string: 'Número',
                    type: 'integer',
                    name: '__count'
                };
            }
            
            console.log('✅ Solo medida "Número" disponible');
        }
        
        return result;
    },
});

console.log('� Módulo cargado: Solo medida "Número" en gráficos de ranking');
