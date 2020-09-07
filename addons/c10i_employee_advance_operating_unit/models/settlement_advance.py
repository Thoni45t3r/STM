# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

import calendar
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools import float_compare, float_is_zero
import odoo.addons.decimal_precision as dp

class AccountSettlementAdvance(models.Model):
    _inherit = 'account.settlement.advance'
    
    operating_unit_id = fields.Many2one('operating.unit', 'Operating Unit',
                                        default=lambda self:
                                        self.env['res.users'].
                                        operating_unit_default_get(self._uid),
                                        readonly=True,
                                        states={'draft': [('readonly',
                                                           False)]})

    @api.multi
    def account_move_get(self):
        move_vals = super(AccountSettlementAdvance, self).account_move_get()
        # move_vals.update({'operating_unit_id': self.operating_unit_id and self.operating_unit_id.id or False}) 
        return move_vals

    @api.multi
    def _prepare_voucher(self, payment_date, journal_id):
        voucher_vals = super(AccountSettlementAdvance, self)._prepare_voucher(payment_date, journal_id)
        voucher_vals.update({'operating_unit_id': self.operating_unit_id and self.operating_unit_id.id or False})
        return voucher_vals

    @api.multi
    def _prepare_return_move_line(self, move):
        move_line_vals = super(AccountSettlementAdvance, self)._prepare_return_move_line(move)
        move_line_vals.update({'operating_unit_id': self.operating_unit_id and self.operating_unit_id.id or False}) 
        return move_line_vals

class SplitSettlementAdvanceLine(models.Model):
    _inherit = 'split.settlement.advance.line'

    def _prepare_expense_split_move_line(self, settlement_line, move):
        move_vals = super(SplitSettlementAdvanceLine, self)._prepare_expense_split_move_line(settlement_line, move)
        if settlement_line.advance_line_id:
            move_vals.update({'operating_unit_id': settlement_line.advance_line_id.operating_unit_id \
                    and settlement_line.advance_line_id.operating_unit_id.id or False})
        else:
            move_vals.update({'operating_unit_id': settlement_line.move_line_id.operating_unit_id \
                    and settlement_line.move_line_id.operating_unit_id.id or False})
        return move_vals

class AccountSettlementAdvanceLine(models.Model):
    _inherit = 'account.settlement.advance.line'

    def _prepare_expense_move_line(self, move):
        move_vals = super(AccountSettlementAdvanceLine, self)._prepare_expense_move_line(move)
        if self.advance_line_id:
            move_vals.update({'operating_unit_id': self.advance_line_id.operating_unit_id \
                    and self.advance_line_id.operating_unit_id.id or False})
        else:
            move_vals.update({'operating_unit_id': self.move_line_id.operating_unit_id \
                    and self.move_line_id.operating_unit_id.id or False})
        return move_vals

    def _prepare_settlement_move_line(self, move, amount_line):
        move_vals = super(AccountSettlementAdvanceLine, self)._prepare_settlement_move_line(move, amount_line)
        if self.advance_line_id:
            move_vals.update({'operating_unit_id': self.advance_line_id.operating_unit_id \
                    and self.advance_line_id.operating_unit_id.id or False})
        else:
            move_vals.update({'operating_unit_id': self.move_line_id.operating_unit_id \
                    and self.move_line_id.operating_unit_id.id or False})
        return move_vals