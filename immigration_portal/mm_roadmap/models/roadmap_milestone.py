# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class RoadmapMilestone(models.Model):
    """Timeline milestones for immigration roadmap."""
    _name = 'mm.roadmap.milestone'
    _description = 'Roadmap Milestone'
    _order = 'target_date, sequence'

    roadmap_id = fields.Many2one(
        comodel_name='mm.roadmap.document',
        string='Roadmap',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    name = fields.Char(
        string='Milestone',
        required=True,
    )
    description = fields.Text(
        string='Description',
    )
    target_date = fields.Date(
        string='Target Date',
    )
    completed_date = fields.Date(
        string='Completed Date',
        readonly=True,
        help='Date when this milestone was marked as completed',
    )
    milestone_type = fields.Selection(
        selection=[
            ('preparation', 'Preparation'),
            ('application', 'Application'),
            ('documentation', 'Documentation'),
            ('interview', 'Interview/Exam'),
            ('decision', 'Decision Point'),
            ('landing', 'Landing/Completion'),
        ],
        string='Type',
        default='preparation',
    )
    is_critical = fields.Boolean(
        string='Critical Path',
        default=False,
        help='Mark if this milestone is on the critical path',
    )
    estimated_duration_days = fields.Integer(
        string='Duration (Days)',
        help='Estimated time to complete this milestone',
    )
    dependencies = fields.Char(
        string='Dependencies',
        help='Other milestones that must be completed first',
    )
    responsible_party = fields.Selection(
        selection=[
            ('client', 'Client'),
            ('consultant', 'Consultant'),
            ('third_party', 'Third Party (ECA, IRCC, etc.)'),
            ('joint', 'Joint Responsibility'),
        ],
        string='Responsible',
        default='client',
    )
    status = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('delayed', 'Delayed'),
            ('skipped', 'Skipped'),
        ],
        string='Status',
        default='pending',
    )
    notes = fields.Text(
        string='Notes',
    )

    # Computed fields
    days_until_target = fields.Integer(
        string='Days Until Target',
        compute='_compute_days_until',
    )
    is_overdue = fields.Boolean(
        string='Overdue',
        compute='_compute_days_until',
    )

    @api.depends('target_date', 'status')
    def _compute_days_until(self):
        today = fields.Date.today()
        for record in self:
            if record.target_date and record.status not in ('completed', 'skipped'):
                delta = (record.target_date - today).days
                record.days_until_target = delta
                record.is_overdue = delta < 0
            else:
                record.days_until_target = 0
                record.is_overdue = False

    def action_mark_in_progress(self):
        """Mark milestone as in progress."""
        for record in self:
            record.status = 'in_progress'

    def action_mark_completed(self):
        """Mark milestone as completed and set completion date."""
        for record in self:
            record.write({
                'status': 'completed',
                'completed_date': fields.Date.today(),
            })

    def action_mark_delayed(self):
        """Mark milestone as delayed."""
        for record in self:
            record.status = 'delayed'

    def action_reset_to_pending(self):
        """Reset milestone to pending status."""
        for record in self:
            record.write({
                'status': 'pending',
                'completed_date': False,
            })
