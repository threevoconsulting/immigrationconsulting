# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ClientProfileQuestionnaire(models.Model):
    """Extends mm.client.profile with questionnaire-related fields."""
    _inherit = 'mm.client.profile'

    # Extend eca_status to add 'not_needed' option
    eca_status = fields.Selection(
        selection_add=[
            ('not_needed', 'Not Needed (Canadian Education)'),
        ],
        ondelete={'not_needed': 'set default'},
    )

    # =====================
    # Additional Personal Fields (Q2 - Section A)
    # =====================
    legal_first_name = fields.Char(
        string='Legal First Name',
        help='First name exactly as it appears on passport',
    )
    legal_middle_name = fields.Char(
        string='Legal Middle Name(s)',
    )
    legal_last_name = fields.Char(
        string='Legal Last Name',
        help='Last/family name exactly as it appears on passport',
    )
    passport_number = fields.Char(
        string='Passport Number',
    )
    passport_country_id = fields.Many2one(
        comodel_name='res.country',
        string='Passport Country',
    )
    passport_expiry = fields.Date(
        string='Passport Expiry Date',
    )
    gender = fields.Selection(
        selection=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
            ('prefer_not_to_say', 'Prefer not to say'),
        ],
        string='Gender',
    )
    current_legal_status = fields.Selection(
        selection=[
            ('citizen', 'Citizen'),
            ('permanent_resident', 'Permanent Resident'),
            ('work_permit', 'Work Permit Holder'),
            ('study_permit', 'Study Permit Holder'),
            ('visitor', 'Visitor/Tourist'),
            ('refugee', 'Refugee/Asylum Seeker'),
            ('undocumented', 'Undocumented'),
            ('other', 'Other'),
        ],
        string='Current Legal Status',
        help='Legal status in your current country of residence',
    )
    current_status_expiry = fields.Date(
        string='Status Expiry Date',
        help='When does your current legal status expire?',
    )

    # =====================
    # Spouse/Partner Fields (Q2 - Section B)
    # =====================
    spouse_first_name = fields.Char(
        string='Spouse First Name',
    )
    spouse_last_name = fields.Char(
        string='Spouse Last Name',
    )
    spouse_date_of_birth = fields.Date(
        string='Spouse Date of Birth',
    )
    spouse_age = fields.Integer(
        string='Spouse Age',
        compute='_compute_spouse_age',
        store=True,
    )
    spouse_citizenship_country_id = fields.Many2one(
        comodel_name='res.country',
        string='Spouse Citizenship',
    )
    spouse_is_accompanying = fields.Boolean(
        string='Spouse Accompanying to Canada',
        default=True,
    )
    spouse_highest_education = fields.Selection(
        selection=[
            ('secondary', 'Secondary School'),
            ('one_year', 'One-year Program'),
            ('two_year', 'Two-year Program'),
            ('bachelors', "Bachelor's Degree"),
            ('two_or_more', 'Two or More Credentials'),
            ('masters', "Master's Degree"),
            ('phd', 'Doctoral (PhD)'),
        ],
        string='Spouse Education',
    )
    spouse_has_eca = fields.Boolean(
        string='Spouse Has ECA',
        default=False,
    )
    spouse_current_occupation = fields.Char(
        string='Spouse Occupation',
    )
    spouse_work_experience_years = fields.Float(
        string='Spouse Work Experience (Years)',
        digits=(4, 1),
    )
    spouse_has_canadian_experience = fields.Boolean(
        string='Spouse Has Canadian Work Experience',
        default=False,
    )

    # Spouse Language (simplified - detailed in language_proficiency)
    spouse_english_clb = fields.Integer(
        string='Spouse English CLB',
        help='Minimum CLB across all abilities',
    )
    spouse_french_clb = fields.Integer(
        string='Spouse French CLB',
        help='Minimum CLB across all abilities',
    )

    # =====================
    # Language (Q1 - Section E)
    # =====================
    first_language = fields.Selection(
        selection=[
            ('english', 'English'),
            ('french', 'French'),
        ],
        string='First Official Language',
        help='Which official language are you most proficient in?',
    )
    second_language = fields.Boolean(
        string='Has Second Official Language',
        default=False,
        help='Do you also have proficiency in the other official language?',
    )

    # =====================
    # Immigration Intent (Q1 - Section B)
    # =====================
    immigration_goal = fields.Selection(
        selection=[
            ('pr', 'Permanent Residence'),
            ('temporary', 'Temporary Residence (Work/Study)'),
            ('undecided', 'Not Sure Yet'),
        ],
        string='Immigration Goal',
    )
    target_year = fields.Selection(
        selection=lambda self: self._get_year_selection(),
        string='Target Year to Move',
    )
    open_to_rural = fields.Selection(
        selection=[
            ('yes', 'Yes'),
            ('no', 'No'),
            ('maybe', 'Maybe'),
        ],
        string='Open to Rural/Smaller Cities',
        help='Would you consider settling outside major cities?',
    )
    preferred_provinces = fields.Many2many(
        comodel_name='res.country.state',
        relation='mm_profile_preferred_province_rel',
        column1='profile_id',
        column2='state_id',
        string='Preferred Provinces',
        domain="[('country_id.code', '=', 'CA')]",
    )

    # =====================
    # Canada Connections (Q1 - Section F)
    # =====================
    family_in_canada_relationship = fields.Selection(
        selection=[
            ('none', 'No family in Canada'),
            ('parent', 'Parent'),
            ('sibling', 'Sibling'),
            ('grandparent', 'Grandparent'),
            ('aunt_uncle', 'Aunt/Uncle'),
            ('cousin', 'Cousin'),
            ('child', 'Adult Child'),
            ('other', 'Other'),
        ],
        string='Family Relationship',
        help='Closest family member in Canada',
    )
    family_member_province_id = fields.Many2one(
        comodel_name='res.country.state',
        string='Family Member Province',
        domain="[('country_id.code', '=', 'CA')]",
    )
    family_member_is_citizen_pr = fields.Boolean(
        string='Family Member is Citizen/PR',
        default=False,
    )
    canada_study_duration_months = fields.Integer(
        string='Canadian Study Duration (Months)',
        default=0,
    )
    canada_work_duration_months = fields.Integer(
        string='Canadian Work Duration (Months)',
        default=0,
    )
    previous_visa_type = fields.Selection(
        selection=[
            ('none', 'Never applied'),
            ('visitor', 'Visitor Visa'),
            ('study', 'Study Permit'),
            ('work', 'Work Permit'),
            ('pr', 'PR Application'),
        ],
        string='Previous Visa Type',
    )
    previous_visa_result = fields.Selection(
        selection=[
            ('approved', 'Approved'),
            ('refused', 'Refused'),
            ('withdrawn', 'Withdrawn'),
            ('pending', 'Still Pending'),
        ],
        string='Previous Visa Result',
    )

    # =====================
    # Financial (Q1 - Section G, Q2 - Section G)
    # =====================
    funds_source = fields.Selection(
        selection=[
            ('savings', 'Personal Savings'),
            ('investments', 'Investments'),
            ('property', 'Property Sale'),
            ('family', 'Family Support'),
            ('business', 'Business Income'),
            ('multiple', 'Multiple Sources'),
        ],
        string='Primary Fund Source',
    )
    funds_liquid = fields.Boolean(
        string='Funds are Liquid',
        default=False,
        help='Can you prove 6 months history of available funds?',
    )
    can_prove_funds = fields.Selection(
        selection=[
            ('yes', 'Yes'),
            ('no', 'No'),
            ('unsure', 'Not Sure'),
        ],
        string='Can Prove Settlement Funds',
    )

    # =====================
    # Risk Factors (Q1 - Section G)
    # =====================
    visa_refusal_details = fields.Text(
        string='Visa Refusal Details',
        help='If you have had a visa refusal, please explain',
    )
    criminal_history_details = fields.Text(
        string='Criminal History Details',
        help='If applicable, please explain',
    )
    medical_condition_details = fields.Text(
        string='Medical Condition Details',
        help='Any conditions requiring ongoing treatment',
    )

    # =====================
    # Related Records
    # =====================
    education_ids = fields.One2many(
        comodel_name='mm.education.record',
        inverse_name='profile_id',
        string='Education Records',
    )
    education_count = fields.Integer(
        string='Education Count',
        compute='_compute_education_count',
        store=True,
    )
    experience_ids = fields.One2many(
        comodel_name='mm.work.experience',
        inverse_name='profile_id',
        string='Work Experience',
    )
    experience_count = fields.Integer(
        string='Experience Count',
        compute='_compute_experience_count',
        store=True,
    )
    language_ids = fields.One2many(
        comodel_name='mm.language.proficiency',
        inverse_name='profile_id',
        string='Language Proficiency',
    )
    language_count = fields.Integer(
        string='Language Count',
        compute='_compute_language_count',
        store=True,
    )

    # =====================
    # Computed Totals for CRS
    # =====================
    total_skilled_experience_years = fields.Float(
        string='Total Skilled Experience (Years)',
        compute='_compute_total_experience',
        store=True,
        digits=(4, 1),
    )
    total_canadian_experience_months = fields.Integer(
        string='Canadian Experience (Months)',
        compute='_compute_total_experience',
        store=True,
    )
    primary_education_level = fields.Selection(
        selection=[
            ('secondary', 'Secondary School'),
            ('one_year', 'One-year Program'),
            ('two_year', 'Two-year Program'),
            ('bachelors', "Bachelor's Degree"),
            ('two_or_more', 'Two or More Credentials'),
            ('masters', "Master's Degree"),
            ('phd', 'Doctoral (PhD)'),
        ],
        string='Primary Education (ECA)',
        compute='_compute_primary_education',
        store=True,
    )
    english_clb_minimum = fields.Integer(
        string='English CLB (Minimum)',
        compute='_compute_language_clb',
        store=True,
    )
    french_clb_minimum = fields.Integer(
        string='French CLB (Minimum)',
        compute='_compute_language_clb',
        store=True,
    )

    def _get_year_selection(self):
        """Generate year selection from current year to +5 years."""
        import datetime
        current_year = datetime.date.today().year
        return [(str(year), str(year)) for year in range(current_year, current_year + 6)]

    @api.depends('spouse_date_of_birth')
    def _compute_spouse_age(self):
        from dateutil.relativedelta import relativedelta
        today = fields.Date.today()
        for profile in self:
            if profile.spouse_date_of_birth:
                profile.spouse_age = relativedelta(today, profile.spouse_date_of_birth).years
            else:
                profile.spouse_age = 0

    @api.depends('education_ids')
    def _compute_education_count(self):
        for profile in self:
            profile.education_count = len(profile.education_ids)

    @api.depends('experience_ids')
    def _compute_experience_count(self):
        for profile in self:
            profile.experience_count = len(profile.experience_ids)

    @api.depends('language_ids')
    def _compute_language_count(self):
        for profile in self:
            profile.language_count = len(profile.language_ids)

    @api.depends('experience_ids', 'experience_ids.duration_years',
                 'experience_ids.qualifies_for_crs', 'experience_ids.in_canada',
                 'experience_ids.duration_months')
    def _compute_total_experience(self):
        for profile in self:
            qualified_exp = profile.experience_ids.filtered('qualifies_for_crs')
            profile.total_skilled_experience_years = sum(qualified_exp.mapped('duration_years'))

            canadian_exp = profile.experience_ids.filtered(
                lambda e: e.in_canada and e.qualifies_for_crs
            )
            profile.total_canadian_experience_months = sum(canadian_exp.mapped('duration_months'))

    @api.depends('education_ids', 'education_ids.is_primary_credential',
                 'education_ids.eca_canadian_equivalent')
    def _compute_primary_education(self):
        for profile in self:
            primary = profile.education_ids.filtered('is_primary_credential')
            if primary:
                profile.primary_education_level = primary[0].eca_canadian_equivalent
            else:
                # Fall back to highest_education if no primary credential marked
                profile.primary_education_level = profile.highest_education

    @api.depends('language_ids', 'language_ids.language', 'language_ids.clb_minimum')
    def _compute_language_clb(self):
        for profile in self:
            english_tests = profile.language_ids.filtered(
                lambda l: l.language == 'english' and l.clb_minimum > 0
            )
            french_tests = profile.language_ids.filtered(
                lambda l: l.language == 'french' and l.clb_minimum > 0
            )

            profile.english_clb_minimum = max(english_tests.mapped('clb_minimum'), default=0)
            profile.french_clb_minimum = max(french_tests.mapped('clb_minimum'), default=0)

    def action_export_pdf(self):
        """Export client profile as PDF report."""
        self.ensure_one()
        return self.env.ref('mm_questionnaire.action_report_client_profile').report_action(self)
