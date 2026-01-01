# -*- coding: utf-8 -*-
"""
GCMS Case Type Extension for mm.immigration.case
Phase 6: GCMS Notes Request Workflow

This module extends the core immigration case model to support
GCMS (Global Case Management System) notes requests as a separate
case type with its own workflow stages.

Odoo 19 Compatibility:
- Uses @api.model_create_multi for create overrides
- No _sql_constraints (use @api.constrains instead)
- No forward model references
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta


class ImmigrationCaseGCMS(models.Model):
    """Extend immigration case with GCMS-specific functionality."""
    
    _inherit = 'mm.immigration.case'
    
    # =====================================================================
    # OVERRIDE STAGE_ID TO FILTER BY CASE TYPE
    # =====================================================================
    
    stage_id = fields.Many2one(
        'mm.immigration.stage',
        domain="[('case_type', 'in', [case_type, False])]",
        group_expand='_read_group_stage_ids',
    )
    
    # =====================================================================
    # CASE TYPE FIELD
    # =====================================================================
    case_type = fields.Selection(
        selection=[
            ('pr', 'PR Strategy'),
            ('gcms', 'GCMS Request'),
        ],
        string='Case Type',
        default='pr',
        required=True,
        tracking=True,
        help="Type of immigration case. PR Strategy is for permanent residence "
             "consultations. GCMS Request is for obtaining GCMS notes from IRCC."
    )
    
    # =====================================================================
    # STAGE FILTERING METHODS
    # =====================================================================
    
    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """
        Override to filter stages by case_type in kanban view.
        Shows only stages matching the current filter's case_type.
        """
        # Get case_type from context or domain
        case_type = self._context.get('default_case_type', 'pr')
        
        # Search for stages matching the case_type or without case_type
        stage_ids = stages.search([
            ('case_type', 'in', [case_type, False])
        ], order='sequence')
        
        return stage_ids
    
    @api.onchange('case_type')
    def _onchange_case_type(self):
        """Reset stage when case type changes to first stage of new type."""
        if self.case_type:
            first_stage = self.env['mm.immigration.stage'].search([
                ('case_type', 'in', [self.case_type, False])
            ], order='sequence', limit=1)
            if first_stage:
                self.stage_id = first_stage
    
    # =====================================================================
    # GCMS-SPECIFIC FIELDS
    # =====================================================================
    
    # Client Information for GCMS Request
    gcms_uci_number = fields.Char(
        string='UCI Number',
        tracking=True,
        help="Unique Client Identifier (UCI) - 8 or 10 digit number assigned by IRCC."
    )
    gcms_application_number = fields.Char(
        string='Application/File Number',
        tracking=True,
        help="Immigration application or file number."
    )
    gcms_application_type = fields.Selection(
        selection=[
            ('express_entry', 'Express Entry'),
            ('pnp', 'Provincial Nominee Program'),
            ('family', 'Family Sponsorship'),
            ('visitor', 'Visitor Visa'),
            ('study_permit', 'Study Permit'),
            ('work_permit', 'Work Permit'),
            ('pr_card', 'PR Card Renewal'),
            ('citizenship', 'Citizenship'),
            ('refugee', 'Refugee Claim'),
            ('other', 'Other'),
        ],
        string='Application Type',
        tracking=True,
        help="Type of immigration application for which GCMS notes are requested."
    )
    gcms_application_type_other = fields.Char(
        string='Other Application Type',
        help="Specify if 'Other' is selected above."
    )
    
    # Consent and Authorization
    gcms_consent_given = fields.Boolean(
        string='Consent Provided',
        default=False,
        tracking=True,
        help="Client has provided consent for GCMS notes request."
    )
    gcms_consent_date = fields.Date(
        string='Consent Date',
        tracking=True,
    )
    
    # GCMS Request Tracking
    gcms_request_date = fields.Date(
        string='Request Submitted Date',
        tracking=True,
        help="Date when GCMS request was submitted to IRCC."
    )
    gcms_received_date = fields.Date(
        string='Notes Received Date',
        tracking=True,
        help="Date when GCMS notes were received from IRCC."
    )
    gcms_notes_document = fields.Binary(
        string='GCMS Notes Document',
        attachment=True,
        help="The received GCMS notes PDF document."
    )
    gcms_notes_filename = fields.Char(
        string='GCMS Notes Filename',
    )
    gcms_breakdown_document = fields.Binary(
        string='Notes Breakdown Document',
        attachment=True,
        help="Consultant's breakdown and analysis of GCMS notes."
    )
    gcms_breakdown_filename = fields.Char(
        string='Breakdown Filename',
    )
    
    # Consultation Tracking
    gcms_consultation_requested = fields.Boolean(
        string='Consultation Requested',
        default=False,
        tracking=True,
        help="Client has requested a follow-up consultation call."
    )
    gcms_consultation_paid = fields.Boolean(
        string='Consultation Paid',
        default=False,
        tracking=True,
        compute='_compute_gcms_consultation_paid',
        store=True,
        help="Consultation fee has been paid."
    )
    gcms_consultation_date = fields.Datetime(
        string='Consultation Date/Time',
        tracking=True,
        help="Scheduled date and time for consultation call."
    )
    gcms_consultation_notes = fields.Text(
        string='Consultation Notes',
        help="Consultant's notes from the consultation call."
    )
    
    # E-signature References (added by mm_esign module)
    gcms_service_agreement_id = fields.Many2one(
        comodel_name='mm.esign.request',
        string='GCMS Service Agreement',
        ondelete='set null',
        help="E-signature request for GCMS service agreement."
    )
    gcms_consultation_agreement_id = fields.Many2one(
        comodel_name='mm.esign.request',
        string='Consultation Agreement',
        ondelete='set null',
        help="E-signature request for consultation service agreement."
    )
    
    # Payment Tracking
    gcms_service_order_id = fields.Many2one(
        comodel_name='sale.order',
        string='GCMS Service Order',
        ondelete='set null',
        help="Sale order for GCMS service fee."
    )
    gcms_consultation_order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Consultation Order',
        ondelete='set null',
        help="Sale order for consultation fee."
    )
    gcms_service_paid = fields.Boolean(
        string='Service Fee Paid',
        default=False,
        tracking=True,
        compute='_compute_gcms_service_paid',
        store=True,
        help="GCMS service fee has been paid."
    )
    
    # =====================================================================
    # STAGE FILTERING
    # =====================================================================
    
    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """
        Filter stages based on case_type for kanban view.
        Always show all stages for the current case type.
        
        Odoo 19: No 'order' parameter in signature.
        """
        # Get case_type from context or default to 'pr'
        case_type = self._context.get('default_case_type', 'pr')
        
        # Search for stages matching the case type
        return stages.search([
            '|',
            ('case_type', '=', case_type),
            ('case_type', '=', False),  # Stages without case_type work for all
        ], order='sequence')
    
    # =====================================================================
    # COMPUTED FIELDS
    # =====================================================================
    
    @api.depends('gcms_service_order_id', 'gcms_service_order_id.invoice_ids.payment_state')
    def _compute_gcms_service_paid(self):
        """Check if GCMS service fee has been paid."""
        for case in self:
            paid = False
            if case.gcms_service_order_id:
                invoices = case.gcms_service_order_id.invoice_ids
                if invoices:
                    paid = all(
                        inv.payment_state in ('paid', 'in_payment')
                        for inv in invoices
                        if inv.state == 'posted'
                    )
            case.gcms_service_paid = paid
    
    @api.depends('gcms_consultation_order_id', 'gcms_consultation_order_id.invoice_ids.payment_state')
    def _compute_gcms_consultation_paid(self):
        """Check if consultation fee has been paid."""
        for case in self:
            paid = False
            if case.gcms_consultation_order_id:
                invoices = case.gcms_consultation_order_id.invoice_ids
                if invoices:
                    paid = all(
                        inv.payment_state in ('paid', 'in_payment')
                        for inv in invoices
                        if inv.state == 'posted'
                    )
            case.gcms_consultation_paid = paid
    
    # =====================================================================
    # ONCHANGE METHODS
    # =====================================================================
    
    @api.onchange('case_type')
    def _onchange_case_type(self):
        """Reset stage when case type changes."""
        if self.case_type:
            # Find the first stage for this case type
            first_stage = self.env['mm.immigration.stage'].search([
                '|',
                ('case_type', '=', self.case_type),
                ('case_type', '=', False),
            ], order='sequence', limit=1)
            if first_stage:
                self.stage_id = first_stage
    
    @api.onchange('gcms_consent_given')
    def _onchange_gcms_consent(self):
        """Auto-fill consent date when consent is given."""
        if self.gcms_consent_given and not self.gcms_consent_date:
            self.gcms_consent_date = fields.Date.today()
    
    # =====================================================================
    # CONSTRAINTS
    # =====================================================================
    
    @api.constrains('gcms_uci_number')
    def _check_uci_number(self):
        """Validate UCI number format (8 or 10 digits)."""
        for case in self:
            if case.gcms_uci_number:
                # Remove spaces and dashes
                uci = case.gcms_uci_number.replace(' ', '').replace('-', '')
                if not uci.isdigit() or len(uci) not in (8, 10):
                    raise ValidationError(
                        _("UCI Number must be 8 or 10 digits. Got: %s") % case.gcms_uci_number
                    )
    
    # =====================================================================
    # WORKFLOW ACTIONS
    # =====================================================================
    
    def action_submit_gcms_request(self):
        """Mark GCMS request as submitted to IRCC."""
        self.ensure_one()
        if self.case_type != 'gcms':
            raise UserError(_("This action is only available for GCMS cases."))
        
        if not self.gcms_uci_number:
            raise UserError(_("Please enter the client's UCI number before submitting."))
        
        if not self.gcms_consent_given:
            raise UserError(_("Client consent is required before submitting GCMS request."))
        
        self.gcms_request_date = fields.Date.today()
        self._advance_to_stage('gcms_processing')
        
        self.message_post(
            body=_("GCMS request submitted to IRCC."),
            message_type='notification',
        )
    
    def action_gcms_notes_received(self):
        """Mark GCMS notes as received from IRCC."""
        self.ensure_one()
        if self.case_type != 'gcms':
            raise UserError(_("This action is only available for GCMS cases."))
        
        self.gcms_received_date = fields.Date.today()
        self._advance_to_stage('gcms_notes_delivered')
        
        # Send notification to client
        self._send_gcms_notes_notification()
        
        self.message_post(
            body=_("GCMS notes received from IRCC and client notified."),
            message_type='notification',
        )
    
    def action_request_consultation(self):
        """Client requests a follow-up consultation."""
        self.ensure_one()
        if self.case_type != 'gcms':
            raise UserError(_("This action is only available for GCMS cases."))
        
        self.gcms_consultation_requested = True
        self._advance_to_stage('gcms_consultation_requested')
        
        self.message_post(
            body=_("Client has requested a follow-up consultation."),
            message_type='notification',
        )
    
    def action_complete_gcms_case(self):
        """Mark GCMS case as completed."""
        self.ensure_one()
        if self.case_type != 'gcms':
            raise UserError(_("This action is only available for GCMS cases."))
        
        self._advance_to_stage('gcms_completed')
        
        self.message_post(
            body=_("GCMS case completed."),
            message_type='notification',
        )
    
    def _advance_to_stage(self, stage_xml_id):
        """Helper to advance case to a specific stage by XML ID."""
        try:
            stage = self.env.ref(f'mm_gcms.{stage_xml_id}')
            self.stage_id = stage
        except ValueError:
            # Stage not found - log warning but don't fail
            pass
    
    def _send_gcms_notes_notification(self):
        """Send email notification to client when GCMS notes are ready."""
        self.ensure_one()
        template = self.env.ref('mm_gcms.mail_template_gcms_notes_ready', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
    
    # =====================================================================
    # PAYMENT HANDLING
    # =====================================================================
    
    def _on_gcms_service_payment_complete(self):
        """Handle GCMS service payment completion."""
        self.ensure_one()
        if self.case_type != 'gcms':
            return
        
        # Advance to processing stage
        self._advance_to_stage('gcms_processing')
        
        self.message_post(
            body=_("GCMS service payment received. Processing can begin."),
            message_type='notification',
        )
    
    def _on_gcms_consultation_payment_complete(self):
        """Handle consultation payment completion."""
        self.ensure_one()
        if self.case_type != 'gcms':
            return
        
        # Advance to call scheduled stage
        self._advance_to_stage('gcms_call_scheduled')
        
        self.message_post(
            body=_("Consultation payment received. Please schedule your call."),
            message_type='notification',
        )
    
    # =====================================================================
    # CREATE ORDERS
    # =====================================================================
    
    def action_create_gcms_service_order(self):
        """Create a sale order for GCMS service."""
        self.ensure_one()
        if self.gcms_service_order_id:
            raise UserError(_("A service order already exists for this case."))
        
        product = self.env.ref('mm_gcms.product_gcms_service', raise_if_not_found=False)
        if not product:
            raise UserError(_("GCMS Service product not found. Please configure products first."))
        
        order = self._create_sale_order(product, 'GCMS Service')
        self.gcms_service_order_id = order
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('GCMS Service Order'),
            'res_model': 'sale.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_create_consultation_order(self):
        """Create a sale order for consultation."""
        self.ensure_one()
        if self.gcms_consultation_order_id:
            raise UserError(_("A consultation order already exists for this case."))
        
        product = self.env.ref('mm_gcms.product_gcms_consultation', raise_if_not_found=False)
        if not product:
            raise UserError(_("GCMS Consultation product not found. Please configure products first."))
        
        order = self._create_sale_order(product, 'GCMS Consultation')
        self.gcms_consultation_order_id = order
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Consultation Order'),
            'res_model': 'sale.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _create_sale_order(self, product, description):
        """Helper to create sale order for a product."""
        self.ensure_one()
        
        order_vals = {
            'partner_id': self.partner_id.id,
            'origin': f'{self.name} - {description}',
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': f'{product.name} - {self.name}',
                'product_uom_qty': 1,
                'price_unit': product.list_price,
            })],
        }
        
        return self.env['sale.order'].create(order_vals)
