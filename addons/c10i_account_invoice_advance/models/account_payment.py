# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import openerp.addons.decimal_precision as dp
from datetime import datetime

class account_payment(models.Model):
    _name = "account.payment"
    _inherit = ['account.payment', 'mail.thread']

    @api.multi
    def _set_outstanding_lines(self, partner_id, account_id, currency_id, journal_id, payment_date):
        super(account_payment, self)._set_outstanding_lines(partner_id, account_id, currency_id, journal_id, payment_date)
        for payment in self:
            account_type = None
            if self.payment_type == 'outbound':
                account_type = 'payable'
            else:
                account_type = 'receivable'
            new_lines = self.env['account.payment.line']
            #SEARCH FOR MOVE LINE; RECEIVABLE/PAYABLE AND NOT FULL RECONCILED
            if account_id:
                adv_lines = self.env['account.invoice.advance'].search([('account_id','=',account_id.id),('partner_id','=',partner_id.id),('reconciled','=',False)])
            else:
                adv_lines = self.env['account.invoice.advance'].search([('account_id.internal_type','=',account_type),('partner_id','=',partner_id.id),('reconciled','=',False)])

            for adv in adv_lines:
                data = payment._prepare_account_move_line(adv.move_line_id)
                data.update({'invoice_advance_id': adv.id})
                if adv.type=='in_advance':
                    data.update({'name': adv.reference or adv.number,
                                 'origin': adv.origin or ''})
                else:
                    data.update({'name': adv.number,
                                 'origin': adv.origin or ''})
                new_line = new_lines.new(data)
                new_lines += new_line
            payment.register_ids += new_lines

class account_payment_line(models.Model):
    _inherit = 'account.payment.line'

    invoice_advance_id = fields.Many2one('account.invoice.advance', string='Advance')
    