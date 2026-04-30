/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { onMounted, onPatched } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { QuestionPageListRenderer } from "@survey/question_page/question_page_list_renderer";

window.__ailmx_new_questions_by_section = window.__ailmx_new_questions_by_section || {};
window.__ailmx_new_sections = window.__ailmx_new_sections || [];
window.__ailmx_deleted_sections = window.__ailmx_deleted_sections || [];
window.__ailmx_skip_deleted_section = false;
window.__ailmx_current_survey_id = window.__ailmx_current_survey_id || null;
window.__ailmx_structure_snapshot = window.__ailmx_structure_snapshot || null;

patch(QuestionPageListRenderer.prototype, {
    setup() {
        super.setup();

        this.action = useService("action");
        window.__ailmx_structure_action_service = this.action;

        onMounted(() => {
            setTimeout(() => renderVisualStructure(this), 300);
        });

        onPatched(() => {
            setTimeout(() => renderVisualStructure(this), 300);
        });
    },
});

function renderVisualStructure(renderer) {
    const fieldContainer = document.querySelector(".ailmx_structure_visual_builder_field");
    if (!fieldContainer) return;

    const table = fieldContainer.querySelector(".o_list_table");
    if (!table) return;

    const rows = Array.from(table.querySelectorAll("tbody tr.o_data_row"));
    if (!rows.length) return;

    const surveyId = getSurveyId(renderer);
    window.__ailmx_current_survey_id = surveyId;

    const oldBuilder = fieldContainer.querySelector(".ailmx_builder_container");

    if (window.__ailmx_structure_snapshot) {
        if (oldBuilder) {
            oldBuilder.remove();
        }

        const container = document.createElement("div");
        container.className = "ailmx_builder_container";

        table.style.display = "none";
        table.parentNode.appendChild(container);

        renderVisualStructureFromSnapshot(window.__ailmx_structure_snapshot, surveyId);
        return;
    }

    if (oldBuilder) oldBuilder.remove();

    const records = renderer?.props?.list?.records || [];
    const container = document.createElement("div");
    container.className = "ailmx_builder_container";

    let currentSection = null;
    window.__ailmx_skip_deleted_section = false;

    rows.forEach((row, index) => {
        const rowData = getRowData(row);
        if (!rowData.title) return;

        if (rowData.isSection) {
            if (isDeletedSection(rowData.title)) {
                currentSection = null;
                window.__ailmx_skip_deleted_section = true;
                return;
            }

            window.__ailmx_skip_deleted_section = false;

            const record = records[index];

            currentSection = createSectionBlock(
                rowData.title,
                surveyId,
                renderer,
                record?.resId
            );
            container.appendChild(currentSection.block);
            return;
        }

        if (window.__ailmx_skip_deleted_section) return;

        if (!currentSection) {
            currentSection = createSectionBlock("Sin sección", surveyId, renderer);
            container.appendChild(currentSection.block);
        }

        const record = records[index];

        const question = createQuestionItem({
            number: currentSection.count + 1,
            title: rowData.title,
            type: rowData.type,
            originalRow: row,
            questionId: record?.resId,
        });

        currentSection.questions.appendChild(question);
        currentSection.count += 1;
        currentSection.badge.textContent = `${currentSection.count} preguntas`;
    });

    container.appendChild(createAddSectionButton(surveyId, renderer));

    table.style.display = "none";
    table.parentNode.appendChild(container);

    restoreRememberedQuestions();
    restoreRememberedSections();
}

function getRowData(row) {
    const cells = Array.from(row.querySelectorAll("td"));
    const textCells = cells
        .map((cell) => cleanText(cell.innerText || cell.textContent || ""))
        .filter(Boolean);

    const title = textCells[0] || "";
    const type = textCells[1] || "";

    return {
        title,
        type,
        isSection: Boolean(title && !type),
    };
}

