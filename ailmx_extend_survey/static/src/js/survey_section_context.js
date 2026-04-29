/** @odoo-module **/

function moveSectionContextToTop() {
    const surveyRoot = document.querySelector(".o_survey_form_content");
    const sectionBox = document.querySelector(".ailmx_section_context_box");

    if (!surveyRoot || !sectionBox) {
        return;
    }

    if (surveyRoot.firstElementChild !== sectionBox) {
        surveyRoot.prepend(sectionBox);
    }
}

document.addEventListener("DOMContentLoaded", function () {
    moveSectionContextToTop();

    const surveyRoot = document.querySelector(".o_survey_form_content");

    if (surveyRoot) {
        new MutationObserver(function () {
            moveSectionContextToTop();
        }).observe(surveyRoot, {
            childList: true,
            subtree: true,
        });
    }
});