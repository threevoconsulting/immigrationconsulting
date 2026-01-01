# -*- coding: utf-8 -*-
{
    'name': 'Immigration Questionnaire System',
    'version': '19.0.1.0.0',
    'category': 'Services/Immigration',
    'summary': 'Two-stage questionnaire system for immigration client onboarding',
    'description': """
Immigration Portal - Questionnaire Module
==========================================

This module provides the questionnaire system for client data collection:

* Pre-Consultation Questionnaire (Q1) - Initial eligibility screening
* Detailed Assessment Questionnaire (Q2) - Comprehensive data for CRS calculation
* Section-by-section navigation with progress tracking
* Auto-save functionality
* Direct population of client profile fields
* Education and work experience repeater sections
* Language proficiency tracking
* Conditional section display based on client data

Part of Phase 2 of the Immigration Portal system.
Developed for The Migration Monitor.
    """,
    'author': 'The Migration Monitor',
    'website': 'https://themigrationmonitor.ca',
    'license': 'LGPL-3',
    'depends': [
        'mm_immigration',
        'mm_portal',
        'website',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        'security/security_rules.xml',
        # Views - Backend
        'views/questionnaire_response_views.xml',
        'views/education_record_views.xml',
        'views/work_experience_views.xml',
        'views/language_proficiency_views.xml',
        'views/client_profile_views.xml',
        'views/immigration_case_views.xml',
        'views/menu_views.xml',
        # Reports
        'views/report_client_profile.xml',
        # Views - Portal Templates
        'views/questionnaire_templates.xml',
        'views/questionnaire_templates_q2.xml',
        'views/portal_questionnaire_status.xml',
        # Data
        'data/questionnaire_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'mm_questionnaire/static/src/scss/questionnaire.scss',
            'mm_questionnaire/static/src/js/questionnaire.js',
        ],
    },
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
