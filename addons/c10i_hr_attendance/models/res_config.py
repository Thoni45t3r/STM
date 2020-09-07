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

    work_time_sunday    = fields.Float("Sunday", related="company_id.work_time_sunday")
    work_time_monday    = fields.Float("Monday", related="company_id.work_time_monday")
    work_time_tuesday   = fields.Float("Tuesday", related="company_id.work_time_tuesday")
    work_time_wednesday = fields.Float("Wednesday", related="company_id.work_time_wednesday")
    work_time_thursday  = fields.Float("Thursday", related="company_id.work_time_thursday")
    work_time_friday    = fields.Float("Friday", related="company_id.work_time_friday")
    work_time_saturday  = fields.Float("Saturday", related="company_id.work_time_saturday")

    @api.model
    def default_get(self, fields):
        settings    = super(BaseConfigSettings, self).default_get(fields)
        company     = self.env.user.company_id
        settings['work_time_sunday']    = company.work_time_sunday
        settings['work_time_monday']    = company.work_time_monday
        settings['work_time_tuesday']   = company.work_time_tuesday
        settings['work_time_wednesday'] = company.work_time_wednesday
        settings['work_time_thursday']  = company.work_time_thursday
        settings['work_time_friday']    = company.work_time_friday
        settings['work_time_saturday']  = company.work_time_saturday
        return settings