# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class ContactInquiry(models.Model):
    """Model to store website contact form submissions."""
    
    _name = 'mm.contact.inquiry'
    _description = 'Website Contact Inquiry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'display_name'
    
    # Contact Information
    first_name = fields.Char(
        string='First Name',
        required=True,
        tracking=True,
    )
    last_name = fields.Char(
        string='Last Name',
        required=True,
        tracking=True,
    )
    email = fields.Char(
        string='Email',
        required=True,
        tracking=True,
    )
    
    # Inquiry Details
    country_id = fields.Many2one(
        comodel_name='res.country',
        string='Country of Residence',
        tracking=True,
    )
    service_interest = fields.Selection(
        selection=[
            ('roadmap', 'Immigration Roadmap'),
            ('gcms', 'GCMS Notes Review'),
            ('application', 'Application Assistance'),
            ('unsure', 'Not Sure Yet'),
        ],
        string='Service Interest',
        tracking=True,
    )
    message = fields.Text(
        string='Message',
        help='Immigration goals and questions',
    )
    
    # Processing
    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('contacted', 'Contacted'),
            ('invited', 'Portal Invited'),
            ('converted', 'Converted to Case'),
            ('closed', 'Closed'),
        ],
        string='Status',
        default='new',
        required=True,
        tracking=True,
    )
    
    # Linked Records
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Contact',
        help='Linked contact record',
        tracking=True,
    )
    case_id = fields.Many2one(
        comodel_name='mm.immigration.case',
        string='Immigration Case',
        help='Linked immigration case (if converted)',
        tracking=True,
    )
    
    # Source Tracking
    source = fields.Char(
        string='Source',
        default='website',
        help='Where this inquiry came from',
    )
    utm_source = fields.Char(string='UTM Source')
    utm_medium = fields.Char(string='UTM Medium')
    utm_campaign = fields.Char(string='UTM Campaign')
    
    # Computed
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
    )
    
    @api.depends('first_name', 'last_name', 'email')
    def _compute_display_name(self):
        for record in self:
            if record.first_name and record.last_name:
                record.display_name = f"{record.first_name} {record.last_name}"
            else:
                record.display_name = record.email or 'New Inquiry'
    
    @api.constrains('email')
    def _check_email(self):
        """Validate email format."""
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        for record in self:
            if record.email and not email_pattern.match(record.email):
                raise ValidationError(_("Please enter a valid email address."))
    
    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    
    def action_mark_contacted(self):
        """Mark inquiry as contacted."""
        self.ensure_one()
        self.write({'state': 'contacted'})
        self.message_post(
            body=_("Inquiry marked as contacted."),
            message_type='notification',
        )
    
    def action_create_contact(self):
        """Create a res.partner from this inquiry."""
        self.ensure_one()
        if self.partner_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'res_id': self.partner_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        
        partner = self.env['res.partner'].create({
            'name': f"{self.first_name} {self.last_name}",
            'email': self.email,
            'country_id': self.country_id.id if self.country_id else False,
            'comment': self.message,
        })
        self.partner_id = partner
        self.message_post(
            body=_("Contact created: %s", partner.name),
            message_type='notification',
        )
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': partner.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_send_portal_invite(self):
        """Send portal invitation (requires mm_immigration module)."""
        self.ensure_one()
        
        # First ensure contact exists
        if not self.partner_id:
            self.action_create_contact()
        
        # Check if mm_immigration module is installed
        if 'mm.immigration.case' not in self.env:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Module Not Installed"),
                    'message': _("The Immigration module is required to send portal invitations."),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Create case and send invite
        Case = self.env['mm.immigration.case']
        case = Case.create({
            'partner_id': self.partner_id.id,
            'source': 'website_inquiry',
        })
        
        self.write({
            'state': 'invited',
            'case_id': case.id,
        })
        
        # Trigger portal invitation
        if hasattr(case, 'action_send_portal_invitation'):
            case.action_send_portal_invitation()
        
        self.message_post(
            body=_("Portal invitation sent. Case created: %s", case.reference),
            message_type='notification',
        )
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mm.immigration.case',
            'res_id': case.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_close(self):
        """Close the inquiry without conversion."""
        self.ensure_one()
        self.write({'state': 'closed'})
        self.message_post(
            body=_("Inquiry closed."),
            message_type='notification',
        )
