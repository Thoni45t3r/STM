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

class AccountVoucher(models.Model):
    _inherit = "account.voucher"

    @api.multi
    def first_move_line_get(self, move_id, company_currency, current_currency):
        default_loc_type = self.env['account.location.type'].search([('name','=','-')])
        move_line = super(AccountVoucher, self).first_move_line_get(move_id, company_currency, current_currency)
        if self.partner_id.commercial_partner_id.id == self.company_id.id:
            move_line.update({
                'partner_id': self.partner_id.id,
                'account_location_type_id': default_loc_type and default_loc_type[0].id or False,
                })
        return move_line

    @api.multi
    def voucher_move_line_create(self, line_total, move_id, company_currency, current_currency):
        '''
        Create one account move line, on the given account move, per voucher line where amount is not 0.0.
        It returns Tuple with tot_line what is total of difference between debit and credit and
        a list of lists with ids to be reconciled with this format (total_deb_cred,list_of_lists).

        :param voucher_id: Voucher id what we are working with
        :param line_total: Amount of the first line, which correspond to the amount we should totally split among all voucher lines.
        :param move_id: Account move wher those lines will be joined.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: Tuple build as (remaining amount not allocated on voucher lines, list of account_move_line created in this method)
        :rtype: tuple(float, list of int)
        '''
        default_loc_type = self.env['account.location.type'].search([('name','=','-')])
        for line in self.line_ids:
            #create one move line per voucher line where amount is not 0.0
            if not line.price_subtotal:
                continue
            # convert the amount set on the voucher line into the currency of the voucher's company
            # this calls res_curreny.compute() with the right context,
            # so that it will take either the rate on the voucher if it is relevant or will use the default behaviour
            debit = credit = 0.0
            amount = self._convert_amount(line.price_unit*line.quantity)
            if self.voucher_type == 'sale':
                if amount < 0.0:
                    debit = abs(amount)
                else:
                    credit = amount
            elif self.voucher_type == 'purchase':
                if amount < 0.0:
                    credit = abs(amount)
                else:
                    debit = amount
            sign = debit - credit < 0 and -1 or 1
            move_line = {
                'journal_id': self.journal_id.id,
                'name': line.name or '/',
                'account_id': line.account_id.id,
                'move_id': move_id,
                'partner_id': self.partner_id.commercial_partner_id.id,
                'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                'quantity': 1,
                'credit': abs(amount) if self.voucher_type == 'sale' else 0.0,
                'debit': abs(amount) if self.voucher_type == 'purchase' else 0.0,
                'date': self.account_date,
                'tax_ids': [(4,t.id) for t in line.tax_ids],
                'amount_currency': sign*line.price_subtotal if current_currency != company_currency else 0.0,
                'currency_id': company_currency != current_currency and current_currency or False,
                'account_location_type_id': line.account_location_type_id and line.account_location_type_id.id or (default_loc_type and default_loc_type[0].id or False),
                'account_location_id': line.account_location_id and line.account_location_id.id or False,
                'payment_id': self._context.get('payment_id'),
            }
            self.env['account.move.line'].with_context(apply_taxes=True).create(move_line)
            line_total += (debit - credit)
        return line_total

class AccountVoucherLine(models.Model):
    _inherit = "account.voucher.line"

    account_location_type_id = fields.Many2one(comodel_name="account.location.type", string="Tipe Lokasi", ondelete="restrict")
    account_location_id = fields.Many2one(comodel_name="account.location", string="Lokasi", ondelete="restrict")
    account_location_type_no_location = fields.Boolean(string="Plantation Validator", related="account_location_type_id.no_location")
    account_account_location_ids        = fields.Many2many('account.account', string='Daftar Account')
    account_location_type_name          = fields.Char("Tipe Lokasi", related="account_location_type_id.name", required=True)
    account_location_name               = fields.Char("Lokasi", related="account_location_id.name", required=True)


    @api.onchange('account_location_type_id')
    def _onchange_account_location_type_id(self):
        if self.account_location_type_id:
            self.account_location_id = False
            if self.account_location_type_id.no_location and (self.account_location_type_id.general_charge):
                self.account_id = False
            else:
                self.account_id = self.account_location_type_id.account_id and self.account_location_type_id.account_id.id or False
            if self.account_location_type_id.account_ids:
                self.account_account_location_ids = self.account_location_type_id.account_ids.ids
            else:
                self.account_account_location_ids = self.env['account.account'].search([]).ids


    @api.onchange('account_location_id')
    def _onchange_account_location_id(self):
        if self.account_location_type_id.project and self.account_location_id:
            if self.account_location_type_id.project:
                project_data = self.env['mill.project'].search([('location_id', '=', self.account_location_id.id)])
                if project_data.categ_id.account_id:
                    self.account_account_location_ids = [(6, 0, [project_data.categ_id.account_id.id])]
                else:
                    self.account_account_location_ids = False