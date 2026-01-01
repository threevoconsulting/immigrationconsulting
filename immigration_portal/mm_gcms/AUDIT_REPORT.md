# GCMS Module - Odoo 19 Compatibility Audit Report

**Module:** mm_gcms  
**Date:** January 1, 2026  
**Audited Against:** Phase1_Immigration_Portal_Lessons_Learned.md, Phase3_eSign_Workflow_Lessons_Learned.md, Lessons_Learned_1, Lessons_Learned_2, LESSON_LEARNED_attrs_states_removed.md

---

## Audit Summary: ✅ PASSED

All code has been verified against the documented lessons learned and Odoo 19 best practices.

---

## Detailed Checks

### 1. Critical Odoo 19 Breaking Changes

| Check | Status | Notes |
|-------|--------|-------|
| No `attrs=` attributes | ✅ PASS | Using `invisible=`, `readonly=`, `required=` with Python expressions |
| No `states=` attributes | ✅ PASS | Using `invisible="state not in (...)"` pattern |
| No `target="inline"` | ✅ PASS | Using `target="current"` |
| No `<tree>` tags | ✅ PASS | Using `<list>` |
| No `view_mode` with "tree" | ✅ PASS | Using "list,form,kanban" |
| No `t-name="kanban-box"` | ✅ PASS | Not applicable (no kanban views in this module) |
| No `_sql_constraints` | ✅ PASS | Using `@api.constrains` decorator |
| No `category_id` in security | ✅ PASS | Field not used |
| No `groups_id` (use `group_ids`) | ✅ PASS | Not applicable |
| No `invisible="1"` without justification | ✅ PASS | Removed filename fields (handled by `filename` attribute) |
| `group_expand` without `order` param | ✅ PASS | `def _read_group_stage_ids(self, stages, domain)` |
| `<chatter/>` not `oe_chatter` div | ✅ PASS | Not applicable (no chatter added in this module) |

### 2. Field Naming Conventions

| Check | Status | Notes |
|-------|--------|-------|
| Many2one fields end with `_id` | ✅ PASS | `gcms_service_agreement_id`, `gcms_service_order_id`, etc. |
| Many2many fields end with `_ids` | ✅ PASS | Not applicable |
| One2many fields end with `_ids` | ✅ PASS | Not applicable |
| State field named `state` | ✅ PASS | Not applicable (using inherited fields) |

### 3. Python Model Patterns

| Check | Status | Notes |
|-------|--------|-------|
| `@api.model_create_multi` for create() | ✅ PASS | No create() overrides in this module |
| `@api.constrains` with ValidationError | ✅ PASS | `_check_uci_number` validates UCI format |
| Computed fields have compute methods | ✅ PASS | `_compute_gcms_service_paid`, `_compute_gcms_consultation_paid` |
| No forward model references | ✅ PASS | Only references existing models |
| Proper cache invalidation | ✅ PASS | `invalidate_recordset()` used in payment detection |

### 4. XML Syntax

| Check | Status | Notes |
|-------|--------|-------|
| `>` escaped as `&gt;` | ✅ PASS | No comparison operators in expressions |
| `<` escaped as `&lt;` | ✅ PASS | No comparison operators in expressions |
| Icons have accessibility attrs | ✅ PASS | All `<i class="fa...">` have `title`, `role`, `aria-label` |

### 5. Security

| Check | Status | Notes |
|-------|--------|-------|
| Admin access first in CSV | ✅ PASS | `base.group_system` rules at top |
| No deprecated fields | ✅ PASS | No `category_id` or `groups_id` |

### 6. Phase 3 Workflow Patterns

| Check | Status | Notes |
|-------|--------|-------|
| Payment detection via `write()` override | ✅ PASS | `account_move_gcms.py` overrides `write()` |
| Portal fallback stage advancement | ✅ PASS | `_check_payment_status()` in controller |
| Cache invalidation before computed field check | ✅ PASS | `invalidate_recordset(['gcms_service_paid'])` |
| Both dashboard AND detail templates updated | ✅ PASS | `gcms_portal_dashboard.xml` + `gcms_portal_templates.xml` |
| Multi-stage signature workflow | ✅ PASS | `pending_client` → `pending_consultant` → `signed` |
| CSRF tokens in forms | ✅ PASS | 5 forms with `csrf_token` |
| `sudo()` for sensitive operations | ✅ PASS | Used for esign creation, order creation |

---

## Files Audited

| File | Lines | Status |
|------|-------|--------|
| `models/immigration_case_gcms.py` | 362 | ✅ |
| `models/immigration_stage_gcms.py` | 63 | ✅ |
| `models/account_move_gcms.py` | 62 | ✅ |
| `controllers/gcms_portal.py` | 418 | ✅ |
| `views/gcms_case_views.xml` | 324 | ✅ |
| `views/gcms_portal_templates.xml` | 640 | ✅ |
| `views/gcms_portal_dashboard.xml` | 182 | ✅ |
| `data/gcms_stage_data.xml` | 118 | ✅ |
| `data/gcms_product_data.xml` | 56 | ✅ |
| `data/gcms_mail_template_data.xml` | 200 | ✅ |
| `security/ir.model.access.csv` | 5 | ✅ |
| `__manifest__.py` | 89 | ✅ |

---

## Fix Applied During Audit

### Issue: `invisible="1"` on filename fields

**Location:** `views/gcms_case_views.xml` lines 81, 85

**Problem:** Odoo 19 rejects `invisible="1"` without technical justification. Filename fields for binary widgets are handled automatically via the `filename` attribute.

**Fix:** Removed the explicit `<field name="gcms_notes_filename" invisible="1"/>` and `<field name="gcms_breakdown_filename" invisible="1"/>` lines.

---

## Conclusion

The mm_gcms module is fully compliant with all documented Odoo 19 patterns and lessons learned from previous phases. The module is ready for installation and testing.
