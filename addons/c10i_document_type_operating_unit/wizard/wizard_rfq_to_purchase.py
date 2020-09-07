# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################


import time
import datetime
from odoo import api, fields, models, SUPERUSER_ID, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError

class WizardRfqToPurchase(models.TransientModel):
    _inherit	    = "wizard.rfq.to.purchase"
    _description 	= "RFQ To Purchase Order"

    @api.multi
    def create_purchase(self):
        ctx = self.env.context.copy()
        ctx.update({'doc_type_id' : self.doc_type_id.id})
        result      = super(WizardRfqToPurchase, self.with_context(ctx)).create_purchase()
        return result
