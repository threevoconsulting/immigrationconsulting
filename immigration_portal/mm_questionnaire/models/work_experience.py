# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class WorkExperience(models.Model):
    """Stores work experience records for immigration clients."""
    _name = 'mm.work.experience'
    _description = 'Work Experience Record'
    _order = 'end_date desc, start_date desc'

    name = fields.Char(
        string='Position',
        compute='_compute_name',
        store=True,
    )
    profile_id = fields.Many2one(
        comodel_name='mm.client.profile',
        string='Client Profile',
        required=True,
        ondelete='cascade',
        index=True,
    )
    partner_id = fields.Many2one(
        related='profile_id.partner_id',
        string='Client',
        store=True,
        readonly=True,
    )

    # Employer Details
    employer_name = fields.Char(
        string='Employer Name',
    )
    employer_country_id = fields.Many2one(
        comodel_name='res.country',
        string='Country',
    )
    employer_city = fields.Char(
        string='City',
    )
    employer_industry = fields.Char(
        string='Industry/Sector',
    )

    # Position Details
    job_title = fields.Char(
        string='Job Title',
    )
    noc_code = fields.Char(
        string='NOC Code',
        help='National Occupational Classification code (e.g., 21234)',
    )
    noc_teer_category = fields.Selection(
        selection=[
            ('0', 'TEER 0 - Management'),
            ('1', 'TEER 1 - Professional'),
            ('2', 'TEER 2 - Technical/Skilled Trades'),
            ('3', 'TEER 3 - Intermediate'),
            ('4', 'TEER 4 - Labour'),
            ('5', 'TEER 5 - No formal education'),
        ],
        string='NOC TEER Category',
        help='Training, Education, Experience, and Responsibilities level',
    )

    # Employment Details
    start_date = fields.Date(
        string='Start Date',
    )
    end_date = fields.Date(
        string='End Date',
        help='Leave blank if currently employed',
    )
    is_current = fields.Boolean(
        string='Current Position',
        default=False,
    )
    hours_per_week = fields.Float(
        string='Hours per Week',
        digits=(4, 1),
        default=40.0,
    )
    is_full_time = fields.Boolean(
        string='Full-time',
        compute='_compute_is_full_time',
        store=True,
        help='30+ hours/week is considered full-time',
    )
    is_paid = fields.Boolean(
        string='Paid Employment',
        default=True,
    )
    is_self_employed = fields.Boolean(
        string='Self-employed',
        default=False,
    )

    # Duration Calculation
    duration_years = fields.Float(
        string='Duration (Years)',
        compute='_compute_duration',
        store=True,
        digits=(4, 2),
    )
    duration_months = fields.Integer(
        string='Duration (Months)',
        compute='_compute_duration',
        store=True,
    )

    # Canada-specific
    in_canada = fields.Boolean(
        string='Worked in Canada',
        compute='_compute_in_canada',
        store=True,
    )
    work_permit_type = fields.Selection(
        selection=[
            ('na', 'N/A - Not in Canada'),
            ('closed', 'Closed Work Permit'),
            ('open', 'Open Work Permit'),
            ('pgwp', 'Post-Graduation Work Permit'),
            ('lmia', 'LMIA-based Work Permit'),
            ('coop', 'Co-op Work Permit'),
            ('citizen_pr', 'Canadian Citizen/PR'),
        ],
        string='Work Authorization',
        default='na',
    )

    # Job Duties
    main_duties = fields.Text(
        string='Main Duties',
        help='Describe 3-5 main job responsibilities',
    )

    # Reference Contact
    reference_name = fields.Char(
        string='Reference Name',
    )
    reference_title = fields.Char(
        string='Reference Title',
    )
    reference_email = fields.Char(
        string='Reference Email',
    )
    reference_phone = fields.Char(
        string='Reference Phone',
    )

    # For CRS Calculation
    is_skilled_work = fields.Boolean(
        string='Skilled Work (TEER 0-3)',
        compute='_compute_is_skilled',
        store=True,
    )
    qualifies_for_crs = fields.Boolean(
        string='Qualifies for CRS',
        compute='_compute_qualifies_for_crs',
        store=True,
        help='Full-time, paid, skilled work qualifies for CRS points',
    )

    notes = fields.Text(
        string='Notes',
    )

    @api.depends('job_title', 'employer_name')
    def _compute_name(self):
        for record in self:
            title = record.job_title or ''
            employer = record.employer_name or ''
            if title and employer:
                record.name = f"{title} at {employer}"
            else:
                record.name = title or employer or "New Experience"

    @api.depends('hours_per_week')
    def _compute_is_full_time(self):
        for record in self:
            record.is_full_time = record.hours_per_week >= 30.0

    @api.depends('start_date', 'end_date', 'is_current')
    def _compute_duration(self):
        today = fields.Date.today()
        for record in self:
            if record.start_date:
                end = record.end_date if not record.is_current else today
                if end and end >= record.start_date:
                    delta = relativedelta(end, record.start_date)
                    record.duration_months = delta.years * 12 + delta.months
                    record.duration_years = record.duration_months / 12.0
                else:
                    record.duration_months = 0
                    record.duration_years = 0.0
            else:
                record.duration_months = 0
                record.duration_years = 0.0

    @api.depends('employer_country_id')
    def _compute_in_canada(self):
        canada = self.env.ref('base.ca', raise_if_not_found=False)
        for record in self:
            record.in_canada = (
                record.employer_country_id.id == canada.id
                if canada and record.employer_country_id
                else False
            )

    @api.depends('noc_teer_category')
    def _compute_is_skilled(self):
        skilled_tiers = ['0', '1', '2', '3']
        for record in self:
            record.is_skilled_work = record.noc_teer_category in skilled_tiers

    @api.depends('is_full_time', 'is_paid', 'is_skilled_work')
    def _compute_qualifies_for_crs(self):
        for record in self:
            record.qualifies_for_crs = (
                record.is_full_time and
                record.is_paid and
                record.is_skilled_work
            )

    @api.onchange('is_current')
    def _onchange_is_current(self):
        if self.is_current:
            self.end_date = False

    @api.onchange('employer_country_id')
    def _onchange_country(self):
        canada = self.env.ref('base.ca', raise_if_not_found=False)
        if canada and self.employer_country_id.id == canada.id:
            if self.work_permit_type == 'na':
                self.work_permit_type = False
        else:
            self.work_permit_type = 'na'

    @api.constrains('start_date', 'end_date', 'is_current')
    def _check_dates(self):
        for record in self:
            if not record.is_current and record.start_date and record.end_date:
                if record.start_date > record.end_date:
                    raise ValidationError(_(
                        "End date must be after start date."
                    ))
            if record.is_current and record.end_date:
                raise ValidationError(_(
                    "Current positions should not have an end date."
                ))

    @api.constrains('hours_per_week')
    def _check_hours(self):
        for record in self:
            if record.hours_per_week < 0 or record.hours_per_week > 168:
                raise ValidationError(_(
                    "Hours per week must be between 0 and 168."
                ))
