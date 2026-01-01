# Phase 6 GCMS Module - Lessons Learned

**Project:** The Migration Monitor - Immigration Portal  
**Platform:** Odoo 19 Community Edition  
**Phase:** Phase 6 - GCMS Case Type Extension  
**Date:** January 1, 2026  
**Version:** 1.0

---

## Executive Summary

Phase 6 extends the mm_immigration module to support GCMS (Global Case Management System) notes requests as a second case type with its own dedicated workflow. This document captures patterns applied and lessons learned specific to extending an existing case management system with new case types.

---

## Key Implementation Patterns

### 1. Case Type Extension Strategy

**Pattern:** Extend existing model rather than create new module

```python
class ImmigrationCaseGCMS(models.Model):
    _inherit = 'mm.immigration.case'
    
    case_type = fields.Selection(
        selection=[
            ('pr', 'PR Strategy'),
            ('gcms', 'GCMS Request'),
        ],
        default='pr',
        required=True,
    )
```

**Benefits:**
- Shares existing partner/portal infrastructure
- Unified dashboard with case type filtering
- Consistent security rules
- Reuses existing esign and payment integration

**Trade-off:** Stages need `case_type` filtering to prevent mixing workflows.

---

### 2. Stage Filtering by Case Type

**Pattern:** Add `case_type` field to stage model and filter in `_read_group_stage_ids`

```python
# In stage model
case_type = fields.Selection([('pr', 'PR'), ('gcms', 'GCMS')])

# In case model
@api.model
def _read_group_stage_ids(self, stages, domain):
    """Filter stages by case type for kanban view."""
    case_type = self._context.get('default_case_type', 'pr')
    return stages.search([
        '|',
        ('case_type', '=', case_type),
        ('case_type', '=', False),  # Stages without case_type work for all
    ], order='sequence')
```

**Key Point:** The `order` parameter was removed in Odoo 19's `group_expand` signature.

---

### 3. Dual Agreement/Payment Workflows

**Pattern:** Separate agreement and payment tracking fields for each service type

```python
# GCMS Service
gcms_service_agreement_id = fields.Many2one('mm.esign.request')
gcms_service_order_id = fields.Many2one('sale.order')
gcms_service_paid = fields.Boolean(compute='_compute_gcms_service_paid', store=True)

# Consultation Service  
gcms_consultation_agreement_id = fields.Many2one('mm.esign.request')
gcms_consultation_order_id = fields.Many2one('sale.order')
gcms_consultation_paid = fields.Boolean(compute='_compute_gcms_consultation_paid', store=True)
```

**Why Separate:**
- Different products and prices
- Independent workflows (consultation is optional)
- Clear audit trail for each service

---

### 4. Optional Workflow Path

**Pattern:** Handle optional consultation as branching workflow

```
GCMS Workflow:
Form → Payment → Processing → Notes Delivered → [BRANCH]
                                                   ↓
                                              Complete (no consultation)
                                                   ↓
                                              Request Consultation → Payment → Schedule → Complete
```

**Implementation:**
- `gcms_consultation_requested` Boolean gates the consultation stages
- Stages 5-7 only appear when consultation is requested
- Case can complete from stage 4 (Notes Delivered) without consultation

---

### 5. UCI Number Validation

**Pattern:** Use `@api.constrains` with input normalization

```python
@api.constrains('gcms_uci_number')
def _check_uci_number(self):
    for case in self:
        if case.gcms_uci_number:
            # Normalize - remove spaces and dashes
            uci = case.gcms_uci_number.replace(' ', '').replace('-', '')
            if not uci.isdigit() or len(uci) not in (8, 10):
                raise ValidationError(
                    _("UCI Number must be 8 or 10 digits. Got: %s") % case.gcms_uci_number
                )
```

**Key Point:** Normalize before validating to accept common input formats (spaces, dashes).

---

### 6. Portal Action Button Filtering

**Pattern:** Use `invisible` with case_type check in view buttons

```xml
<button name="action_submit_gcms_request" 
        string="Submit GCMS Request"
        type="object"
        invisible="case_type != 'gcms' or not gcms_service_paid or gcms_request_date"/>
```

**Odoo 19 Syntax:**
- Use Python expressions, not domain lists
- No `attrs=` or `states=` attributes
- Multiple conditions with `or`/`and`

---

### 7. Separate Menu Actions per Case Type

**Pattern:** Create dedicated actions with domain and context filters

```xml
<!-- GCMS Cases Action -->
<record id="action_mm_immigration_case_gcms" model="ir.actions.act_window">
    <field name="domain">[('case_type', '=', 'gcms')]</field>
    <field name="context">{
        'default_case_type': 'gcms',
        'search_default_filter_gcms_cases': 1
    }</field>
</record>
```

**Benefits:**
- Users see only relevant cases
- New cases default to correct type
- Search filters auto-applied

---

## Validation Patterns Applied

### From Phase 1 Lessons:
- ✅ No `attrs=` or `states=` attributes
- ✅ No `invisible="1"` on filename fields
- ✅ `group_expand` without `order` parameter
- ✅ Admin access first in security CSV

### From Phase 3 Lessons:
- ✅ Payment detection via `account.move.write()` override
- ✅ Portal fallback `_check_payment_status()`
- ✅ `invalidate_recordset()` before checking computed fields
- ✅ CSRF tokens in all forms
- ✅ `sudo()` for creating esign requests and orders

### From Lessons_Learned_1:
- ✅ No `category_id` in security groups
- ✅ No `_sql_constraints` (using `@api.constrains`)
- ✅ Proper field naming (`_id`, `_ids` suffixes)
- ✅ XML entity escaping where needed

---

## Files Created

| File | Purpose |
|------|---------|
| `models/immigration_case_gcms.py` | Case model extension with GCMS fields |
| `models/immigration_stage_gcms.py` | Stage model with case_type filter |
| `models/account_move_gcms.py` | Payment completion detection |
| `controllers/gcms_portal.py` | All portal routes |
| `views/gcms_case_views.xml` | Backend form/list/search views |
| `views/gcms_portal_templates.xml` | Portal page templates |
| `views/gcms_portal_dashboard.xml` | Dashboard widgets |
| `data/gcms_stage_data.xml` | GCMS workflow stages |
| `data/gcms_product_data.xml` | Service products |
| `data/gcms_mail_template_data.xml` | Email notifications |

---

## Future Considerations

1. **Calendar Integration:** Consultation scheduling could integrate with Google Calendar or Calendly
2. **Document Generation:** Auto-generate GCMS breakdown document from template
3. **Bulk Operations:** Admin view for processing multiple GCMS requests
4. **Status Updates:** Webhook from IRCC (if available) for automatic status updates

---

## Document Control

**Version:** 1.0  
**Created:** January 1, 2026  
**Author:** Phase 6 Development  
**Status:** Active Reference Document

---

**END OF DOCUMENT**
