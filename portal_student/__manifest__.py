# -*- coding: utf-8 -*-
{
    "name": "Portal del Estudiante",
    "summary": "Portal web para estudiantes de Benglish (HU-E1 a HU-E8)",
    "version": "1.1.0",
    "category": "Website/Portal",
    "author": "Codex",
    "website": "https://www.benglish.com",
    "license": "LGPL-3",
    "depends": [
        "portal",
        "website",
        "web",
        "auth_signup",
        "benglish_academy",
    ],
    "data": [
        "security/portal_student_security.xml",
        "security/ir.model.access.csv",
        "data/portal_student_menu.xml",
        "views/portal_student_templates.xml",
        "views/portal_student_auth_templates.xml",
        "views/login_template.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "portal_student/static/src/css/portal_student.css",
            "portal_student/static/src/js/portal_student.js",
        ],
    },
    "post_init_hook": "post_init_hook",
    "application": False,
    "installable": True,
}
