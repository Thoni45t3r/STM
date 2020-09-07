# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
from openerp import models, fields, api, _
from odoo.addons.jasper_reports import JasperDataParser
from odoo.addons.jasper_reports import jasper_report
import time

class wizard_general_ledger_account(models.TransientModel):
    _inherit        = "wizard.general.ledger.account"

    operating_unit_ids = fields.Many2many('operating.unit', 'wizard_gl_ou_rel', 'wizard_id', 'operating_unit_id', 
                        required=False, string="Operating Unit", default=lambda self:
                        self.env['res.users'].operating_unit_default_get(self._uid))
    
wizard_general_ledger_account()