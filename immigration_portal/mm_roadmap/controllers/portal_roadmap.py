# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError
import base64
import logging

_logger = logging.getLogger(__name__)


class PortalRoadmap(http.Controller):
    """Portal controller for roadmap viewing and acknowledgment."""

    def _get_case_for_user(self):
        """Get the immigration case for the current portal user."""
        user = request.env.user
        if user._is_public():
            return None

        case = request.env['mm.immigration.case'].sudo().search([
            ('partner_id', '=', user.partner_id.id),
        ], limit=1)
        return case

    def _check_roadmap_access(self, roadmap, case):
        """Verify user has access to the roadmap."""
        if not roadmap or not case:
            return False
        if roadmap.case_id.id != case.id:
            return False
        return True

    @http.route('/my/immigration/roadmap', type='http', auth='user', website=True)
    def portal_roadmap_main(self, **kw):
        """Main roadmap portal page."""
        case = self._get_case_for_user()
        if not case:
            return request.redirect('/my')

        roadmap = case.current_roadmap_id

        # Check if roadmap is ready for viewing
        if not roadmap or roadmap.state not in ('delivered', 'acknowledged'):
            return request.render('mm_roadmap.portal_roadmap_not_ready', {
                'case': case,
            })

        values = {
            'case': case,
            'roadmap': roadmap,
            'page_name': 'roadmap',
        }
        return request.render('mm_roadmap.portal_roadmap_view', values)

    @http.route('/my/immigration/roadmap/<int:roadmap_id>', type='http', auth='user', website=True)
    def portal_roadmap_detail(self, roadmap_id, **kw):
        """View specific roadmap."""
        case = self._get_case_for_user()
        if not case:
            return request.redirect('/my')

        roadmap = request.env['mm.roadmap.document'].sudo().browse(roadmap_id)
        if not self._check_roadmap_access(roadmap, case):
            raise AccessError(_("You don't have access to this roadmap."))

        values = {
            'case': case,
            'roadmap': roadmap,
            'page_name': 'roadmap',
        }
        return request.render('mm_roadmap.portal_roadmap_view', values)

    @http.route('/my/immigration/roadmap/<int:roadmap_id>/download', type='http', auth='user', website=True)
    def portal_roadmap_download(self, roadmap_id, **kw):
        """Download roadmap PDF."""
        case = self._get_case_for_user()
        if not case:
            return request.redirect('/my')

        roadmap = request.env['mm.roadmap.document'].sudo().browse(roadmap_id)
        if not self._check_roadmap_access(roadmap, case):
            raise AccessError(_("You don't have access to this roadmap."))

        if not roadmap.pdf_document:
            # Generate if not exists
            roadmap.action_generate_pdf()

        if roadmap.pdf_document:
            pdf_content = base64.b64decode(roadmap.pdf_document)
            headers = [
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename="{roadmap.pdf_filename}"'),
                ('Content-Length', len(pdf_content)),
            ]
            return request.make_response(pdf_content, headers)

        return request.redirect(f'/my/immigration/roadmap/{roadmap_id}')

    @http.route('/my/immigration/roadmap/<int:roadmap_id>/acknowledge', type='http', auth='user', website=True, methods=['GET'])
    def portal_roadmap_acknowledge_page(self, roadmap_id, **kw):
        """Show acknowledgment page with signature pad."""
        case = self._get_case_for_user()
        if not case:
            return request.redirect('/my')

        roadmap = request.env['mm.roadmap.document'].sudo().browse(roadmap_id)
        if not self._check_roadmap_access(roadmap, case):
            raise AccessError(_("You don't have access to this roadmap."))

        if roadmap.state != 'delivered':
            return request.redirect(f'/my/immigration/roadmap/{roadmap_id}')

        values = {
            'case': case,
            'roadmap': roadmap,
            'page_name': 'roadmap_acknowledge',
        }
        return request.render('mm_roadmap.portal_roadmap_acknowledge', values)

    @http.route('/my/immigration/roadmap/<int:roadmap_id>/acknowledge', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_roadmap_acknowledge_submit(self, roadmap_id, signature=None, **kw):
        """Process roadmap acknowledgment."""
        case = self._get_case_for_user()
        if not case:
            return request.redirect('/my')

        roadmap = request.env['mm.roadmap.document'].sudo().browse(roadmap_id)
        if not self._check_roadmap_access(roadmap, case):
            raise AccessError(_("You don't have access to this roadmap."))

        if roadmap.state != 'delivered':
            return request.redirect(f'/my/immigration/roadmap/{roadmap_id}')

        # Process signature
        signature_data = None
        if signature:
            # Remove data URL prefix if present
            if ',' in signature:
                signature = signature.split(',')[1]
            signature_data = signature

        # Get client IP
        ip_address = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR', 
                     request.httprequest.environ.get('REMOTE_ADDR', ''))
        if ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()

        # Mark as acknowledged
        roadmap.action_mark_acknowledged(
            signature=signature_data,
            ip_address=ip_address,
        )

        # Redirect to confirmation
        return request.redirect('/my/immigration/roadmap/acknowledged')

    @http.route('/my/immigration/roadmap/acknowledged', type='http', auth='user', website=True)
    def portal_roadmap_acknowledged(self, **kw):
        """Show acknowledgment confirmation."""
        case = self._get_case_for_user()
        if not case:
            return request.redirect('/my')

        values = {
            'case': case,
            'page_name': 'roadmap_acknowledged',
        }
        return request.render('mm_roadmap.portal_roadmap_acknowledged', values)
