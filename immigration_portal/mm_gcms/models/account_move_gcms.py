# -*- coding: utf-8 -*-
"""
Account Move Extension for GCMS Payment Detection
Phase 6: GCMS Notes Request Workflow

Extends account.move to detect when GCMS-related payments are completed
and trigger the appropriate workflow advancement.

Pattern from Phase 3 Lessons Learned:
- Override write() not create() for payment state changes
- Filter for out_invoice move type
- Invalidate computed field cache before checking
- Check payment state AND current case state to avoid duplicate triggers
"""

from odoo import api, fields, models, _


class AccountMoveGCMS(models.Model):
    """Extend account move to detect GCMS payment completion."""
    
    _inherit = 'account.move'
    
    def write(self, vals):
        """Override write to detect payment state changes."""
        res = super().write(vals)
        
        # Detect payment state change
        if 'payment_state' in vals and vals['payment_state'] in ('paid', 'in_payment'):
            self._check_gcms_case_payment()
        
        return res
    
    def _check_gcms_case_payment(self):
        """
        Check if a payment completion affects a GCMS case
        and trigger the appropriate workflow advancement.
        """
        for move in self:
            # Only process customer invoices
            if move.move_type != 'out_invoice':
                continue
            
            # Find linked sale orders
            sale_orders = self.env['sale.order'].search([
                ('invoice_ids', 'in', move.id)
            ])
            
            for order in sale_orders:
                # Check for GCMS service orders
                cases_service = self.env['mm.immigration.case'].search([
                    ('gcms_service_order_id', '=', order.id),
                    ('case_type', '=', 'gcms'),
                ])
                
                for case in cases_service:
                    # Invalidate cache before checking computed field
                    case.invalidate_recordset(['gcms_service_paid'])
                    
                    if case.gcms_service_paid:
                        case._on_gcms_service_payment_complete()
                
                # Check for consultation orders
                cases_consultation = self.env['mm.immigration.case'].search([
                    ('gcms_consultation_order_id', '=', order.id),
                    ('case_type', '=', 'gcms'),
                ])
                
                for case in cases_consultation:
                    # Invalidate cache before checking computed field
                    case.invalidate_recordset(['gcms_consultation_paid'])
                    
                    if case.gcms_consultation_paid:
                        case._on_gcms_consultation_payment_complete()
