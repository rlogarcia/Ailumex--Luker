# Script para poblar phase_ids, level_ids y subject_ids en planes existentes.
# Úsalo con `odoo shell -d <db>` o ejecútalo como script desde un entorno Odoo.

def populate(env):
    Plan = env['benglish.plan']
    Phase = env['benglish.phase']
    Level = env['benglish.level']
    Subject = env['benglish.subject']

    plans = Plan.search([])
    count = 0
    for plan in plans:
        if plan.program_id:
            phases = Phase.search([('program_id', '=', plan.program_id.id)])
            levels = Level.search([('phase_id', 'in', phases.ids)])
            subjects = Subject.search([('level_id', 'in', levels.ids)])
            plan.write({
                'phase_ids': [(6, 0, phases.ids)],
                'level_ids': [(6, 0, levels.ids)],
                'subject_ids': [(6, 0, subjects.ids)],
            })
            count += 1
    return count

if __name__ == '__main__':
    print('Este archivo debe ejecutarse desde un entorno Odoo con `odoo shell`.')
