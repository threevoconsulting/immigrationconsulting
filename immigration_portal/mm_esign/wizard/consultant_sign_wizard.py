# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError


class ConsultantSignWizard(models.TransientModel):
    _name = 'mm.esign.consultant.sign.wizard'
    _description = 'Consultant Signature Wizard'

    esign_request_id = fields.Many2one(
        comodel_name='mm.esign.request',
        string='Signature Request',
        required=True,
        readonly=True,
    )
    document_type = fields.Selection(
        related='esign_request_id.document_type',
        string='Document Type',
        readonly=True,
    )
    client_name = fields.Char(
        related='esign_request_id.partner_id.name',
        string='Client',
        readonly=True,
    )
    case_name = fields.Char(
        related='esign_request_id.case_id.name',
        string='Case Reference',
        readonly=True,
    )
    client_signed_date = fields.Datetime(
        related='esign_request_id.signed_date',
        string='Client Signed On',
        readonly=True,
    )
    
    signature_type = fields.Selection(
        selection=[
            ('draw', 'Draw Signature'),
            ('type', 'Type Signature'),
        ],
        string='Signature Method',
        default='type',
        required=True,
    )
    signature_data = fields.Binary(
        string='Drawn Signature',
        help='Draw your signature using the canvas.',
    )
    typed_signature = fields.Char(
        string='Typed Signature',
        help='Type your full name as your signature.',
    )

    def action_sign(self):
        """Apply the consultant's signature."""
        self.ensure_one()
        
        if not self.esign_request_id:
            raise UserError(_("No signature request specified."))
        
        # Validate signature
        if self.signature_type == 'draw' and not self.signature_data:
            raise UserError(_("Please draw your signature."))
        if self.signature_type == 'type' and not self.typed_signature:
            raise UserError(_("Please type your signature."))
        
        # Get IP address (from request context if available)
        ip_address = self.env.context.get('ip_address', 'Backend')
        
        # Prepare signature data
        signature_data = self.signature_data
        if self.signature_type == 'type':
            # Generate signature image from typed name
            signature_data = self._generate_typed_signature_image(self.typed_signature)
        
        # Apply signature
        self.esign_request_id.action_consultant_sign(
            signature_data=signature_data,
            signature_type=self.signature_type,
            typed_name=self.typed_signature if self.signature_type == 'type' else None,
            ip_address=ip_address,
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Document has been counter-signed successfully.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def _generate_typed_signature_image(self, name):
        """Generate a signature image from typed text."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import base64
            from io import BytesIO
            
            # Create image
            width, height = 400, 100
            img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            # Try to use a cursive font, fall back to default
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
            except:
                font = ImageFont.load_default()
            
            # Calculate text position (center)
            bbox = draw.textbbox((0, 0), name, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (width - text_width) / 2
            y = (height - text_height) / 2
            
            # Draw text
            draw.text((x, y), name, fill=(0, 0, 0, 255), font=font)
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
            
        except Exception as e:
            # If image generation fails, return None and let the model handle it
            return None