function createSectionBlock(title, surveyId, renderer, sectionId = null) {
    const block = document.createElement("div");
    block.className = "ailmx_section_block";

    const header = document.createElement("div");
    header.className = "ailmx_section_header";

    const titleEl = document.createElement("div");
    titleEl.className = "ailmx_section_block_title";

    const titleText = document.createElement("span");
    titleText.textContent = title;

    titleEl.appendChild(titleText);

    if (sectionId && cleanText(title) !== "Sin sección") {
        const editSectionButton = document.createElement("button");
        editSectionButton.type = "button";
        editSectionButton.className = "ailmx_section_edit_button";
        editSectionButton.innerHTML = "✎";
        editSectionButton.title = "Editar sección";

        editSectionButton.addEventListener("click", () => {
            openSectionModal(sectionId, surveyId);
        });

        titleEl.appendChild(editSectionButton);
    }

    const actions = document.createElement("div");
    actions.className = "ailmx_section_actions";

    const badge = document.createElement("span");
    badge.className = "ailmx_badge";
    badge.textContent = "0 preguntas";

    const addQuestionButton = document.createElement("button");
    addQuestionButton.type = "button";
    addQuestionButton.className = "ailmx_section_add_question";
    addQuestionButton.textContent = "+ Pregunta";
    addQuestionButton.addEventListener("click", () => {
        createQuestionInSection(title, surveyId, renderer);
    });

    const deleteSectionButton = document.createElement("button");
    deleteSectionButton.type = "button";
    deleteSectionButton.className = "ailmx_section_delete_button";
    deleteSectionButton.textContent = "× Eliminar sección";
    deleteSectionButton.addEventListener("click", () => {
        deleteSectionFromSurvey(title, surveyId, block);
    });

    actions.appendChild(badge);
    actions.appendChild(addQuestionButton);

    if (cleanText(title) !== "Sin sección") {
        actions.appendChild(deleteSectionButton);
    }

    header.appendChild(titleEl);
    header.appendChild(actions);

    const questions = document.createElement("div");
    questions.className = "ailmx_questions_list";

    block.appendChild(header);
    block.appendChild(questions);

    return {
        block,
        questions,
        badge,
        count: 0,
    };
}

function openSectionModal(sectionId, surveyId) {
    const actionService = window.__ailmx_structure_action_service;

    if (!actionService || !sectionId) {
        console.warn("[STRUCTURE_BUILDER] No se pudo abrir sección", sectionId);
        return;
    }

    actionService.doAction({
        type: "ir.actions.act_window",
        name: "Editar sección",
        res_model: "survey.question",
        res_id: sectionId,
        views: [[false, "form"]],
        view_mode: "form",
        target: "new",
    }, {
        onClose: function () {
            setTimeout(() => {
                syncSurveySections(surveyId);
            }, 800);
        },
    });
}

function createQuestionItem(question) {
    const item = document.createElement("div");
    item.className = "ailmx_question_item";
    item.draggable = true;

    if (question.questionId || question.id) {
        item.dataset.questionId = question.questionId || question.id;
    }

    const numberEl = document.createElement("div");
    numberEl.className = "ailmx_q_number";
    numberEl.textContent = question.number;

    const content = document.createElement("div");
    content.className = "ailmx_q_content";

    const titleEl = document.createElement("div");
    titleEl.className = "ailmx_q_title";
    titleEl.textContent = question.title || "Pregunta sin título";

    const typeEl = document.createElement("div");
    typeEl.className = "ailmx_q_type";
    typeEl.innerHTML = question.type
        ? `<span class="ailmx_q_label">Tipo:</span> ${escapeHtml(question.type)}`
        : `<span class="ailmx_q_label">Tipo:</span> Sin tipo definido`;

    content.appendChild(titleEl);
    content.appendChild(typeEl);

    const actions = createQuestionActions(question.originalRow, question.questionId || question.id);

    const dragHandle = document.createElement("div");
    dragHandle.className = "ailmx_drag_handle";
    dragHandle.innerHTML = "☰";
    dragHandle.title = "Arrastrar pregunta";
    
    item.appendChild(dragHandle);
    item.appendChild(numberEl);
    item.appendChild(content);
    item.appendChild(actions);

    enableDragForQuestion(item);
    return item;
}

