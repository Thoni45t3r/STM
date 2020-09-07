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

class ResCompany(models.Model):
    _inherit        = 'res.company'

    work_time_sunday    = fields.Float("Sunday")
    work_time_monday    = fields.Float("Monday")
    work_time_tuesday   = fields.Float("Tuesday")
    work_time_wednesday = fields.Float("Wednesday")
    work_time_thursday  = fields.Float("Thursday")
    work_time_friday    = fields.Float("Friday")
    work_time_saturday  = fields.Float("Saturday")