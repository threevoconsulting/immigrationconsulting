# -*- coding: utf-8 -*-
{
    'name': 'Immigration E-Signature',
    'version': '19.0.1.1.0',
    'category': 'Services/Immigration',
    'summary': 'Electronic signature and payment processing for immigration services',
    'description': """
Immigration Portal - E-Signature Module
=======================================

This module provides electronic signature and payment integration:

* E-signature capture (draw or type)
* Dual signature workflow (client + consultant)
* PDF document stamping with signature and audit trail
* Service agreement generation from templates
* Integration with Odoo's payment system
* Automatic stage advancement on signature/payment
* Email notifications at key workflow points
* 7-day signature request expiration
* PIPEDA-compliant audit logging
* Timezone-aware date formatting

Part of Phase 3 of the Immigration Portal system.
Developed for The Migration Monitor.
    """,
    'author': 'The Migration Monitor',
    'website': 'https://themigrationmonitor.ca',
    'license': 'LGPL-3',
    'depends': [
        'mm_immigration',
        'mm_portal',
        'mm_questionnaire',
        'sale',
        'account',
        'payment',
        'website',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        'security/security_rules.xml',
        # Data
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        # Reports (must load BEFORE mail templates that reference them)
        'report/report_service_agreement.xml',
        # Data (continued)
        'data/mail_template_data.xml',
        # Views - Backend
        'views/esign_request_views.xml',
        'views/immigration_case_views.xml',
        'views/menu_views.xml',
        # Wizards
        'wizard/consultant_sign_wizard_views.xml',
        # Views - Portal
        'views/portal_esign_templates.xml',
        'views/portal_quote_templates.xml',
        'views/portal_payment_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'mm_esign/static/src/scss/esign.scss',
            'mm_esign/static/src/js/signature_pad.js',
            'mm_esign/static/src/js/esign.js',
        ],
    },
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