function createQuestionActions(originalRow, questionId) {
    const actions = document.createElement("div");
    actions.className = "ailmx_q_actions";

    // const moveUpButton = createActionButton("↑", "", "Mover arriba");
    // moveUpButton.addEventListener("click", () => {
    //     moveQuestionInsideSection(questionId, "up", moveUpButton);
    // });

    // const moveDownButton = createActionButton("↓", "", "Mover abajo");
    // moveDownButton.addEventListener("click", () => {
    //     moveQuestionInsideSection(questionId, "down", moveDownButton);
    // });

    const editButton = createActionButton("✎", "Editar");
    editButton.addEventListener("click", () => {
        triggerRowOpen(originalRow, questionId);
    });

    const duplicateButton = createActionButton("⧉", "Duplicar");
    duplicateButton.addEventListener("click", () => {
        triggerRowDuplicate(originalRow, questionId, duplicateButton);
    });

    const deleteButton = createActionButton("×", "Eliminar");
    deleteButton.addEventListener("click", () => {
        triggerRowDelete(originalRow, questionId, deleteButton);
    });

    //actions.appendChild(moveUpButton);
    //actions.appendChild(moveDownButton);
    actions.appendChild(editButton);
    actions.appendChild(duplicateButton);
    actions.appendChild(deleteButton);

    return actions;
}

function createActionButton(icon, text, title = "") {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "ailmx_q_action_btn";
    button.innerHTML = text
        ? `<span class="ailmx_q_action_icon">${icon}</span> ${text}`
        : `<span class="ailmx_q_action_icon">${icon}</span>`;
    if (title) button.title = title;
    return button;
}

function triggerRowOpen(row, questionId = null) {
    if (row) {
        const firstDataCell = row.querySelector("td.o_data_cell");

        if (firstDataCell) {
            firstDataCell.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
            firstDataCell.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true, view: window }));
            return;
        }

        row.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true, view: window }));
        return;
    }

    if (questionId) {
        openQuestionModal(questionId);
    }
}

function openQuestionModal(questionId) {
    const actionService = window.__ailmx_structure_action_service;

    if (!actionService || !questionId) {
        console.warn("[STRUCTURE_BUILDER] No se pudo abrir pregunta", questionId);
        return;
    }

    actionService.doAction({
        type: "ir.actions.act_window",
        name: "Editar pregunta",
        res_model: "survey.question",
        res_id: questionId,
        views: [[false, "form"]],
        view_mode: "form",
        target: "new",
    }, {
        onClose: () => fetchUpdatedQuestionAndUpdateCard(questionId),
    });
}

function createQuestionInSection(sectionTitle, surveyId, renderer) {
    if (!surveyId) {
        console.warn("[STRUCTURE_BUILDER] No se encontró survey_id");
        return;
    }

    rpcCall("survey.question", "create_question_in_section", [surveyId, sectionTitle])
        .then((data) => {
            if (data.error || !data.result) {
                console.error("[STRUCTURE_BUILDER] Error creando pregunta:", data.error || data);
                return;
            }

            const actionService = getActionService(renderer);
            if (!actionService) {
                console.warn("[STRUCTURE_BUILDER] No se encontró servicio de acciones");
                return;
            }

            actionService.doAction(data.result, {
                onClose: function () {
                    setTimeout(() => {
                        syncSectionQuestions(sectionTitle, surveyId);
                    }, 800);
                },
            });
        })
        .catch((error) => console.error("[STRUCTURE_BUILDER]", error));
}

function syncSectionQuestions(sectionTitle, surveyId) {
    rpcCall("survey.question", "get_section_questions_for_builder", [surveyId, sectionTitle])
        .then((data) => {
            if (data.error) {
                console.error("[STRUCTURE_BUILDER] Error sincronizando sección:", data.error);
                return;
            }

            const section = findSectionBlock(sectionTitle);
            if (!section) return;

            const list = section.querySelector(".ailmx_questions_list");
            if (!list) return;

            list.innerHTML = "";

            const questions = data.result || [];

            questions.forEach((question, index) => {
                const card = createQuestionItem({
                    number: index + 1,
                    title: question.title,
                    type: question.type,
                    originalRow: null,
                    questionId: question.id,
                });

                list.appendChild(card);
            });

            updateSectionBadge(section);
        })
        .catch((error) => console.error("[STRUCTURE_BUILDER]", error));
}

