# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ImmigrationStage(models.Model):
    _name = 'mm.immigration.stage'
    _description = 'Immigration Case Stage'
    _order = 'sequence, id'

    name = fields.Char(
        string='Stage Name',
        required=True,
        translate=True,
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Determines the order of stages in the workflow',
    )
    fold = fields.Boolean(
        string='Folded in Kanban',
        default=False,
        help='If checked, this stage will be folded by default in kanban view',
    )
    state = fields.Selection(
        selection=[
            ('invited', 'Invited'),
            ('onboarding', 'Onboarding'),
            ('quoted', 'Quoted'),
            ('paid', 'Payment'),
            ('assessment', 'Assessment'),
            ('roadmap_delivered', 'Roadmap Delivered'),
            ('call_scheduled', 'Consultation'),
            ('application', 'Application'),
        ],
        string='State',
        required=True,
        help='Technical state linked to this stage',
    )
    portal_description = fields.Text(
        string='Portal Description',
        translate=True,
        help='Description shown to client in the portal for this stage',
    )
    portal_action_text = fields.Char(
        string='Portal Action Text',
        translate=True,
        help='Text for the action button shown in portal (e.g., "Start Questionnaire")',
    )
    portal_action_url = fields.Char(
        string='Portal Action URL',
        help='Relative URL for the portal action button (e.g., "/my/immigration/questionnaire/pre")',
    )
    requires_signature = fields.Boolean(
        string='Requires Signature',
        default=False,
        help='Check if this stage requires an e-signature before advancing',
    )
    requires_payment = fields.Boolean(
        string='Requires Payment',
        default=False,
        help='Check if this stage requires payment completion before advancing',
    )
    is_closing_stage = fields.Boolean(
        string='Is Closing Stage',
        default=False,
        help='Check if this is a final/closing stage',
    )
    case_count = fields.Integer(
        string='Case Count',
        compute='_compute_case_count',
    )

    @api.depends()
    def _compute_case_count(self):
        """Compute the number of cases in each stage."""
        case_data = self.env['mm.immigration.case'].read_group(
            domain=[('stage_id', 'in', self.ids)],
            fields=['stage_id'],
            groupby=['stage_id'],
        )
        mapped_data = {
            data['stage_id'][0]: data['stage_id_count']
            for data in case_data
        }
        for stage in self:
            stage.case_count = mapped_data.get(stage.id, 0)

    def _get_default_stage(self):
        """Return the default (first) stage for new cases."""
        return self.search([('state', '=', 'invited')], limit=1)
