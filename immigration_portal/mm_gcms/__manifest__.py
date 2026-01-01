# -*- coding: utf-8 -*-
{
    'name': 'Migration Monitor - GCMS Requests',
    'version': '19.0.1.0.0',
    'category': 'Services/Immigration',
    'summary': 'GCMS Notes Request Management for Immigration Cases',
    'description': """
Migration Monitor - GCMS Notes Request Module
==============================================

This module extends the Immigration Portal to support GCMS (Global Case 
Management System) notes requests as a separate case type with its own 
workflow.

Features
--------
* **GCMS Case Type**: New case type for GCMS notes requests
* **Dedicated Workflow**: 8-stage workflow specific to GCMS requests
* **UCI Validation**: Automatic validation of UCI number format
* **Service Agreement**: E-signature integration for GCMS service agreement
* **Payment Processing**: Stripe integration for service and consultation fees
* **Document Delivery**: Upload and deliver GCMS notes and breakdown documents
* **Optional Consultation**: Full workflow for booking follow-up consultations
* **Email Notifications**: Automated emails for key workflow events

GCMS Workflow Stages
--------------------
1. Form Submitted - Client fills GCMS request form
2. Service Payment - Client pays GCMS service fee
3. Processing - Request submitted to IRCC
4. Notes Delivered - GCMS notes received and delivered
5. Consultation Requested (optional) - Client requests follow-up call
6. Consultation Payment - Client pays consultation fee
7. Call Scheduled - Consultation call booked
8. Completed - Case closed

Odoo 19 Compatibility
---------------------
* No deprecated attrs/states attributes
* @api.model_create_multi for create overrides
* No forward model references
* Updated group_expand signature
* Proper XML entity escaping

Technical Notes
---------------
This module extends mm_immigration rather than creating a new model,
allowing GCMS cases to share the same partner and portal infrastructure
while maintaining separate workflow stages.

License: LGPL-3
    """,
    'author': 'The Migration Monitor',
    'website': 'https://themigrationmonitor.ca',
    'license': 'LGPL-3',
    
    # Module dependencies
    'depends': [
        'mm_immigration',      # Core case management
        'mm_esign',            # Electronic signatures
        'sale',                # Sale orders
        'account',             # Invoicing
        'mail',                # Email templates
        'portal',              # Portal framework
        'website',             # Web forms
    ],
    
    # Data files (order matters!)
    'data': [
        # Security first
        'security/ir.model.access.csv',
        
        # Data files
        'data/gcms_stage_data.xml',
        'data/gcms_product_data.xml',
        'data/gcms_mail_template_data.xml',
        
        # Views
        'views/gcms_case_views.xml',
        'views/gcms_portal_templates.xml',
        'views/gcms_portal_dashboard.xml',
    ],
    
    # Demo data (optional)
    'demo': [],
    
    # Assets
    'assets': {},
    
    # Module configuration
    'installable': True,
    'application': False,
    'auto_install': False,
    
    # External dependencies
    'external_dependencies': {
        'python': [],
    },
    
    # Post-init hook to set case_type on existing stages
    'post_init_hook': '_set_pr_case_type_on_existing_stages',
    
    # Uninstall hook (if needed)
    # 'uninstall_hook': 'uninstall_hook',
}