function triggerRowDuplicate(row, questionId = null, buttonElement = null) {
    if (row) {
        const duplicateElement =
            row.querySelector(".fa-clone") ||
            row.querySelector(".fa-copy") ||
            row.querySelector("[title='Duplicar']") ||
            row.querySelector("[aria-label='Duplicar']");

        clickClosestAction(duplicateElement);
        return;
    }

    if (!questionId || !buttonElement) return;

    rpcCall("survey.question", "duplicate_question_in_section", [questionId])
        .then((data) => {
            if (data.error || !data.result) {
                console.error("[STRUCTURE_BUILDER] Error duplicando pregunta:", data.error || data);
                return;
            }

            const originalCard = buttonElement.closest(".ailmx_question_item");
            const list = originalCard.closest(".ailmx_questions_list");
            const section = originalCard.closest(".ailmx_section_block");
            const sectionTitle = section.querySelector(".ailmx_section_block_title")?.textContent || "";

            const duplicatedQuestion = {
                id: data.result.id,
                title: data.result.title,
                type: data.result.type,
            };

            const card = createQuestionItem({
                number: list.querySelectorAll(".ailmx_question_item").length + 1,
                title: duplicatedQuestion.title,
                type: duplicatedQuestion.type,
                originalRow: null,
                questionId: duplicatedQuestion.id,
            });

            originalCard.after(card);

            rememberNewQuestion(sectionTitle, duplicatedQuestion);
            renumberQuestionCards(list);
            updateSectionBadge(section);
        })
        .catch((error) => console.error("[STRUCTURE_BUILDER]", error));
}

function triggerRowDelete(row, questionId = null, buttonElement = null) {
    if (row) {
        const deleteElement =
            row.querySelector(".o_list_record_remove") ||
            row.querySelector(".fa-trash") ||
            row.querySelector("[title='Eliminar']") ||
            row.querySelector("[aria-label='Eliminar']");

        clickClosestAction(deleteElement);
        return;
    }

    if (!questionId || !buttonElement) return;

    rpcCall("survey.question", "unlink", [[questionId]])
        .then((data) => {
            if (data.error) {
                console.error("[STRUCTURE_BUILDER] Error eliminando pregunta:", data.error);
                return;
            }

            const card = buttonElement.closest(".ailmx_question_item");
            const list = card.closest(".ailmx_questions_list");
            const section = card.closest(".ailmx_section_block");

            forgetNewQuestion(questionId);

            card.remove();
            renumberQuestionCards(list);
            updateSectionBadge(section);
        })
        .catch((error) => console.error("[STRUCTURE_BUILDER]", error));
}

function moveQuestionInsideSection(questionId, direction, buttonElement) {
    if (!questionId) {
        console.warn("[STRUCTURE_BUILDER] No se encontró question_id");
        return;
    }

    rpcCall("survey.question", "move_question_inside_section", [questionId, direction])
        .then((data) => {
            if (data.error) {
                console.error("[STRUCTURE_BUILDER] Error moviendo pregunta:", data.error);
                return;
            }

            if (data.result) {
                moveQuestionCardVisually(buttonElement, direction);
            }
        })
        .catch((error) => console.error("[STRUCTURE_BUILDER]", error));
}

function moveQuestionCardVisually(buttonElement, direction) {
    const card = buttonElement.closest(".ailmx_question_item");
    const list = card?.closest(".ailmx_questions_list");

    if (!card || !list) return;

    if (direction === "up") {
        const previous = card.previousElementSibling;
        if (previous) list.insertBefore(card, previous);
    }

    if (direction === "down") {
        const next = card.nextElementSibling;
        if (next) list.insertBefore(next, card);
    }

    renumberQuestionCards(list);
}

