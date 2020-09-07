# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    cal_api_key     = fields.Char("Google API Keys")
    cal_id_google   = fields.Char("CalendarId")
