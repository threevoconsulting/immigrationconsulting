# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ImmigrationCase(models.Model):
    _name = 'mm.immigration.case'
    _description = 'Immigration Case'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'create_date desc'

    # === Core Fields ===
    name = fields.Char(
        string='Case Reference',
        required=True,
        readonly=True,
        default='New',
        copy=False,
        tracking=True,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Client',
        required=True,
        tracking=True,
        domain=[('is_company', '=', False)],
        help='The client contact for this immigration case',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    # === Workflow Fields ===
    stage_id = fields.Many2one(
        comodel_name='mm.immigration.stage',
        string='Stage',
        tracking=True,
        group_expand='_read_group_stage_ids',
        default=lambda self: self.env['mm.immigration.stage']._get_default_stage(),
        copy=False,
    )
    state = fields.Selection(
        related='stage_id.state',
        string='State',
        store=True,
        readonly=True,
    )
    kanban_state = fields.Selection(
        selection=[
            ('normal', 'Grey'),
            ('done', 'Green'),
            ('blocked', 'Red'),
        ],
        string='Kanban State',
        default='normal',
        copy=False,
    )
    priority = fields.Selection(
        selection=[
            ('0', 'Normal'),
            ('1', 'High'),
        ],
        string='Priority',
        default='0',
    )

    # === Profile & Related Records ===
    profile_id = fields.Many2one(
        comodel_name='mm.client.profile',
        string='Client Profile',
        tracking=True,
    )
    consultant_id = fields.Many2one(
        comodel_name='res.users',
        string='Assigned Consultant',
        tracking=True,
        domain=[('share', '=', False)],
        default=lambda self: self.env.user,
    )

    # === Immigration Details ===
    immigration_goal = fields.Selection(
        selection=[
            ('pr', 'Permanent Residence'),
            ('temporary', 'Temporary Residence'),
            ('undecided', 'Undecided'),
        ],
        string='Immigration Goal',
        tracking=True,
    )
    target_year = fields.Selection(
        selection=lambda self: self._get_year_selection(),
        string='Target Year',
    )
    recommended_pathway = fields.Selection(
        selection=[
            ('express_entry', 'Express Entry (FSW/CEC)'),
            ('ee_pnp', 'Express Entry + PNP'),
            ('pnp_direct', 'Direct PNP'),
            ('francophone', 'Francophone Pathway'),
            ('study_permit', 'Study Permit'),
            ('work_permit', 'Work Permit'),
            ('other', 'Other'),
        ],
        string='Recommended Pathway',
        tracking=True,
    )

    # === Portal & Communication ===
    portal_invited = fields.Boolean(
        string='Portal Invitation Sent',
        default=False,
        copy=False,
    )
    portal_invite_date = fields.Datetime(
        string='Invitation Date',
        copy=False,
    )
    portal_first_access = fields.Datetime(
        string='First Portal Access',
        copy=False,
    )

    # === Computed Fields ===
    client_email = fields.Char(
        related='partner_id.email',
        string='Client Email',
        readonly=True,
    )
    client_phone = fields.Char(
        related='partner_id.phone',
        string='Client Phone',
        readonly=True,
    )
    stage_progress = fields.Integer(
        string='Stage Progress',
        compute='_compute_stage_progress',
    )

    # === Document Fields ===
    # Note: Additional fields (questionnaires, CRS, e-sign, payments) will be
    # added via model inheritance when those modules are developed in later phases.
    roadmap_document = fields.Binary(
        string='Roadmap Document',
        attachment=True,
        copy=False,
    )
    roadmap_filename = fields.Char(
        string='Roadmap Filename',
    )

    # === Notes ===
    internal_notes = fields.Html(
        string='Internal Notes',
    )

    # === Constraints ===
    @api.constrains('name')
    def _check_name_unique(self):
        """Ensure case reference is unique."""
        for record in self:
            if record.name and record.name != 'New':
                duplicate = self.search([
                    ('name', '=', record.name),
                    ('id', '!=', record.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(_('Case reference must be unique!'))

    # === Computed Methods ===
    @api.depends('stage_id', 'stage_id.sequence')
    def _compute_stage_progress(self):
        """Calculate progress percentage based on stage sequence."""
        all_stages = self.env['mm.immigration.stage'].search([], order='sequence')
        total_stages = len(all_stages)
        for case in self:
            if case.stage_id and total_stages:
                # Find position of current stage
                stage_sequences = all_stages.mapped('sequence')
                current_sequence = case.stage_id.sequence
                position = stage_sequences.index(current_sequence) + 1 if current_sequence in stage_sequences else 0
                case.stage_progress = int((position / total_stages) * 100)
            else:
                case.stage_progress = 0

    def _get_year_selection(self):
        """Generate year selection from current year to +5 years."""
        import datetime
        current_year = datetime.date.today().year
        return [(str(year), str(year)) for year in range(current_year, current_year + 6)]

    # === CRUD Methods ===
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('mm.immigration.case') or 'New'
        cases = super().create(vals_list)
        # Auto-create profile for each case
        for case in cases:
            if not case.profile_id:
                profile = self.env['mm.client.profile'].create({
                    'partner_id': case.partner_id.id,
                    'case_id': case.id,
                })
                case.profile_id = profile.id
        return cases

    def write(self, vals):
        # Track stage changes
        if 'stage_id' in vals:
            for case in self:
                old_stage = case.stage_id.name
                case.message_post(
                    body=_("Stage changed from <b>%s</b>") % old_stage,
                    message_type='notification',
                )
        return super().write(vals)

    # === Business Methods ===
    def action_send_portal_invite(self):
        """Send portal invitation to client."""
        self.ensure_one()
        if not self.partner_id.email:
            raise UserError(_("Client must have an email address to receive portal invitation."))

        # Use Odoo's built-in portal wizard
        wizard = self.env['portal.wizard'].create({
            'partner_ids': [(6, 0, [self.partner_id.id])],
        })
        
        # Get the portal wizard user line
        wizard_user = wizard.user_ids.filtered(lambda u: u.partner_id == self.partner_id)
        if wizard_user:
            wizard_user.action_grant_access()

        self.write({
            'portal_invited': True,
            'portal_invite_date': fields.Datetime.now(),
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Portal Invitation Sent'),
                'message': _('Portal invitation has been sent to %s', self.partner_id.email),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_profile(self):
        """Open the client profile form."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Client Profile'),
            'res_model': 'mm.client.profile',
            'view_mode': 'form',
            'res_id': self.profile_id.id,
            'target': 'current',
        }

    def action_advance_stage(self):
        """Move case to the next stage."""
        self.ensure_one()
        current_sequence = self.stage_id.sequence
        next_stage = self.env['mm.immigration.stage'].search(
            [('sequence', '>', current_sequence)],
            order='sequence',
            limit=1,
        )
        if next_stage:
            self.stage_id = next_stage
        else:
            raise UserError(_("This case is already at the final stage."))

    # === Portal Methods ===
    def _compute_access_url(self):
        super()._compute_access_url()
        for case in self:
            case.access_url = f'/my/immigration/case/{case.id}'

    # === Group Expand for Kanban ===
    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Always display all stages in kanban view."""
        return stages.search([], order='sequence')
