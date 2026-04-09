/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";

/**
 * Widget visual para el wizard del GRID matemático.
 * Igual que el de lectura pero con dos campos por celda:
 * - cell_value: contenido visible para el participante
 * - correct_value: valor correcto para evaluación
 */
class MathGridWizardWidget extends Component {
    static template = "ailmx_extend_survey.MathGridWizardWidget";
    static props = {
        record: Object,
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        this.state = useState({
            grid: [],
            cols: 3,
            rows: 2,
            // Modo de edición: 'value' = contenido visible, 'correct' = valor correcto
            editMode: 'value',
        });

        onWillStart(() => this._buildGrid());
    }

    _buildGrid() {
        const record = this.props.record;
        const cols = record.data.cols || 3;
        const rows = record.data.rows || 2;

        let cellMap = {};
        try {
            const jsonStr = record.data.grid_data_json || '[]';
            const cells = JSON.parse(jsonStr);
            for (const cell of cells) {
                cellMap[`${cell.row_index}_${cell.col_index}`] = {
                    cell_value: cell.cell_value || '',
                    correct_value: cell.correct_value || '',
                };
            }
        } catch (e) {
            cellMap = {};
        }

        const grid = [];
        for (let r = 0; r < rows; r++) {
            const row = [];
            for (let c = 0; c < cols; c++) {
                const data = cellMap[`${r}_${c}`] || {};
                row.push({
                    rowIndex: r,
                    colIndex: c,
                    cell_value: data.cell_value || '',
                    correct_value: data.correct_value || '',
                });
            }
            grid.push(row);
        }

        this.state.grid = grid;
        this.state.cols = cols;
        this.state.rows = rows;
    }

    setEditMode(mode) {
        this.state.editMode = mode;
    }

    onInput(rowIndex, colIndex, field, value) {
        this.state.grid[rowIndex][colIndex][field] = value;
        this._syncGridDataJson();
    }

    _syncGridDataJson() {
        const cells = [];
        for (const row of this.state.grid) {
            for (const cell of row) {
                cells.push({
                    row_index: cell.rowIndex,
                    col_index: cell.colIndex,
                    cell_value: cell.cell_value || '',
                    correct_value: cell.correct_value || '',
                });
            }
        }
        this.props.record.update({ grid_data_json: JSON.stringify(cells) });
    }

    onKeyDown(ev, rowIndex, colIndex) {
        if (ev.key !== 'Tab' && ev.key !== 'Enter') return;
        ev.preventDefault();

        const cols = this.state.cols;
        const rows = this.state.rows;
        const mode = this.state.editMode;
        let nextR = rowIndex;
        let nextC = ev.shiftKey ? colIndex - 1 : colIndex + 1;

        if (nextC >= cols) { nextC = 0; nextR++; }
        if (nextC < 0)     { nextC = cols - 1; nextR--; }
        if (nextR < 0 || nextR >= rows) return;

        const nextEl = document.getElementById(`ailmx_math_${mode}_${nextR}_${nextC}`);
        if (nextEl) nextEl.focus();
    }

    getCellDisplayValue(cell) {
        const mode = this.state.editMode;
        return mode === 'value' ? cell.cell_value : cell.correct_value;
    }
}

registry.category("fields").add("math_grid_wizard_widget", {
    component: MathGridWizardWidget,
    supportedTypes: ["one2many"],
});