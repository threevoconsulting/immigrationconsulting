# -*- coding: utf-8 -*-

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class ClientProfile(models.Model):
    _name = 'mm.client.profile'
    _description = 'Immigration Client Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Profile Name',
        compute='_compute_name',
        store=True,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Contact',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    case_id = fields.Many2one(
        comodel_name='mm.immigration.case',
        string='Immigration Case',
        ondelete='cascade',
    )

    # Personal Information
    date_of_birth = fields.Date(
        string='Date of Birth',
        tracking=True,
    )
    age = fields.Integer(
        string='Age',
        compute='_compute_age',
        store=True,
    )
    citizenship_country_id = fields.Many2one(
        comodel_name='res.country',
        string='Country of Citizenship',
        tracking=True,
    )
    residence_country_id = fields.Many2one(
        comodel_name='res.country',
        string='Country of Residence',
        tracking=True,
    )
    marital_status = fields.Selection(
        selection=[
            ('single', 'Single'),
            ('married', 'Married'),
            ('common_law', 'Common-law'),
            ('divorced', 'Divorced/Separated'),
            ('widowed', 'Widowed'),
        ],
        string='Marital Status',
        tracking=True,
    )

    # Dependent Children
    has_children = fields.Boolean(
        string='Has Dependent Children',
        default=False,
    )
    children_ids = fields.One2many(
        comodel_name='mm.dependent.child',
        inverse_name='profile_id',
        string='Dependent Children',
    )
    children_count = fields.Integer(
        string='Number of Children',
        compute='_compute_children_count',
        store=True,
    )

    # Education
    highest_education = fields.Selection(
        selection=[
            ('secondary', 'Secondary School'),
            ('one_year', 'One-year Program'),
            ('two_year', 'Two-year Program'),
            ('bachelors', "Bachelor's Degree"),
            ('two_or_more', 'Two or More Credentials'),
            ('masters', "Master's Degree"),
            ('phd', 'Doctoral (PhD)'),
        ],
        string='Highest Education Level',
        tracking=True,
    )
    education_country_id = fields.Many2one(
        comodel_name='res.country',
        string='Education Country',
        help='Country where highest education was completed',
    )
    eca_status = fields.Selection(
        selection=[
            ('not_started', 'Not Started'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
        ],
        string='ECA Status',
        default='not_started',
        tracking=True,
    )
    eca_reference = fields.Char(
        string='ECA Reference Number',
    )

    # Work Experience
    current_occupation = fields.Char(
        string='Current Occupation',
        tracking=True,
    )
    work_experience_years = fields.Float(
        string='Years of Skilled Work Experience',
        digits=(4, 1),
        tracking=True,
    )
    work_country_id = fields.Many2one(
        comodel_name='res.country',
        string='Primary Work Country',
    )

    # Financial
    settlement_funds = fields.Monetary(
        string='Settlement Funds (CAD)',
        currency_field='currency_id',
        tracking=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        default=lambda self: self.env.ref('base.CAD', raise_if_not_found=False),
    )

    # Canada Connections
    has_family_in_canada = fields.Boolean(
        string='Family in Canada',
        default=False,
    )
    studied_in_canada = fields.Boolean(
        string='Previously Studied in Canada',
        default=False,
    )
    worked_in_canada = fields.Boolean(
        string='Previously Worked in Canada',
        default=False,
    )
    previous_visa_application = fields.Boolean(
        string='Previous Canadian Visa Application',
        default=False,
    )

    # Risk Factors
    visa_refusal = fields.Boolean(
        string='Previous Visa Refusal',
        default=False,
    )
    criminal_history = fields.Boolean(
        string='Criminal History',
        default=False,
    )
    medical_conditions = fields.Boolean(
        string='Medical Conditions',
        default=False,
    )

    @api.depends('partner_id', 'partner_id.name')
    def _compute_name(self):
        for profile in self:
            if profile.partner_id:
                profile.name = f"Profile - {profile.partner_id.name}"
            else:
                profile.name = "New Profile"

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = fields.Date.today()
        for profile in self:
            if profile.date_of_birth:
                profile.age = relativedelta(today, profile.date_of_birth).years
            else:
                profile.age = 0

    @api.depends('children_ids')
    def _compute_children_count(self):
        for profile in self:
            profile.children_count = len(profile.children_ids)


class DependentChild(models.Model):
    _name = 'mm.dependent.child'
    _description = 'Dependent Child'
    _order = 'date_of_birth'

    name = fields.Char(
        string='Full Name',
        required=True,
    )
    profile_id = fields.Many2one(
        comodel_name='mm.client.profile',
        string='Client Profile',
        required=True,
        ondelete='cascade',
    )
    date_of_birth = fields.Date(
        string='Date of Birth',
        required=True,
    )
    age = fields.Integer(
        string='Age',
        compute='_compute_age',
        store=True,
    )
    country_id = fields.Many2one(
        comodel_name='res.country',
        string='Country of Residence',
    )
    is_accompanying = fields.Boolean(
        string='Accompanying to Canada',
        default=True,
    )
    notes = fields.Text(
        string='Notes',
        help='Custody arrangements, medical considerations, etc.',
    )

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = fields.Date.today()
        for child in self:
            if child.date_of_birth:
                child.age = relativedelta(today, child.date_of_birth).years
            else:
                child.age = 0
