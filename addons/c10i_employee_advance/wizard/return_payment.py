# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
import time
import datetime
from dateutil.relativedelta import relativedelta

from odoo import models, fields, tools, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
import odoo.addons.decimal_precision as dp

class SettlementReturnPayment(models.TransientModel):
    _name           = "settlement.return.payment"
    _description    = "Create Return Payment"

    employee_id = fields.Many2one('hr.employee', 'Employee')
    return_amount_total = fields.Float('Return Amount', digits=dp.get_precision('Account'))
    journal_id = fields.Many2one('account.journal', 'Payment Journal', domain="[('type','in',['cash','bank'])]", required=True)
    payment_date = fields.Date('Payment Date', required=True)

    @api.model
    def default_get(self, fields):
        settlement_datas = self.env['account.settlement.advance'].browse(self._context.get('active_id'))
        result = super(SettlementReturnPayment, self).default_get(fields)
        if settlement_datas:
            if 'employee_id' in fields:
                result['employee_id'] = settlement_datas[-1].employee_id.id
            if 'payment_date' in fields:
                result['payment_date'] = settlement_datas[-1].date
            if 'return_amount_total' in fields:
                result['return_amount_total'] = settlement_datas[-1].return_amount_total
        return result

    @api.multi
    def create_payment(self):
        self.ensure_one()
        settlement_datas = self.env['account.settlement.advance'].browse(self._context.get('active_id'))
        voucher_ids = settlement_datas.action_create_return_payment(self.payment_date, self.journal_id.id)
        
        if self.return_amount_total < 0:
            action = self.env.ref('account_voucher.action_purchase_receipt').read()[0]
        else:
            action = self.env.ref('account_voucher.action_sale_receipt').read()[0]
        action['domain'] = [('id', 'in', voucher_ids)]
        return action