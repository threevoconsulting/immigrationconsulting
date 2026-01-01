# -*- coding: utf-8 -*-

import base64
import json

from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError, ValidationError


class EsignPortal(CustomerPortal):
    """Portal controller for e-signature and payment pages."""

    # =====================
    # Quote Routes
    # =====================
    @http.route(['/my/immigration/quote/<int:case_id>'], type='http', auth='user', website=True)
    def portal_quote_view(self, case_id, **kw):
        """Display quote details and service agreement option."""
        partner = request.env.user.partner_id
        
        # Get case and verify access
        case = request.env['mm.immigration.case'].sudo().browse(case_id)
        if not case.exists():
            raise MissingError(_("Case not found."))
        if case.partner_id.id != partner.id:
            raise AccessError(_("You do not have access to this case."))
        
        # Get quote
        sale_order = case.sale_order_id
        if not sale_order:
            return request.render('mm_esign.portal_quote_not_found', {
                'case': case,
            })
        
        values = {
            'page_name': 'immigration_quote',
            'case': case,
            'sale_order': sale_order,
            'order_lines': sale_order.order_line,
            'total_amount': sale_order.amount_total,
            'currency': sale_order.currency_id,
            'can_sign': (
                case.state == 'quoted' and 
                not case.agreement_signed and
                not case.service_agreement_id and
                sale_order.state in ('draft', 'sent', 'sale')
            ),
            'agreement_pending': (
                case.service_agreement_id and 
                case.service_agreement_id.state in ('sent', 'viewed')
            ),
            'pending_consultant': (
                case.service_agreement_id and 
                case.service_agreement_id.state == 'pending_consultant'
            ),
            'agreement_signed': case.agreement_signed,
            'service_agreement': case.service_agreement_id,
        }
        
        return request.render('mm_esign.portal_quote_view', values)

    @http.route(['/my/immigration/quote/<int:case_id>/request-agreement'], 
                type='http', auth='user', website=True, methods=['POST'])
    def portal_request_agreement(self, case_id, **kw):
        """Request service agreement to be sent for signature."""
        partner = request.env.user.partner_id
        
        case = request.env['mm.immigration.case'].sudo().browse(case_id)
        if not case.exists() or case.partner_id.id != partner.id:
            return request.redirect('/my/immigration')
        
        # Check if agreement can be created
        if case.service_agreement_id:
            return request.redirect(f'/my/immigration/quote/{case_id}')
        
        if not case.sale_order_id:
            return request.redirect(f'/my/immigration/quote/{case_id}')
        
        # Confirm sale order if in draft
        if case.sale_order_id.state == 'draft':
            case.sale_order_id.sudo().action_confirm()
        
        # Create and send service agreement
        esign_request = request.env['mm.esign.request'].sudo().create({
            'document_type': 'service_agreement',
            'case_id': case.id,
            'partner_id': case.partner_id.id,
            'requires_consultant_signature': True,  # Enable dual signature
        })
        esign_request.action_generate_document()
        esign_request.action_send()
        
        return request.redirect(f'/my/immigration/sign/{esign_request.access_token}')

    # =====================
    # Signing Routes
    # =====================
    @http.route(['/my/immigration/sign/<string:token>'], type='http', auth='public', website=True)
    def portal_sign_view(self, token, **kw):
        """Public signing page accessed via token in email."""
        # Find esign request by token
        esign_request = request.env['mm.esign.request'].sudo().search([
            ('access_token', '=', token)
        ], limit=1)
        
        if not esign_request:
            return request.render('mm_esign.portal_sign_invalid_token', {})
        
        # Check if expired
        if esign_request.is_expired:
            return request.render('mm_esign.portal_sign_expired', {
                'esign_request': esign_request,
            })
        
        # Check if already signed (client signed, waiting for consultant)
        if esign_request.state == 'pending_consultant':
            return request.render('mm_esign.portal_sign_pending_consultant', {
                'esign_request': esign_request,
                'case': esign_request.case_id,
            })
        
        # Check if fully signed
        if esign_request.state == 'signed':
            return request.render('mm_esign.portal_sign_already_signed', {
                'esign_request': esign_request,
            })
        
        # Check if client signed (without consultant requirement)
        if esign_request.state == 'client_signed':
            return request.render('mm_esign.portal_sign_already_signed', {
                'esign_request': esign_request,
            })
        
        # Check if cancelled
        if esign_request.state == 'cancelled':
            return request.render('mm_esign.portal_sign_cancelled', {
                'esign_request': esign_request,
            })
        
        # Mark as viewed
        if esign_request.state == 'sent':
            esign_request.action_mark_viewed()
        
        # Get document type display name
        doc_type_display = dict(esign_request._fields['document_type'].selection).get(
            esign_request.document_type, esign_request.document_type
        )
        
        values = {
            'page_name': 'immigration_sign',
            'esign_request': esign_request,
            'document_type_display': doc_type_display,
            'signer_name': esign_request.partner_id.name,
            'case': esign_request.case_id,
            'token': token,
        }
        
        return request.render('mm_esign.portal_sign_view', values)

    @http.route(['/my/immigration/sign/<string:token>/document'], 
                type='http', auth='public', website=True)
    def portal_sign_document_view(self, token, **kw):
        """Return the PDF document for viewing in browser."""
        esign_request = request.env['mm.esign.request'].sudo().search([
            ('access_token', '=', token)
        ], limit=1)
        
        if not esign_request or not esign_request.document:
            return request.not_found()
        
        # Return PDF
        pdf_content = base64.b64decode(esign_request.document)
        
        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'inline; filename="{esign_request.document_filename}"'),
            ]
        )

    @http.route(['/my/immigration/sign/<string:token>/submit'], 
                type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def portal_sign_submit(self, token, **kw):
        """Process signature submission."""
        esign_request = request.env['mm.esign.request'].sudo().search([
            ('access_token', '=', token)
        ], limit=1)
        
        if not esign_request:
            return json.dumps({'success': False, 'error': 'Invalid token'})
        
        if esign_request.state not in ('sent', 'viewed'):
            return json.dumps({'success': False, 'error': 'Cannot sign this document'})
        
        if esign_request.is_expired:
            return json.dumps({'success': False, 'error': 'Signature request has expired'})
        
        # Get signature data
        signature_type = kw.get('signature_type', 'draw')
        signature_data = kw.get('signature_data')
        typed_name = kw.get('typed_name')
        
        if not signature_data:
            return json.dumps({'success': False, 'error': 'Signature is required'})
        
        # Clean up base64 data URL if present
        if signature_data.startswith('data:image'):
            signature_data = signature_data.split(',')[1]
        
        # Get client info
        ip_address = request.httprequest.remote_addr
        user_agent = request.httprequest.user_agent.string if request.httprequest.user_agent else ''
        
        try:
            # Use the new action_client_sign method for dual-signature workflow
            esign_request.action_client_sign(
                signature_data=signature_data,
                signature_type=signature_type,
                typed_name=typed_name,
                ip_address=ip_address,
                user_agent=user_agent[:500],  # Truncate long user agents
            )
            
            return json.dumps({
                'success': True,
                'redirect_url': f'/my/immigration/sign/{token}/complete'
            })
            
        except Exception as e:
            return json.dumps({'success': False, 'error': str(e)})

    @http.route(['/my/immigration/sign/<string:token>/complete'], 
                type='http', auth='public', website=True)
    def portal_sign_complete(self, token, **kw):
        """Show signature completion page."""
        esign_request = request.env['mm.esign.request'].sudo().search([
            ('access_token', '=', token)
        ], limit=1)
        
        if not esign_request:
            return request.redirect('/my/immigration')
        
        # Handle different completion states
        if esign_request.state == 'pending_consultant':
            # Client signed, waiting for consultant
            return request.render('mm_esign.portal_sign_pending_consultant', {
                'page_name': 'immigration_sign_complete',
                'esign_request': esign_request,
                'case': esign_request.case_id,
            })
        
        if esign_request.state not in ('signed', 'client_signed'):
            return request.redirect('/my/immigration')
        
        values = {
            'page_name': 'immigration_sign_complete',
            'esign_request': esign_request,
            'case': esign_request.case_id,
            'show_payment_link': (
                esign_request.document_type == 'service_agreement' and 
                esign_request.state == 'signed'  # Only show payment link when fully signed
            ),
        }
        
        return request.render('mm_esign.portal_sign_complete', values)

    # =====================
    # Payment Routes
    # =====================
    @http.route(['/my/immigration/pay/<int:case_id>'], type='http', auth='user', website=True)
    def portal_payment_view(self, case_id, **kw):
        """Display payment page with invoice link."""
        partner = request.env.user.partner_id
        
        # Get case and verify access
        case = request.env['mm.immigration.case'].sudo().browse(case_id)
        if not case.exists():
            raise MissingError(_("Case not found."))
        if case.partner_id.id != partner.id:
            raise AccessError(_("You do not have access to this case."))
        
        # Check if payment is needed
        if case.payment_confirmed:
            return request.render('mm_esign.portal_payment_already_paid', {
                'case': case,
            })
        
        # Check if agreement is signed (fully signed, not just client signed)
        if not case.agreement_signed:
            return request.redirect(f'/my/immigration/quote/{case_id}')
        
        # Get invoice
        invoices = case.invoice_ids.filtered(
            lambda inv: inv.state == 'posted' and inv.payment_state != 'paid'
        )
        
        if not invoices:
            return request.render('mm_esign.portal_payment_no_invoice', {
                'case': case,
            })
        
        invoice = invoices[0]  # Get first unpaid invoice
        
        values = {
            'page_name': 'immigration_payment',
            'case': case,
            'invoice': invoice,
            'amount': invoice.amount_residual,
            'currency': invoice.currency_id,
            'invoice_url': invoice.get_portal_url(),
        }
        
        return request.render('mm_esign.portal_payment_view', values)

    @http.route(['/my/immigration/pay/<int:case_id>/redirect'], 
                type='http', auth='user', website=True)
    def portal_payment_redirect(self, case_id, **kw):
        """Redirect to invoice payment page."""
        partner = request.env.user.partner_id
        
        case = request.env['mm.immigration.case'].sudo().browse(case_id)
        if not case.exists() or case.partner_id.id != partner.id:
            return request.redirect('/my/immigration')
        
        invoices = case.invoice_ids.filtered(
            lambda inv: inv.state == 'posted' and inv.payment_state != 'paid'
        )
        
        if invoices:
            return request.redirect(invoices[0].get_portal_url())
        
        return request.redirect(f'/my/immigration/case/{case_id}')

    # =====================
    # Override Placeholder Routes from mm_portal
    # =====================
    @http.route(['/my/immigration/quote'], type='http', auth='user', website=True)
    def portal_quote_redirect(self, **kw):
        """Redirect to case-specific quote page."""
        partner = request.env.user.partner_id
        cases = request.env['mm.immigration.case'].sudo().search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'quoted'),
        ], limit=1)
        
        if cases:
            return request.redirect(f'/my/immigration/quote/{cases[0].id}')
        
        return request.redirect('/my/immigration')

    @http.route(['/my/immigration/pay'], type='http', auth='user', website=True)
    def portal_pay_redirect(self, **kw):
        """Redirect to case-specific payment page."""
        partner = request.env.user.partner_id
        cases = request.env['mm.immigration.case'].sudo().search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'paid'),
        ], limit=1)
        
        if cases:
            return request.redirect(f'/my/immigration/pay/{cases[0].id}')
        
        return request.redirect('/my/immigration')
