# -*- coding: utf-8 -*-

from odoo import models, api


class AccountMove(models.Model):
    """Extends account.move to detect payment completion for immigration cases."""
    _inherit = 'account.move'

    def write(self, vals):
        """Override write to detect payment state changes."""
        res = super().write(vals)
        
        # Check if payment_state changed to paid
        if 'payment_state' in vals and vals['payment_state'] in ('paid', 'in_payment'):
            self._check_immigration_case_payment()
        
        return res

    def _check_immigration_case_payment(self):
        """Check if any linked immigration cases should advance."""
        for move in self:
            if move.move_type != 'out_invoice':
                continue
            
            # Find sale orders linked to this invoice
            sale_orders = self.env['sale.order'].search([
                ('invoice_ids', 'in', move.id)
            ])
            
            for order in sale_orders:
                # Find immigration cases linked to this sale order
                cases = self.env['mm.immigration.case'].search([
                    ('sale_order_id', '=', order.id)
                ])
                
                for case in cases:
                    # Invalidate computed field cache to ensure fresh computation
                    case.invalidate_recordset(['payment_confirmed'])
                    
                    # Check if payment is now confirmed and case is in payment stage
                    if case.payment_confirmed and case.state == 'paid':
                        case._on_payment_complete()
