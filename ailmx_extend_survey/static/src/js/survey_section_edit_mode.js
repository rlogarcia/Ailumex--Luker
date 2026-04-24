/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { QuestionPageListRenderer } from "@survey/question_page/question_page_list_renderer";

patch(QuestionPageListRenderer.prototype, {
    isInlineEditable(record) {
        if (this.isSection(record)) {
            return false;
        }
        return super.isInlineEditable(record);
    },
});