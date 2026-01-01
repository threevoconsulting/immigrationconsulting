# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError


class ImmigrationPortal(CustomerPortal):
    """Controller for immigration portal pages."""

    def _prepare_home_portal_values(self, counters):
        """Add immigration case count to portal home."""
        values = super()._prepare_home_portal_values(counters)
        if 'immigration_count' in counters:
            partner = request.env.user.partner_id
            values['immigration_count'] = request.env['mm.immigration.case'].sudo().search_count([
                ('partner_id', '=', partner.id)
            ])
        return values

    def _get_portal_settings(self):
        """Get portal branding settings."""
        settings = request.env['mm.immigration.settings'].sudo()
        return settings.get_all_settings()

    def _get_immigration_cases(self, partner):
        """Get all immigration cases for a partner."""
        return request.env['mm.immigration.case'].sudo().search([
            ('partner_id', '=', partner.id)
        ], order='create_date desc')

    def _get_all_stages(self):
        """Get all workflow stages in order."""
        return request.env['mm.immigration.stage'].sudo().search([], order='sequence')

    def _check_case_access(self, case_id):
        """Check if current user has access to the case."""
        partner = request.env.user.partner_id
        case = request.env['mm.immigration.case'].sudo().browse(case_id)
        if not case.exists():
            raise MissingError(_("This case does not exist."))
        if case.partner_id.id != partner.id:
            raise AccessError(_("You do not have access to this case."))
        return case

    @http.route(['/my/immigration'], type='http', auth='user', website=True)
    def portal_immigration_dashboard(self, **kw):
        """Main immigration portal dashboard."""
        partner = request.env.user.partner_id
        cases = self._get_immigration_cases(partner)
        stages = self._get_all_stages()
        settings = self._get_portal_settings()

        # Track first portal access and check for pending stage advancements
        for case in cases:
            if not case.portal_first_access:
                case.sudo().write({
                    'portal_first_access': fields.Datetime.now()
                })
            
            # Fallback check: If payment is confirmed but case is still in Payment stage, advance it
            # (Only if mm_esign module is installed and provides the method)
            if hasattr(case, 'payment_confirmed') and hasattr(case, '_on_payment_complete'):
                if case.state == 'paid' and case.payment_confirmed:
                    case.sudo()._on_payment_complete()

        # Refresh cases after potential updates
        cases = self._get_immigration_cases(partner)

        values = {
            'page_name': 'immigration',
            'cases': cases,
            'stages': stages,
            'settings': settings,
            'default_url': '/my/immigration',
        }
        return request.render('mm_portal.portal_immigration_dashboard', values)

    @http.route(['/my/immigration/case/<int:case_id>'], type='http', auth='user', website=True)
    def portal_immigration_case(self, case_id, **kw):
        """Individual case detail view."""
        case = self._check_case_access(case_id)
        stages = self._get_all_stages()
        settings = self._get_portal_settings()

        # Fallback check: If payment is confirmed but case is still in Payment stage, advance it
        # (Only if mm_esign module is installed and provides the method)
        if hasattr(case, 'payment_confirmed') and hasattr(case, '_on_payment_complete'):
            if case.state == 'paid' and case.payment_confirmed:
                case.sudo()._on_payment_complete()
                # Refresh the case to get updated stage
                case = self._check_case_access(case_id)

        # Calculate stage position for progress
        stage_list = list(stages)
        current_position = 0
        for idx, stage in enumerate(stage_list):
            if stage.id == case.stage_id.id:
                current_position = idx + 1
                break

        values = {
            'page_name': 'immigration_case',
            'case': case,
            'stages': stages,
            'current_position': current_position,
            'total_stages': len(stage_list),
            'settings': settings,
        }
        return request.render('mm_portal.portal_immigration_case', values)

    @http.route(['/my/immigration/case/<int:case_id>/documents'], type='http', auth='user', website=True)
    def portal_case_documents(self, case_id, **kw):
        """Case documents page."""
        case = self._check_case_access(case_id)
        settings = self._get_portal_settings()

        # Get signed documents from esign module if available
        signed_agreements = []
        try:
            esign_requests = request.env['mm.esign.request'].sudo().search([
                ('case_id', '=', case.id),
                ('state', '=', 'signed'),
                ('signed_document', '!=', False),
            ])
            signed_agreements = esign_requests
        except Exception:
            # mm_esign module may not be installed
            pass

        values = {
            'page_name': 'immigration_documents',
            'case': case,
            'settings': settings,
            'signed_agreements': signed_agreements,
        }
        return request.render('mm_portal.portal_case_documents', values)

    # Placeholder routes for future phases
    @http.route(['/my/immigration/questionnaire/<string:qtype>'], type='http', auth='user', website=True)
    def portal_questionnaire(self, qtype, **kw):
        """Questionnaire page - placeholder for Phase 2."""
        settings = self._get_portal_settings()
        values = {
            'page_name': 'immigration_questionnaire',
            'questionnaire_type': qtype,
            'settings': settings,
            'message': _("Questionnaire system will be available in a future update."),
        }
        return request.render('mm_portal.portal_placeholder', values)

    @http.route(['/my/immigration/quote'], type='http', auth='user', website=True)
    def portal_quote(self, **kw):
        """Quote review page - redirects to case-specific URL."""
        partner = request.env.user.partner_id
        # Find the user's case in quoted state
        case = request.env['mm.immigration.case'].sudo().search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'quoted')
        ], limit=1)
        if case:
            return request.redirect(f'/my/immigration/quote/{case.id}')
        # Fallback: find any case
        case = request.env['mm.immigration.case'].sudo().search([
            ('partner_id', '=', partner.id)
        ], limit=1, order='create_date desc')
        if case:
            return request.redirect(f'/my/immigration/quote/{case.id}')
        # No case found - show placeholder
        settings = self._get_portal_settings()
        values = {
            'page_name': 'immigration_quote',
            'settings': settings,
            'message': _("No active quote found. Please contact us for assistance."),
        }
        return request.render('mm_portal.portal_placeholder', values)

    @http.route(['/my/immigration/pay'], type='http', auth='user', website=True)
    def portal_payment(self, **kw):
        """Payment page - redirects to case-specific URL."""
        partner = request.env.user.partner_id
        # Find the user's case in payment state
        case = request.env['mm.immigration.case'].sudo().search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'paid')
        ], limit=1)
        if case:
            return request.redirect(f'/my/immigration/pay/{case.id}')
        # Fallback: find any case with unpaid invoice
        case = request.env['mm.immigration.case'].sudo().search([
            ('partner_id', '=', partner.id),
            ('payment_confirmed', '=', False)
        ], limit=1, order='create_date desc')
        if case:
            return request.redirect(f'/my/immigration/pay/{case.id}')
        # No case found - show placeholder
        settings = self._get_portal_settings()
        values = {
            'page_name': 'immigration_payment',
            'settings': settings,
            'message': _("No pending payment found. Please contact us for assistance."),
        }
        return request.render('mm_portal.portal_placeholder', values)

    @http.route(['/my/immigration/roadmap'], type='http', auth='user', website=True)
    def portal_roadmap(self, **kw):
        """Roadmap page - placeholder for Phase 4."""
        settings = self._get_portal_settings()
        values = {
            'page_name': 'immigration_roadmap',
            'settings': settings,
            'message': _("Roadmap viewer will be available in a future update."),
        }
        return request.render('mm_portal.portal_placeholder', values)

    @http.route(['/my/immigration/book'], type='http', auth='user', website=True)
    def portal_booking(self, **kw):
        """Booking page - placeholder."""
        settings = self._get_portal_settings()
        values = {
            'page_name': 'immigration_booking',
            'settings': settings,
            'message': _("Consultation booking will be available in a future update."),
        }
        return request.render('mm_portal.portal_placeholder', values)

    @http.route(['/my/immigration/application'], type='http', auth='user', website=True)
    def portal_application(self, **kw):
        """Application tracking page - placeholder for Phase 4."""
        settings = self._get_portal_settings()
        values = {
            'page_name': 'immigration_application',
            'settings': settings,
            'message': _("Application tracking will be available in a future update."),
        }
        return request.render('mm_portal.portal_placeholder', values)
