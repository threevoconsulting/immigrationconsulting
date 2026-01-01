# -*- coding: utf-8 -*-
"""
Custom Portal Invitation - Case Type Specific Emails
The Migration Monitor

Overrides the default portal invitation to send customized emails
based on the case type (PR Strategy vs GCMS Request).
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ImmigrationCasePortalInvite(models.Model):
    """Override portal invitation to send case-type-specific emails."""
    
    _inherit = 'mm.immigration.case'
    
    def action_send_portal_invite(self):
        """
        Send portal invitation to client with case-type-specific email.
        
        This method:
        1. Grants portal access to the client
        2. Sends our custom welcome email based on case_type
        """
        self.ensure_one()
        
        if not self.partner_id.email:
            raise UserError(_(
                "Client must have an email address to receive portal invitation."
            ))
        
        # Step 1: Grant portal access using Odoo's portal wizard
        # This handles both new users and existing users without portal access
        wizard = self.env['portal.wizard'].sudo().create({
            'partner_ids': [(6, 0, [self.partner_id.id])],
        })
        
        wizard_user = wizard.user_ids.filtered(
            lambda u: u.partner_id == self.partner_id
        )
        
        if wizard_user:
            # Grant access - this sends Odoo's password reset email
            # which is needed for first-time login
            wizard_user.action_grant_access()
            _logger.info("Granted portal access to %s", self.partner_id.email)
        
        # Step 2: Send our custom welcome email
        template = self._get_portal_invite_template()
        
        if template:
            try:
                template.sudo().send_mail(
                    self.id,
                    force_send=True,
                    raise_exception=False,
                    email_values={
                        'email_to': self.partner_id.email,
                        'auto_delete': False,
                    }
                )
                _logger.info(
                    "Sent custom portal invitation to %s for case %s (type: %s)",
                    self.partner_id.email, self.name, 
                    getattr(self, 'case_type', 'pr')
                )
            except Exception as e:
                _logger.error("Failed to send custom portal email: %s", str(e))
                # Don't raise - portal access was still granted
        
        # Step 3: Update case tracking fields
        self.write({
            'portal_invited': True,
            'portal_invite_date': fields.Datetime.now(),
        })
        
        # Step 4: Log in chatter
        self.message_post(
            body=_("Portal invitation sent to %s") % self.partner_id.email,
            message_type='notification',
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Portal Invitation Sent'),
                'message': _('Portal invitation has been sent to %s') % self.partner_id.email,
                'type': 'success',
                'sticky': False,
            }
        }
    
    def _get_portal_invite_template(self):
        """
        Get the appropriate email template based on case type.
        
        Returns:
            mail.template record or False if not found
        """
        template_map = {
            'gcms': 'mm_gcms.mail_template_portal_invite_gcms',
            'pr': 'mm_gcms.mail_template_portal_invite_pr',
        }
        
        # Get case_type, default to 'pr' if not set
        case_type = getattr(self, 'case_type', 'pr') or 'pr'
        
        template_xmlid = template_map.get(case_type)
        
        if template_xmlid:
            try:
                template = self.env.ref(template_xmlid)
                _logger.info("Found email template: %s", template_xmlid)
                return template
            except ValueError:
                _logger.warning(
                    "Email template %s not found for case type %s",
                    template_xmlid, case_type
                )
        
        return False
    
    def action_resend_portal_invite(self):
        """
        Resend the portal invitation email.
        
        Useful when the client didn't receive the first email or
        needs a reminder.
        """
        self.ensure_one()
        
        if not self.partner_id.email:
            raise UserError(_(
                "Client must have an email address to receive portal invitation."
            ))
        
        template = self._get_portal_invite_template()
        
        if template:
            template.sudo().send_mail(
                self.id,
                force_send=True,
                raise_exception=True,
            )
            
            self.message_post(
                body=_("Portal invitation email resent to %s") % self.partner_id.email,
                message_type='notification',
            )
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Email Sent'),
                    'message': _('Portal invitation resent to %s') % self.partner_id.email,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise UserError(_(
                "Email template not found. Please contact support."
            ))
    
    def action_test_email_template(self):
        """
        Debug action to test if email template can be found and rendered.
        Use this from the case form to troubleshoot email issues.
        """
        self.ensure_one()
        
        template = self._get_portal_invite_template()
        
        if not template:
            raise UserError(_("Email template not found for case type: %s") % getattr(self, 'case_type', 'unknown'))
        
        # Try to render the template
        try:
            body = template._render_field('body_html', [self.id])[self.id]
            subject = template._render_field('subject', [self.id])[self.id]
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Template Found'),
                    'message': _('Template: %s\nSubject: %s\nBody length: %d chars') % (
                        template.name, subject, len(body or '')
                    ),
                    'type': 'success',
                    'sticky': True,
                }
            }
        except Exception as e:
            raise UserError(_("Template render error: %s") % str(e))
