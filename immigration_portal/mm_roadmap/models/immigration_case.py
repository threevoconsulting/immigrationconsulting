# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ImmigrationCaseRoadmap(models.Model):
    """Extends mm.immigration.case with roadmap fields."""
    _inherit = 'mm.immigration.case'

    # =====================
    # Roadmap Links
    # =====================
    roadmap_ids = fields.One2many(
        comodel_name='mm.roadmap.document',
        inverse_name='case_id',
        string='Roadmaps',
    )
    current_roadmap_id = fields.Many2one(
        comodel_name='mm.roadmap.document',
        string='Current Roadmap',
        compute='_compute_current_roadmap',
        store=True,
    )
    roadmap_count = fields.Integer(
        string='Roadmap Count',
        compute='_compute_roadmap_count',
        store=True,
    )
    roadmap_state = fields.Selection(
        related='current_roadmap_id.state',
        string='Roadmap Status',
        store=True,
    )

    @api.depends('roadmap_ids', 'roadmap_ids.state', 'roadmap_ids.version')
    def _compute_current_roadmap(self):
        for case in self:
            # Get the latest version roadmap
            roadmaps = case.roadmap_ids.sorted('version', reverse=True)
            case.current_roadmap_id = roadmaps[0] if roadmaps else False

    @api.depends('roadmap_ids')
    def _compute_roadmap_count(self):
        for case in self:
            case.roadmap_count = len(case.roadmap_ids)

    def action_create_roadmap(self):
        """Create a new roadmap document for this case."""
        self.ensure_one()

        # Check prerequisites
        if not self.profile_id:
            from odoo.exceptions import UserError
            raise UserError(_("Please complete the client profile before creating a roadmap."))

        if self.q2_state != 'completed':
            from odoo.exceptions import UserError
            raise UserError(_(
                "Please complete the Detailed Assessment Questionnaire (Q2) before creating a roadmap."
            ))

        # Determine version
        existing_count = len(self.roadmap_ids)
        new_version = existing_count + 1

        # Create roadmap
        roadmap = self.env['mm.roadmap.document'].create({
            'case_id': self.id,
            'version': new_version,
            'consultant_id': self.env.user.id,
            'crs_calculation_id': self.current_crs_calculation_id.id if self.current_crs_calculation_id else False,
        })

        # Auto-populate from profile
        roadmap.action_populate_from_profile()

        return {
            'name': _('Immigration Roadmap'),
            'type': 'ir.actions.act_window',
            'res_model': 'mm.roadmap.document',
            'view_mode': 'form',
            'res_id': roadmap.id,
            'target': 'current',
        }

    def action_view_roadmaps(self):
        """View all roadmaps for this case."""
        self.ensure_one()
        return {
            'name': _('Immigration Roadmaps'),
            'type': 'ir.actions.act_window',
            'res_model': 'mm.roadmap.document',
            'view_mode': 'list,form',
            'domain': [('case_id', '=', self.id)],
            'context': {'default_case_id': self.id},
        }

    def action_view_current_roadmap(self):
        """View the current roadmap."""
        self.ensure_one()
        if not self.current_roadmap_id:
            return self.action_create_roadmap()

        return {
            'name': _('Immigration Roadmap'),
            'type': 'ir.actions.act_window',
            'res_model': 'mm.roadmap.document',
            'view_mode': 'form',
            'res_id': self.current_roadmap_id.id,
            'target': 'current',
        }
