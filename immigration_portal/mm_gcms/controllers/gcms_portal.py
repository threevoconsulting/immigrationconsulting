# -*- coding: utf-8 -*-
"""
GCMS Portal Controller
Phase 6: GCMS Notes Request Workflow

Handles portal routes for GCMS cases including:
- GCMS request form submission
- Service agreement signing
- Payment processing
- Document downloads
- Consultation requests and scheduling

Pattern from Phase 3 Lessons Learned:
- Portal fallback stage advancement for self-healing
- Dual signature workflows (client and consultant)
- Proper template context for conditional UI states
"""

from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
import werkzeug
from datetime import datetime


class GCMSPortalController(http.Controller):
    """Controller for GCMS case portal functionality."""
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _get_gcms_case(self, case_id, access_token=None):
        """
        Get a GCMS case with proper access control.
        
        Args:
            case_id: ID of the case
            access_token: Optional access token for public access
            
        Returns:
            mm.immigration.case record or raises AccessError
        """
        Case = request.env['mm.immigration.case']
        
        if access_token:
            case = Case.sudo().search([
                ('id', '=', int(case_id)),
                ('access_token', '=', access_token),
                ('case_type', '=', 'gcms'),
            ], limit=1)
        else:
            partner = request.env.user.partner_id
            case = Case.search([
                ('id', '=', int(case_id)),
                ('partner_id', '=', partner.id),
                ('case_type', '=', 'gcms'),
            ], limit=1)
        
        if not case:
            raise AccessError(_("You do not have access to this case."))
        
        return case
    
    def _check_payment_status(self, case):
        """
        Fallback check for payment status and stage advancement.
        Pattern from Phase 3 Lessons Learned.
        """
        if hasattr(case, 'gcms_service_paid') and hasattr(case, '_on_gcms_service_payment_complete'):
            # Check GCMS service payment
            case.invalidate_recordset(['gcms_service_paid'])
            if case.gcms_service_paid and not case.gcms_request_date:
                case.sudo()._on_gcms_service_payment_complete()
        
        if hasattr(case, 'gcms_consultation_paid') and hasattr(case, '_on_gcms_consultation_payment_complete'):
            # Check consultation payment
            case.invalidate_recordset(['gcms_consultation_paid'])
            if case.gcms_consultation_paid and case.gcms_consultation_requested:
                case.sudo()._on_gcms_consultation_payment_complete()
    
    # =========================================================================
    # GCMS REQUEST FORM
    # =========================================================================
    
    @http.route(['/my/immigration/gcms/request'], type='http', auth='user', website=True)
    def gcms_request_form(self, **kw):
        """Display GCMS request form for new requests."""
        partner = request.env.user.partner_id
        
        # Check if user already has a pending GCMS case
        existing_case = request.env['mm.immigration.case'].search([
            ('partner_id', '=', partner.id),
            ('case_type', '=', 'gcms'),
            ('gcms_received_date', '=', False),  # Not yet completed
        ], limit=1)
        
        if existing_case:
            return request.redirect(f'/my/immigration/case/{existing_case.id}')
        
        values = {
            'partner': partner,
            'countries': request.env['res.country'].search([]),
            'application_types': [
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
            'page_name': 'gcms_request',
        }
        
        return request.render('mm_gcms.gcms_request_form', values)
    
    @http.route(['/my/immigration/gcms/request/submit'], type='http', auth='user', website=True, methods=['POST'])
    def gcms_request_submit(self, **post):
        """Handle GCMS request form submission."""
        partner = request.env.user.partner_id
        
        # Validate required fields
        required_fields = ['uci_number', 'application_type']
        for field in required_fields:
            if not post.get(field):
                return request.redirect('/my/immigration/gcms/request?error=missing_fields')
        
        # Create GCMS case
        case_vals = {
            'partner_id': partner.id,
            'case_type': 'gcms',
            'gcms_uci_number': post.get('uci_number'),
            'gcms_application_number': post.get('application_number'),
            'gcms_application_type': post.get('application_type'),
            'gcms_application_type_other': post.get('application_type_other'),
            'gcms_consent_given': post.get('consent') == 'on',
            'gcms_consent_date': fields.Date.today() if post.get('consent') == 'on' else False,
        }
        
        # Find first GCMS stage
        first_stage = request.env['mm.immigration.stage'].search([
            ('case_type', '=', 'gcms'),
        ], order='sequence', limit=1)
        
        if first_stage:
            case_vals['stage_id'] = first_stage.id
        
        case = request.env['mm.immigration.case'].create(case_vals)
        
        # Redirect to agreement signing
        return request.redirect(f'/my/immigration/gcms/agreement/{case.id}')
    
    # =========================================================================
    # SERVICE AGREEMENT
    # =========================================================================
    
    @http.route(['/my/immigration/gcms/agreement/<int:case_id>'], type='http', auth='user', website=True)
    def gcms_service_agreement(self, case_id, **kw):
        """Display GCMS service agreement for signing."""
        case = self._get_gcms_case(case_id)
        
        # Check if agreement already exists
        esign_request = case.gcms_service_agreement_id
        
        values = {
            'case': case,
            'esign_request': esign_request,
            'pending_client': esign_request and esign_request.state == 'pending_client',
            'pending_consultant': esign_request and esign_request.state == 'pending_consultant',
            'signed': esign_request and esign_request.state == 'signed',
            'page_name': 'gcms_agreement',
        }
        
        return request.render('mm_gcms.gcms_service_agreement_page', values)
    
    @http.route(['/my/immigration/gcms/agreement/<int:case_id>/sign'], type='http', auth='user', website=True, methods=['POST'])
    def gcms_sign_agreement(self, case_id, **post):
        """Handle GCMS service agreement signature."""
        case = self._get_gcms_case(case_id)
        
        signature_data = post.get('signature')
        if not signature_data:
            return request.redirect(f'/my/immigration/gcms/agreement/{case_id}?error=no_signature')
        
        # Create or update e-signature request
        if not case.gcms_service_agreement_id:
            esign_vals = {
                'name': f'GCMS Service Agreement - {case.name}',
                'document_type': 'service_agreement',
                'case_id': case.id,
                'partner_id': case.partner_id.id,
                'state': 'pending_consultant',  # After client signs
            }
            esign_request = request.env['mm.esign.request'].sudo().create(esign_vals)
            case.sudo().write({'gcms_service_agreement_id': esign_request.id})
        else:
            esign_request = case.gcms_service_agreement_id
        
        # Record signature
        esign_request.sudo().write({
            'signature_data': signature_data,
            'signed_date': fields.Datetime.now(),
            'ip_address': request.httprequest.remote_addr,
            'user_agent': request.httprequest.user_agent.string,
            'state': 'pending_consultant',
        })
        
        case.message_post(
            body=_("Client signed GCMS service agreement."),
            message_type='notification',
        )
        
        return request.redirect(f'/my/immigration/case/{case_id}')
    
    # =========================================================================
    # PAYMENT
    # =========================================================================
    
    @http.route(['/my/immigration/gcms/payment/<int:case_id>'], type='http', auth='user', website=True)
    def gcms_payment_page(self, case_id, **kw):
        """Display GCMS service payment page."""
        case = self._get_gcms_case(case_id)
        
        # Check payment fallback
        self._check_payment_status(case)
        
        # Get or create sale order
        if not case.gcms_service_order_id:
            product = request.env.ref('mm_gcms.product_gcms_service', raise_if_not_found=False)
            if product:
                order = case.sudo()._create_sale_order(product, 'GCMS Service')
                case.sudo().write({'gcms_service_order_id': order.id})
        
        order = case.gcms_service_order_id
        invoice = order.invoice_ids[:1] if order and order.invoice_ids else None
        
        values = {
            'case': case,
            'order': order,
            'invoice': invoice,
            'amount': order.amount_total if order else 0,
            'currency': order.currency_id if order else request.env.company.currency_id,
            'payment_confirmed': case.gcms_service_paid,
            'page_name': 'gcms_payment',
        }
        
        return request.render('mm_gcms.gcms_payment_page', values)
    
    # =========================================================================
    # DOCUMENTS
    # =========================================================================
    
    @http.route(['/my/immigration/gcms/documents/<int:case_id>'], type='http', auth='user', website=True)
    def gcms_documents_page(self, case_id, **kw):
        """Display GCMS documents (notes and breakdown)."""
        case = self._get_gcms_case(case_id)
        
        values = {
            'case': case,
            'has_notes': bool(case.gcms_notes_document),
            'has_breakdown': bool(case.gcms_breakdown_document),
            'page_name': 'gcms_documents',
        }
        
        return request.render('mm_gcms.gcms_documents_page', values)
    
    @http.route(['/my/immigration/gcms/download/<int:case_id>/<string:doc_type>'], type='http', auth='user', website=True)
    def gcms_download_document(self, case_id, doc_type, **kw):
        """Download GCMS document (notes or breakdown)."""
        case = self._get_gcms_case(case_id)
        
        if doc_type == 'notes':
            document = case.gcms_notes_document
            filename = case.gcms_notes_filename or f'gcms_notes_{case.name}.pdf'
        elif doc_type == 'breakdown':
            document = case.gcms_breakdown_document
            filename = case.gcms_breakdown_filename or f'gcms_breakdown_{case.name}.pdf'
        else:
            raise MissingError(_("Document not found."))
        
        if not document:
            raise MissingError(_("Document not available yet."))
        
        import base64
        content = base64.b64decode(document)
        
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', f'attachment; filename="{filename}"'),
            ('Content-Length', len(content)),
        ]
        
        return request.make_response(content, headers)
    
    # =========================================================================
    # CONSULTATION
    # =========================================================================
    
    @http.route(['/my/immigration/gcms/consultation/request/<int:case_id>'], type='http', auth='user', website=True, methods=['POST'])
    def gcms_request_consultation(self, case_id, **post):
        """Handle consultation request."""
        case = self._get_gcms_case(case_id)
        
        if not case.gcms_received_date:
            return request.redirect(f'/my/immigration/case/{case_id}?error=notes_not_ready')
        
        case.sudo().action_request_consultation()
        
        return request.redirect(f'/my/immigration/gcms/consultation/agreement/{case_id}')
    
    @http.route(['/my/immigration/gcms/consultation/agreement/<int:case_id>'], type='http', auth='user', website=True)
    def gcms_consultation_agreement(self, case_id, **kw):
        """Display consultation agreement for signing."""
        case = self._get_gcms_case(case_id)
        
        esign_request = case.gcms_consultation_agreement_id
        
        values = {
            'case': case,
            'esign_request': esign_request,
            'pending_client': esign_request and esign_request.state == 'pending_client',
            'pending_consultant': esign_request and esign_request.state == 'pending_consultant',
            'signed': esign_request and esign_request.state == 'signed',
            'page_name': 'gcms_consultation_agreement',
        }
        
        return request.render('mm_gcms.gcms_consultation_agreement_page', values)
    
    @http.route(['/my/immigration/gcms/consultation/agreement/<int:case_id>/sign'], type='http', auth='user', website=True, methods=['POST'])
    def gcms_sign_consultation_agreement(self, case_id, **post):
        """Handle consultation agreement signature."""
        case = self._get_gcms_case(case_id)
        
        signature_data = post.get('signature')
        if not signature_data:
            return request.redirect(f'/my/immigration/gcms/consultation/agreement/{case_id}?error=no_signature')
        
        # Create or update e-signature request
        if not case.gcms_consultation_agreement_id:
            esign_vals = {
                'name': f'GCMS Consultation Agreement - {case.name}',
                'document_type': 'consultation_agreement',
                'case_id': case.id,
                'partner_id': case.partner_id.id,
                'state': 'pending_consultant',
            }
            esign_request = request.env['mm.esign.request'].sudo().create(esign_vals)
            case.sudo().write({'gcms_consultation_agreement_id': esign_request.id})
        else:
            esign_request = case.gcms_consultation_agreement_id
        
        # Record signature
        esign_request.sudo().write({
            'signature_data': signature_data,
            'signed_date': fields.Datetime.now(),
            'ip_address': request.httprequest.remote_addr,
            'user_agent': request.httprequest.user_agent.string,
            'state': 'pending_consultant',
        })
        
        return request.redirect(f'/my/immigration/gcms/consultation/payment/{case_id}')
    
    @http.route(['/my/immigration/gcms/consultation/payment/<int:case_id>'], type='http', auth='user', website=True)
    def gcms_consultation_payment(self, case_id, **kw):
        """Display consultation payment page."""
        case = self._get_gcms_case(case_id)
        
        # Check payment fallback
        self._check_payment_status(case)
        
        # Get or create sale order
        if not case.gcms_consultation_order_id:
            product = request.env.ref('mm_gcms.product_gcms_consultation', raise_if_not_found=False)
            if product:
                order = case.sudo()._create_sale_order(product, 'GCMS Consultation')
                case.sudo().write({'gcms_consultation_order_id': order.id})
        
        order = case.gcms_consultation_order_id
        invoice = order.invoice_ids[:1] if order and order.invoice_ids else None
        
        values = {
            'case': case,
            'order': order,
            'invoice': invoice,
            'amount': order.amount_total if order else 0,
            'currency': order.currency_id if order else request.env.company.currency_id,
            'payment_confirmed': case.gcms_consultation_paid,
            'page_name': 'gcms_consultation_payment',
        }
        
        return request.render('mm_gcms.gcms_consultation_payment_page', values)
    
    @http.route(['/my/immigration/gcms/schedule/<int:case_id>'], type='http', auth='user', website=True)
    def gcms_schedule_consultation(self, case_id, **kw):
        """Display consultation scheduling page."""
        case = self._get_gcms_case(case_id)
        
        if not case.gcms_consultation_paid:
            return request.redirect(f'/my/immigration/gcms/consultation/payment/{case_id}')
        
        values = {
            'case': case,
            'consultant': case.consultant_id,
            'scheduled': bool(case.gcms_consultation_date),
            'consultation_date': case.gcms_consultation_date,
            'page_name': 'gcms_schedule',
        }
        
        return request.render('mm_gcms.gcms_schedule_page', values)
    
    @http.route(['/my/immigration/gcms/schedule/<int:case_id>/confirm'], type='http', auth='user', website=True, methods=['POST'])
    def gcms_confirm_schedule(self, case_id, **post):
        """Confirm consultation schedule."""
        case = self._get_gcms_case(case_id)
        
        date_str = post.get('consultation_date')
        time_str = post.get('consultation_time')
        
        if not date_str or not time_str:
            return request.redirect(f'/my/immigration/gcms/schedule/{case_id}?error=missing_datetime')
        
        try:
            consultation_datetime = datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %H:%M')
        except ValueError:
            return request.redirect(f'/my/immigration/gcms/schedule/{case_id}?error=invalid_datetime')
        
        case.sudo().write({
            'gcms_consultation_date': consultation_datetime,
        })
        
        # Send confirmation email
        template = request.env.ref('mm_gcms.mail_template_gcms_consultation_scheduled', raise_if_not_found=False)
        if template:
            template.sudo().send_mail(case.id, force_send=True)
        
        case.message_post(
            body=_("Consultation scheduled for %s.") % consultation_datetime,
            message_type='notification',
        )
        
        return request.redirect(f'/my/immigration/case/{case_id}')
