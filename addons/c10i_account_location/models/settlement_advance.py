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
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.osv import expression
from odoo.tools import float_compare, float_is_zero
import urllib3
from lxml import etree
import time

class AccountSettlementAdvanceLine(models.Model):
    _inherit = 'account.settlement.advance.line'

    account_location_type_id = fields.Many2one(comodel_name="account.location.type", string="Tipe Lokasi", ondelete="restrict")
    account_location_id = fields.Many2one(comodel_name="account.location", string="Lokasi", ondelete="restrict")
    account_location_type_no_location = fields.Boolean(string="Plantation Validator", related="account_location_type_id.no_location")

    @api.onchange('account_location_type_id')
    def _onchange_account_location_type_id(self):
        if self.account_location_type_id:
            self.account_location_id = False
            if self.account_location_type_id.no_location and (self.account_location_type_id.general_charge):
                self.account_id = False
            else:
                self.account_id = self.account_location_type_id.account_id and self.account_location_type_id.account_id.id or False

    def _prepare_expense_move_line(self, move):
        move_vals = super(AccountSettlementAdvanceLine, self)._prepare_expense_move_line(move)
        move_vals.update({
            'account_location_type_id': self.account_location_type_id and self.account_location_type_id.id or False,
            'account_location_id': self.account_location_id and self.account_location_id.id or False,
            'account_location_type_no_location': self.account_location_type_no_location,
            })
        return move_vals

class SplitSettlementAdvanceLine(models.Model):
    _inherit = 'split.settlement.advance.line'

    account_location_type_id = fields.Many2one(comodel_name="account.location.type", string="Tipe Lokasi", ondelete="restrict")
    account_location_id = fields.Many2one(comodel_name="account.location", string="Lokasi", ondelete="restrict")
    account_location_type_no_location = fields.Boolean(string="Plantation Validator", related="account_location_type_id.no_location")

    @api.onchange('account_location_type_id')
    def _onchange_account_location_type_id(self):
        if self.account_location_type_id:
            self.account_location_id = False
            if self.account_location_type_id.no_location and (self.account_location_type_id.general_charge):
                self.account_id = False
            else:
                self.account_id = self.account_location_type_id.account_id and self.account_location_type_id.account_id.id or False

    def _prepare_expense_split_move_line(self, settlement_line, move):
        move_vals = super(SplitSettlementAdvanceLine, self)._prepare_expense_split_move_line(settlement_line, move)
        move_vals.update({
            'account_location_type_id': self.account_location_type_id and self.account_location_type_id.id or False,
            'account_location_id': self.account_location_id and self.account_location_id.id or False,
            'account_location_type_no_location': self.account_location_type_no_location,
            })
        return move_vals