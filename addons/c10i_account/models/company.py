# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import api, fields, models

class ResCompany(models.Model):
    _inherit        = 'res.company'
    _description    = "Company"

    allow_inverse_currency_rate = fields.Boolean('Allow Inverse Currency Rate')

class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    allow_inverse_currency_rate = fields.Boolean(related='company_id.allow_inverse_currency_rate', string='Allow Inverse Currency Rate')
