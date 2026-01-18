#!/usr/bin/env python3
"""
Script to fix sequence numbers and level references in subjects_bskills_beteens.xml
"""
import re

def fix_bskills_file():
    file_path = r'c:\Benglish\benglish_academy\data\subjects_bskills_beteens.xml'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    current_record = []
    in_record = False
    current_bskill_num = None
    current_unit = None
    
    for line in lines:
        # Track when we're in a record
        if '<record id="subject_beteens_bskill_u' in line:
            in_record = True
            # Extract unit number from ID
            match = re.search(r'subject_beteens_bskill_u(\d+)_(\d+)', line)
            if match:
                current_unit = int(match.group(1))
                current_bskill_num = match.group(2)
        
        if in_record:
            # Fix sequence based on bskill_number
            if '<field name="sequence">20</field>' in line and current_bskill_num:
                sequence_map = {'1': '20', '2': '30', '3': '40', '4': '50'}
                new_seq = sequence_map.get(current_bskill_num, '20')
                line = line.replace('20', new_seq, 1)
            
            # Fix phase names
            if current_unit and 9 <= current_unit <= 16:
                line = line.replace('Elementary-', 'Intermediate-')
                line = line.replace('level_beteens_plus_mixto_elementary_', 'level_beteens_plus_mixto_intermediate_')
            elif current_unit and 17 <= current_unit <= 24:
                line = line.replace('Pre-Intermediate-', 'Advanced-')
                line = line.replace('level_beteens_plus_mixto_preintermediate_', 'level_beteens_plus_mixto_advanced_')
            
            # Fix unit numbers in various fields for units 9-24
            if current_unit and 9 <= current_unit <= 16:
                old_num = current_unit - 8
                new_num = current_unit
                if f'Bskill U{old_num}' in line:
                    line = line.replace(f'Bskill U{old_num}', f'Bskill U{new_num}')
                if f'BSKILL-U{old_num}-' in line:
                    line = line.replace(f'BSKILL-U{old_num}-', f'BSKILL-U{new_num}-')
                if f'<field name="unit_number">{old_num}</field>' in line:
                    line = line.replace(f'<field name="unit_number">{old_num}</field>', 
                                      f'<field name="unit_number">{new_num}</field>')
                if f'Unidad {old_num}' in line:
                    line = line.replace(f'Unidad {old_num}', f'Unidad {new_num}')
            elif current_unit and 17 <= current_unit <= 24:
                old_num = current_unit - 16
                new_num = current_unit
                if f'Bskill U{old_num}' in line:
                    line = line.replace(f'Bskill U{old_num}', f'Bskill U{new_num}')
                if f'BSKILL-U{old_num}-' in line:
                    line = line.replace(f'BSKILL-U{old_num}-', f'BSKILL-U{new_num}-')
                if f'<field name="unit_number">{old_num}</field>' in line:
                    line = line.replace(f'<field name="unit_number">{old_num}</field>', 
                                      f'<field name="unit_number">{new_num}</field>')
                if f'Unidad {old_num}' in line:
                    line = line.replace(f'Unidad {old_num}', f'Unidad {new_num}')
            
            # Fix level unit references for units 9-24
            if current_unit and 9 <= current_unit <= 16:
                for i in range(1, 9):
                    old_ref = f'intermediate_unit{i}'
                    new_ref = f'intermediate_unit{current_unit}'
                    if old_ref in line:
                        line = line.replace(old_ref, new_ref)
                        break
            elif current_unit and 17 <= current_unit <= 24:
                for i in range(1, 9):
                    old_ref = f'advanced_unit{i}'
                    new_ref = f'advanced_unit{current_unit}'
                    if old_ref in line:
                        line = line.replace(old_ref, new_ref)
                        break
        
        new_lines.append(line)
        
        if '</record>' in line:
            in_record = False
            current_bskill_num = None
            current_unit = None
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print("✓ Fixed subjects_bskills_beteens.xml")
    print("  - Updated all sequence numbers based on bskill_number")
    print("  - Fixed Elementary -> Intermediate for units 9-16")
    print("  - Fixed Pre-Intermediate -> Advanced for units 17-24")
    print("  - Fixed all level references")
    print("  - Fixed all unit numbers, codes, and descriptions")

if __name__ == '__main__':
    fix_bskills_file()
