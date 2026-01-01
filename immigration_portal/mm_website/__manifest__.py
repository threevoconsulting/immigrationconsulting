# -*- coding: utf-8 -*-
{
    'name': 'Migration Monitor Website',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': 'Public website for The Migration Monitor immigration consulting',
    'description': """
Migration Monitor Website
=========================

This module provides the public-facing website for The Migration Monitor,
featuring:

* Modern, responsive homepage design
* Service showcase (Roadmaps, GCMS Review, Application Assistance)
* How It Works process section
* Technology platform showcase
* Newsletter subscription
* Contact form with inquiry handling
* Integration with existing portal authentication

The website is designed to convert visitors into portal clients through
the contact-to-invite workflow.
    """,
    'author': 'The Migration Monitor',
    'website': 'https://www.themigrationmonitor.ca',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'website_mass_mailing',  # For newsletter functionality
        'mail',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/website_menu_data.xml',
        'data/mail_template_data.xml',
        # Views
        'views/website_templates.xml',
        'views/contact_inquiry_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'mm_website/static/src/css/website.css',
            'mm_website/static/src/js/website.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
