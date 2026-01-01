# -*- coding: utf-8 -*-
{
    'name': 'Immigration Roadmap',
    'version': '19.0.1.0.0',
    'category': 'Services/Immigration',
    'summary': 'Immigration Roadmap Document Generation and Delivery',
    'description': """
Immigration Roadmap
==================

This module provides:
- Personalized immigration roadmap document generation
- PDF generation with professional branding
- PNP opportunity analysis with province fit ratings
- Consultant workflow (draft → review → approved → delivered)
- Client portal viewing and acknowledgment
- Integration with CRS Calculator

Key Features:
- Auto-populate from Q2 profile and CRS calculation
- Hybrid data entry: structured tables + rich text narratives
- Professional PDF output matching branded template
- Province-by-province PNP fit assessment
- Timeline milestone planning
- Client signature acknowledgment
- Document versioning
    """,
    'author': 'The Migration Monitor',
    'website': 'https://www.migrationmonitor.ca',
    'license': 'LGPL-3',
    'depends': [
        'mm_crs_calculator',
        'mm_esign',
        'mail',
        'portal',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        'security/security_rules.xml',
        # Data files
        'data/mail_template_data.xml',
        # Views
        'views/roadmap_document_views.xml',
        'views/pnp_opportunity_views.xml',
        'views/roadmap_milestone_views.xml',
        'views/immigration_case_views.xml',
        'views/portal_roadmap_templates.xml',
        'views/menu_views.xml',
        # Report
        'report/report_roadmap.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'mm_roadmap/static/src/scss/roadmap.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
