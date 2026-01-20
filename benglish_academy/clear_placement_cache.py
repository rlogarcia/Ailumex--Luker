#!/usr/bin/env python3
"""
Script to clear cached placement test data from Odoo database.
Run this with: odoo-bin shell -d benglish_db -c odoo.conf
Then in the shell: exec(open('clear_placement_cache.py').read())
"""

# Clear any cached filters that might reference is_placement_test
filters = env['ir.filters'].search([
    ('model_id', 'in', ['benglish.academic.history', 'benglish.placement.test.prospect'])
])
if filters:
    print(f"Deleting {len(filters)} cached filters...")
    filters.unlink()

# Clear any cached actions
actions = env['ir.actions.act_window'].search([
    ('res_model', 'in', ['benglish.academic.history', 'benglish.placement.test.prospect'])
])
if actions:
    print(f"Found {len(actions)} actions on placement test models")
    for action in actions:
        # Clear the domain field if it contains is_placement_test
        if action.domain and 'is_placement_test' in action.domain:
            print(f"Clearing domain from action: {action.name}")
            action.write({'domain': '[]'})

# Clear view cache
env['ir.ui.view'].clear_caches()

# Clear model cache
env['ir.model'].clear_caches()

print("✓ Cache cleared successfully!")
print("Please restart the Odoo server to complete the cleanup.")
