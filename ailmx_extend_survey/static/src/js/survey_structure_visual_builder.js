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

    const oldBuilder = fieldContainer.querySelector(".ailmx_builder_container");
    if (oldBuilder) oldBuilder.remove();

    const rows = Array.from(table.querySelectorAll("tbody tr.o_data_row"));
    if (!rows.length) return;

    const surveyId = getSurveyId(renderer);
    window.__ailmx_current_survey_id = surveyId;

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
            currentSection = createSectionBlock(rowData.title, surveyId, renderer);
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

function createSectionBlock(title, surveyId, renderer) {
    const block = document.createElement("div");
    block.className = "ailmx_section_block";

    const header = document.createElement("div");
    header.className = "ailmx_section_header";

    const titleEl = document.createElement("div");
    titleEl.className = "ailmx_section_block_title";
    titleEl.textContent = title;

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
    actions.appendChild(deleteSectionButton);

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

function createQuestionItem(question) {
    const item = document.createElement("div");
    item.className = "ailmx_question_item";

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

    item.appendChild(numberEl);
    item.appendChild(content);
    item.appendChild(actions);

    return item;
}

function createQuestionActions(originalRow, questionId) {
    const actions = document.createElement("div");
    actions.className = "ailmx_q_actions";

    const moveUpButton = createActionButton("↑", "", "Mover arriba");
    moveUpButton.addEventListener("click", () => {
        moveQuestionInsideSection(questionId, "up", moveUpButton);
    });

    const moveDownButton = createActionButton("↓", "", "Mover abajo");
    moveDownButton.addEventListener("click", () => {
        moveQuestionInsideSection(questionId, "down", moveDownButton);
    });

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

    actions.appendChild(moveUpButton);
    actions.appendChild(moveDownButton);
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
                    window.location.reload();
                },
            });
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
                    window.location.reload();
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

function escapeHtml(value) {
    return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}