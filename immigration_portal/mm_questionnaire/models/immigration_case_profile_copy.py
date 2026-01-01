# -*- coding: utf-8 -*-
"""
Immigration Case Extension - Profile Copy Functionality
Phase 6 Enhancement

When a new case is created for a client who already has a completed profile
from another case, copy the existing profile data so the client can review
and confirm rather than re-entering everything.

This provides a better UX - clients confirm/update existing data instead of
starting from scratch for each new case.
"""

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class ImmigrationCaseProfileCopy(models.Model):
    """Extend immigration case to copy profile data from existing cases."""
    
    _inherit = 'mm.immigration.case'
    
    # Track if profile was copied from another case
    profile_copied_from_id = fields.Many2one(
        'mm.client.profile',
        string='Profile Copied From',
        readonly=True,
        copy=False,
        help='If set, indicates this profile was pre-populated from an existing profile.',
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to copy profile data from existing client profiles."""
        cases = super().create(vals_list)
        
        for case in cases:
            if case.profile_id and case.partner_id:
                # Find existing profiles for this partner (from other cases)
                existing_profile = self._find_existing_profile(case)
                
                if existing_profile:
                    # Copy profile data
                    self._copy_profile_data(existing_profile, case.profile_id)
                    
                    # Track that we copied from this profile
                    case.profile_copied_from_id = existing_profile.id
                    
                    # Log the copy action
                    case.message_post(
                        body=_("Profile data pre-populated from existing case. "
                               "Client can review and update as needed."),
                        message_type='notification',
                    )
                    _logger.info(
                        "Copied profile data from profile %s to new profile %s for partner %s",
                        existing_profile.id, case.profile_id.id, case.partner_id.id
                    )
        
        return cases
    
    def _find_existing_profile(self, new_case):
        """
        Find an existing completed profile for the same partner.
        
        Prioritizes:
        1. Most recently completed profile (has questionnaire data)
        2. Profile with most data filled in
        """
        Profile = self.env['mm.client.profile']
        
        # Find all profiles for this partner (excluding the new one)
        existing_profiles = Profile.search([
            ('partner_id', '=', new_case.partner_id.id),
            ('id', '!=', new_case.profile_id.id),
        ], order='write_date desc')
        
        if not existing_profiles:
            return False
        
        # Find profile with the most complete data
        # Prioritize profiles that have core fields filled
        best_profile = False
        best_score = 0
        
        for profile in existing_profiles:
            score = self._calculate_profile_completeness(profile)
            if score > best_score:
                best_score = score
                best_profile = profile
        
        # Only copy if the profile has meaningful data (score > 5)
        if best_score > 5:
            return best_profile
        
        return False
    
    def _calculate_profile_completeness(self, profile):
        """
        Calculate a completeness score for a profile.
        Higher score = more data filled in.
        """
        score = 0
        
        # Core personal fields (1 point each)
        if profile.legal_first_name:
            score += 1
        if profile.legal_last_name:
            score += 1
        if profile.date_of_birth:
            score += 1
        if profile.citizenship_country_id:
            score += 1
        if profile.residence_country_id:
            score += 1
        if profile.marital_status:
            score += 1
        
        # Immigration intent (2 points each - important data)
        if profile.immigration_goal:
            score += 2
        if profile.target_year:
            score += 2
        
        # Education (3 points - complex data)
        if profile.highest_education:
            score += 2
        if profile.education_ids:
            score += 3
        
        # Work experience (3 points - complex data)
        if profile.experience_ids:
            score += 3
        
        # Language (3 points - complex data)
        if profile.language_ids:
            score += 3
        if profile.first_language:
            score += 1
        
        # Financial
        if profile.settlement_funds:
            score += 2
        
        # Canada connections
        if profile.family_in_canada_relationship:
            score += 1
        
        return score
    
    def _copy_profile_data(self, source_profile, target_profile):
        """
        Copy data from source profile to target profile.
        
        Copies:
        - All scalar fields (Char, Text, Date, Selection, Boolean, Integer, Float)
        - Many2one fields
        - One2many records (creates copies)
        
        Does NOT copy:
        - ID fields
        - Case-specific links
        - Computed fields (they'll recompute automatically)
        """
        # Fields to skip (either computed, case-specific, or shouldn't be copied)
        skip_fields = {
            'id', 'create_date', 'create_uid', 'write_date', 'write_uid',
            '__last_update', 'display_name', 'name',
            'case_id', 'partner_id',  # These are set by the new case
            # Computed fields - will be recomputed
            'age', 'spouse_age', 'education_count', 'experience_count',
            'language_count', 'total_skilled_experience_years',
            'total_canadian_experience_months', 'primary_education_level',
            'english_clb_minimum', 'french_clb_minimum',
        }
        
        # One2many fields to copy (we'll handle these specially)
        one2many_fields = {
            'education_ids': 'mm.education.record',
            'experience_ids': 'mm.work.experience',
            'language_ids': 'mm.language.proficiency',
            'children_ids': 'mm.dependent.child',
        }
        
        # Build vals dict for scalar/many2one fields
        vals = {}
        
        for field_name, field_obj in source_profile._fields.items():
            # Skip excluded fields
            if field_name in skip_fields:
                continue
            
            # Skip One2many (handled separately)
            if field_name in one2many_fields:
                continue
            
            # Skip computed fields without store
            if getattr(field_obj, 'compute', None) and not getattr(field_obj, 'store', False):
                continue
            
            # Get the value from source
            value = source_profile[field_name]
            
            # Handle different field types
            if field_obj.type == 'many2one':
                vals[field_name] = value.id if value else False
            elif field_obj.type == 'many2many':
                vals[field_name] = [(6, 0, value.ids)] if value else [(5, 0, 0)]
            elif field_obj.type in ('char', 'text', 'html', 'selection', 'date', 
                                     'datetime', 'boolean', 'integer', 'float', 
                                     'monetary', 'binary'):
                vals[field_name] = value
        
        # Write scalar fields to target
        if vals:
            target_profile.write(vals)
        
        # Copy One2many records
        for field_name, model_name in one2many_fields.items():
            source_records = source_profile[field_name]
            if source_records:
                self._copy_one2many_records(source_records, target_profile, field_name)
    
    def _copy_one2many_records(self, source_records, target_profile, field_name):
        """
        Copy One2many records from source to target profile.
        Creates new records linked to the target profile.
        """
        # Fields to skip when copying records
        skip_fields = {
            'id', 'create_date', 'create_uid', 'write_date', 'write_uid',
            '__last_update', 'display_name', 'profile_id',
        }
        
        for source_record in source_records:
            vals = {}
            
            for field_name_inner, field_obj in source_record._fields.items():
                # Skip excluded fields
                if field_name_inner in skip_fields:
                    continue
                
                # Skip computed fields without store
                if getattr(field_obj, 'compute', None) and not getattr(field_obj, 'store', False):
                    continue
                
                value = source_record[field_name_inner]
                
                if field_obj.type == 'many2one':
                    vals[field_name_inner] = value.id if value else False
                elif field_obj.type == 'many2many':
                    vals[field_name_inner] = [(6, 0, value.ids)] if value else [(5, 0, 0)]
                elif field_obj.type in ('char', 'text', 'html', 'selection', 'date',
                                         'datetime', 'boolean', 'integer', 'float',
                                         'monetary', 'binary'):
                    vals[field_name_inner] = value
            
            # Set the profile_id to the target profile
            vals['profile_id'] = target_profile.id
            
            # Create the new record
            try:
                source_record.sudo().copy(default={'profile_id': target_profile.id})
            except Exception as e:
                # If copy fails, try create
                _logger.warning(
                    "Could not copy %s record, trying create: %s",
                    source_record._name, str(e)
                )
                try:
                    self.env[source_record._name].create(vals)
                except Exception as e2:
                    _logger.error(
                        "Failed to create %s record: %s",
                        source_record._name, str(e2)
                    )
