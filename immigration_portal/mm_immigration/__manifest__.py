# -*- coding: utf-8 -*-
{
    'name': 'Immigration Case Management',
    'version': '19.0.1.0.0',
    'category': 'Services/Immigration',
    'summary': 'Core immigration case management for RCIC consulting practices',
    'description': """
Immigration Portal - Core Module
================================

This module provides the foundation for immigration case management:

* Immigration case tracking with workflow stages
* Client profile management
* Dependent children records
* Consultant assignment
* Portal invitation integration
* Configurable branding

Developed for The Migration Monitor.
    """,
    'author': 'The Migration Monitor',
    'website': 'https://themigrationmonitor.ca',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts',
        'mail',
        'portal',
    ],
    'data': [
        # Security
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        'data/stage_data.xml',
        'data/config_data.xml',
        # Views
        'views/immigration_stage_views.xml',
        'views/client_profile_views.xml',
        'views/immigration_case_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
