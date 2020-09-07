# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
from odoo import models, fields, api, _

class ResPartner(models.Model):
    _inherit        = 'res.partner'
    _description    = 'Res Partner'

    is_pks                          = fields.Boolean('Pabrik Kelapa Sawit')
    account_payable_contractor_id   = fields.Many2one('account.account', 'Account Payable Perantara Buku Kontraktor')