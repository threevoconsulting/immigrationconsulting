# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EducationRecord(models.Model):
    """Stores education credentials for immigration clients."""
    _name = 'mm.education.record'
    _description = 'Education Record'
    _order = 'end_date desc, start_date desc'

    name = fields.Char(
        string='Credential Name',
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

    # Institution Details
    institution_name = fields.Char(
        string='Institution Name',
    )
    institution_country_id = fields.Many2one(
        comodel_name='res.country',
        string='Country',
    )
    institution_city = fields.Char(
        string='City',
    )

    # Credential Details
    credential_type = fields.Selection(
        selection=[
            ('secondary', 'Secondary School Diploma'),
            ('certificate', 'Certificate (less than 1 year)'),
            ('one_year', 'One-year Diploma/Certificate'),
            ('two_year', 'Two-year Diploma/Degree'),
            ('three_year', 'Three-year Diploma/Degree'),
            ('bachelors', "Bachelor's Degree"),
            ('post_grad_diploma', 'Post-graduate Diploma'),
            ('masters', "Master's Degree"),
            ('phd', 'Doctoral Degree (PhD)'),
            ('professional', 'Professional Degree (MD, JD, etc.)'),
        ],
        string='Credential Type',
        default='bachelors',
    )
    field_of_study = fields.Char(
        string='Field of Study',
    )
    credential_name = fields.Char(
        string='Credential Name',
        help='Official name of the degree/diploma',
    )

    # Dates
    start_date = fields.Date(
        string='Start Date',
    )
    end_date = fields.Date(
        string='End Date / Expected',
    )
    is_completed = fields.Boolean(
        string='Completed',
        default=True,
    )

    # Program Details
    was_full_time = fields.Boolean(
        string='Full-time Program',
        default=True,
        help='Was this a full-time program (at least 15 hours/week)?',
    )
    program_duration_years = fields.Float(
        string='Program Duration (Years)',
        digits=(3, 1),
        help='Official program length in years',
    )
    in_canada = fields.Boolean(
        string='Studied in Canada',
        compute='_compute_in_canada',
        store=True,
    )

    # ECA (Educational Credential Assessment)
    eca_status = fields.Selection(
        selection=[
            ('not_needed', 'Not Needed (Canadian credential)'),
            ('not_started', 'Not Started'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
        ],
        string='ECA Status',
        default='not_started',
    )
    eca_organization = fields.Selection(
        selection=[
            ('wes', 'WES (World Education Services)'),
            ('iqas', 'IQAS (International Qualifications Assessment Service)'),
            ('ces', 'CES (Comparative Education Service)'),
            ('icas', 'ICAS (International Credential Assessment Service)'),
            ('mcc', 'MCC (Medical Council of Canada)'),
            ('pebc', 'PEBC (Pharmacy Examining Board of Canada)'),
            ('other', 'Other'),
        ],
        string='ECA Organization',
    )
    eca_reference = fields.Char(
        string='ECA Reference Number',
    )
    eca_date = fields.Date(
        string='ECA Issue Date',
    )
    eca_canadian_equivalent = fields.Selection(
        selection=[
            ('secondary', 'Secondary School'),
            ('one_year', 'One-year post-secondary'),
            ('two_year', 'Two-year post-secondary'),
            ('bachelors', "Bachelor's Degree"),
            ('two_or_more', 'Two or more credentials'),
            ('masters', "Master's Degree"),
            ('phd', 'Doctoral (PhD)'),
        ],
        string='Canadian Equivalent',
        help='Equivalent credential as assessed by ECA',
    )

    # For CRS Calculation
    is_primary_credential = fields.Boolean(
        string='Primary Credential',
        default=False,
        help='Mark as primary credential for CRS calculation',
    )

    notes = fields.Text(
        string='Notes',
    )

    @api.depends('credential_type', 'institution_name', 'field_of_study')
    def _compute_name(self):
        credential_labels = dict(self._fields['credential_type'].selection)
        for record in self:
            cred_type = credential_labels.get(record.credential_type, '')
            institution = record.institution_name or ''
            field = record.field_of_study or ''
            if cred_type and institution:
                record.name = f"{cred_type} - {field} ({institution})"
            else:
                record.name = "New Education Record"

    @api.depends('institution_country_id')
    def _compute_in_canada(self):
        canada = self.env.ref('base.ca', raise_if_not_found=False)
        for record in self:
            record.in_canada = (
                record.institution_country_id.id == canada.id
                if canada and record.institution_country_id
                else False
            )

    @api.onchange('institution_country_id')
    def _onchange_country(self):
        """Update ECA status when country changes."""
        canada = self.env.ref('base.ca', raise_if_not_found=False)
        if canada and self.institution_country_id.id == canada.id:
            self.eca_status = 'not_needed'
        elif self.eca_status == 'not_needed':
            self.eca_status = 'not_started'

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date > record.end_date:
                    raise ValidationError(_(
                        "End date must be after start date."
                    ))

    @api.constrains('is_primary_credential', 'profile_id')
    def _check_single_primary(self):
        """Ensure only one primary credential per profile."""
        for record in self:
            if record.is_primary_credential:
                other_primary = self.search([
                    ('profile_id', '=', record.profile_id.id),
                    ('is_primary_credential', '=', True),
                    ('id', '!=', record.id),
                ], limit=1)
                if other_primary:
                    raise ValidationError(_(
                        "Only one education record can be marked as primary. "
                        "Please unmark '%s' first.",
                        other_primary.name
                    ))

    def action_mark_primary(self):
        """Mark this credential as the primary credential."""
        self.ensure_one()
        # Unmark any existing primary
        existing_primary = self.search([
            ('profile_id', '=', self.profile_id.id),
            ('is_primary_credential', '=', True),
            ('id', '!=', self.id),
        ])
        existing_primary.write({'is_primary_credential': False})
        self.write({'is_primary_credential': True})
