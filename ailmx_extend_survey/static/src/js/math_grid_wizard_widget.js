/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";

class MathGridWizardWidget extends Component {
    static template = "ailmx_extend_survey.MathGridWizardWidget";
    static props = {
        record: Object,
        readonly: { type: Boolean, optional: true },
        id: { type: String, optional: true },
        name: { type: String, optional: true },
    };

    setup() {
        this.state = useState({
            grid: [],
            cols: 3,
            rows: 2,
            editMode: "value",
            showCommaModal: false,
            commaVisibleInput: "",
            commaCorrectInput: "",
            previewGrid: [],
        });

        this._openCommaModalHandler = () => {
            this.openCommaImportModal();
        };

        onWillStart(() => this._buildGrid());

        onMounted(() => {
            window.addEventListener(
                "ailmx_open_math_grid_comma_modal",
                this._openCommaModalHandler
            );
        });

        onWillUnmount(() => {
            window.removeEventListener(
                "ailmx_open_math_grid_comma_modal",
                this._openCommaModalHandler
            );
        });
    }

    _buildGrid() {
        const record = this.props.record;
        const cols = record.data.cols || 3;
        const rows = record.data.rows || 2;

        let cellMap = {};
        try {
            const jsonStr = record.data.grid_data_json || "[]";
            const cells = JSON.parse(jsonStr);
            for (const cell of cells) {
                cellMap[`${cell.row_index}_${cell.col_index}`] = {
                    cell_value: cell.cell_value || "",
                    correct_value: cell.correct_value || "",
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
                    cell_value: data.cell_value || "",
                    correct_value: data.correct_value || "",
                });
            }
            grid.push(row);
        }

        this.state.grid = grid;
        this.state.cols = cols;
        this.state.rows = rows;
        this._refreshPreviewFromCommaInputs();
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
                    cell_value: cell.cell_value || "",
                    correct_value: cell.correct_value || "",
                });
            }
        }
        this.props.record.update({ grid_data_json: JSON.stringify(cells) });
    }

    onKeyDown(ev, rowIndex, colIndex) {
        if (ev.key !== "Tab" && ev.key !== "Enter") return;
        ev.preventDefault();

        const cols = this.state.cols;
        const rows = this.state.rows;
        const mode = this.state.editMode;
        let nextR = rowIndex;
        let nextC = ev.shiftKey ? colIndex - 1 : colIndex + 1;

        if (nextC >= cols) {
            nextC = 0;
            nextR++;
        }
        if (nextC < 0) {
            nextC = cols - 1;
            nextR--;
        }
        if (nextR < 0 || nextR >= rows) return;

        const nextEl = document.getElementById(`ailmx_math_${mode}_${nextR}_${nextC}`);
        if (nextEl) nextEl.focus();
    }

    openCommaImportModal() {
        this.state.showCommaModal = true;
        this.state.commaVisibleInput = this._exportFieldAsCommaText("cell_value");
        this.state.commaCorrectInput = this._exportFieldAsCommaText("correct_value");
        this._refreshPreviewFromCommaInputs();
    }

    closeCommaImportModal() {
        this.state.showCommaModal = false;
    }

    onCommaVisibleInput(ev) {
        this.state.commaVisibleInput = ev.target.value || "";
        this._refreshPreviewFromCommaInputs();
    }

    onCommaCorrectInput(ev) {
        this.state.commaCorrectInput = ev.target.value || "";
        this._refreshPreviewFromCommaInputs();
    }

    applyCommaImport() {
        const visibleValues = this._parseCommaInput(this.state.commaVisibleInput);
        const correctValues = this._parseCommaInput(this.state.commaCorrectInput);
        let index = 0;

        for (let r = 0; r < this.state.rows; r++) {
            for (let c = 0; c < this.state.cols; c++) {
                this.state.grid[r][c].cell_value = visibleValues[index] || "";
                this.state.grid[r][c].correct_value = correctValues[index] || "";
                index++;
            }
        }

        this._syncGridDataJson();
        this.state.showCommaModal = false;
    }

    _parseCommaInput(rawText) {
        return (rawText || "").split(",").map((item) => item.trim());
    }

    _refreshPreviewFromCommaInputs() {
        const visibleValues = this._parseCommaInput(this.state.commaVisibleInput);
        const correctValues = this._parseCommaInput(this.state.commaCorrectInput);

        const previewGrid = [];
        let index = 0;

        for (let r = 0; r < this.state.rows; r++) {
            const row = {
                rowKey: `row_${r}`,
                cells: [],
            };
            for (let c = 0; c < this.state.cols; c++) {
                row.cells.push({
                    cellKey: `cell_${r}_${c}`,
                    visible: visibleValues[index] || "",
                    correct: correctValues[index] || "",
                });
                index++;
            }
            previewGrid.push(row);
        }

        this.state.previewGrid = previewGrid;
    }

    _exportFieldAsCommaText(fieldName) {
        const values = [];
        for (const row of this.state.grid) {
            for (const cell of row) {
                values.push((cell[fieldName] || "").trim());
            }
        }
        return values.join(", ");
    }
}

registry.category("fields").add("math_grid_wizard_widget", {
    component: MathGridWizardWidget,
    supportedTypes: ["one2many"],
});