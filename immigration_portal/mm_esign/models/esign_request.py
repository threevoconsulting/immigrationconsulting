# -*- coding: utf-8 -*-

import base64
import hashlib
import uuid
from datetime import timedelta
from io import BytesIO
import pytz

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError


class EsignRequest(models.Model):
    _name = 'mm.esign.request'
    _description = 'E-Signature Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # =====================
    # Core Fields
    # =====================
    name = fields.Char(
        string='Reference',
        required=True,
        readonly=True,
        default='New',
        copy=False,
        tracking=True,
    )
    document_type = fields.Selection(
        selection=[
            ('service_agreement', 'Service Agreement'),
            ('roadmap_ack', 'Roadmap Acknowledgment'),
            ('retainer', 'Retainer Agreement'),
        ],
        string='Document Type',
        required=True,
        tracking=True,
    )
    case_id = fields.Many2one(
        comodel_name='mm.immigration.case',
        string='Immigration Case',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Client (Signer)',
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    # =====================
    # Document Fields
    # =====================
    document = fields.Binary(
        string='Document',
        attachment=True,
        copy=False,
    )
    document_filename = fields.Char(
        string='Document Filename',
    )
    signed_document = fields.Binary(
        string='Signed Document',
        attachment=True,
        copy=False,
        readonly=True,
    )
    signed_filename = fields.Char(
        string='Signed Filename',
        readonly=True,
    )

    # =====================
    # Workflow Fields
    # =====================
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('sent', 'Sent to Client'),
            ('viewed', 'Viewed by Client'),
            ('client_signed', 'Client Signed'),
            ('pending_consultant', 'Pending Consultant Signature'),
            ('signed', 'Fully Signed'),
            ('expired', 'Expired'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    requires_consultant_signature = fields.Boolean(
        string='Requires Consultant Signature',
        default=True,
        help='If checked, document requires both client and consultant signatures.',
    )

    # =====================
    # Access Token Fields
    # =====================
    access_token = fields.Char(
        string='Access Token',
        copy=False,
        readonly=True,
    )
    expires_at = fields.Datetime(
        string='Expires At',
        copy=False,
        readonly=True,
    )

    # =====================
    # Client Signature Fields
    # =====================
    signature_data = fields.Binary(
        string='Client Signature Image',
        attachment=True,
        copy=False,
        readonly=True,
    )
    signature_type = fields.Selection(
        selection=[
            ('draw', 'Drawn'),
            ('type', 'Typed'),
        ],
        string='Client Signature Type',
        readonly=True,
        copy=False,
    )
    typed_signature = fields.Char(
        string='Client Typed Signature',
        readonly=True,
        copy=False,
    )
    signed_date = fields.Datetime(
        string='Client Signed Date',
        readonly=True,
        copy=False,
    )
    ip_address = fields.Char(
        string='Client IP Address',
        readonly=True,
        copy=False,
    )
    user_agent = fields.Char(
        string='Client User Agent',
        readonly=True,
        copy=False,
    )

    # =====================
    # Consultant Signature Fields
    # =====================
    consultant_id = fields.Many2one(
        comodel_name='res.users',
        string='Consultant',
        help='The consultant who will counter-sign the document.',
        tracking=True,
    )
    consultant_signature_data = fields.Binary(
        string='Consultant Signature Image',
        attachment=True,
        copy=False,
        readonly=True,
    )
    consultant_signature_type = fields.Selection(
        selection=[
            ('draw', 'Drawn'),
            ('type', 'Typed'),
        ],
        string='Consultant Signature Type',
        readonly=True,
        copy=False,
    )
    consultant_typed_signature = fields.Char(
        string='Consultant Typed Signature',
        readonly=True,
        copy=False,
    )
    consultant_signed_date = fields.Datetime(
        string='Consultant Signed Date',
        readonly=True,
        copy=False,
    )
    consultant_ip_address = fields.Char(
        string='Consultant IP Address',
        readonly=True,
        copy=False,
    )

    # =====================
    # Audit Fields
    # =====================
    viewed_at = fields.Datetime(
        string='First Viewed',
        readonly=True,
        copy=False,
    )
    email_sent = fields.Boolean(
        string='Email Sent',
        default=False,
        copy=False,
    )

    # =====================
    # Computed Fields
    # =====================
    is_expired = fields.Boolean(
        string='Is Expired',
        compute='_compute_is_expired',
    )
    signing_url = fields.Char(
        string='Signing URL',
        compute='_compute_signing_url',
    )
    days_until_expiry = fields.Integer(
        string='Days Until Expiry',
        compute='_compute_days_until_expiry',
    )
    is_fully_signed = fields.Boolean(
        string='Fully Signed',
        compute='_compute_is_fully_signed',
    )

    # =====================
    # Constraints
    # =====================
    @api.constrains('access_token')
    def _check_access_token_unique(self):
        """Ensure access token is unique."""
        for record in self:
            if record.access_token:
                existing = self.search([
                    ('access_token', '=', record.access_token),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_("Access token must be unique!"))

    @api.constrains('document')
    def _check_document(self):
        """Ensure document is provided before sending."""
        for record in self:
            if record.state == 'sent' and not record.document:
                raise ValidationError(_("Document is required before sending for signature."))

    # =====================
    # Computed Methods
    # =====================
    @api.depends('expires_at', 'state')
    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_expired = (
                record.expires_at and 
                record.expires_at < now and 
                record.state not in ('signed', 'client_signed', 'cancelled')
            )

    @api.depends('access_token')
    def _compute_signing_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            if record.access_token:
                record.signing_url = f"{base_url}/my/immigration/sign/{record.access_token}"
            else:
                record.signing_url = False

    @api.depends('expires_at')
    def _compute_days_until_expiry(self):
        now = fields.Datetime.now()
        for record in self:
            if record.expires_at and record.state in ('sent', 'viewed'):
                delta = record.expires_at - now
                record.days_until_expiry = max(0, delta.days)
            else:
                record.days_until_expiry = 0

    @api.depends('state', 'requires_consultant_signature', 'signature_data', 'consultant_signature_data')
    def _compute_is_fully_signed(self):
        for record in self:
            if record.requires_consultant_signature:
                record.is_fully_signed = (
                    record.signature_data and 
                    record.consultant_signature_data and
                    record.state == 'signed'
                )
            else:
                record.is_fully_signed = (
                    record.signature_data and 
                    record.state in ('signed', 'client_signed')
                )

    # =====================
    # Timezone Helper
    # =====================
    def _get_user_timezone(self, user=None):
        """Get the timezone for displaying dates."""
        if user and user.tz:
            return pytz.timezone(user.tz)
        if self.company_id and self.company_id.partner_id.tz:
            return pytz.timezone(self.company_id.partner_id.tz)
        # Default to company timezone or UTC
        return pytz.timezone('America/Edmonton')  # Alberta timezone

    def _format_datetime_local(self, dt, user=None):
        """Format a datetime in the user's timezone."""
        if not dt:
            return ''
        tz = self._get_user_timezone(user)
        utc_dt = pytz.UTC.localize(dt) if dt.tzinfo is None else dt
        local_dt = utc_dt.astimezone(tz)
        return local_dt.strftime('%B %d, %Y at %H:%M %Z')

    def _format_datetime_short(self, dt, user=None):
        """Format a datetime in short format."""
        if not dt:
            return ''
        tz = self._get_user_timezone(user)
        utc_dt = pytz.UTC.localize(dt) if dt.tzinfo is None else dt
        local_dt = utc_dt.astimezone(tz)
        return local_dt.strftime('%Y-%m-%d %H:%M %Z')

    def _format_date_only(self, dt, user=None):
        """Format just the date portion in user's timezone (for signature date field)."""
        if not dt:
            return ''
        tz = self._get_user_timezone(user)
        utc_dt = pytz.UTC.localize(dt) if dt.tzinfo is None else dt
        local_dt = utc_dt.astimezone(tz)
        return local_dt.strftime('%B %d, %Y')  # e.g., "December 31, 2025"

    # =====================
    # CRUD Methods
    # =====================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('mm.esign.request') or 'New'
            # Default consultant to case consultant
            if not vals.get('consultant_id') and vals.get('case_id'):
                case = self.env['mm.immigration.case'].browse(vals['case_id'])
                if case.consultant_id:
                    vals['consultant_id'] = case.consultant_id.id
        return super().create(vals_list)

    # =====================
    # Business Methods
    # =====================
    def _generate_access_token(self):
        """Generate a unique access token for the signing URL."""
        self.ensure_one()
        token = str(uuid.uuid4())
        # Verify uniqueness
        while self.search_count([('access_token', '=', token)]) > 0:
            token = str(uuid.uuid4())
        return token

    def action_generate_document(self):
        """Generate the PDF document for signing."""
        self.ensure_one()
        
        # Determine which report to use based on document type
        report_mapping = {
            'service_agreement': 'mm_esign.report_service_agreement',
            'roadmap_ack': 'mm_esign.report_roadmap_acknowledgment',
            'retainer': 'mm_esign.report_retainer_agreement',
        }
        
        report_ref = report_mapping.get(self.document_type)
        if not report_ref:
            raise UserError(_("No report template configured for document type: %s") % self.document_type)
        
        # Check if report exists
        report = self.env.ref(report_ref, raise_if_not_found=False)
        if not report:
            raise UserError(_("Report template '%s' not found. Please install the required module.") % report_ref)
        
        # Generate PDF
        pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
            report_ref,
            [self.case_id.id],
        )
        
        # Set filename
        filename = f"{self.document_type.replace('_', ' ').title()}_{self.case_id.name}.pdf"
        
        self.write({
            'document': base64.b64encode(pdf_content),
            'document_filename': filename,
        })
        
        return True

    def action_send(self):
        """Send the signature request to the client."""
        self.ensure_one()
        
        if not self.document:
            self.action_generate_document()
        
        # Generate access token
        token = self._generate_access_token()
        expires_at = fields.Datetime.now() + timedelta(days=7)
        
        self.write({
            'access_token': token,
            'expires_at': expires_at,
            'state': 'sent',
        })

        # Send email to client
        template = self.env.ref('mm_esign.email_template_signature_request', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.write({'email_sent': True})

        self.message_post(
            body=_("Signature request sent to %s. Token expires on %s.") % (
                self.partner_id.email,
                self._format_datetime_local(expires_at)
            ),
            message_type='notification',
        )
        
        return True

    def action_mark_viewed(self):
        """Mark the document as viewed by the client."""
        self.ensure_one()
        if self.state == 'sent' and not self.viewed_at:
            self.write({
                'state': 'viewed',
                'viewed_at': fields.Datetime.now(),
            })

    def action_client_sign(self, signature_data, signature_type, typed_name=None, ip_address=None, user_agent=None):
        """Record the client's signature."""
        self.ensure_one()
        
        if self.state not in ('sent', 'viewed'):
            raise UserError(_("This document cannot be signed in its current state."))
        
        if self.is_expired:
            raise UserError(_("This signature request has expired."))
        
        # Handle signature data - can be bytes (from Binary field) or string (from portal)
        if signature_data:
            # If it's bytes, decode to string first
            if isinstance(signature_data, bytes):
                signature_data = signature_data.decode('utf-8')
            # Remove data URL prefix if present (e.g., "data:image/png;base64,...")
            if isinstance(signature_data, str) and ',' in signature_data:
                signature_data = signature_data.split(',')[1]
        
        now = fields.Datetime.now()
        
        # Determine next state
        if self.requires_consultant_signature:
            next_state = 'pending_consultant'
        else:
            next_state = 'signed'
        
        self.write({
            'signature_data': signature_data,
            'signature_type': signature_type,
            'typed_signature': typed_name,
            'signed_date': now,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'state': next_state,
        })

        self.message_post(
            body=_("Document signed by client %s from IP %s") % (
                self.partner_id.name,
                ip_address or 'Unknown'
            ),
            message_type='notification',
        )

        # If no consultant signature required, generate final PDF and trigger workflow
        if not self.requires_consultant_signature:
            self._generate_signed_pdf()
            self._send_completion_email()
            if self.case_id:
                self.case_id._on_signature_complete(self)
        else:
            # Notify consultant
            self._notify_consultant_to_sign()

        return True

    def _notify_consultant_to_sign(self):
        """Notify the consultant that their signature is needed."""
        self.ensure_one()
        if not self.consultant_id:
            return
        
        # Create activity for consultant
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=self.consultant_id.id,
            summary=_('Counter-signature required'),
            note=_('Client %s has signed the %s. Your counter-signature is required.') % (
                self.partner_id.name,
                self.document_type.replace('_', ' ').title()
            ),
        )
        
        self.message_post(
            body=_("Awaiting consultant signature from %s.") % self.consultant_id.name,
            message_type='notification',
        )

    def action_consultant_sign(self, signature_data, signature_type, typed_name=None, ip_address=None):
        """Record the consultant's counter-signature."""
        self.ensure_one()
        
        if self.state != 'pending_consultant':
            raise UserError(_("This document is not ready for consultant signature."))
        
        # Verify user is the assigned consultant or has manager rights
        if self.env.user != self.consultant_id and not self.env.user.has_group('mm_immigration.group_immigration_manager'):
            raise AccessError(_("Only the assigned consultant or a manager can sign this document."))
        
        # Handle signature data - can be bytes (from Binary field) or string (from portal)
        if signature_data:
            # If it's bytes, decode to string first
            if isinstance(signature_data, bytes):
                signature_data = signature_data.decode('utf-8')
            # Remove data URL prefix if present (e.g., "data:image/png;base64,...")
            if isinstance(signature_data, str) and ',' in signature_data:
                signature_data = signature_data.split(',')[1]
        
        now = fields.Datetime.now()
        
        self.write({
            'consultant_signature_data': signature_data,
            'consultant_signature_type': signature_type,
            'consultant_typed_signature': typed_name,
            'consultant_signed_date': now,
            'consultant_ip_address': ip_address,
            'state': 'signed',
        })

        # Generate final signed PDF with both signatures
        self._generate_signed_pdf()

        # Send confirmation email
        self._send_completion_email()

        self.message_post(
            body=_("Document counter-signed by consultant %s from IP %s. Document is now fully executed.") % (
                self.consultant_id.name,
                ip_address or 'Unknown'
            ),
            message_type='notification',
        )

        # Trigger case workflow
        if self.case_id:
            self.case_id._on_signature_complete(self)

        return True

    def _send_completion_email(self):
        """Send completion email to client."""
        template = self.env.ref('mm_esign.email_template_signature_complete', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _generate_signed_pdf(self):
        """Generate the signed PDF with signature stamps and audit footer."""
        self.ensure_one()
        
        if not self.document or not self.signature_data:
            return False

        try:
            # Import PDF libraries
            from PyPDF2 import PdfReader, PdfWriter
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.units import inch
            from PIL import Image
            
            # Read original PDF
            original_pdf = BytesIO(base64.b64decode(self.document))
            pdf_reader = PdfReader(original_pdf)
            pdf_writer = PdfWriter()
            
            # Get number of pages
            num_pages = len(pdf_reader.pages)
            
            # Decode client signature image
            client_sig_data = base64.b64decode(self.signature_data)
            client_sig_image = Image.open(BytesIO(client_sig_data))
            
            # Decode consultant signature if present
            consultant_sig_image = None
            if self.consultant_signature_data:
                consultant_sig_data = base64.b64decode(self.consultant_signature_data)
                consultant_sig_image = Image.open(BytesIO(consultant_sig_data))
            
            # Process each page
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)
                
                # Create overlay
                overlay_buffer = BytesIO()
                c = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))
                
                # Add initials to all pages except last
                if page_num < num_pages - 1:
                    initials = self._get_initials()
                    c.setFont("Helvetica", 8)
                    c.drawString(page_width - 60, 30, f"Initials: {initials}")
                    c.drawString(page_width - 60, 20, self.signed_date.strftime('%Y-%m-%d'))
                
                # Add signatures to last page
                if page_num == num_pages - 1:
                    from reportlab.lib.utils import ImageReader
                    
                    # Signature dimensions - sized to fit within the 60px signature area
                    sig_width = 140
                    sig_height = 45
                    
                    # ----- CLIENT SIGNATURE (LEFT SIDE) -----
                    # Template has: "Client:" label, then 60px div for signature, then line, name, date
                    # The signature div starts approximately 200pts from bottom on last page
                    # Position signature to appear INSIDE the 60px box, ABOVE the line
                    client_sig_x = 72  # 1 inch from left margin
                    client_sig_y = 185  # Position inside the signature box
                    
                    # Save and draw client signature
                    client_sig_temp = BytesIO()
                    client_sig_image.save(client_sig_temp, format='PNG')
                    client_sig_temp.seek(0)
                    
                    c.drawImage(
                        ImageReader(client_sig_temp), 
                        client_sig_x, client_sig_y, 
                        width=sig_width, height=sig_height, 
                        preserveAspectRatio=True,
                        mask='auto'
                    )
                    
                    # Add client signature date (fill in the date field)
                    # Date line is at the bottom of the signature block
                    c.setFont("Helvetica", 10)
                    c.setFillColorRGB(0, 0, 0)
                    client_date_str = self._format_date_only(self.signed_date)
                    c.drawString(110, 120, client_date_str)  # After "Date:" label
                    
                    # ----- CONSULTANT SIGNATURE (RIGHT SIDE) -----
                    if consultant_sig_image:
                        # Right side signature block - starts at page midpoint
                        consultant_sig_x = page_width / 2 + 20
                        consultant_sig_y = 185  # Same height as client signature
                        
                        consultant_sig_temp = BytesIO()
                        consultant_sig_image.save(consultant_sig_temp, format='PNG')
                        consultant_sig_temp.seek(0)
                        
                        c.drawImage(
                            ImageReader(consultant_sig_temp), 
                            consultant_sig_x, consultant_sig_y, 
                            width=sig_width, height=sig_height, 
                            preserveAspectRatio=True,
                            mask='auto'
                        )
                        
                        # Add consultant signature date
                        c.setFont("Helvetica", 10)
                        c.setFillColorRGB(0, 0, 0)
                        consultant_date_str = self._format_date_only(self.consultant_signed_date)
                        c.drawString(page_width / 2 + 58, 120, consultant_date_str)  # After "Date:" label
                
                # Add audit footer to all pages
                c.setFont("Helvetica", 6)
                c.setFillColorRGB(0.5, 0.5, 0.5)
                
                # Build audit text
                audit_parts = [
                    f"Electronically signed by {self.partner_id.name} on {self._format_datetime_short(self.signed_date)}"
                ]
                if self.consultant_signed_date:
                    consultant_name = self.consultant_id.name if self.consultant_id else 'Consultant'
                    audit_parts.append(f"Counter-signed by {consultant_name} on {self._format_datetime_short(self.consultant_signed_date)}")
                audit_parts.append(f"IP: {self.ip_address or 'N/A'}")
                audit_parts.append(f"Doc ID: {self.name}")
                
                audit_text = " | ".join(audit_parts)
                c.drawCentredString(page_width / 2, 10, audit_text)
                
                c.save()
                
                # Merge overlay with original page
                overlay_buffer.seek(0)
                overlay_pdf = PdfReader(overlay_buffer)
                if len(overlay_pdf.pages) > 0:
                    page.merge_page(overlay_pdf.pages[0])
                
                pdf_writer.add_page(page)
            
            # Write output
            output_buffer = BytesIO()
            pdf_writer.write(output_buffer)
            output_buffer.seek(0)
            
            # Save signed document
            signed_filename = f"Signed_{self.document_filename or 'document.pdf'}"
            self.write({
                'signed_document': base64.b64encode(output_buffer.getvalue()),
                'signed_filename': signed_filename,
            })
            
            return True
            
        except ImportError as e:
            # Fallback: just copy original with metadata
            self.message_post(
                body=_("PDF signing libraries not available. Signature recorded but PDF not stamped. Error: %s") % str(e),
                message_type='notification',
            )
            self.write({
                'signed_document': self.document,
                'signed_filename': f"Signed_{self.document_filename or 'document.pdf'}",
            })
            return False
        except Exception as e:
            self.message_post(
                body=_("Error generating signed PDF: %s") % str(e),
                message_type='notification',
            )
            return False

    def _get_initials(self):
        """Get initials from signer name."""
        if not self.partner_id.name:
            return "XX"
        parts = self.partner_id.name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        elif len(parts) == 1:
            return parts[0][:2].upper()
        return "XX"

    def action_cancel(self):
        """Cancel the signature request."""
        self.ensure_one()
        if self.state == 'signed':
            raise UserError(_("Cannot cancel a fully signed document."))
        
        self.write({'state': 'cancelled'})
        self.message_post(
            body=_("Signature request cancelled."),
            message_type='notification',
        )
        return True

    def action_resend(self):
        """Resend the signature request with a new token."""
        self.ensure_one()
        if self.state not in ('sent', 'viewed', 'expired'):
            raise UserError(_("Can only resend requests that are pending or expired."))
        
        # Generate new token and reset expiration
        token = self._generate_access_token()
        expires_at = fields.Datetime.now() + timedelta(days=7)
        
        self.write({
            'access_token': token,
            'expires_at': expires_at,
            'state': 'sent',
            'viewed_at': False,
        })

        # Send email
        template = self.env.ref('mm_esign.email_template_signature_request', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

        self.message_post(
            body=_("Signature request resent to %s.") % self.partner_id.email,
            message_type='notification',
        )
        return True

    def action_view_document(self):
        """Open document in browser."""
        self.ensure_one()
        if not self.document:
            raise UserError(_("No document available."))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/document/{self.document_filename}?download=false',
            'target': 'new',
        }

    def action_download_signed(self):
        """Download signed document."""
        self.ensure_one()
        if not self.signed_document:
            raise UserError(_("No signed document available."))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/signed_document/{self.signed_filename}?download=true',
            'target': 'self',
        }

    def action_open_consultant_signing(self):
        """Open the consultant signing wizard."""
        self.ensure_one()
        if self.state != 'pending_consultant':
            raise UserError(_("This document is not ready for consultant signature."))
        
        return {
            'name': _('Sign Document'),
            'type': 'ir.actions.act_window',
            'res_model': 'mm.esign.consultant.sign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_esign_request_id': self.id,
            },
        }

    # =====================
    # Cron Methods
    # =====================
    @api.model
    def _cron_expire_requests(self):
        """Cron job to expire old signature requests."""
        now = fields.Datetime.now()
        expired_requests = self.search([
            ('state', 'in', ['sent', 'viewed']),
            ('expires_at', '<', now),
        ])
        
        for request in expired_requests:
            request.write({'state': 'expired'})
            request.message_post(
                body=_("Signature request expired."),
                message_type='notification',
            )
        
        return True

    # =====================
    # Portal Access
    # =====================
    def _get_signing_url(self):
        """Get the full signing URL for email templates."""
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/my/immigration/sign/{self.access_token}"
