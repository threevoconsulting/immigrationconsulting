# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LanguageProficiency(models.Model):
    """Stores language test results and CLB scores for immigration clients."""
    _name = 'mm.language.proficiency'
    _description = 'Language Proficiency Record'
    _order = 'is_first_official desc, test_date desc'

    name = fields.Char(
        string='Language Test',
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

    # Language Selection
    language = fields.Selection(
        selection=[
            ('english', 'English'),
            ('french', 'French'),
        ],
        string='Language',
        required=True,
    )
    is_first_official = fields.Boolean(
        string='First Official Language',
        default=False,
        help='Check if this is your strongest official language',
    )

    # Test Information
    test_type = fields.Selection(
        selection=[
            # English tests
            ('ielts_general', 'IELTS General Training'),
            ('celpip_general', 'CELPIP General'),
            # French tests
            ('tef_canada', 'TEF Canada'),
            ('tcf_canada', 'TCF Canada'),
            # No test
            ('none', 'No Test Taken'),
        ],
        string='Test Type',
        required=True,
    )
    test_date = fields.Date(
        string='Test Date',
    )
    test_expires = fields.Date(
        string='Expiry Date',
        compute='_compute_expiry',
        store=True,
        help='Language tests are valid for 2 years',
    )
    is_valid = fields.Boolean(
        string='Currently Valid',
        compute='_compute_is_valid',
        store=True,
    )
    test_report_number = fields.Char(
        string='Test Report Number / TRF',
    )

    # Raw Scores - IELTS (0.0 - 9.0 scale)
    ielts_listening = fields.Float(string='IELTS Listening', digits=(3, 1))
    ielts_reading = fields.Float(string='IELTS Reading', digits=(3, 1))
    ielts_writing = fields.Float(string='IELTS Writing', digits=(3, 1))
    ielts_speaking = fields.Float(string='IELTS Speaking', digits=(3, 1))

    # Raw Scores - CELPIP (1-12 scale)
    celpip_listening = fields.Integer(string='CELPIP Listening')
    celpip_reading = fields.Integer(string='CELPIP Reading')
    celpip_writing = fields.Integer(string='CELPIP Writing')
    celpip_speaking = fields.Integer(string='CELPIP Speaking')

    # Raw Scores - TEF Canada (various scales)
    tef_listening = fields.Integer(string='TEF Listening (0-360)')
    tef_reading = fields.Integer(string='TEF Reading (0-300)')
    tef_writing = fields.Integer(string='TEF Writing (0-450)')
    tef_speaking = fields.Integer(string='TEF Speaking (0-450)')

    # Raw Scores - TCF Canada (various scales)
    tcf_listening = fields.Integer(string='TCF Listening (0-699)')
    tcf_reading = fields.Integer(string='TCF Reading (0-699)')
    tcf_writing = fields.Integer(string='TCF Writing (0-20)')
    tcf_speaking = fields.Integer(string='TCF Speaking (0-20)')

    # Computed CLB Scores (Canadian Language Benchmark)
    clb_listening = fields.Integer(
        string='CLB Listening',
        compute='_compute_clb_scores',
        store=True,
    )
    clb_reading = fields.Integer(
        string='CLB Reading',
        compute='_compute_clb_scores',
        store=True,
    )
    clb_writing = fields.Integer(
        string='CLB Writing',
        compute='_compute_clb_scores',
        store=True,
    )
    clb_speaking = fields.Integer(
        string='CLB Speaking',
        compute='_compute_clb_scores',
        store=True,
    )
    clb_average = fields.Float(
        string='CLB Average',
        compute='_compute_clb_scores',
        store=True,
        digits=(3, 1),
    )
    clb_minimum = fields.Integer(
        string='CLB Minimum',
        compute='_compute_clb_scores',
        store=True,
        help='Lowest CLB score across all abilities',
    )

    notes = fields.Text(
        string='Notes',
    )

    @api.depends('language', 'test_type', 'clb_minimum')
    def _compute_name(self):
        test_labels = dict(self._fields['test_type'].selection)
        for record in self:
            test = test_labels.get(record.test_type, 'Unknown')
            clb = f"CLB {record.clb_minimum}" if record.clb_minimum else "No CLB"
            record.name = f"{test} - {clb}"

    @api.depends('test_date')
    def _compute_expiry(self):
        for record in self:
            if record.test_date:
                # Language tests are valid for 2 years
                record.test_expires = fields.Date.add(record.test_date, years=2)
            else:
                record.test_expires = False

    @api.depends('test_expires')
    def _compute_is_valid(self):
        today = fields.Date.today()
        for record in self:
            if record.test_expires:
                record.is_valid = record.test_expires >= today
            else:
                record.is_valid = False

    @api.depends(
        'test_type',
        'ielts_listening', 'ielts_reading', 'ielts_writing', 'ielts_speaking',
        'celpip_listening', 'celpip_reading', 'celpip_writing', 'celpip_speaking',
        'tef_listening', 'tef_reading', 'tef_writing', 'tef_speaking',
        'tcf_listening', 'tcf_reading', 'tcf_writing', 'tcf_speaking',
    )
    def _compute_clb_scores(self):
        """Convert raw test scores to CLB equivalents."""
        for record in self:
            if record.test_type == 'ielts_general':
                record.clb_listening = record._ielts_to_clb(record.ielts_listening, 'listening')
                record.clb_reading = record._ielts_to_clb(record.ielts_reading, 'reading')
                record.clb_writing = record._ielts_to_clb(record.ielts_writing, 'writing')
                record.clb_speaking = record._ielts_to_clb(record.ielts_speaking, 'speaking')
            elif record.test_type == 'celpip_general':
                # CELPIP scores map directly to CLB
                record.clb_listening = record.celpip_listening or 0
                record.clb_reading = record.celpip_reading or 0
                record.clb_writing = record.celpip_writing or 0
                record.clb_speaking = record.celpip_speaking or 0
            elif record.test_type == 'tef_canada':
                record.clb_listening = record._tef_to_clb(record.tef_listening, 'listening')
                record.clb_reading = record._tef_to_clb(record.tef_reading, 'reading')
                record.clb_writing = record._tef_to_clb(record.tef_writing, 'writing')
                record.clb_speaking = record._tef_to_clb(record.tef_speaking, 'speaking')
            elif record.test_type == 'tcf_canada':
                record.clb_listening = record._tcf_to_clb(record.tcf_listening, 'listening')
                record.clb_reading = record._tcf_to_clb(record.tcf_reading, 'reading')
                record.clb_writing = record._tcf_to_clb(record.tcf_writing, 'writing')
                record.clb_speaking = record._tcf_to_clb(record.tcf_speaking, 'speaking')
            else:
                record.clb_listening = 0
                record.clb_reading = 0
                record.clb_writing = 0
                record.clb_speaking = 0

            # Calculate average and minimum
            clb_scores = [
                record.clb_listening,
                record.clb_reading,
                record.clb_writing,
                record.clb_speaking,
            ]
            non_zero_scores = [s for s in clb_scores if s > 0]
            if non_zero_scores:
                record.clb_average = sum(non_zero_scores) / len(non_zero_scores)
                record.clb_minimum = min(non_zero_scores)
            else:
                record.clb_average = 0.0
                record.clb_minimum = 0

    def _ielts_to_clb(self, score, ability):
        """Convert IELTS score to CLB level."""
        if not score:
            return 0

        # IELTS to CLB conversion tables (General Training)
        # Different tables for reading vs. other abilities
        if ability == 'reading':
            conversion = [
                (8.0, 10), (7.0, 9), (6.5, 8), (6.0, 7),
                (5.0, 6), (4.0, 5), (3.5, 4),
            ]
        else:  # listening, writing, speaking
            conversion = [
                (8.5, 10), (8.0, 9), (7.5, 8), (7.0, 7),
                (6.0, 6), (5.5, 5), (5.0, 4),
            ]

        for threshold, clb in conversion:
            if score >= threshold:
                return clb
        return 0

    def _tef_to_clb(self, score, ability):
        """Convert TEF Canada score to CLB level."""
        if not score:
            return 0

        # TEF to CLB conversion tables
        if ability == 'listening':
            # TEF Listening: 0-360
            conversion = [
                (316, 10), (298, 9), (280, 8), (249, 7),
                (217, 6), (181, 5), (145, 4),
            ]
        elif ability == 'reading':
            # TEF Reading: 0-300
            conversion = [
                (263, 10), (248, 9), (233, 8), (207, 7),
                (181, 6), (151, 5), (121, 4),
            ]
        else:  # writing, speaking: 0-450
            conversion = [
                (393, 10), (371, 9), (349, 8), (310, 7),
                (271, 6), (226, 5), (181, 4),
            ]

        for threshold, clb in conversion:
            if score >= threshold:
                return clb
        return 0

    def _tcf_to_clb(self, score, ability):
        """Convert TCF Canada score to CLB level."""
        if not score:
            return 0

        # TCF to CLB conversion tables
        if ability in ('listening', 'reading'):
            # TCF Listening/Reading: 0-699
            conversion = [
                (549, 10), (523, 9), (503, 8), (458, 7),
                (406, 6), (331, 5), (331, 4),
            ]
        else:  # writing, speaking: 0-20
            conversion = [
                (16, 10), (14, 9), (12, 8), (10, 7),
                (7, 6), (6, 5), (4, 4),
            ]

        for threshold, clb in conversion:
            if score >= threshold:
                return clb
        return 0

    @api.onchange('language')
    def _onchange_language(self):
        """Clear test type when language changes."""
        if self.language == 'english':
            if self.test_type and 'tef' in self.test_type or 'tcf' in self.test_type:
                self.test_type = False
        elif self.language == 'french':
            if self.test_type and 'ielts' in self.test_type or 'celpip' in self.test_type:
                self.test_type = False

    @api.constrains('is_first_official', 'profile_id', 'language')
    def _check_single_first_official(self):
        """Ensure only one language can be first official per profile."""
        for record in self:
            if record.is_first_official:
                other_first = self.search([
                    ('profile_id', '=', record.profile_id.id),
                    ('is_first_official', '=', True),
                    ('id', '!=', record.id),
                ], limit=1)
                if other_first:
                    raise ValidationError(_(
                        "Only one language can be marked as first official language. "
                        "Please unmark '%s' first.",
                        other_first.name
                    ))

    @api.constrains('test_type', 'language')
    def _check_test_language_match(self):
        """Ensure test type matches language."""
        english_tests = ['ielts_general', 'celpip_general']
        french_tests = ['tef_canada', 'tcf_canada']

        for record in self:
            if record.test_type == 'none':
                continue
            if record.language == 'english' and record.test_type not in english_tests:
                raise ValidationError(_(
                    "Please select an English test (IELTS or CELPIP) for English language."
                ))
            if record.language == 'french' and record.test_type not in french_tests:
                raise ValidationError(_(
                    "Please select a French test (TEF or TCF) for French language."
                ))

    @api.constrains('ielts_listening', 'ielts_reading', 'ielts_writing', 'ielts_speaking')
    def _check_ielts_scores(self):
        """Validate IELTS score ranges."""
        for record in self:
            if record.test_type != 'ielts_general':
                continue
            for field_name in ['ielts_listening', 'ielts_reading', 'ielts_writing', 'ielts_speaking']:
                score = getattr(record, field_name)
                if score and (score < 0 or score > 9):
                    raise ValidationError(_(
                        "IELTS scores must be between 0 and 9."
                    ))

    @api.constrains('celpip_listening', 'celpip_reading', 'celpip_writing', 'celpip_speaking')
    def _check_celpip_scores(self):
        """Validate CELPIP score ranges."""
        for record in self:
            if record.test_type != 'celpip_general':
                continue
            for field_name in ['celpip_listening', 'celpip_reading', 'celpip_writing', 'celpip_speaking']:
                score = getattr(record, field_name)
                if score and (score < 1 or score > 12):
                    raise ValidationError(_(
                        "CELPIP scores must be between 1 and 12."
                    ))
