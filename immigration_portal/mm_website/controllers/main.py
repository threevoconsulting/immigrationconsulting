# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class MigrationMonitorWebsite(http.Controller):
    """Controller for The Migration Monitor public website."""
    
    # -------------------------------------------------------------------------
    # Main Pages
    # -------------------------------------------------------------------------
    
    @http.route(['/'], type='http', auth='public', website=True, sitemap=True)
    def homepage(self, **kw):
        """Render the homepage."""
        values = self._prepare_homepage_values()
        return request.render('mm_website.homepage', values)
    
    @http.route(['/services'], type='http', auth='public', website=True, sitemap=True)
    def services_page(self, **kw):
        """Render the services page."""
        values = {
            'page_title': 'Our Services',
        }
        return request.render('mm_website.services_page', values)
    
    @http.route(['/how-it-works'], type='http', auth='public', website=True, sitemap=True)
    def how_it_works_page(self, **kw):
        """Render the how it works page."""
        values = {
            'page_title': 'How It Works',
        }
        return request.render('mm_website.how_it_works_page', values)
    
    @http.route(['/contact'], type='http', auth='public', website=True, sitemap=True)
    def contact_page(self, **kw):
        """Render the contact page."""
        countries = request.env['res.country'].sudo().search([], order='name')
        values = {
            'page_title': 'Contact Us',
            'countries': countries,
        }
        return request.render('mm_website.contact_page', values)
    
    # -------------------------------------------------------------------------
    # Contact Form Submission
    # -------------------------------------------------------------------------
    
    @http.route(['/contact/submit'], type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def contact_submit(self, **post):
        """Handle contact form submission."""
        # Validate required fields
        required_fields = ['first_name', 'last_name', 'email']
        for field in required_fields:
            if not post.get(field):
                return request.redirect('/contact?error=missing_fields')
        
        # Prepare values
        values = {
            'first_name': post.get('first_name', '').strip(),
            'last_name': post.get('last_name', '').strip(),
            'email': post.get('email', '').strip().lower(),
            'country_id': int(post.get('country_id')) if post.get('country_id') else False,
            'service_interest': post.get('service_interest') or False,
            'message': post.get('message', '').strip(),
            'source': 'website',
            'utm_source': post.get('utm_source', ''),
            'utm_medium': post.get('utm_medium', ''),
            'utm_campaign': post.get('utm_campaign', ''),
        }
        
        try:
            # Create the inquiry
            inquiry = request.env['mm.contact.inquiry'].sudo().create(values)
            _logger.info("Contact inquiry created: %s <%s>", 
                        f"{values['first_name']} {values['last_name']}", 
                        values['email'])
            
            # Send notification email to admin
            self._send_inquiry_notification(inquiry)
            
            # Send confirmation to visitor
            self._send_confirmation_email(inquiry)
            
            return request.redirect('/contact/thank-you')
            
        except Exception as e:
            _logger.exception("Error creating contact inquiry: %s", str(e))
            return request.redirect('/contact?error=submission_failed')
    
    @http.route(['/contact/thank-you'], type='http', auth='public', website=True)
    def contact_thank_you(self, **kw):
        """Render thank you page after form submission."""
        values = {
            'page_title': 'Thank You',
        }
        return request.render('mm_website.contact_thank_you', values)
    
    # -------------------------------------------------------------------------
    # Newsletter Subscription
    # -------------------------------------------------------------------------
    
    @http.route(['/newsletter/subscribe'], type='json', auth='public', website=True, methods=['POST'])
    def newsletter_subscribe(self, email, **kw):
        """Handle newsletter subscription via AJAX."""
        if not email:
            return {'success': False, 'message': _("Please enter your email address.")}
        
        email = email.strip().lower()
        
        # Validate email format
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return {'success': False, 'message': _("Please enter a valid email address.")}
        
        try:
            # Find the newsletter mailing list
            MassMailing = request.env['mailing.list'].sudo()
            newsletter_list = MassMailing.search([('name', 'ilike', 'newsletter')], limit=1)
            
            if not newsletter_list:
                # Create default newsletter list if not exists
                newsletter_list = MassMailing.create({
                    'name': 'Immigration Newsletter',
                    'is_public': True,
                })
            
            # Check if already subscribed
            Contact = request.env['mailing.contact'].sudo()
            existing = Contact.search([
                ('email', '=', email),
                ('list_ids', 'in', newsletter_list.ids),
            ], limit=1)
            
            if existing:
                return {'success': True, 'message': _("You're already subscribed!")}
            
            # Create or update contact
            contact = Contact.search([('email', '=', email)], limit=1)
            if contact:
                contact.write({'list_ids': [(4, newsletter_list.id)]})
            else:
                Contact.create({
                    'email': email,
                    'list_ids': [(4, newsletter_list.id)],
                })
            
            _logger.info("Newsletter subscription: %s", email)
            return {'success': True, 'message': _("Successfully subscribed!")}
            
        except Exception as e:
            _logger.exception("Newsletter subscription error: %s", str(e))
            return {'success': False, 'message': _("An error occurred. Please try again.")}
    
    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    
    def _prepare_homepage_values(self):
        """Prepare values for homepage template."""
        return {
            'page_title': 'Canadian Immigration Consulting',
        }
    
    def _send_inquiry_notification(self, inquiry):
        """Send notification email to admin about new inquiry."""
        try:
            template = request.env.ref('mm_website.mail_template_inquiry_notification', raise_if_not_found=False)
            if template:
                template.sudo().send_mail(inquiry.id, force_send=True)
        except Exception as e:
            _logger.warning("Failed to send inquiry notification: %s", str(e))
    
    def _send_confirmation_email(self, inquiry):
        """Send confirmation email to the person who submitted the form."""
        try:
            template = request.env.ref('mm_website.mail_template_inquiry_confirmation', raise_if_not_found=False)
            if template:
                template.sudo().send_mail(inquiry.id, force_send=True)
        except Exception as e:
            _logger.warning("Failed to send confirmation email: %s", str(e))
