# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import api, fields, models, _
from odoo.exceptions import except_orm, Warning, RedirectWarning, ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def create_downpayment(self):
        downpayment = super(SaleOrder, self.sudo()).create_downpayment()
        self.advance_invoice_id.sudo().operating_unit_id = self.env.user.default_operating_unit_id.id
        return downpayment