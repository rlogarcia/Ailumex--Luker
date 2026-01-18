# -*- coding: utf-8 -*-
"""
Script SQL para actualizar program_id en asignaturas.

Este script actualiza el campo program_id de todas las asignaturas
basándose en la jerarquía: subject → level → phase → program
"""

UPDATE benglish_subject AS s
SET program_id = ph.program_id
FROM benglish_level AS l
JOIN benglish_phase AS ph ON l.phase_id = ph.id
WHERE s.level_id = l.id
  AND (s.program_id IS NULL OR s.program_id != ph.program_id);

-- Verificar resultados
SELECT 
    p.name AS programa,
    p.program_type,
    COUNT(s.id) AS total_asignaturas
FROM benglish_subject AS s
JOIN benglish_level AS l ON s.level_id = l.id
JOIN benglish_phase AS ph ON l.phase_id = ph.id
JOIN benglish_program AS p ON ph.program_id = p.id
WHERE s.active = true
GROUP BY p.name, p.program_type
ORDER BY p.program_type;