function createSectionInSurvey(surveyId, renderer) {
    if (!surveyId) {
        console.warn("[STRUCTURE_BUILDER] No se encontró survey_id para crear sección");
        return;
    }

    rpcCall("survey.question", "create_section_in_survey", [surveyId])
        .then((data) => {
            if (data.error || !data.result) {
                console.error("[STRUCTURE_BUILDER] Error creando sección:", data.error || data);
                return;
            }

            const actionService = getActionService(renderer);
            if (!actionService) {
                console.warn("[STRUCTURE_BUILDER] No se encontró servicio de acciones para sección");
                return;
            }

            actionService.doAction(data.result, {
                onClose: function () {
                    setTimeout(() => {
                        syncSurveySections(surveyId);
                    }, 800);
                },
            });
        })
        .catch((error) => console.error("[STRUCTURE_BUILDER]", error));
}

function deleteSectionFromSurvey(sectionTitle, surveyId, sectionBlock) {
    if (!surveyId) {
        console.warn("[STRUCTURE_BUILDER] No se encontró survey_id para eliminar sección");
        return;
    }

    rpcCall("survey.question", "delete_section_from_survey", [sectionTitle, surveyId])
        .then((data) => {
            if (data.error || !data.result) {
                console.error("[STRUCTURE_BUILDER] Error eliminando sección:", data.error || data);
                return;
            }

            rememberDeletedSection(sectionTitle);
            forgetNewSection(sectionTitle);
            sectionBlock.remove();
        })
        .catch((error) => console.error("[STRUCTURE_BUILDER]", error));
}

function createAddSectionButton(surveyId, renderer) {
    const wrapper = document.createElement("div");
    wrapper.className = "ailmx_add_section_wrapper";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "ailmx_add_section_button";
    button.textContent = "+ Agregar sección";
    button.addEventListener("click", () => createSectionInSurvey(surveyId, renderer));

    wrapper.appendChild(button);
    return wrapper;
}

function fetchUpdatedQuestionAndRemember(sectionTitle, questionId) {
    readQuestion(questionId)
        .then((question) => {
            if (!question) return;

            rememberNewQuestion(sectionTitle, question);
            addQuestionCardVisually(sectionTitle, question);
        })
        .catch((error) => console.error("[STRUCTURE_BUILDER]", error));
}

function fetchUpdatedQuestionAndUpdateCard(questionId) {
    readQuestion(questionId)
        .then((updatedQuestion) => {
            if (!updatedQuestion) return;

            updateRememberedQuestion(questionId, updatedQuestion);

            const card = document.querySelector(`.ailmx_question_item[data-question-id="${questionId}"]`);
            if (!card) return;

            const title = card.querySelector(".ailmx_q_title");
            const type = card.querySelector(".ailmx_q_type");

            if (title) title.textContent = updatedQuestion.title;
            if (type) type.innerHTML = `<span class="ailmx_q_label">Tipo:</span> ${escapeHtml(updatedQuestion.type)}`;
        })
        .catch((error) => console.error("[STRUCTURE_BUILDER]", error));
}

function readQuestion(questionId) {
    return rpcCall("survey.question", "read", [[questionId], ["title", "question_type"]])
        .then((data) => {
            if (data.error || !data.result || !data.result.length) {
                console.warn("[STRUCTURE_BUILDER] No se pudo leer la pregunta", data);
                return null;
            }

            const question = data.result[0];

            return {
                id: questionId,
                title: question.title || "Pregunta sin título",
                type: getQuestionTypeLabel(question.question_type),
            };
        });
}

function fetchUpdatedSectionAndRemember(sectionId) {
    rpcCall("survey.question", "read", [[sectionId], ["title"]])
        .then((data) => {
            if (data.error || !data.result || !data.result.length) {
                console.warn("[STRUCTURE_BUILDER] No se pudo leer sección actualizada", data);
                return;
            }

            const section = {
                id: sectionId,
                title: data.result[0].title || "Nueva sección",
            };

            rememberNewSection(section);
            addSectionBlockVisually(section);
        })
        .catch((error) => console.error("[STRUCTURE_BUILDER]", error));
}

