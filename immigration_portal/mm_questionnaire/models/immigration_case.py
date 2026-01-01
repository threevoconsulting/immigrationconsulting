# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ImmigrationCaseQuestionnaire(models.Model):
    """Extends mm.immigration.case with questionnaire-related fields and automation."""
    _inherit = 'mm.immigration.case'

    # =====================
    # Questionnaire Response Links
    # =====================
    questionnaire_response_ids = fields.One2many(
        comodel_name='mm.questionnaire.response',
        inverse_name='case_id',
        string='Questionnaire Responses',
    )
    pre_consultation_id = fields.Many2one(
        comodel_name='mm.questionnaire.response',
        string='Pre-Consultation (Q1)',
        compute='_compute_questionnaire_responses',
        store=True,
    )
    detailed_assessment_id = fields.Many2one(
        comodel_name='mm.questionnaire.response',
        string='Detailed Assessment (Q2)',
        compute='_compute_questionnaire_responses',
        store=True,
    )

    # =====================
    # Questionnaire Status
    # =====================
    q1_state = fields.Selection(
        selection=[
            ('not_started', 'Not Started'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
        ],
        string='Q1 Status',
        compute='_compute_questionnaire_status',
        store=True,
    )
    q2_state = fields.Selection(
        selection=[
            ('not_started', 'Not Started'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
        ],
        string='Q2 Status',
        compute='_compute_questionnaire_status',
        store=True,
    )
    q1_progress = fields.Integer(
        string='Q1 Progress %',
        compute='_compute_questionnaire_status',
        store=True,
    )
    q2_progress = fields.Integer(
        string='Q2 Progress %',
        compute='_compute_questionnaire_status',
        store=True,
    )

    # =====================
    # Quick Access Flags
    # =====================
    can_start_q1 = fields.Boolean(
        string='Can Start Q1',
        compute='_compute_questionnaire_availability',
    )
    can_start_q2 = fields.Boolean(
        string='Can Start Q2',
        compute='_compute_questionnaire_availability',
    )

    @api.depends('questionnaire_response_ids', 'questionnaire_response_ids.questionnaire_type')
    def _compute_questionnaire_responses(self):
        for case in self:
            q1 = case.questionnaire_response_ids.filtered(
                lambda r: r.questionnaire_type == 'pre_consultation'
            )
            q2 = case.questionnaire_response_ids.filtered(
                lambda r: r.questionnaire_type == 'detailed_assessment'
            )
            case.pre_consultation_id = q1[0] if q1 else False
            case.detailed_assessment_id = q2[0] if q2 else False

    @api.depends('pre_consultation_id', 'pre_consultation_id.state',
                 'pre_consultation_id.progress_percent',
                 'detailed_assessment_id', 'detailed_assessment_id.state',
                 'detailed_assessment_id.progress_percent',
                 'questionnaire_response_ids.state',
                 'questionnaire_response_ids.progress_percent')
    def _compute_questionnaire_status(self):
        for case in self:
            # Q1 Status
            if case.pre_consultation_id:
                case.q1_state = case.pre_consultation_id.state
                case.q1_progress = case.pre_consultation_id.progress_percent
            else:
                case.q1_state = 'not_started'
                case.q1_progress = 0

            # Q2 Status
            if case.detailed_assessment_id:
                case.q2_state = case.detailed_assessment_id.state
                case.q2_progress = case.detailed_assessment_id.progress_percent
            else:
                case.q2_state = 'not_started'
                case.q2_progress = 0

    @api.depends('state', 'q1_state', 'q2_state')
    def _compute_questionnaire_availability(self):
        for case in self:
            # Q1 available from Invited or Onboarding stage
            case.can_start_q1 = (
                case.state in ('invited', 'onboarding') and
                case.q1_state != 'completed'
            )
            # Q2 available from Assessment stage (after payment)
            case.can_start_q2 = (
                case.state == 'assessment' and
                case.q2_state != 'completed'
            )

    def _on_questionnaire_complete(self, questionnaire_type):
        """Called when a questionnaire is completed. Triggers stage advancement."""
        self.ensure_one()

        if questionnaire_type == 'pre_consultation':
            # Q1 complete -> Stay in current stage, consultant will manually advance
            # Copy immigration_goal from profile to case
            if self.profile_id and self.profile_id.immigration_goal:
                self.write({'immigration_goal': self.profile_id.immigration_goal})
            
            # Log the completion
            self.message_post(
                body=_("Pre-consultation questionnaire completed. Ready for consultant review."),
                message_type='notification',
            )

        elif questionnaire_type == 'detailed_assessment':
            # Q2 complete -> Stay at Assessment stage
            # Consultant will manually advance to Roadmap Delivered when roadmap is ready
            self.message_post(
                body=_("Detailed assessment questionnaire completed. "
                       "Your consultant will review your responses and prepare your personalized immigration roadmap. "
                       "This typically takes 3-5 business days."),
                message_type='notification',
            )
            
            # Create activity for consultant to prepare roadmap
            if self.consultant_id:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=self.consultant_id.id,
                    summary=_('Prepare Immigration Roadmap'),
                    note=_('Client %s has completed their detailed assessment questionnaire. '
                           'Please review their responses and prepare their personalized immigration roadmap.') % (
                        self.partner_id.name,
                    ),
                )

    def action_start_questionnaire(self, questionnaire_type):
        """Create and start a questionnaire response."""
        self.ensure_one()

        # Check if response already exists
        existing = self.env['mm.questionnaire.response'].search([
            ('case_id', '=', self.id),
            ('questionnaire_type', '=', questionnaire_type),
        ], limit=1)

        if existing:
            return existing

        # Create new response
        response = self.env['mm.questionnaire.response'].create({
            'case_id': self.id,
            'questionnaire_type': questionnaire_type,
        })
        response.action_start()
        return response

    def action_view_q1(self):
        """Open Q1 questionnaire response."""
        self.ensure_one()
        if self.pre_consultation_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Pre-Consultation Questionnaire'),
                'res_model': 'mm.questionnaire.response',
                'view_mode': 'form',
                'res_id': self.pre_consultation_id.id,
                'target': 'current',
            }
        return False

    def action_view_q2(self):
        """Open Q2 questionnaire response."""
        self.ensure_one()
        if self.detailed_assessment_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Detailed Assessment Questionnaire'),
                'res_model': 'mm.questionnaire.response',
                'view_mode': 'form',
                'res_id': self.detailed_assessment_id.id,
                'target': 'current',
            }
        return False
