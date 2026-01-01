# Migration Monitor - GCMS Module (mm_gcms)

## Phase 6: GCMS Notes Request Workflow

This module extends the Immigration Portal to support GCMS (Global Case Management System) notes requests as a separate case type with its own workflow.

---

## Overview

GCMS notes are detailed records from Immigration, Refugees and Citizenship Canada (IRCC) that contain information about an individual's immigration application. This module allows clients to request their GCMS notes through The Migration Monitor's portal.

---

## Features

### Case Type Extension
- New `case_type` field on `mm.immigration.case` with options: 'PR Strategy' and 'GCMS Request'
- GCMS cases have dedicated workflow stages separate from PR cases
- Both case types share the same portal dashboard with filtered views

### GCMS Workflow Stages
| # | Stage | Description |
|---|-------|-------------|
| 1 | Form Submitted | Client fills out GCMS request form |
| 2 | Awaiting Payment | Client pays GCMS service fee ($150) |
| 3 | Processing | Request submitted to IRCC (30-45 days) |
| 4 | Notes Delivered | GCMS notes received, breakdown provided |
| 5 | Consultation Requested | Client requests follow-up call (optional) |
| 6 | Consultation Payment | Client pays consultation fee ($100) |
| 7 | Call Scheduled | Consultation call booked |
| 8 | Completed | Case closed |

### Portal Features
- GCMS request form with UCI number validation
- Service agreement e-signature
- Stripe payment integration
- Document download portal (notes + breakdown)
- Consultation scheduling system
- Email notifications for key events

---

## Technical Implementation

### Dependencies
```python
'depends': [
    'mm_immigration',      # Core case management
    'mm_esign',            # Electronic signatures
    'sale',                # Sale orders
    'account',             # Invoicing
    'mail',                # Email templates
    'portal',              # Portal framework
    'website',             # Web forms
]
```

### Models Extended

#### mm.immigration.case
New fields added:
- `case_type` - Selection field (pr/gcms)
- `gcms_uci_number` - Client's UCI number
- `gcms_application_number` - Application/file number
- `gcms_application_type` - Type of immigration application
- `gcms_consent_given` / `gcms_consent_date` - Consent tracking
- `gcms_request_date` / `gcms_received_date` - Request tracking
- `gcms_notes_document` / `gcms_breakdown_document` - Documents
- `gcms_consultation_requested` / `gcms_consultation_paid` - Consultation
- `gcms_service_order_id` / `gcms_consultation_order_id` - Sale orders

#### mm.immigration.stage
New fields added:
- `case_type` - Filter stages by case type
- `requires_gcms_consent` - Stage requires consent
- `requires_gcms_payment` - Stage requires service payment
- `requires_consultation_payment` - Stage requires consultation payment

### Portal Routes

| Route | Description |
|-------|-------------|
| `/my/immigration/gcms/request` | GCMS request form |
| `/my/immigration/gcms/agreement/<id>` | Service agreement |
| `/my/immigration/gcms/payment/<id>` | Service payment |
| `/my/immigration/gcms/documents/<id>` | Document download |
| `/my/immigration/gcms/consultation/request/<id>` | Request consultation |
| `/my/immigration/gcms/consultation/agreement/<id>` | Consultation agreement |
| `/my/immigration/gcms/consultation/payment/<id>` | Consultation payment |
| `/my/immigration/gcms/schedule/<id>` | Schedule consultation |

### Products Created

1. **GCMS Notes Request Service** (`GCMS-SERVICE`)
   - Price: $150.00 CAD
   - Includes: GCMS notes request, retrieval, and breakdown

2. **GCMS Notes Consultation** (`GCMS-CONSULT`)
   - Price: $100.00 CAD
   - Includes: 30-minute consultation with RCIC

---

## Odoo 19 Compatibility

This module follows all Odoo 19 best practices documented in the lessons learned:

### View Syntax
- ✅ No `attrs=` or `states=` attributes
- ✅ Uses `invisible=`, `readonly=`, `required=` with Python expressions
- ✅ Uses `<list>` instead of `<tree>`
- ✅ Kanban templates use `t-name="card"` not `kanban-box`
- ✅ XML operators escaped (`&gt;`, `&lt;`)
- ✅ Uses `<chatter/>` syntax
- ✅ No `invisible="1"` without justification
- ✅ All icons have `title`, `role`, `aria-label` attributes

### Python Code
- ✅ Uses `@api.model_create_multi` for create overrides
- ✅ No forward model references
- ✅ `group_expand` method without `order` parameter
- ✅ Uses `@api.constrains` instead of `_sql_constraints`
- ✅ Payment detection via `write()` override on `account.move`

### Security
- ✅ Admin access (base.group_system) in CSV files
- ✅ No deprecated `category_id` in security groups

---

## Installation

1. Place the `mm_gcms` folder in your Odoo addons path
2. Update the app list: Settings → Apps → Update Apps List
3. Search for "GCMS" and install "Migration Monitor - GCMS Requests"

---

## Configuration

### Products
After installation, verify products are created:
- Settings → Products → Search "GCMS"
- Adjust prices as needed

### Stripe Payment
Ensure Stripe is configured:
- Settings → Payment Providers → Stripe
- Enter API keys and configure webhook

### Email Templates
Email templates are created automatically. Customize as needed:
- Settings → Technical → Email Templates → Search "GCMS"

---

## Usage

### Creating a GCMS Case (Backend)
1. Go to Immigration → Cases → GCMS Requests
2. Click "Create"
3. Fill in client and GCMS information
4. Use workflow buttons to advance stages

### Client Portal Flow
1. Client clicks "Request GCMS Notes" on portal dashboard
2. Fills out request form with UCI number
3. Signs service agreement
4. Completes payment via Stripe
5. Waits for processing (30-45 days)
6. Downloads notes and breakdown when ready
7. Optionally requests consultation call

---

## File Structure

```
mm_gcms/
├── __init__.py
├── __manifest__.py
├── README.md
├── controllers/
│   ├── __init__.py
│   └── gcms_portal.py           # Portal controllers
├── data/
│   ├── gcms_stage_data.xml      # GCMS workflow stages
│   ├── gcms_product_data.xml    # Service products
│   └── gcms_mail_template_data.xml  # Email templates
├── models/
│   ├── __init__.py
│   ├── immigration_case_gcms.py  # Case model extension
│   ├── immigration_stage_gcms.py # Stage model extension
│   └── account_move_gcms.py      # Payment detection
├── security/
│   └── ir.model.access.csv       # Access rules
└── views/
    ├── gcms_case_views.xml       # Backend views
    ├── gcms_portal_templates.xml # Portal pages
    └── gcms_portal_dashboard.xml # Dashboard widgets
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 19.0.1.0.0 | 2025-01-01 | Initial release |

---

## License

LGPL-3

---

## Author

The Migration Monitor  
https://themigrationmonitor.ca