function addQuestionCardVisually(sectionTitle, question) {
    const section = findSectionBlock(sectionTitle);
    if (!section) return;

    const list = section.querySelector(".ailmx_questions_list");
    const badge = section.querySelector(".ailmx_badge");

    if (!list || !badge) return;

    const currentCount = list.querySelectorAll(".ailmx_question_item").length;

    const card = createQuestionItem({
        number: currentCount + 1,
        title: question.title || "Nueva pregunta",
        type: question.type || "Sin tipo definido",
        originalRow: null,
        questionId: question.id,
    });

    list.appendChild(card);
    badge.textContent = `${currentCount + 1} preguntas`;
}

function addSectionBlockVisually(section) {
    const container = document.querySelector(".ailmx_builder_container");
    if (!container) return;

    const exists = Array.from(container.querySelectorAll(".ailmx_section_block_title")).some((title) => {
        return cleanText(title.textContent) === cleanText(section.title);
    });

    if (exists) return;

    const addSectionWrapper = container.querySelector(".ailmx_add_section_wrapper");

    const blockData = createSectionBlock(
        section.title,
        window.__ailmx_current_survey_id,
        null
    );

    if (addSectionWrapper) {
        container.insertBefore(blockData.block, addSectionWrapper);
    } else {
        container.appendChild(blockData.block);
    }
}

function findSectionBlock(sectionTitle) {
    return Array.from(document.querySelectorAll(".ailmx_section_block")).find((sectionBlock) => {
        const title = sectionBlock.querySelector(".ailmx_section_block_title");
        return title && cleanText(title.textContent) === cleanText(sectionTitle);
    });
}

function rememberNewQuestion(sectionTitle, question) {
    const key = cleanText(sectionTitle);

    if (!window.__ailmx_new_questions_by_section[key]) {
        window.__ailmx_new_questions_by_section[key] = [];
    }

    const exists = window.__ailmx_new_questions_by_section[key].some((item) => Number(item.id) === Number(question.id));

    if (!exists) {
        window.__ailmx_new_questions_by_section[key].push(question);
    }
}

function restoreRememberedQuestions() {
    const memory = window.__ailmx_new_questions_by_section || {};

    Object.keys(memory).forEach((sectionTitle) => {
        memory[sectionTitle].forEach((question) => {
            addQuestionCardVisually(sectionTitle, question);
        });
    });
}

function forgetNewQuestion(questionId) {
    const memory = window.__ailmx_new_questions_by_section || {};

    Object.keys(memory).forEach((sectionTitle) => {
        memory[sectionTitle] = memory[sectionTitle].filter((question) => Number(question.id) !== Number(questionId));

        if (!memory[sectionTitle].length) {
            delete memory[sectionTitle];
        }
    });
}

function updateRememberedQuestion(questionId, updatedQuestion) {
    const memory = window.__ailmx_new_questions_by_section || {};

    Object.keys(memory).forEach((sectionTitle) => {
        memory[sectionTitle] = memory[sectionTitle].map((question) => {
            if (Number(question.id) === Number(questionId)) {
                return {
                    ...question,
                    title: updatedQuestion.title || question.title,
                    type: updatedQuestion.type || question.type,
                };
            }

            return question;
        });
    });
}

function rememberNewSection(section) {
    const exists = window.__ailmx_new_sections.some((item) => Number(item.id) === Number(section.id));

    if (!exists) {
        window.__ailmx_new_sections.push(section);
    }
}

function restoreRememberedSections() {
    const sections = window.__ailmx_new_sections || [];
    sections.forEach((section) => addSectionBlockVisually(section));
}

function forgetNewSection(sectionTitle) {
    window.__ailmx_new_sections = (window.__ailmx_new_sections || []).filter((section) => {
        return cleanText(section.title) !== cleanText(sectionTitle);
    });
}

function rememberDeletedSection(sectionTitle) {
    const key = cleanText(sectionTitle);

    if (!window.__ailmx_deleted_sections.includes(key)) {
        window.__ailmx_deleted_sections.push(key);
    }
}

function isDeletedSection(sectionTitle) {
    return window.__ailmx_deleted_sections.includes(cleanText(sectionTitle));
}

function updateSectionBadge(section) {
    if (!section) return;

    const badge = section.querySelector(".ailmx_badge");
    const count = section.querySelectorAll(".ailmx_question_item").length;

    if (badge) badge.textContent = `${count} preguntas`;
}

