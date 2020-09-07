# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import api, fields, models

class ResCompany(models.Model):
    _description    = "Company"
    _inherit        = 'res.company'

    has_office          = fields.Boolean("Has Head Office")
    partner_office_id   = fields.Many2one(comodel_name="res.partner", string="Head Office")