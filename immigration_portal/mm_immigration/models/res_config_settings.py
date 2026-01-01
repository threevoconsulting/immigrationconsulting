# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    immigration_portal_name = fields.Char(
        string='Portal Brand Name',
        config_parameter='mm_immigration.portal_name',
        default='The Migration Monitor',
        help='The brand name displayed in the immigration portal',
    )
    immigration_portal_email = fields.Char(
        string='Portal Contact Email',
        config_parameter='mm_immigration.portal_email',
        help='Contact email displayed in the immigration portal',
    )
    immigration_portal_phone = fields.Char(
        string='Portal Contact Phone',
        config_parameter='mm_immigration.portal_phone',
        help='Contact phone displayed in the immigration portal',
    )
    immigration_portal_website = fields.Char(
        string='Portal Website URL',
        config_parameter='mm_immigration.portal_website',
        help='Website URL displayed in the immigration portal',
    )


class ImmigrationSettings(models.Model):
    """Helper model to retrieve portal settings."""
    _name = 'mm.immigration.settings'
    _description = 'Immigration Portal Settings Helper'

    @api.model
    def get_portal_name(self):
        """Get the configured portal brand name."""
        return self.env['ir.config_parameter'].sudo().get_param(
            'mm_immigration.portal_name',
            default='The Migration Monitor'
        )

    @api.model
    def get_portal_email(self):
        """Get the configured portal contact email."""
        return self.env['ir.config_parameter'].sudo().get_param(
            'mm_immigration.portal_email',
            default=''
        )

    @api.model
    def get_portal_phone(self):
        """Get the configured portal contact phone."""
        return self.env['ir.config_parameter'].sudo().get_param(
            'mm_immigration.portal_phone',
            default=''
        )

    @api.model
    def get_portal_website(self):
        """Get the configured portal website URL."""
        return self.env['ir.config_parameter'].sudo().get_param(
            'mm_immigration.portal_website',
            default=''
        )

    @api.model
    def get_all_settings(self):
        """Get all portal settings as a dictionary."""
        return {
            'portal_name': self.get_portal_name(),
            'portal_email': self.get_portal_email(),
            'portal_phone': self.get_portal_phone(),
            'portal_website': self.get_portal_website(),
        }
