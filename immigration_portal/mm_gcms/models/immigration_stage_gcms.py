# -*- coding: utf-8 -*-
"""
Immigration Stage Extension for GCMS Case Types
Phase 6: GCMS Notes Request Workflow

Extends the stage model to support filtering stages by case type,
allowing PR and GCMS cases to have independent workflow stages.
"""

from odoo import api, fields, models, _


class ImmigrationStageGCMS(models.Model):
    """Extend immigration stage with case type filtering."""
    
    _inherit = 'mm.immigration.stage'
    
    # =====================================================================
    # CASE TYPE FIELD
    # =====================================================================
    
    case_type = fields.Selection(
        selection=[
            ('pr', 'PR Strategy'),
            ('gcms', 'GCMS Request'),
        ],
        string='Case Type',
        index=True,
        help="Limit this stage to a specific case type. "
             "Leave empty to apply to all case types."
    )
    
    # =====================================================================
    # GCMS-SPECIFIC STAGE FIELDS
    # =====================================================================
    
    requires_gcms_consent = fields.Boolean(
        string='Requires GCMS Consent',
        default=False,
        help="Stage requires client GCMS consent before advancing."
    )
    
    requires_gcms_payment = fields.Boolean(
        string='Requires GCMS Payment',
        default=False,
        help="Stage requires GCMS service payment before advancing."
    )
    
    requires_consultation_payment = fields.Boolean(
        string='Requires Consultation Payment',
        default=False,
        help="Stage requires consultation payment before advancing."
    )
    
    gcms_portal_action_url = fields.Char(
        string='GCMS Portal Action URL',
        help="Portal URL for GCMS-specific action at this stage."
    )
    
    gcms_portal_action_text = fields.Char(
        string='GCMS Portal Action Text',
        help="Button text for GCMS-specific portal action."
    )
