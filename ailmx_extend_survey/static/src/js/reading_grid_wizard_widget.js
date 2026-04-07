/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";

class ReadingGridWizardWidget extends Component {
    static template = "ailmx_extend_survey.ReadingGridWizardWidget";
    static props = {
        record: Object,
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        this.state = useState({
            grid: [],
            cols: 3,
            rows: 2,
        });

        onWillStart(() => this._buildGrid());
    }

    _buildGrid() {
        const record = this.props.record;
        const cols = record.data.cols || 3;
        const rows = record.data.rows || 2;

        // Leer desde grid_data_json — tiene los índices y valores correctos
        let cellMap = {};
        try {
            const jsonStr = record.data.grid_data_json || '[]';
            const cells = JSON.parse(jsonStr);
            for (const cell of cells) {
                cellMap[`${cell.row_index}_${cell.col_index}`] = cell.cell_value || '';
            }
        } catch (e) {
            cellMap = {};
        }

        const grid = [];
        for (let r = 0; r < rows; r++) {
            const row = [];
            for (let c = 0; c < cols; c++) {
                row.push({
                    rowIndex: r,
                    colIndex: c,
                    value: cellMap[`${r}_${c}`] || '',
                });
            }
            grid.push(row);
        }

        this.state.grid = grid;
        this.state.cols = cols;
        this.state.rows = rows;
    }

    onInput(rowIndex, colIndex, value) {
        this.state.grid[rowIndex][colIndex].value = value;
        this._syncGridDataJson();
    }

    _syncGridDataJson() {
        const cells = [];
        for (const row of this.state.grid) {
            for (const cell of row) {
                cells.push({
                    row_index: cell.rowIndex,
                    col_index: cell.colIndex,
                    cell_value: cell.value || '',
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
        let nextR = rowIndex;
        let nextC = ev.shiftKey ? colIndex - 1 : colIndex + 1;

        if (nextC >= cols) { nextC = 0; nextR++; }
        if (nextC < 0)     { nextC = cols - 1; nextR--; }
        if (nextR < 0 || nextR >= rows) return;

        const nextEl = document.getElementById(`ailmx_cell_${nextR}_${nextC}`);
        if (nextEl) nextEl.focus();
    }
}

registry.category("fields").add("reading_grid_wizard_widget", {
    component: ReadingGridWizardWidget,
    supportedTypes: ["one2many"],
});