# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import models, fields, tools, api, exceptions, _


class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    attendance_partner_id              = fields.Many2one('res.partner', string="Payroll", related="company_id.attendance_partner_id")
    attendance_partner_kesehatan       = fields.Many2one('res.partner', string="BPJS Kesehatan", related="company_id.attendance_partner_kesehatan")
    attendance_partner_ketenagakerjaan = fields.Many2one('res.partner', string="BPJS Ketenagakerjaan", related="company_id.attendance_partner_ketenagakerjaan")
    attendance_partner_pensiun         = fields.Many2one('res.partner', string="BPJS Pensiun", related="company_id.attendance_partner_pensiun")
    attendance_partner_keselamatan     = fields.Many2one('res.partner', string="JKK + JKM", related="company_id.attendance_partner_keselamatan")

    @api.model
    def default_get(self, fields):
        settings    = super(BaseConfigSettings, self).default_get(fields)
        company     = self.env.user.company_id
        settings['attendance_partner_id']               = company.attendance_partner_id and company.attendance_partner_id.id or False
        settings['attendance_partner_kesehatan']        = company.attendance_partner_kesehatan and company.attendance_partner_kesehatan.id or False
        settings['attendance_partner_ketenagakerjaan']  = company.attendance_partner_ketenagakerjaan and company.attendance_partner_ketenagakerjaan.id or False
        settings['attendance_partner_pensiun']          = company.attendance_partner_pensiun and company.attendance_partner_pensiun.id or False
        settings['attendance_partner_keselamatan']      = company.attendance_partner_keselamatan and company.attendance_partner_keselamatan.id or False
        return settings