function renumberQuestionCards(list) {
    const cards = Array.from(list.querySelectorAll(".ailmx_question_item"));

    cards.forEach((card, index) => {
        const number = card.querySelector(".ailmx_q_number");
        if (number) number.textContent = index + 1;
    });
}

function clickClosestAction(element) {
    if (!element) {
        console.warn("[STRUCTURE_BUILDER] No se encontró acción nativa.");
        return;
    }

    const clickable = element.closest("button, a, span, i") || element;
    clickable.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
}

function getActionService(renderer) {
    return renderer?.env?.services?.action ||
        renderer?.action ||
        window.__ailmx_structure_action_service;
}

function getSurveyId(renderer) {
    try {
        const records = renderer?.props?.list?.records || [];

        for (const record of records) {
            const surveyValue = record.data?.survey_id;

            if (Array.isArray(surveyValue) && surveyValue[0]) return surveyValue[0];
            if (surveyValue && surveyValue.resId) return surveyValue.resId;
            if (typeof surveyValue === "number") return surveyValue;
        }
    } catch (error) {
        console.warn("[STRUCTURE_BUILDER] No se pudo leer survey_id desde records", error);
    }

    const match = window.location.href.match(/[?&#]id=(\d+)/);
    return match ? parseInt(match[1], 10) : null;
}

function rpcCall(model, method, args = [], kwargs = {}) {
    return fetch(`/web/dataset/call_kw/${model}/${method}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "call",
            params: {
                model,
                method,
                args,
                kwargs,
            },
        }),
    }).then((res) => res.json());
}

function cleanText(value) {
    return String(value || "")
        .replace(/\s+/g, " ")
        .trim();
}

function getQuestionTypeLabel(questionType) {
    const labels = {
        simple_choice: "Opción múltiple: solo una respuesta",
        multiple_choice: "Opción múltiple: varias respuestas",
        text_box: "Cuadro de texto de una línea",
        char_box: "Cuadro de texto de una línea",
        numerical_box: "Valor numérico",
        date: "Fecha",
        datetime: "Fecha y hora",
        matrix: "Matriz",
        reading_grid: "GRID lectura",
        math_grid: "GRID matemático",
    };

    return labels[questionType] || questionType || "Sin tipo definido";
}

function enableDragForQuestion(item) {
    item.addEventListener("dragstart", function (event) {
        item.classList.add("ailmx_dragging");
        event.dataTransfer.effectAllowed = "move";
    });

    item.addEventListener("dragend", function () {
        item.classList.remove("ailmx_dragging");

        renumberAllSections();
        saveQuestionOrderBetweenSections();
    });
}

document.addEventListener("dragover", function (event) {
    const dragging = document.querySelector(".ailmx_dragging");
    if (!dragging) return;

    const targetList = event.target.closest(".ailmx_questions_list");
    if (!targetList) return;

    event.preventDefault();

    const targetCard = event.target.closest(".ailmx_question_item");

    if (!targetCard) {
        targetList.appendChild(dragging);
        return;
    }

    if (targetCard === dragging) return;

    const rect = targetCard.getBoundingClientRect();
    const shouldMoveAfter = event.clientY > rect.top + rect.height / 2;

    if (shouldMoveAfter) {
        targetCard.after(dragging);
    } else {
        targetCard.before(dragging);
    }
});

function saveQuestionOrderInsideSection(list) {
    const orderedIds = Array.from(list.querySelectorAll(".ailmx_question_item"))
        .map((card) => card.dataset.questionId)
        .filter(Boolean);

    if (!orderedIds.length) {
        return;
    }

    rpcCall("survey.question", "reorder_questions_inside_section", [orderedIds])
        .then((data) => {
            if (data.error) {
                console.error("[STRUCTURE_BUILDER] Error guardando orden:", data.error);
            }
        })
        .catch((error) => {
            console.error("[STRUCTURE_BUILDER]", error);
        });
}

function renumberAllSections() {
    const lists = document.querySelectorAll(".ailmx_questions_list");

    lists.forEach((list) => {
        renumberQuestionCards(list);
        updateSectionBadge(list.closest(".ailmx_section_block"));
    });
}

function collectSectionOrders() {
    const sections = Array.from(document.querySelectorAll(".ailmx_section_block"));

    return sections.map((section) => {
        const title = section.querySelector(".ailmx_section_block_title");
        const list = section.querySelector(".ailmx_questions_list");

        return {
            section_title: cleanText(title ? title.textContent : ""),
            question_ids: Array.from(list.querySelectorAll(".ailmx_question_item"))
                .map((card) => card.dataset.questionId)
                .filter(Boolean),
        };
    });
}

function saveQuestionOrderBetweenSections() {
    const sectionOrders = collectSectionOrders();

    window.__ailmx_structure_snapshot = buildSnapshotFromCurrentBuilder();

    rpcCall("survey.question", "reorder_questions_between_sections", [sectionOrders])
        .then((data) => {
            if (data.error) {
                console.error("[STRUCTURE_BUILDER] Error guardando orden entre secciones:", data.error);
                return;
            }
        })
        .catch((error) => {
            console.error("[STRUCTURE_BUILDER]", error);
        });
}

function buildSnapshotFromCurrentBuilder() {
    const sections = Array.from(document.querySelectorAll(".ailmx_section_block"));

    return sections.map((section) => {
        const title = section.querySelector(".ailmx_section_block_title")?.textContent || "";

        const questions = Array.from(section.querySelectorAll(".ailmx_question_item")).map((card) => {
            return {
                id: card.dataset.questionId,
                title: card.querySelector(".ailmx_q_title")?.textContent || "Pregunta sin título",
                type: cleanText(
                    (card.querySelector(".ailmx_q_type")?.textContent || "")
                        .replace("Tipo:", "")
                ),
            };
        });

        return {
            title: cleanText(title),
            questions,
        };
    });
}

function renderVisualStructureFromSnapshot(snapshot, surveyId) {
    const container = document.querySelector(".ailmx_builder_container");

    if (!container) {
        return;
    }

    container.innerHTML = "";

    snapshot.forEach((sectionData) => {
        if (isDeletedSection(sectionData.title)) return;

        const section = createSectionBlock(
            sectionData.title,
            surveyId,
            null,
            sectionData.id
        );

        container.appendChild(section.block);

        sectionData.questions.forEach((question, index) => {
            const card = createQuestionItem({
                number: index + 1,
                title: question.title,
                type: question.type,
                originalRow: null,
                questionId: question.id,
            });

            section.questions.appendChild(card);
            section.count += 1;
        });

        section.badge.textContent = `${section.count} preguntas`;
    });

    container.appendChild(createAddSectionButton(surveyId, null));
}

function syncSurveySections(surveyId) {
    renderVisualStructureFromServer(surveyId);
}

function renderVisualStructureFromServer(surveyId) {
    if (!surveyId) return;

    rpcCall("survey.question", "get_survey_structure_for_builder", [surveyId])
        .then((data) => {
            if (data.error) {
                console.error("[STRUCTURE_BUILDER] Error sincronizando estructura:", data.error);
                return;
            }

            const container = document.querySelector(".ailmx_builder_container");
            if (!container) return;

            container.innerHTML = "";

            const sections = data.result || [];

            window.__ailmx_structure_snapshot = sections;

            sections.forEach((sectionData) => {
                if (isDeletedSection(sectionData.title)) return;

                const section = createSectionBlock(
                    sectionData.title,
                    surveyId,
                    null,
                    sectionData.id
                );

                container.appendChild(section.block);

                sectionData.questions.forEach((question, index) => {
                    const card = createQuestionItem({
                        number: index + 1,
                        title: question.title,
                        type: question.type,
                        originalRow: null,
                        questionId: question.id,
                    });

                    section.questions.appendChild(card);
                    section.count += 1;
                });

                section.badge.textContent = `${section.count} preguntas`;
            });

            container.appendChild(createAddSectionButton(surveyId, null));
        })
        .catch((error) => {
            console.error("[STRUCTURE_BUILDER]", error);
        });
}

function escapeHtml(value) {
    return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}