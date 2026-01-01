# -*- coding: utf-8 -*-
"""
mm_gcms Module
Phase 6: GCMS Notes Request Workflow

Extension of mm_immigration to support GCMS (Global Case Management System)
notes requests as a separate case type with its own workflow.

Features:
- GCMS case type with dedicated workflow stages
- GCMS request form with UCI validation
- Service agreement e-signature integration
- Stripe payment processing for service and consultation fees
- Document delivery (GCMS notes + breakdown)
- Optional consultation booking workflow
- Email notifications for key events

Dependencies:
- mm_immigration (core case management)
- mm_esign (electronic signatures)
- sale (order management)
- account (invoicing)
- payment_stripe (Stripe payments)
- mail (email templates)

Odoo 19 Compatibility:
- No attrs/states attributes in views
- @api.model_create_multi for create overrides
- No forward model references
- group_expand without 'order' parameter
"""

from . import models
from . import controllers


def _set_pr_case_type_on_existing_stages(env):
    """
    Post-init hook to set case_type='pr' on existing stages.
    This ensures PR stages are properly filtered when GCMS is installed.
    """
    # Find all stages without a case_type set
    stages_without_type = env['mm.immigration.stage'].search([
        ('case_type', '=', False)
    ])
    if stages_without_type:
        stages_without_type.write({'case_type': 'pr'})
