# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import logging

_logger = logging.getLogger(__name__)


class RoadmapDocument(models.Model):
    """Immigration Roadmap Document."""
    _name = 'mm.roadmap.document'
    _description = 'Immigration Roadmap'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
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
        tracking=True,
    )
    profile_id = fields.Many2one(
        related='case_id.profile_id',
        string='Client Profile',
        store=True,
    )
    partner_id = fields.Many2one(
        related='case_id.partner_id',
        string='Client',
        store=True,
    )
    crs_calculation_id = fields.Many2one(
        comodel_name='mm.crs.calculation',
        string='CRS Calculation',
        domain="[('case_id', '=', case_id), ('is_scenario', '=', False)]",
        tracking=True,
    )
    consultant_id = fields.Many2one(
        comodel_name='res.users',
        string='Prepared By',
        default=lambda self: self.env.user,
        tracking=True,
    )
    version = fields.Integer(
        string='Version',
        default=1,
        tracking=True,
    )

    # =====================
    # Workflow States
    # =====================
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('review', 'Under Review'),
            ('approved', 'Approved'),
            ('delivered', 'Delivered'),
            ('acknowledged', 'Acknowledged'),
        ],
        string='Status',
        default='draft',
        tracking=True,
        required=True,
    )

    # =====================
    # Section 1: Cover Page (auto-generated)
    # =====================
    document_date = fields.Date(
        string='Document Date',
        default=fields.Date.today,
    )
    client_full_name = fields.Char(
        string='Client Full Name',
        compute='_compute_client_info',
        store=True,
    )
    client_citizenship = fields.Char(
        string='Client Citizenship',
        compute='_compute_client_info',
        store=True,
    )

    # =====================
    # Section 3: Executive Summary (rich text)
    # =====================
    executive_summary = fields.Html(
        string='Executive Summary',
        help='High-level overview of the client situation and recommended strategy',
    )

    # =====================
    # Section 4: Profile Overview (auto-populated from Q2)
    # =====================
    # Personal
    profile_age = fields.Integer(related='profile_id.age', string='Age')
    profile_marital_status = fields.Selection(
        related='profile_id.marital_status', string='Marital Status')
    profile_children_count = fields.Integer(
        related='profile_id.children_count', string='Dependents')
    
    # Education
    profile_education = fields.Selection(
        related='profile_id.primary_education_level', string='Education Level')
    
    # Language
    profile_english_clb = fields.Integer(
        related='profile_id.english_clb_minimum', string='English CLB')
    profile_french_clb = fields.Integer(
        related='profile_id.french_clb_minimum', string='French CLB')
    
    # Experience
    profile_experience_years = fields.Float(
        related='profile_id.total_skilled_experience_years', string='Work Experience (Years)')
    profile_canadian_exp_months = fields.Integer(
        related='profile_id.total_canadian_experience_months', string='Canadian Experience (Months)')

    # =====================
    # Section 5: PR Factors Assessment (from CRS)
    # =====================
    crs_total_score = fields.Integer(
        related='crs_calculation_id.total_crs_score',
        string='CRS Score',
    )
    crs_tier = fields.Selection(
        related='crs_calculation_id.crs_tier',
        string='CRS Tier',
    )
    fsw_total_points = fields.Integer(
        related='crs_calculation_id.fsw_total_points',
        string='FSW Points',
    )
    fsw_eligible = fields.Boolean(
        related='crs_calculation_id.fsw_eligible',
        string='FSW Eligible',
    )

    # =====================
    # Section 6: FSW Assessment Details
    # =====================
    fsw_analysis = fields.Html(
        string='FSW Analysis',
        help='Detailed breakdown of FSW 67-point grid assessment',
    )
    crs_simulation_notes = fields.Html(
        string='CRS Simulation Notes',
        help='Analysis of English-first vs French-first strategies',
    )

    # =====================
    # Section 7: PNP Opportunities
    # =====================
    pnp_opportunity_ids = fields.One2many(
        comodel_name='mm.pnp.opportunity',
        inverse_name='roadmap_id',
        string='PNP Opportunities',
    )
    pnp_analysis = fields.Html(
        string='PNP Analysis Summary',
        help='Overall analysis of PNP opportunities',
    )

    # =====================
    # Section 8: Recommended Strategy
    # =====================
    primary_strategy = fields.Selection(
        selection=[
            ('express_entry_fsw', 'Express Entry - Federal Skilled Worker'),
            ('express_entry_cec', 'Express Entry - Canadian Experience Class'),
            ('express_entry_fst', 'Express Entry - Federal Skilled Trades'),
            ('ee_pnp', 'Express Entry + PNP Enhancement'),
            ('pnp_direct', 'Direct PNP Application'),
            ('francophone', 'Francophone Mobility'),
            ('other', 'Other Pathway'),
        ],
        string='Primary Strategy',
        tracking=True,
    )
    primary_strategy_rationale = fields.Html(
        string='Primary Strategy Rationale',
        help='Explanation of why this strategy is recommended',
    )
    backup_strategy = fields.Selection(
        selection=[
            ('express_entry_fsw', 'Express Entry - Federal Skilled Worker'),
            ('express_entry_cec', 'Express Entry - Canadian Experience Class'),
            ('express_entry_fst', 'Express Entry - Federal Skilled Trades'),
            ('ee_pnp', 'Express Entry + PNP Enhancement'),
            ('pnp_direct', 'Direct PNP Application'),
            ('francophone', 'Francophone Mobility'),
            ('study_permit', 'Study Permit Pathway'),
            ('work_permit', 'Work Permit Pathway'),
            ('none', 'No Backup Needed'),
        ],
        string='Backup Strategy',
    )
    backup_strategy_rationale = fields.Html(
        string='Backup Strategy Rationale',
    )

    # =====================
    # Section 9: Timeline
    # =====================
    milestone_ids = fields.One2many(
        comodel_name='mm.roadmap.milestone',
        inverse_name='roadmap_id',
        string='Timeline Milestones',
    )
    timeline_start_date = fields.Date(
        string='Timeline Start',
        default=fields.Date.today,
    )
    estimated_pr_date = fields.Date(
        string='Estimated PR Date',
    )
    timeline_notes = fields.Html(
        string='Timeline Notes',
    )

    # =====================
    # Section 10: Next Steps
    # =====================
    next_steps = fields.Html(
        string='Next Steps',
        help='Immediate action items for the client (ECA, language tests, etc.)',
    )
    eca_guidance = fields.Html(
        string='ECA Guidance',
        help='Specific guidance on Educational Credential Assessment',
    )
    language_guidance = fields.Html(
        string='Language Test Guidance',
        help='Specific guidance on language testing',
    )

    # =====================
    # Section 11: Appendices
    # =====================
    appendix_notes = fields.Html(
        string='Appendices',
        help='Additional reference material, links, or documents',
    )

    # =====================
    # Document Generation
    # =====================
    pdf_document = fields.Binary(
        string='PDF Document',
        attachment=True,
    )
    pdf_filename = fields.Char(
        string='PDF Filename',
    )
    generated_date = fields.Datetime(
        string='Generated Date',
    )

    # =====================
    # Client Acknowledgment
    # =====================
    client_signature = fields.Binary(
        string='Client Signature',
        attachment=True,
    )
    acknowledged_date = fields.Datetime(
        string='Acknowledged Date',
    )
    acknowledged_ip = fields.Char(
        string='Acknowledged IP',
    )

    # =====================
    # Branding Settings
    # =====================
    company_logo = fields.Binary(
        string='Company Logo',
        compute='_compute_branding',
    )
    header_color = fields.Char(
        string='Header Color',
        compute='_compute_branding',
    )

    @api.depends('case_id', 'version')
    def _compute_name(self):
        for record in self:
            case_ref = record.case_id.name if record.case_id else 'New'
            record.name = f"{case_ref} - Roadmap v{record.version}"

    @api.depends('partner_id', 'profile_id')
    def _compute_client_info(self):
        for record in self:
            if record.partner_id:
                record.client_full_name = record.partner_id.name
            else:
                record.client_full_name = ''
            
            if record.profile_id and record.profile_id.citizenship_country_id:
                record.client_citizenship = record.profile_id.citizenship_country_id.name
            else:
                record.client_citizenship = ''

    def _compute_branding(self):
        """Get branding from company settings."""
        for record in self:
            company = record.case_id.company_id or self.env.company
            record.company_logo = company.logo
            # Default to Migration Monitor orange/salmon
            record.header_color = '#E8967A'

    def _compute_access_url(self):
        super()._compute_access_url()
        for record in self:
            record.access_url = f'/my/immigration/roadmap/{record.id}'

    # =====================
    # Workflow Actions
    # =====================
    def action_submit_for_review(self):
        """Submit roadmap for review."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Only draft roadmaps can be submitted for review."))
        
        self.write({'state': 'review'})
        self.message_post(
            body=_("Roadmap submitted for review."),
            message_type='notification',
        )

    def action_approve(self):
        """Approve the roadmap."""
        self.ensure_one()
        if self.state != 'review':
            raise UserError(_("Only roadmaps under review can be approved."))
        
        self.write({'state': 'approved'})
        self.message_post(
            body=_("Roadmap approved by %s.") % self.env.user.name,
            message_type='notification',
        )

    def action_deliver(self):
        """Deliver the roadmap to client."""
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_("Only approved roadmaps can be delivered."))
        
        # Generate PDF if not already generated
        if not self.pdf_document:
            self.action_generate_pdf()
        
        self.write({'state': 'delivered'})
        
        # Advance case stage to Roadmap Delivered
        roadmap_stage = self.env.ref('mm_immigration.stage_roadmap', raise_if_not_found=False)
        if roadmap_stage and self.case_id.stage_id != roadmap_stage:
            self.case_id.stage_id = roadmap_stage
        
        # Send notification email to client
        template = self.env.ref('mm_roadmap.mail_template_roadmap_delivered', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        
        self.message_post(
            body=_("Roadmap delivered to client."),
            message_type='notification',
        )

    def action_mark_acknowledged(self, signature=None, ip_address=None):
        """Mark roadmap as acknowledged by client."""
        self.ensure_one()
        if self.state != 'delivered':
            raise UserError(_("Only delivered roadmaps can be acknowledged."))
        
        vals = {
            'state': 'acknowledged',
            'acknowledged_date': fields.Datetime.now(),
        }
        if signature:
            vals['client_signature'] = signature
        if ip_address:
            vals['acknowledged_ip'] = ip_address
        
        self.write(vals)
        
        # Advance case to consultation stage
        consultation_stage = self.env.ref('mm_immigration.stage_consultation', raise_if_not_found=False)
        if consultation_stage:
            self.case_id.stage_id = consultation_stage
        
        self.message_post(
            body=_("Roadmap acknowledged by client."),
            message_type='notification',
        )

    def action_return_to_draft(self):
        """Return to draft for further edits."""
        self.ensure_one()
        if self.state not in ('review', 'approved'):
            raise UserError(_("Cannot return to draft from current state."))
        
        self.write({'state': 'draft'})

    def action_create_new_version(self):
        """Create a new version of this roadmap."""
        self.ensure_one()
        
        new_roadmap = self.copy({
            'version': self.version + 1,
            'state': 'draft',
            'pdf_document': False,
            'pdf_filename': False,
            'generated_date': False,
            'client_signature': False,
            'acknowledged_date': False,
            'acknowledged_ip': False,
        })
        
        return {
            'name': _('New Roadmap Version'),
            'type': 'ir.actions.act_window',
            'res_model': 'mm.roadmap.document',
            'view_mode': 'form',
            'res_id': new_roadmap.id,
            'target': 'current',
        }

    # =====================
    # PDF Generation
    # =====================
    def action_generate_pdf(self):
        """Generate PDF document."""
        self.ensure_one()
        
        # Use Odoo's report engine
        report = self.env.ref('mm_roadmap.action_report_roadmap')
        pdf_content, _ = report._render_qweb_pdf(report.id, [self.id])
        
        filename = f"Immigration_Roadmap_{self.case_id.name}_{self.version}.pdf"
        
        self.write({
            'pdf_document': base64.b64encode(pdf_content),
            'pdf_filename': filename,
            'generated_date': fields.Datetime.now(),
        })
        
        self.message_post(
            body=_("PDF document generated."),
            message_type='notification',
        )
        
        return True

    def action_download_pdf(self):
        """Download the PDF document."""
        self.ensure_one()
        if not self.pdf_document:
            self.action_generate_pdf()
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/mm.roadmap.document/{self.id}/pdf_document/{self.pdf_filename}?download=true',
            'target': 'self',
        }

    # =====================
    # Auto-populate from Profile
    # =====================
    def action_populate_from_profile(self):
        """Populate roadmap fields from profile and CRS calculation."""
        self.ensure_one()
        
        if not self.case_id.profile_id:
            raise UserError(_("No client profile found for this case."))
        
        # Get current CRS calculation
        if not self.crs_calculation_id:
            current_crs = self.case_id.current_crs_calculation_id
            if current_crs:
                self.crs_calculation_id = current_crs.id
        
        self.message_post(
            body=_("Roadmap populated from profile data."),
            message_type='notification',
        )

    def action_add_default_milestones(self):
        """Add default timeline milestones."""
        self.ensure_one()
        
        # Clear existing milestones
        self.milestone_ids.unlink()
        
        # Default milestones based on primary strategy
        milestones = []
        start_date = self.timeline_start_date or fields.Date.today()
        
        if self.primary_strategy in ('express_entry_fsw', 'express_entry_cec', 'express_entry_fst', 'ee_pnp'):
            milestones = [
                ('ECA Application', 1, 'Apply for Educational Credential Assessment'),
                ('Language Test', 2, 'Book and complete IELTS/CELPIP or TEF/TCF'),
                ('ECA Results', 8, 'Receive ECA results'),
                ('Create Express Entry Profile', 10, 'Submit Express Entry profile to IRCC pool'),
                ('PNP Application (if applicable)', 12, 'Apply to Provincial Nominee Program'),
                ('Receive ITA', 16, 'Receive Invitation to Apply'),
                ('Submit eAPR', 18, 'Submit electronic Application for Permanent Residence'),
                ('Medical Exam', 19, 'Complete immigration medical examination'),
                ('Biometrics', 20, 'Provide biometric information'),
                ('COPR Received', 28, 'Receive Confirmation of Permanent Residence'),
                ('Landing', 30, 'Complete PR landing in Canada'),
            ]
        elif self.primary_strategy == 'pnp_direct':
            milestones = [
                ('ECA Application', 1, 'Apply for Educational Credential Assessment'),
                ('Language Test', 2, 'Book and complete language test'),
                ('ECA Results', 8, 'Receive ECA results'),
                ('PNP Application', 10, 'Submit Provincial Nominee Program application'),
                ('PNP Nomination', 20, 'Receive provincial nomination'),
                ('Submit PR Application', 22, 'Submit federal PR application'),
                ('Medical Exam', 24, 'Complete immigration medical examination'),
                ('Biometrics', 25, 'Provide biometric information'),
                ('COPR Received', 40, 'Receive Confirmation of Permanent Residence'),
                ('Landing', 42, 'Complete PR landing in Canada'),
            ]
        
        for name, weeks, description in milestones:
            self.env['mm.roadmap.milestone'].create({
                'roadmap_id': self.id,
                'name': name,
                'target_date': fields.Date.add(start_date, weeks=weeks),
                'description': description,
            })

    @api.constrains('case_id', 'version')
    def _check_unique_version(self):
        """Ensure version is unique per case."""
        for record in self:
            existing = self.search([
                ('case_id', '=', record.case_id.id),
                ('version', '=', record.version),
                ('id', '!=', record.id),
            ], limit=1)
            if existing:
                raise ValidationError(_(
                    "Version %s already exists for this case. Please use a different version number."
                ) % record.version)
