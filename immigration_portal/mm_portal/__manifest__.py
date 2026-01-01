# -*- coding: utf-8 -*-
{
    'name': 'Immigration Portal',
    'version': '19.0.1.0.0',
    'category': 'Services/Immigration',
    'summary': 'Client portal for immigration case tracking',
    'description': """
Immigration Portal - Client Portal Module
==========================================

This module provides the client-facing portal for immigration cases:

* Progress tracker with visual stage indicators
* Case dashboard with current action prompts
* Document access and downloads
* Multi-case support per client

Depends on mm_immigration core module.
    """,
    'author': 'The Migration Monitor',
    'website': 'https://themigrationmonitor.ca',
    'license': 'LGPL-3',
    'depends': [
        'mm_immigration',
        'portal',
        'website',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Views
        'views/portal_templates.xml',
    ],
    'assets': {
        # Variables MUST be loaded first - they are shared across all mm_* modules
        # Order is critical: variables -> main styles
        'web.assets_frontend': [
            'mm_portal/static/src/scss/_variables.scss',
            'mm_portal/static/src/scss/portal.scss',
        ],
    },
    'installable': True,
    'auto_install': False,
}
