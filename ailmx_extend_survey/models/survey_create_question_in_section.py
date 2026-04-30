# -*- coding: utf-8 -*-

from odoo import models, api


class SurveyCreateQuestionInSection(models.Model):
    _inherit = 'survey.question'

    @api.model
    def create_question_in_section(self, survey_id, section_title):
        survey = self.env['survey.survey'].browse(int(survey_id))

        if not survey.exists():
            return False

        items = survey.question_and_page_ids.sorted(key=lambda q: (q.sequence, q.id))

        # =========================================================
        # CASO 1: BLOQUE VISUAL "SIN SECCIÓN"
        # =========================================================
        if (section_title or '').strip().lower() == 'sin sección':
            questions_without_section = []

            for item in items:
                if item.is_page:
                    break

                questions_without_section.append(item)

            if questions_without_section:
                new_sequence = questions_without_section[-1].sequence + 1
            elif items:
                # Si ya hay secciones, insertar antes de la primera sección
                first_item = items[0]
                new_sequence = first_item.sequence - 1
            else:
                new_sequence = 10

            return {
                'type': 'ir.actions.act_window',
                'name': 'Nueva pregunta',
                'res_model': 'survey.question',
                'views': [(False, 'form')],
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_survey_id': survey.id,
                    'default_title': 'Nueva pregunta',
                    'default_sequence': new_sequence,
                    'default_is_page': False,
                },
            }

        # =========================================================
        # CASO 2: SECCIÓN REAL
        # =========================================================
        target_section = False
        section_items = []
        inside_section = False

        for item in items:
            if item.is_page:
                if inside_section:
                    break

                if (item.title or '').strip() == (section_title or '').strip():
                    target_section = item
                    inside_section = True
                    continue

            elif inside_section:
                section_items.append(item)

        if not target_section:
            return False

        if section_items:
            new_sequence = section_items[-1].sequence + 1
        else:
            new_sequence = target_section.sequence + 1

        return {
            'type': 'ir.actions.act_window',
            'name': 'Nueva pregunta',
            'res_model': 'survey.question',
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_survey_id': survey.id,
                'default_title': 'Nueva pregunta',
                'default_sequence': new_sequence,
                'default_is_page': False,
            },
        }

    @api.model
    def move_question_inside_section(self, question_id, direction):
        question = self.env['survey.question'].browse(int(question_id))

        if not question.exists() or question.is_page or not question.survey_id:
            return False

        survey = question.survey_id
        items = survey.question_and_page_ids.sorted(key=lambda q: (q.sequence, q.id))

        section_questions = []
        inside_question_section = False

        for item in items:
            if item.is_page:
                # Si ya estábamos dentro de la sección de la pregunta,
                # al encontrar otra sección paramos.
                if inside_question_section:
                    break

                # La sección correcta es la page_id de la pregunta.
                if question.page_id and item.id == question.page_id.id:
                    inside_question_section = True

                continue

            if inside_question_section:
                section_questions.append(item)

        if question not in section_questions:
            return False

        current_index = section_questions.index(question)

        if direction == 'up':
            if current_index == 0:
                return False
            target_question = section_questions[current_index - 1]

        elif direction == 'down':
            if current_index >= len(section_questions) - 1:
                return False
            target_question = section_questions[current_index + 1]

        else:
            return False

        current_sequence = question.sequence
        question.write({'sequence': target_question.sequence})
        target_question.write({'sequence': current_sequence})

        return True

    @api.model
    def duplicate_question_in_section(self, question_id):
        original = self.env['survey.question'].browse(int(question_id))

        if not original.exists() or original.is_page or not original.survey_id:
            return False

        survey = original.survey_id

        new_question = original.copy({
            'title': '%s (copia)' % (original.title or 'Pregunta'),
            'sequence': original.sequence + 0.1,
        })

        items = survey.question_and_page_ids.sorted(key=lambda q: (q.sequence, q.id))

        sequence = 10
        for item in items:
            item.write({'sequence': sequence})
            sequence += 10

        return {
            'id': new_question.id,
            'title': new_question.title,
            'type': dict(new_question._fields['question_type'].selection).get(
                new_question.question_type,
                new_question.question_type or 'Sin tipo definido'
            ),
        }

    @api.model
    def create_section_in_survey(self, survey_id):
        survey = self.env['survey.survey'].browse(int(survey_id))

        if not survey.exists():
            return False

        items = survey.question_and_page_ids.sorted(key=lambda q: (q.sequence, q.id))

        if items:
            new_sequence = max(item.sequence for item in items) + 10
        else:
            new_sequence = 10

        return {
            'type': 'ir.actions.act_window',
            'name': 'Nueva sección',
            'res_model': 'survey.question',
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_survey_id': survey.id,
                'default_title': 'Nueva sección',
                'default_is_page': True,
                'default_sequence': new_sequence,
            },
        }

    @api.model
    def delete_section_from_survey(self, section_title, survey_id):
        survey = self.env['survey.survey'].browse(int(survey_id))

        if not survey.exists():
            return False

        items = survey.question_and_page_ids.sorted(key=lambda q: (q.sequence, q.id))

        target_section = False

        for item in items:
            if item.is_page and (item.title or '').strip() == (section_title or '').strip():
                target_section = item
                break

        if not target_section:
            return False

        target_section.unlink()
        return True

    @api.model
    def get_section_questions_for_builder(self, survey_id, section_title):
        survey = self.env['survey.survey'].browse(int(survey_id))

        if not survey.exists():
            return []

        items = survey.question_and_page_ids.sorted(key=lambda q: (q.sequence, q.id))
        section_title_clean = (section_title or '').strip().lower()

        questions = []

        # =========================================================
        # CASO 1: BLOQUE VISUAL "SIN SECCIÓN"
        # =========================================================
        if section_title_clean == 'sin sección':
            for item in items:
                if item.is_page:
                    break

                questions.append({
                    'id': item.id,
                    'title': item.title or 'Pregunta sin título',
                    'type': dict(item._fields['question_type'].selection).get(
                        item.question_type,
                        item.question_type or 'Sin tipo definido'
                    ),
                })

            return questions

        # =========================================================
        # CASO 2: SECCIÓN REAL
        # =========================================================
        inside_section = False

        for item in items:
            if item.is_page:
                if inside_section:
                    break

                if (item.title or '').strip() == (section_title or '').strip():
                    inside_section = True

                continue

            if inside_section:
                questions.append({
                    'id': item.id,
                    'title': item.title or 'Pregunta sin título',
                    'type': dict(item._fields['question_type'].selection).get(
                        item.question_type,
                        item.question_type or 'Sin tipo definido'
                    ),
                })

        return questions

    @api.model
    def reorder_questions_inside_section(self, ordered_question_ids):
        if not ordered_question_ids:
            return False

        questions = self.env['survey.question'].browse([int(qid) for qid in ordered_question_ids])

        if not questions:
            return False

        sequence = 10
        for question_id in ordered_question_ids:
            question = self.env['survey.question'].browse(int(question_id))

            if question.exists() and not question.is_page:
                question.write({'sequence': sequence})
                sequence += 10

        return True

    @api.model
    def reorder_questions_between_sections(self, section_orders):
        """
        Reordena preguntas dentro y entre secciones.

        section_orders debe llegar así:
        [
            {
                "section_title": "Sin sección",
                "question_ids": [1, 2, 3]
            },
            {
                "section_title": "Sección 1",
                "question_ids": [4, 5]
            }
        ]
        """
        if not section_orders:
            return False

        all_question_ids = []

        for section in section_orders:
            all_question_ids += [int(qid) for qid in section.get("question_ids", [])]

        questions = self.env["survey.question"].browse(all_question_ids)

        if not questions:
            return False

        survey = questions[0].survey_id

        if not survey:
            return False

        items = survey.question_and_page_ids.sorted(key=lambda q: (q.sequence, q.id))

        new_order = []

        for item in items:
            if item.is_page:
                new_order.append(item)

                section_title = (item.title or "").strip()

                matching_section = next(
                    (
                        section for section in section_orders
                        if (section.get("section_title") or "").strip() == section_title
                    ),
                    None
                )

                if matching_section:
                    for question_id in matching_section.get("question_ids", []):
                        question = self.env["survey.question"].browse(int(question_id))
                        if question.exists() and not question.is_page:
                            new_order.append(question)

        # Preguntas sin sección van antes de la primera sección
        no_section = next(
            (
                section for section in section_orders
                if (section.get("section_title") or "").strip().lower() == "sin sección"
            ),
            None
        )

        if no_section:
            no_section_questions = []

            for question_id in no_section.get("question_ids", []):
                question = self.env["survey.question"].browse(int(question_id))
                if question.exists() and not question.is_page:
                    no_section_questions.append(question)

            first_section_index = next(
                (index for index, item in enumerate(new_order) if item.is_page),
                len(new_order)
            )

            new_order = (
                new_order[:first_section_index]
                + no_section_questions
                + new_order[first_section_index:]
            )

        # Evitar duplicados conservando orden
        clean_order = []
        seen_ids = set()

        for item in new_order:
            if item.id not in seen_ids:
                clean_order.append(item)
                seen_ids.add(item.id)

        sequence = 10

        for item in clean_order:
            item.write({"sequence": sequence})
            sequence += 10

        return True

    @api.model
    def get_survey_structure_for_builder(self, survey_id):
        survey = self.env['survey.survey'].browse(int(survey_id))

        if not survey.exists():
            return []

        items = survey.question_and_page_ids.sorted(key=lambda q: (q.sequence, q.id))

        result = []
        current_section = {
            'id': False,
            'title': 'Sin sección',
            'questions': [],
        }

        for item in items:
            if item.is_page:
                if current_section['questions'] or current_section['title'] != 'Sin sección':
                    result.append(current_section)

                current_section = {
                    'id': item.id,
                    'title': item.title or 'Sección sin título',
                    'questions': [],
                }
                continue

            current_section['questions'].append({
                'id': item.id,
                'title': item.title or 'Pregunta sin título',
                'type': dict(item._fields['question_type'].selection).get(
                    item.question_type,
                    item.question_type or 'Sin tipo definido'
                ),
            })

        if current_section['questions'] or current_section['title'] != 'Sin sección':
            result.append(current_section)

        return result