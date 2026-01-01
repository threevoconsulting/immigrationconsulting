# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PNPOpportunity(models.Model):
    """Provincial Nominee Program opportunity assessment."""
    _name = 'mm.pnp.opportunity'
    _description = 'PNP Opportunity'
    _order = 'fit_rating desc, sequence'

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
    province_id = fields.Many2one(
        comodel_name='res.country.state',
        string='Province/Territory',
        required=True,
        domain="[('country_id.code', '=', 'CA')]",
    )
    province_code = fields.Char(
        related='province_id.code',
        string='Code',
    )

    # Program Details
    program_name = fields.Char(
        string='Program Name',
        help='Specific PNP stream name (e.g., Ontario Human Capital Priorities)',
    )
    program_stream = fields.Selection(
        selection=[
            ('ee_aligned', 'Express Entry Aligned'),
            ('non_ee', 'Non-Express Entry'),
            ('employer_driven', 'Employer-Driven'),
            ('entrepreneur', 'Entrepreneur/Business'),
            ('international_graduate', 'International Graduate'),
        ],
        string='Stream Type',
    )

    # Fit Assessment
    fit_rating = fields.Selection(
        selection=[
            ('5', 'Excellent Fit'),
            ('4', 'Good Fit'),
            ('3', 'Moderate Fit'),
            ('2', 'Limited Fit'),
            ('1', 'Poor Fit'),
            ('0', 'Not Eligible'),
        ],
        string='Fit Rating',
        required=True,
        default='3',
    )
    fit_rating_display = fields.Char(
        string='Fit Display',
        compute='_compute_fit_display',
    )

    # Key Factors
    meets_education_requirement = fields.Boolean(
        string='Meets Education',
        default=False,
    )
    meets_language_requirement = fields.Boolean(
        string='Meets Language',
        default=False,
    )
    meets_experience_requirement = fields.Boolean(
        string='Meets Experience',
        default=False,
    )
    meets_settlement_funds = fields.Boolean(
        string='Meets Settlement Funds',
        default=False,
    )
    has_job_offer = fields.Boolean(
        string='Has/Can Get Job Offer',
        default=False,
    )
    has_connection = fields.Boolean(
        string='Has Provincial Connection',
        default=False,
        help='Family, previous study, or work in province',
    )

    # Processing
    estimated_processing_months = fields.Integer(
        string='Processing Time (Months)',
    )
    current_draw_score = fields.Integer(
        string='Recent Draw Score',
        help='Most recent minimum score for this stream',
    )
    draw_frequency = fields.Selection(
        selection=[
            ('weekly', 'Weekly'),
            ('biweekly', 'Bi-weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('irregular', 'Irregular'),
        ],
        string='Draw Frequency',
    )

    # Notes
    key_advantages = fields.Text(
        string='Key Advantages',
        help='Why this province/program is a good fit',
    )
    key_challenges = fields.Text(
        string='Key Challenges',
        help='Potential obstacles or considerations',
    )
    consultant_notes = fields.Text(
        string='Consultant Notes',
    )

    @api.depends('fit_rating')
    def _compute_fit_display(self):
        rating_labels = dict(self._fields['fit_rating'].selection)
        for record in self:
            label = rating_labels.get(record.fit_rating, '')
            stars = '★' * int(record.fit_rating or 0) + '☆' * (5 - int(record.fit_rating or 0))
            record.fit_rating_display = f"{stars} {label}"

    @api.onchange('province_id')
    def _onchange_province(self):
        """Set default program name based on province."""
        province_programs = {
            'ON': 'Ontario Immigrant Nominee Program (OINP)',
            'BC': 'BC Provincial Nominee Program (BC PNP)',
            'AB': 'Alberta Advantage Immigration Program (AAIP)',
            'MB': 'Manitoba Provincial Nominee Program (MPNP)',
            'SK': 'Saskatchewan Immigrant Nominee Program (SINP)',
            'NS': 'Nova Scotia Nominee Program (NSNP)',
            'NB': 'New Brunswick Provincial Nominee Program (NBPNP)',
            'NL': 'Newfoundland and Labrador Provincial Nominee Program (NLPNP)',
            'PE': 'Prince Edward Island Provincial Nominee Program (PEI PNP)',
            'YT': 'Yukon Nominee Program (YNP)',
            'NT': 'Northwest Territories Nominee Program (NTNP)',
            'NU': 'Nunavut Nominee Program',
            'QC': 'Quebec Skilled Worker Program (QSWP)',
        }
        if self.province_id and self.province_id.code:
            self.program_name = province_programs.get(self.province_id.code, '')
