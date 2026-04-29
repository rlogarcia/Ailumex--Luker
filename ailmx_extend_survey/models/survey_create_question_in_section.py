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