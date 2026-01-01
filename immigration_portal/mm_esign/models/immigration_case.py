# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ImmigrationCaseEsign(models.Model):
    """Extends mm.immigration.case with e-signature and payment fields."""
    _inherit = 'mm.immigration.case'

    # =====================
    # Sales & Payment Fields
    # =====================
    sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Quote / Sale Order',
        tracking=True,
        copy=False,
    )
    sale_order_state = fields.Selection(
        related='sale_order_id.state',
        string='Quote Status',
        readonly=True,
    )
    sale_order_amount = fields.Monetary(
        related='sale_order_id.amount_total',
        string='Quote Amount',
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='sale_order_id.currency_id',
        string='Currency',
        readonly=True,
    )

    # =====================
    # E-Sign Fields
    # =====================
    esign_request_ids = fields.One2many(
        comodel_name='mm.esign.request',
        inverse_name='case_id',
        string='E-Sign Requests',
    )
    service_agreement_id = fields.Many2one(
        comodel_name='mm.esign.request',
        string='Service Agreement',
        compute='_compute_esign_documents',
        store=True,
    )
    roadmap_ack_id = fields.Many2one(
        comodel_name='mm.esign.request',
        string='Roadmap Acknowledgment',
        compute='_compute_esign_documents',
        store=True,
    )

    # =====================
    # Payment Fields
    # =====================
    payment_confirmed = fields.Boolean(
        string='Payment Confirmed',
        compute='_compute_payment_status',
        store=True,
    )
    payment_date = fields.Date(
        string='Payment Date',
        copy=False,
        tracking=True,
    )
    invoice_ids = fields.Many2many(
        comodel_name='account.move',
        string='Invoices',
        compute='_compute_invoices',
    )
    invoice_count = fields.Integer(
        string='Invoice Count',
        compute='_compute_invoices',
    )

    # =====================
    # Status Flags
    # =====================
    has_quote = fields.Boolean(
        string='Has Quote',
        compute='_compute_quote_status',
    )
    quote_confirmed = fields.Boolean(
        string='Quote Confirmed',
        compute='_compute_quote_status',
    )
    agreement_signed = fields.Boolean(
        string='Agreement Signed',
        compute='_compute_esign_status',
        store=True,
    )
    can_create_quote = fields.Boolean(
        string='Can Create Quote',
        compute='_compute_action_availability',
    )
    can_send_agreement = fields.Boolean(
        string='Can Send Agreement',
        compute='_compute_action_availability',
    )

    # =====================
    # Computed Methods
    # =====================
    @api.depends('esign_request_ids', 'esign_request_ids.document_type', 'esign_request_ids.state')
    def _compute_esign_documents(self):
        for case in self:
            service_agreement = case.esign_request_ids.filtered(
                lambda r: r.document_type == 'service_agreement' and r.state != 'cancelled'
            )
            roadmap_ack = case.esign_request_ids.filtered(
                lambda r: r.document_type == 'roadmap_ack' and r.state != 'cancelled'
            )
            # Get most recent of each type
            case.service_agreement_id = service_agreement[0] if service_agreement else False
            case.roadmap_ack_id = roadmap_ack[0] if roadmap_ack else False

    @api.depends('sale_order_id', 'sale_order_id.invoice_ids', 
                 'sale_order_id.invoice_ids.payment_state')
    def _compute_payment_status(self):
        for case in self:
            if case.sale_order_id and case.sale_order_id.invoice_ids:
                invoices = case.sale_order_id.invoice_ids.filtered(
                    lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted'
                )
                case.payment_confirmed = (
                    bool(invoices) and
                    all(inv.payment_state in ('paid', 'in_payment') for inv in invoices)
                )
            else:
                case.payment_confirmed = False

    @api.depends('sale_order_id', 'sale_order_id.invoice_ids')
    def _compute_invoices(self):
        for case in self:
            if case.sale_order_id:
                case.invoice_ids = case.sale_order_id.invoice_ids.filtered(
                    lambda inv: inv.move_type == 'out_invoice'
                )
                case.invoice_count = len(case.invoice_ids)
            else:
                case.invoice_ids = False
                case.invoice_count = 0

    @api.depends('sale_order_id', 'sale_order_id.state')
    def _compute_quote_status(self):
        for case in self:
            case.has_quote = bool(case.sale_order_id)
            case.quote_confirmed = (
                case.sale_order_id and 
                case.sale_order_id.state in ('sale', 'done')
            )

    @api.depends('service_agreement_id', 'service_agreement_id.state')
    def _compute_esign_status(self):
        for case in self:
            case.agreement_signed = (
                case.service_agreement_id and 
                case.service_agreement_id.state == 'signed'
            )

    @api.depends('state', 'q1_state', 'has_quote')
    def _compute_action_availability(self):
        for case in self:
            # Can create quote when Q1 is complete and no quote exists
            case.can_create_quote = (
                case.q1_state == 'completed' and
                not case.has_quote
            )
            # Can send agreement when quote is confirmed and no agreement sent
            case.can_send_agreement = (
                case.quote_confirmed and
                not case.service_agreement_id
            )

    # =====================
    # Action Methods
    # =====================
    def action_create_quote(self):
        """Open wizard to create a sale order for this case."""
        self.ensure_one()
        
        if self.sale_order_id:
            raise UserError(_("A quote already exists for this case."))
        
        # Create a new sale order linked to this case
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'client_order_ref': self.name,
        })
        
        self.write({'sale_order_id': sale_order.id})
        
        # Open the sale order form for editing
        return {
            'type': 'ir.actions.act_window',
            'name': _('Quote for %s') % self.name,
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': sale_order.id,
            'target': 'current',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_origin': self.name,
            }
        }

    def action_view_quote(self):
        """Open the linked sale order."""
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_("No quote exists for this case."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Quote'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
            'target': 'current',
        }

    def action_view_invoices(self):
        """Open related invoices."""
        self.ensure_one()
        
        invoices = self.invoice_ids
        if not invoices:
            raise UserError(_("No invoices found for this case."))
        
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Invoices'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoices.ids)],
            'context': {'default_move_type': 'out_invoice'},
        }
        
        if len(invoices) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = invoices[0].id
        
        return action

    def action_create_service_agreement(self):
        """Create and send service agreement for signature."""
        self.ensure_one()
        
        if not self.sale_order_id:
            raise UserError(_("Please create a quote first."))
        
        if self.sale_order_id.state not in ('sale', 'done'):
            raise UserError(_("Please confirm the quote before sending the service agreement."))
        
        if self.service_agreement_id:
            raise UserError(_("A service agreement already exists for this case."))
        
        # Create e-sign request
        esign_request = self.env['mm.esign.request'].create({
            'document_type': 'service_agreement',
            'case_id': self.id,
            'partner_id': self.partner_id.id,
        })
        
        # Generate document and send
        esign_request.action_generate_document()
        esign_request.action_send()
        
        self.message_post(
            body=_("Service agreement sent for signature."),
            message_type='notification',
        )
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Service Agreement'),
            'res_model': 'mm.esign.request',
            'view_mode': 'form',
            'res_id': esign_request.id,
            'target': 'current',
        }

    def action_view_esign_requests(self):
        """View all e-sign requests for this case."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('E-Sign Requests'),
            'res_model': 'mm.esign.request',
            'view_mode': 'list,form',
            'domain': [('case_id', '=', self.id)],
            'context': {'default_case_id': self.id},
        }

    # =====================
    # Workflow Callbacks
    # =====================
    def _on_signature_complete(self, esign_request):
        """Called when an e-signature is completed."""
        self.ensure_one()
        
        if esign_request.document_type == 'service_agreement':
            # Advance to Payment stage
            payment_stage = self.env['mm.immigration.stage'].search([
                ('state', '=', 'paid')
            ], limit=1)
            
            if payment_stage and self.stage_id.state == 'quoted':
                self.write({'stage_id': payment_stage.id})
                
                # Confirm sale order if not already
                if self.sale_order_id and self.sale_order_id.state == 'draft':
                    self.sale_order_id.action_confirm()
                
                # Create invoice from sale order
                if self.sale_order_id and self.sale_order_id.state == 'sale':
                    try:
                        self.sale_order_id._create_invoices()
                        # Post the invoice
                        for invoice in self.sale_order_id.invoice_ids:
                            if invoice.state == 'draft':
                                invoice.action_post()
                    except Exception as e:
                        self.message_post(
                            body=_("Could not auto-create invoice: %s") % str(e),
                            message_type='notification',
                        )
                
                self.message_post(
                    body=_("Service agreement signed. Case moved to Payment stage."),
                    message_type='notification',
                )
        
        elif esign_request.document_type == 'roadmap_ack':
            # Advance to Consultation stage
            consultation_stage = self.env['mm.immigration.stage'].search([
                ('state', '=', 'call_scheduled')
            ], limit=1)
            
            if consultation_stage and self.stage_id.state == 'roadmap_delivered':
                self.write({'stage_id': consultation_stage.id})
                self.message_post(
                    body=_("Roadmap acknowledged. Case moved to Consultation stage."),
                    message_type='notification',
                )

    def _on_payment_complete(self):
        """Called when payment is confirmed."""
        self.ensure_one()
        
        # Advance to Assessment stage
        assessment_stage = self.env['mm.immigration.stage'].search([
            ('state', '=', 'assessment')
        ], limit=1)
        
        if assessment_stage and self.stage_id.state == 'paid':
            self.write({
                'stage_id': assessment_stage.id,
                'payment_date': fields.Date.today(),
            })
            
            # Send Q2 invitation email
            self._send_q2_invitation()
            
            self.message_post(
                body=_("Payment confirmed. Case moved to Assessment stage. Q2 invitation sent."),
                message_type='notification',
            )

    def _send_q2_invitation(self):
        """Send email inviting client to complete Q2."""
        self.ensure_one()
        template = self.env.ref('mm_esign.email_template_payment_received', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
