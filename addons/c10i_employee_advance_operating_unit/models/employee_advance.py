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

class AccountEmployeeAdvance(models.Model):
    _inherit = 'account.employee.advance'

    operating_unit_id = fields.Many2one('operating.unit', 'Operating Unit',
                                        default=lambda self:
                                        self.env['res.users'].
                                        operating_unit_default_get(self._uid),
                                        readonly=True,
                                        states={'draft': [('readonly',
                                                           False)]})
    @api.multi
    def advance_payment_create(self, current_currency_id):
        payment_vals = super(AccountEmployeeAdvance, self).advance_payment_create(current_currency_id)
        payment_vals.update({'operating_unit_id': self.operating_unit_id and self.operating_unit_id.id or False}) 
        return payment_vals

    @api.multi
    def account_move_get(self):
        move_vals = super(AccountEmployeeAdvance, self).account_move_get()
        move_vals.update({'operating_unit_id': self.operating_unit_id and self.operating_unit_id.id or False}) 
        return move_vals

    @api.multi
    def first_move_line_get(self, move_id, company_currency, current_currency):
        move_line_vals = super(AccountEmployeeAdvance, self).first_move_line_get(move_id, company_currency, current_currency)
        move_line_vals.update({'operating_unit_id': self.operating_unit_id and self.operating_unit_id.id or False}) 
        return move_line_vals

class AccountEmployeeAdvanceLine(models.Model):
    _inherit = 'account.employee.advance.line'

    operating_unit_id = fields.Many2one('operating.unit',
                                        related='advance_id.operating_unit_id',
                                        string='Operating Unit', store=True,
                                        readonly=True)

    @api.multi
    def _prepare_move_line(self, amount):
        move_line_vals = super(AccountEmployeeAdvanceLine, self)._prepare_move_line(amount)
        move_line_vals.update({'operating_unit_id': self.operating_unit_id and self.operating_unit_id.id or False}) 
        return move_line_vals