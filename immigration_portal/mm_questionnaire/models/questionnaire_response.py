# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class QuestionnaireResponse(models.Model):
    """Tracks questionnaire completion state for each immigration case."""
    _name = 'mm.questionnaire.response'
    _description = 'Questionnaire Response Tracker'
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        compute='_compute_name',
        store=True,
    )
    case_id = fields.Many2one(
        comodel_name='mm.immigration.case',
        string='Immigration Case',
        required=True,
        ondelete='cascade',
        index=True,
    )
    partner_id = fields.Many2one(
        related='case_id.partner_id',
        string='Client',
        store=True,
        readonly=True,
    )
    profile_id = fields.Many2one(
        related='case_id.profile_id',
        string='Client Profile',
        store=True,
        readonly=True,
    )
    questionnaire_type = fields.Selection(
        selection=[
            ('pre_consultation', 'Pre-Consultation (Q1)'),
            ('detailed_assessment', 'Detailed Assessment (Q2)'),
        ],
        string='Questionnaire Type',
        required=True,
    )
    state = fields.Selection(
        selection=[
            ('not_started', 'Not Started'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
        ],
        string='Status',
        default='not_started',
    )

    # =====================
    # Related Profile Fields for Q1 Display
    # =====================
    # Personal Info
    profile_legal_first_name = fields.Char(
        related='profile_id.legal_first_name', string='First Name')
    profile_legal_last_name = fields.Char(
        related='profile_id.legal_last_name', string='Last Name')
    profile_date_of_birth = fields.Date(
        related='profile_id.date_of_birth', string='Date of Birth')
    profile_citizenship = fields.Many2one(
        related='profile_id.citizenship_country_id', string='Citizenship')
    profile_residence = fields.Many2one(
        related='profile_id.residence_country_id', string='Residence')
    profile_marital_status = fields.Selection(
        related='profile_id.marital_status', string='Marital Status')
    profile_has_children = fields.Boolean(
        related='profile_id.has_children', string='Has Children')
    
    # Immigration Intent (Q1)
    profile_immigration_goal = fields.Selection(
        related='profile_id.immigration_goal', string='Immigration Goal')
    profile_target_year = fields.Selection(
        related='profile_id.target_year', string='Target Year')
    
    # Education Summary (Q1)
    profile_highest_education = fields.Selection(
        related='profile_id.highest_education', string='Highest Education')
    profile_eca_status = fields.Selection(
        related='profile_id.eca_status', string='ECA Status')
    
    # Work Summary (Q1)
    profile_current_occupation = fields.Char(
        related='profile_id.current_occupation', string='Current Occupation')
    profile_years_experience = fields.Float(
        related='profile_id.work_experience_years', string='Years of Experience')
    
    # Language Summary (Q1)
    profile_first_language = fields.Selection(
        related='profile_id.first_language', string='First Official Language')
    profile_second_language = fields.Boolean(
        related='profile_id.second_language', string='Second Language Proficiency')
    
    # Canada Connections (Q1)
    profile_has_family_canada = fields.Boolean(
        related='profile_id.has_family_in_canada', string='Has Family in Canada')
    profile_family_relationship = fields.Selection(
        related='profile_id.family_in_canada_relationship', string='Family Relationship')
    profile_family_province = fields.Many2one(
        related='profile_id.family_member_province_id', string='Family Member Province')
    profile_family_is_citizen_pr = fields.Boolean(
        related='profile_id.family_member_is_citizen_pr', string='Family Member is Citizen/PR')
    profile_studied_canada = fields.Boolean(
        related='profile_id.studied_in_canada', string='Studied in Canada')
    profile_worked_canada = fields.Boolean(
        related='profile_id.worked_in_canada', string='Worked in Canada')
    profile_previous_visa = fields.Boolean(
        related='profile_id.previous_visa_application', string='Previous Visa Application')
    
    # Financial & Risk (Q1)
    profile_currency_id = fields.Many2one(
        related='profile_id.currency_id', string='Currency')
    profile_settlement_funds = fields.Monetary(
        related='profile_id.settlement_funds', string='Settlement Funds',
        currency_field='profile_currency_id')
    profile_visa_refusal = fields.Boolean(
        related='profile_id.visa_refusal', string='Visa Refusal')
    profile_criminal_history = fields.Boolean(
        related='profile_id.criminal_history', string='Criminal History')
    profile_medical_conditions = fields.Boolean(
        related='profile_id.medical_conditions', string='Medical Conditions')
    
    # =====================
    # Related Profile Fields for Q2 Display (Detailed Records)
    # =====================
    profile_education_ids = fields.One2many(
        related='profile_id.education_ids', string='Education Records')
    profile_experience_ids = fields.One2many(
        related='profile_id.experience_ids', string='Work Experience')
    profile_language_ids = fields.One2many(
        related='profile_id.language_ids', string='Language Proficiency')

    # Section completion tracking
    current_section = fields.Integer(
        string='Current Section',
        default=1,
        help='The section the user is currently on',
    )
    total_sections = fields.Integer(
        string='Total Sections',
        compute='_compute_total_sections',
    )
    progress_percent = fields.Integer(
        string='Progress %',
        compute='_compute_progress',
    )

    # Q1 Section completion flags
    q1_section_personal = fields.Boolean(string='Personal Info Complete', default=False)
    q1_section_intent = fields.Boolean(string='Immigration Intent Complete', default=False)
    q1_section_education = fields.Boolean(string='Education Complete', default=False)
    q1_section_work = fields.Boolean(string='Work Experience Complete', default=False)
    q1_section_language = fields.Boolean(string='Language Complete', default=False)
    q1_section_canada = fields.Boolean(string='Canada Connections Complete', default=False)
    q1_section_financial = fields.Boolean(string='Financial/Risk Complete', default=False)

    # Q2 Section completion flags
    q2_section_principal = fields.Boolean(string='Principal Details Complete', default=False)
    q2_section_spouse = fields.Boolean(string='Spouse Details Complete', default=False)
    q2_section_children = fields.Boolean(string='Dependent Children Complete', default=False)
    q2_section_education = fields.Boolean(string='Education Details Complete', default=False)
    q2_section_experience = fields.Boolean(string='Work Experience Complete', default=False)
    q2_section_language = fields.Boolean(string='Language Proficiency Complete', default=False)
    q2_section_funds = fields.Boolean(string='Settlement Funds Complete', default=False)

    # Timestamps
    started_at = fields.Datetime(
        string='Started At',
        readonly=True,
    )
    completed_at = fields.Datetime(
        string='Completed At',
        readonly=True,
    )
    last_saved_at = fields.Datetime(
        string='Last Saved',
        readonly=True,
    )

    @api.depends('case_id', 'questionnaire_type')
    def _compute_name(self):
        for record in self:
            q_type = dict(self._fields['questionnaire_type'].selection).get(
                record.questionnaire_type, ''
            )
            case_ref = record.case_id.name if record.case_id else 'New'
            record.name = f"{case_ref} - {q_type}"

    @api.depends('questionnaire_type')
    def _compute_total_sections(self):
        for record in self:
            if record.questionnaire_type == 'pre_consultation':
                record.total_sections = 7
            elif record.questionnaire_type == 'detailed_assessment':
                record.total_sections = 7
            else:
                record.total_sections = 0

    @api.depends('questionnaire_type', 'current_section', 'total_sections',
                 'q1_section_personal', 'q1_section_intent', 'q1_section_education',
                 'q1_section_work', 'q1_section_language', 'q1_section_canada',
                 'q1_section_financial', 'q2_section_principal', 'q2_section_spouse',
                 'q2_section_children', 'q2_section_education', 'q2_section_experience',
                 'q2_section_language', 'q2_section_funds')
    def _compute_progress(self):
        for record in self:
            if record.questionnaire_type == 'pre_consultation':
                completed = sum([
                    record.q1_section_personal,
                    record.q1_section_intent,
                    record.q1_section_education,
                    record.q1_section_work,
                    record.q1_section_language,
                    record.q1_section_canada,
                    record.q1_section_financial,
                ])
                record.progress_percent = int((completed / 7) * 100) if completed else 0
            elif record.questionnaire_type == 'detailed_assessment':
                completed = sum([
                    record.q2_section_principal,
                    record.q2_section_spouse,
                    record.q2_section_children,
                    record.q2_section_education,
                    record.q2_section_experience,
                    record.q2_section_language,
                    record.q2_section_funds,
                ])
                record.progress_percent = int((completed / 7) * 100) if completed else 0
            else:
                record.progress_percent = 0

    def action_start(self):
        """Mark questionnaire as started."""
        self.ensure_one()
        if self.state == 'not_started':
            self.write({
                'state': 'in_progress',
                'started_at': fields.Datetime.now(),
            })

    def action_complete(self):
        """Mark questionnaire as completed and trigger stage advancement."""
        self.ensure_one()
        self.write({
            'state': 'completed',
            'completed_at': fields.Datetime.now(),
        })
        
        # Trigger case stage advancement and refresh computed fields
        if self.case_id:
            # Flush to ensure state change is committed to database
            self.flush_recordset(['state', 'completed_at'])
            
            # For stored computed fields, we need to:
            # 1. Invalidate the cache so Odoo knows the dependency changed
            # 2. Trigger recomputation which will write to database
            # Note: The dependency chain is questionnaire_response -> detailed_assessment_id -> q2_state
            self.case_id.invalidate_recordset([
                'pre_consultation_id', 'detailed_assessment_id',
                'q1_state', 'q2_state', 'q1_progress', 'q2_progress'
            ])
            
            # Access the fields to trigger recomputation and database write
            _ = self.case_id.detailed_assessment_id
            _ = self.case_id.q2_state
            
            # Flush the case to ensure computed values are written to database
            self.case_id.flush_recordset([
                'pre_consultation_id', 'detailed_assessment_id',
                'q1_state', 'q2_state', 'q1_progress', 'q2_progress'
            ])
            
            # Then trigger the workflow callback
            self.case_id._on_questionnaire_complete(self.questionnaire_type)

    def action_save_progress(self):
        """Update last saved timestamp."""
        self.ensure_one()
        self.write({
            'last_saved_at': fields.Datetime.now(),
        })
        if self.state == 'not_started':
            self.action_start()

    def mark_section_complete(self, section_number):
        """Mark a specific section as complete."""
        self.ensure_one()
        section_field = self._get_section_field(section_number)
        if section_field:
            self.write({
                section_field: True,
                'current_section': min(section_number + 1, self.total_sections),
                'last_saved_at': fields.Datetime.now(),
            })

    def _get_section_field(self, section_number):
        """Get the field name for a section number."""
        if self.questionnaire_type == 'pre_consultation':
            mapping = {
                1: 'q1_section_personal',
                2: 'q1_section_intent',
                3: 'q1_section_education',
                4: 'q1_section_work',
                5: 'q1_section_language',
                6: 'q1_section_canada',
                7: 'q1_section_financial',
            }
        elif self.questionnaire_type == 'detailed_assessment':
            mapping = {
                1: 'q2_section_principal',
                2: 'q2_section_spouse',
                3: 'q2_section_children',
                4: 'q2_section_education',
                5: 'q2_section_experience',
                6: 'q2_section_language',
                7: 'q2_section_funds',
            }
        else:
            return None
        return mapping.get(section_number)

    def is_section_complete(self, section_number):
        """Check if a specific section is complete."""
        self.ensure_one()
        section_field = self._get_section_field(section_number)
        if section_field:
            return getattr(self, section_field, False)
        return False

    def get_completed_sections(self):
        """Return list of completed section numbers."""
        self.ensure_one()
        completed = []
        for i in range(1, self.total_sections + 1):
            if self.is_section_complete(i):
                completed.append(i)
        return completed

    @api.constrains('case_id', 'questionnaire_type')
    def _check_unique_questionnaire(self):
        """Ensure only one questionnaire response per type per case."""
        for record in self:
            existing = self.search([
                ('case_id', '=', record.case_id.id),
                ('questionnaire_type', '=', record.questionnaire_type),
                ('id', '!=', record.id),
            ], limit=1)
            if existing:
                raise ValidationError(_(
                    "A %s questionnaire already exists for this case.",
                    dict(self._fields['questionnaire_type'].selection).get(
                        record.questionnaire_type
                    )
                ))

    def action_view_profile(self):
        """Open the full client profile form."""
        self.ensure_one()
        if self.profile_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Client Profile'),
                'res_model': 'mm.client.profile',
                'view_mode': 'form',
                'res_id': self.profile_id.id,
                'target': 'current',
            }
        return False

    def action_export_pdf(self):
        """Export questionnaire responses as PDF."""
        self.ensure_one()
        return self.env.ref('mm_questionnaire.action_report_client_profile').report_action(self.profile_id)
