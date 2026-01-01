# Immigration E-Signature Module (mm_esign)

## Overview

The `mm_esign` module provides electronic signature and payment integration for The Migration Monitor immigration portal. It bridges the gap between the "Quoted" stage (Q1 completion) and the "Assessment" stage (Q2 availability), handling:

- Electronic signature capture (draw or type)
- PDF document generation and stamping
- Service agreement management
- Integration with Odoo's payment system
- Automatic workflow progression

## Features

### E-Signature System
- **Draw Signature**: Canvas-based signature capture with smooth rendering
- **Type Signature**: Typed name converted to signature-style image
- **PDF Stamping**: Signatures and audit trail stamped onto documents
- **Initials**: All pages except last get initials in bottom-right corner
- **Audit Trail**: IP address, timestamp, and browser info recorded
- **7-Day Expiration**: Signature requests expire after 7 days

### Payment Integration
- Leverages Odoo's built-in `payment_stripe` module
- Monitors invoice payment state for automatic stage advancement
- No custom payment handling - uses standard Odoo payment flow

### Automated Workflow
- **After Q1 Complete**: Consultant can create quote
- **Quote Confirmed**: Service agreement sent for signature
- **Agreement Signed**: Invoice created, case moves to Payment stage
- **Payment Confirmed**: Case moves to Assessment stage, Q2 invitation sent

## Installation

### Prerequisites
- Odoo 19 Community Edition
- `mm_immigration` module installed
- `mm_portal` module installed
- `mm_questionnaire` module installed
- Stripe payment provider configured in Odoo

### Steps
1. Copy the `mm_esign` folder to your Odoo addons directory
2. Update the app list: Apps → Update App List
3. Search for "Immigration E-Signature" and click Install
4. Configure Stripe payment provider in Settings → Payment Providers

## Configuration

### Stripe Setup
1. Navigate to Settings → Payment Providers
2. Click on Stripe
3. Enter your Publishable Key and Secret Key
4. Set mode (Test or Production)
5. Save and Activate

### Email Templates
The module includes three email templates that are automatically installed:
- **Signature Request**: Sent when agreement is ready for signature
- **Signature Complete**: Sent after successful signing (includes signed PDF)
- **Payment Received**: Sent after payment with Q2 invitation

### Service Agreement Template
The service agreement is generated from a QWeb report template. The content is based on your provided Master Service Agreement with dynamic fields:
- Company information from `res.company`
- Client information from `res.partner` and `mm.client.profile`
- Quote details from `sale.order`

## Usage

### For Consultants

1. **Create Quote**: After Q1 completion, click "Create Quote" on the case
2. **Add Products**: Add services to the sale order
3. **Confirm Quote**: Confirm the sale order
4. **Send Agreement**: Click "Send Service Agreement" to email the signing link
5. **Monitor**: Track signature and payment status on the case form

### For Clients (Portal)

1. **Review Quote**: View quote details at `/my/immigration/quote/{case_id}`
2. **Sign Agreement**: Click through to signing page
3. **Draw/Type Signature**: Choose signature method and sign
4. **Complete Payment**: Pay via Stripe checkout
5. **Start Q2**: Assessment questionnaire unlocked after payment

## Technical Details

### Models

#### mm.esign.request
- `name`: Auto-generated reference (ESR-YYYY-NNNN)
- `document_type`: service_agreement, roadmap_ack, retainer
- `state`: draft, sent, viewed, signed, expired, cancelled
- `access_token`: Unique URL token for signing
- `signature_data`: PNG image of signature
- `signed_document`: PDF with signature applied

#### mm.immigration.case (Extended)
- `sale_order_id`: Link to quote
- `service_agreement_id`: Link to e-sign request
- `payment_confirmed`: Computed from invoice state
- `payment_date`: Date payment received

### Portal Routes

| Route | Description |
|-------|-------------|
| `/my/immigration/quote/<id>` | View quote details |
| `/my/immigration/sign/<token>` | Signing page (public) |
| `/my/immigration/sign/<token>/submit` | Submit signature |
| `/my/immigration/pay/<id>` | Payment page |

### Security

- Portal users can only view/sign their own requests
- Token-based access for signing (no login required)
- Consultants see assigned cases' requests
- Managers have full access

## PDF Libraries

The module uses PyPDF2 and ReportLab for PDF manipulation. If these libraries are not available, the module will fall back to storing the signature data without stamping the PDF.

## Troubleshooting

### Signature Not Appearing on PDF
- Ensure PyPDF2 and ReportLab are installed
- Check Odoo logs for PDF generation errors
- The signature data is always stored even if PDF stamping fails

### Payment Not Triggering Stage Change
- Verify invoice is posted (not draft)
- Check that payment_state changed to 'paid'
- Review the account.move write override in logs

### Emails Not Sending
- Verify outgoing mail server is configured
- Check email template configurations
- Review mail queue for errors

## File Structure

```
mm_esign/
├── __init__.py
├── __manifest__.py
├── controllers/
│   └── esign.py              # Portal routes
├── data/
│   ├── ir_cron_data.xml      # Expiration cron
│   ├── ir_sequence_data.xml  # ESR sequence
│   └── mail_template_data.xml # Email templates
├── models/
│   ├── account_move.py       # Payment detection
│   ├── esign_request.py      # Main e-sign model
│   └── immigration_case.py   # Case extensions
├── report/
│   └── report_service_agreement.xml
├── security/
│   ├── ir.model.access.csv
│   └── security_rules.xml
├── static/src/
│   ├── js/
│   │   ├── esign.js          # Signing page JS
│   │   └── signature_pad.js  # Canvas signature library
│   └── scss/
│       └── esign.scss        # Portal styling
└── views/
    ├── esign_request_views.xml
    ├── immigration_case_views.xml
    ├── menu_views.xml
    ├── portal_esign_templates.xml
    ├── portal_payment_templates.xml
    └── portal_quote_templates.xml
```

## Version History

- **19.0.1.0.0**: Initial release for Odoo 19

## License

LGPL-3

## Author

The Migration Monitor
https://themigrationmonitor.ca
