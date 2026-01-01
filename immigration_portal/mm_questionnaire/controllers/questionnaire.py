# -*- coding: utf-8 -*-

import json
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import AccessError, MissingError, ValidationError


class QuestionnairePortal(http.Controller):
    """Controller for questionnaire portal pages and AJAX endpoints."""

    # =====================
    # Helper Methods
    # =====================

    def _get_case_for_partner(self, case_id=None):
        """Get case(s) for current partner. Optionally filter by case_id."""
        partner = request.env.user.partner_id
        domain = [('partner_id', '=', partner.id)]
        if case_id:
            domain.append(('id', '=', case_id))
        cases = request.env['mm.immigration.case'].sudo().search(domain)
        return cases

    def _check_case_access(self, case_id):
        """Verify current user has access to the case."""
        case = self._get_case_for_partner(case_id)
        if not case:
            raise AccessError(_("You do not have access to this case."))
        return case

    def _get_or_create_response(self, case, questionnaire_type):
        """Get existing questionnaire response or create new one."""
        Response = request.env['mm.questionnaire.response'].sudo()
        response = Response.search([
            ('case_id', '=', case.id),
            ('questionnaire_type', '=', questionnaire_type),
        ], limit=1)

        if not response:
            response = Response.create({
                'case_id': case.id,
                'questionnaire_type': questionnaire_type,
            })

        return response

    def _get_profile(self, case):
        """Get client profile for a case."""
        return case.profile_id

    def _get_section_config(self, questionnaire_type):
        """Get section configuration for a questionnaire type."""
        if questionnaire_type == 'pre_consultation':
            return {
                1: {'name': 'Personal Information', 'code': 'personal'},
                2: {'name': 'Immigration Intent', 'code': 'intent'},
                3: {'name': 'Education', 'code': 'education'},
                4: {'name': 'Work Experience', 'code': 'work'},
                5: {'name': 'Language Ability', 'code': 'language'},
                6: {'name': 'Canada Connections', 'code': 'canada'},
                7: {'name': 'Financial & Risk', 'code': 'financial'},
            }
        elif questionnaire_type == 'detailed_assessment':
            return {
                1: {'name': 'Principal Applicant Details', 'code': 'principal'},
                2: {'name': 'Spouse/Partner Details', 'code': 'spouse'},
                3: {'name': 'Dependent Children', 'code': 'children'},
                4: {'name': 'Education Details', 'code': 'education'},
                5: {'name': 'Work Experience', 'code': 'experience'},
                6: {'name': 'Language Proficiency', 'code': 'language'},
                7: {'name': 'Settlement Funds', 'code': 'funds'},
            }
        return {}

    def _get_portal_settings(self):
        """Get portal branding settings."""
        settings = request.env['mm.immigration.settings'].sudo()
        return settings.get_all_settings()

    # =====================
    # Main Questionnaire Routes
    # =====================

    @http.route(
        '/my/immigration/questionnaire/<string:qtype>',
        type='http', auth='user', website=True
    )
    def questionnaire_start(self, qtype, case_id=None, **kw):
        """Questionnaire landing page - redirects to first incomplete section."""
        # Validate questionnaire type
        if qtype not in ('pre', 'detailed'):
            return request.redirect('/my/immigration')

        questionnaire_type = 'pre_consultation' if qtype == 'pre' else 'detailed_assessment'

        # Get case - if case_id provided use that, otherwise get first available
        if case_id:
            case = self._check_case_access(int(case_id))
        else:
            cases = self._get_case_for_partner()
            if not cases:
                return request.redirect('/my/immigration')
            case = cases[0]

        # Check if questionnaire is already completed - show completion page
        if questionnaire_type == 'pre_consultation' and case.q1_state == 'completed':
            return request.render('mm_questionnaire.questionnaire_completed', {
                'case': case,
                'qtype': 'pre',
                'questionnaire_type': 'pre_consultation',
                'questionnaire_name': 'Pre-Consultation Questionnaire',
            })
        if questionnaire_type == 'detailed_assessment' and case.q2_state == 'completed':
            return request.render('mm_questionnaire.questionnaire_completed', {
                'case': case,
                'qtype': 'detailed',
                'questionnaire_type': 'detailed_assessment',
                'questionnaire_name': 'Detailed Assessment',
            })

        # Check if questionnaire is available for this stage
        if questionnaire_type == 'pre_consultation' and not case.can_start_q1:
            return request.redirect(f'/my/immigration/case/{case.id}')
        if questionnaire_type == 'detailed_assessment' and not case.can_start_q2:
            return request.redirect(f'/my/immigration/case/{case.id}')

        # Get or create response
        response = self._get_or_create_response(case, questionnaire_type)

        # Find first incomplete section
        section = response.current_section
        for i in range(1, response.total_sections + 1):
            if not response.is_section_complete(i):
                section = i
                break

        return request.redirect(
            f'/my/immigration/questionnaire/{qtype}/section/{section}?case_id={case.id}'
        )

    @http.route(
        '/my/immigration/questionnaire/<string:qtype>/section/<int:section>',
        type='http', auth='user', website=True
    )
    def questionnaire_section(self, qtype, section, case_id=None, **kw):
        """Render a specific questionnaire section."""
        # Validate
        if qtype not in ('pre', 'detailed'):
            return request.redirect('/my/immigration')

        questionnaire_type = 'pre_consultation' if qtype == 'pre' else 'detailed_assessment'

        # Get case
        if not case_id:
            return request.redirect('/my/immigration')
        case = self._check_case_access(int(case_id))

        # Get response and profile
        response = self._get_or_create_response(case, questionnaire_type)
        profile = self._get_profile(case)

        # Mark as started if not already
        if response.state == 'not_started':
            response.action_start()

        # Update current section
        if response.current_section != section:
            response.sudo().write({'current_section': section})

        # Get section config
        section_config = self._get_section_config(questionnaire_type)
        if section not in section_config:
            return request.redirect(f'/my/immigration/questionnaire/{qtype}?case_id={case.id}')

        current_section_info = section_config[section]
        settings = self._get_portal_settings()

        # Get countries for dropdowns
        countries = request.env['res.country'].sudo().search([], order='name')
        canada_provinces = request.env['res.country.state'].sudo().search([
            ('country_id.code', '=', 'CA')
        ], order='name')

        # Build values for template
        values = {
            'page_name': 'questionnaire',
            'case': case,
            'profile': profile,
            'response': response,
            'questionnaire_type': questionnaire_type,
            'qtype': qtype,
            'section': section,
            'section_name': current_section_info['name'],
            'section_code': current_section_info['code'],
            'total_sections': response.total_sections,
            'section_config': section_config,
            'completed_sections': response.get_completed_sections(),
            'settings': settings,
            'countries': countries,
            'canada_provinces': canada_provinces,
            # For conditional sections
            'show_spouse_section': profile.marital_status in ('married', 'common_law'),
            'show_children_section': profile.has_children,
        }

        # Determine template based on questionnaire type and section
        template = f'mm_questionnaire.questionnaire_{qtype}_section_{section}'

        return request.render(template, values)

    @http.route(
        '/my/immigration/questionnaire/<string:qtype>/review',
        type='http', auth='user', website=True
    )
    def questionnaire_review(self, qtype, case_id=None, **kw):
        """Review page before final submission."""
        if qtype not in ('pre', 'detailed'):
            return request.redirect('/my/immigration')

        questionnaire_type = 'pre_consultation' if qtype == 'pre' else 'detailed_assessment'

        if not case_id:
            return request.redirect('/my/immigration')
        case = self._check_case_access(int(case_id))

        response = self._get_or_create_response(case, questionnaire_type)
        profile = self._get_profile(case)
        settings = self._get_portal_settings()
        section_config = self._get_section_config(questionnaire_type)

        values = {
            'page_name': 'questionnaire_review',
            'case': case,
            'profile': profile,
            'response': response,
            'questionnaire_type': questionnaire_type,
            'qtype': qtype,
            'section_config': section_config,
            'completed_sections': response.get_completed_sections(),
            'total_sections': response.total_sections,
            'settings': settings,
        }

        return request.render('mm_questionnaire.questionnaire_review', values)

    # =====================
    # AJAX Endpoints
    # =====================

    @http.route(
        '/my/immigration/questionnaire/save',
        type='jsonrpc', auth='user', methods=['POST']
    )
    def save_field(self, case_id, field_name, field_value, model='profile', **kw):
        """AJAX endpoint to save a single field value."""
        case = self._check_case_access(int(case_id))

        # Determine target model
        if model == 'profile':
            target = case.profile_id.sudo()
        elif model == 'case':
            target = case.sudo()
        else:
            return {'success': False, 'error': 'Invalid model'}

        # Check field exists on model
        if field_name not in target._fields:
            return {'success': False, 'error': f'Field {field_name} not found'}

        try:
            # Handle special field types
            field_def = target._fields[field_name]

            if field_def.type == 'many2one':
                field_value = int(field_value) if field_value else False
            elif field_def.type == 'boolean':
                field_value = field_value in ('true', 'True', True, 1, '1')
            elif field_def.type == 'integer':
                field_value = int(field_value) if field_value else 0
            elif field_def.type == 'float':
                field_value = float(field_value) if field_value else 0.0
            elif field_def.type == 'date':
                # Expect YYYY-MM-DD format
                field_value = field_value if field_value else False

            target.write({field_name: field_value})

            # Update response timestamp
            response = self._get_questionnaire_response(case, kw.get('qtype'))
            if response:
                response.action_save_progress()

            return {'success': True, 'saved_at': fields.Datetime.now().isoformat()}

        except (ValueError, ValidationError) as e:
            return {'success': False, 'error': str(e)}

    def _get_questionnaire_response(self, case, qtype):
        """Helper to get questionnaire response by type code."""
        if not qtype:
            return None
        questionnaire_type = 'pre_consultation' if qtype == 'pre' else 'detailed_assessment'
        return request.env['mm.questionnaire.response'].sudo().search([
            ('case_id', '=', case.id),
            ('questionnaire_type', '=', questionnaire_type),
        ], limit=1)

    @http.route(
        '/my/immigration/questionnaire/complete-section',
        type='jsonrpc', auth='user', methods=['POST']
    )
    def complete_section(self, case_id, qtype, section, **kw):
        """AJAX endpoint to mark a section as complete."""
        case = self._check_case_access(int(case_id))
        questionnaire_type = 'pre_consultation' if qtype == 'pre' else 'detailed_assessment'

        response = request.env['mm.questionnaire.response'].sudo().search([
            ('case_id', '=', case.id),
            ('questionnaire_type', '=', questionnaire_type),
        ], limit=1)

        if response:
            response.mark_section_complete(int(section))
            return {
                'success': True,
                'progress': response.progress_percent,
                'next_section': min(int(section) + 1, response.total_sections),
            }

        return {'success': False, 'error': 'Response not found'}

    @http.route(
        '/my/immigration/questionnaire/submit',
        type='jsonrpc', auth='user', methods=['POST']
    )
    def submit_questionnaire(self, case_id, qtype, **kw):
        """AJAX endpoint to submit the complete questionnaire."""
        case = self._check_case_access(int(case_id))
        questionnaire_type = 'pre_consultation' if qtype == 'pre' else 'detailed_assessment'

        response = request.env['mm.questionnaire.response'].sudo().search([
            ('case_id', '=', case.id),
            ('questionnaire_type', '=', questionnaire_type),
        ], limit=1)

        if not response:
            return {'success': False, 'error': 'Response not found'}

        # Validate required sections
        # For now, allow submission if at least 50% complete
        if response.progress_percent < 50:
            return {
                'success': False,
                'error': 'Please complete at least 50% of the questionnaire before submitting.'
            }

        response.action_complete()
        
        # Redirect to completion page based on questionnaire type
        if questionnaire_type == 'pre_consultation':
            redirect_url = f'/my/immigration/questionnaire/pre?case_id={case.id}'
        else:
            redirect_url = f'/my/immigration/questionnaire/detailed?case_id={case.id}'

        return {
            'success': True,
            'redirect_url': redirect_url,
            'message': 'Questionnaire submitted successfully!',
        }

    # =====================
    # Repeater AJAX Endpoints
    # =====================

    @http.route(
        '/my/immigration/questionnaire/add-education',
        type='jsonrpc', auth='user', methods=['POST']
    )
    def add_education(self, case_id, **kw):
        """AJAX endpoint to add a new education record."""
        case = self._check_case_access(int(case_id))
        profile = case.profile_id

        try:
            education = request.env['mm.education.record'].sudo().create({
                'profile_id': profile.id,
                'institution_name': kw.get('institution_name', ''),
                'institution_country_id': int(kw.get('institution_country_id')) if kw.get('institution_country_id') else False,
                'credential_type': kw.get('credential_type', 'bachelors'),
                'field_of_study': kw.get('field_of_study', ''),
            })

            return {
                'success': True,
                'id': education.id,
                'name': education.name,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(
        '/my/immigration/questionnaire/update-education',
        type='jsonrpc', auth='user', methods=['POST']
    )
    def update_education(self, case_id, education_id, **kw):
        """AJAX endpoint to update an education record."""
        case = self._check_case_access(int(case_id))
        profile = case.profile_id

        education = request.env['mm.education.record'].sudo().browse(int(education_id))
        if education.profile_id.id != profile.id:
            return {'success': False, 'error': 'Access denied'}

        try:
            vals = {}
            field_mapping = {
                'institution_name': str,
                'institution_country_id': lambda x: int(x) if x else False,
                'institution_city': str,
                'credential_type': str,
                'field_of_study': str,
                'start_date': str,
                'end_date': str,
                'is_completed': lambda x: x in ('true', 'True', True, 1, '1'),
                'was_full_time': lambda x: x in ('true', 'True', True, 1, '1'),
                'eca_status': str,
                'eca_organization': str,
                'eca_reference': str,
                'is_primary_credential': lambda x: x in ('true', 'True', True, 1, '1'),
            }

            for field, converter in field_mapping.items():
                if field in kw:
                    vals[field] = converter(kw[field]) if kw[field] else False

            if vals:
                education.write(vals)

            return {'success': True, 'name': education.name}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(
        '/my/immigration/questionnaire/delete-education',
        type='jsonrpc', auth='user', methods=['POST']
    )
    def delete_education(self, case_id, education_id, **kw):
        """AJAX endpoint to delete an education record."""
        case = self._check_case_access(int(case_id))
        profile = case.profile_id

        education = request.env['mm.education.record'].sudo().browse(int(education_id))
        if education.profile_id.id != profile.id:
            return {'success': False, 'error': 'Access denied'}

        education.unlink()
        return {'success': True}

    @http.route(
        '/my/immigration/questionnaire/add-experience',
        type='jsonrpc', auth='user', methods=['POST']
    )
    def add_experience(self, case_id, **kw):
        """AJAX endpoint to add a new work experience record."""
        case = self._check_case_access(int(case_id))
        profile = case.profile_id

        try:
            experience = request.env['mm.work.experience'].sudo().create({
                'profile_id': profile.id,
                'employer_name': kw.get('employer_name', ''),
                'employer_country_id': int(kw.get('employer_country_id')) if kw.get('employer_country_id') else False,
                'job_title': kw.get('job_title', ''),
                'start_date': kw.get('start_date') or fields.Date.today(),
            })

            return {
                'success': True,
                'id': experience.id,
                'name': experience.name,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(
        '/my/immigration/questionnaire/update-experience',
        type='jsonrpc', auth='user', methods=['POST']
    )
    def update_experience(self, case_id, experience_id, **kw):
        """AJAX endpoint to update a work experience record."""
        case = self._check_case_access(int(case_id))
        profile = case.profile_id

        experience = request.env['mm.work.experience'].sudo().browse(int(experience_id))
        if experience.profile_id.id != profile.id:
            return {'success': False, 'error': 'Access denied'}

        try:
            vals = {}
            field_mapping = {
                'employer_name': str,
                'employer_country_id': lambda x: int(x) if x else False,
                'employer_city': str,
                'job_title': str,
                'noc_code': str,
                'noc_teer_category': str,
                'start_date': str,
                'end_date': str,
                'is_current': lambda x: x in ('true', 'True', True, 1, '1'),
                'hours_per_week': lambda x: float(x) if x else 40.0,
                'is_paid': lambda x: x in ('true', 'True', True, 1, '1'),
                'is_self_employed': lambda x: x in ('true', 'True', True, 1, '1'),
                'main_duties': str,
            }

            for field, converter in field_mapping.items():
                if field in kw:
                    vals[field] = converter(kw[field]) if kw[field] else False

            if vals:
                experience.write(vals)

            return {'success': True, 'name': experience.name}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(
        '/my/immigration/questionnaire/delete-experience',
        type='jsonrpc', auth='user', methods=['POST']
    )
    def delete_experience(self, case_id, experience_id, **kw):
        """AJAX endpoint to delete a work experience record."""
        case = self._check_case_access(int(case_id))
        profile = case.profile_id

        experience = request.env['mm.work.experience'].sudo().browse(int(experience_id))
        if experience.profile_id.id != profile.id:
            return {'success': False, 'error': 'Access denied'}

        experience.unlink()
        return {'success': True}

    @http.route(
        '/my/immigration/questionnaire/add-child',
        type='jsonrpc', auth='user', methods=['POST']
    )
    def add_child(self, case_id, **kw):
        """AJAX endpoint to add a new dependent child."""
        case = self._check_case_access(int(case_id))
        profile = case.profile_id

        try:
            child = request.env['mm.dependent.child'].sudo().create({
                'profile_id': profile.id,
                'name': kw.get('name', 'Child'),
                'date_of_birth': kw.get('date_of_birth') or fields.Date.today(),
            })

            # Ensure has_children is True
            if not profile.has_children:
                profile.sudo().write({'has_children': True})

            return {
                'success': True,
                'id': child.id,
                'name': child.name,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(
        '/my/immigration/questionnaire/update-child',
        type='jsonrpc', auth='user', methods=['POST']
    )
    def update_child(self, case_id, child_id, **kw):
        """AJAX endpoint to update a dependent child."""
        case = self._check_case_access(int(case_id))
        profile = case.profile_id

        child = request.env['mm.dependent.child'].sudo().browse(int(child_id))
        if child.profile_id.id != profile.id:
            return {'success': False, 'error': 'Access denied'}

        try:
            vals = {}
            if 'name' in kw:
                vals['name'] = kw['name']
            if 'date_of_birth' in kw:
                vals['date_of_birth'] = kw['date_of_birth'] or False
            if 'country_id' in kw:
                vals['country_id'] = int(kw['country_id']) if kw['country_id'] else False
            if 'is_accompanying' in kw:
                vals['is_accompanying'] = kw['is_accompanying'] in ('true', 'True', True, 1, '1')
            if 'notes' in kw:
                vals['notes'] = kw['notes']

            if vals:
                child.write(vals)

            return {'success': True, 'name': child.name}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(
        '/my/immigration/questionnaire/delete-child',
        type='jsonrpc', auth='user', methods=['POST']
    )
    def delete_child(self, case_id, child_id, **kw):
        """AJAX endpoint to delete a dependent child."""
        case = self._check_case_access(int(case_id))
        profile = case.profile_id

        child = request.env['mm.dependent.child'].sudo().browse(int(child_id))
        if child.profile_id.id != profile.id:
            return {'success': False, 'error': 'Access denied'}

        child.unlink()

        # Update has_children if no children left
        if not profile.children_ids:
            profile.sudo().write({'has_children': False})

        return {'success': True}

    @http.route(
        '/my/immigration/questionnaire/add-language',
        type='jsonrpc', auth='user', methods=['POST']
    )
    def add_language(self, case_id, **kw):
        """AJAX endpoint to add a new language proficiency record."""
        case = self._check_case_access(int(case_id))
        profile = case.profile_id

        try:
            language = request.env['mm.language.proficiency'].sudo().create({
                'profile_id': profile.id,
                'language': kw.get('language', 'english'),
                'test_type': kw.get('test_type', 'none'),
            })

            return {
                'success': True,
                'id': language.id,
                'name': language.name,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(
        '/my/immigration/questionnaire/update-language',
        type='jsonrpc', auth='user', methods=['POST']
    )
    def update_language(self, case_id, language_id, **kw):
        """AJAX endpoint to update a language proficiency record."""
        case = self._check_case_access(int(case_id))
        profile = case.profile_id

        lang_record = request.env['mm.language.proficiency'].sudo().browse(int(language_id))
        if lang_record.profile_id.id != profile.id:
            return {'success': False, 'error': 'Access denied'}

        try:
            vals = {}
            # Map fields to converters
            string_fields = ['test_type', 'language', 'test_report_number']
            bool_fields = ['is_first_official']
            int_fields = [
                'celpip_listening', 'celpip_reading', 'celpip_writing', 'celpip_speaking',
                'tef_listening', 'tef_reading', 'tef_writing', 'tef_speaking',
                'tcf_listening', 'tcf_reading', 'tcf_writing', 'tcf_speaking',
            ]
            float_fields = [
                'ielts_listening', 'ielts_reading', 'ielts_writing', 'ielts_speaking',
            ]

            for field in string_fields:
                if field in kw:
                    vals[field] = kw[field] or False

            for field in bool_fields:
                if field in kw:
                    vals[field] = kw[field] in ('true', 'True', True, 1, '1')

            for field in int_fields:
                if field in kw:
                    vals[field] = int(kw[field]) if kw[field] else 0

            for field in float_fields:
                if field in kw:
                    vals[field] = float(kw[field]) if kw[field] else 0.0

            if 'test_date' in kw:
                vals['test_date'] = kw['test_date'] or False

            if vals:
                lang_record.write(vals)

            return {
                'success': True,
                'name': lang_record.name,
                'clb_scores': {
                    'listening': lang_record.clb_listening,
                    'reading': lang_record.clb_reading,
                    'writing': lang_record.clb_writing,
                    'speaking': lang_record.clb_speaking,
                    'minimum': lang_record.clb_minimum,
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(
        '/my/immigration/questionnaire/delete-language',
        type='jsonrpc', auth='user', methods=['POST']
    )
    def delete_language(self, case_id, language_id, **kw):
        """AJAX endpoint to delete a language proficiency record."""
        case = self._check_case_access(int(case_id))
        profile = case.profile_id

        lang_record = request.env['mm.language.proficiency'].sudo().browse(int(language_id))
        if lang_record.profile_id.id != profile.id:
            return {'success': False, 'error': 'Access denied'}

        lang_record.unlink()
        return {'success': True}
