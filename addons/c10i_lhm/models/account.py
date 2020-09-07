# -*- coding: utf-8 -*-
from hashlib import sha256
from json import dumps

from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.exceptions import UserError



class AccountMove(models.Model):
    _inherit = "account.move"
    @api.multi
    def post(self):
        ml_obj = self.env['account.move.line']
        default_loc_type = self.env['lhm.location.type'].search([('name','=','-')])
        for move in self:
            for line in move.line_ids:
                if not line.plantation_location_type_id:
                    line.plantation_location_type_id = default_loc_type and default_loc_type[0].id or False
        return super(AccountMove, self).post()

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    plantation_location_type_id = fields.Many2one(comodel_name="lhm.location.type", string="Tipe Lokasi", ondelete="restrict")
    plantation_location_id      = fields.Many2one(comodel_name="lhm.location", string="Lokasi", ondelete="restrict")
    plantation_activity_id      = fields.Many2one(comodel_name="lhm.activity", string="Aktivitas", ondelete="restrict")
    plantation_validator        = fields.Boolean(string="Plantation Validator", related="plantation_location_type_id.no_line")

    @api.onchange('plantation_location_type_id')
    def _onchange_plantation_location_type_id(self):
        if self.plantation_location_type_id:
            self.plantation_location_id = False
            self.plantation_activity_id = False
            if self.plantation_location_type_id.no_line and (self.plantation_location_type_id.general_charge or self.plantation_location_type_id.indirect):
                self.account_id = False
            else:
                self.account_id = self.plantation_location_type_id.account_id and self.plantation_location_type_id.account_id.id or False

    @api.onchange('plantation_location_id')
    def _onchange_plantation_location_id(self):
        if self.plantation_location_id:
            self.plantation_activity_id = False

    @api.onchange('plantation_activity_id')
    def _onchange_plantation_activity_id(self):
        if self.plantation_activity_id and (self.plantation_location_type_id.general_charge or self.plantation_location_type_id.indirect):
            self.account_id = self.plantation_activity_id.account_id and self.plantation_activity_id.account_id.id or False

class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    
    @api.model
    def invoice_line_move_line_get(self):
        res = super(AccountInvoice, self).invoice_line_move_line_get()
        default_loc_type = self.env['lhm.location.type'].search([('name','=','-')])
        for line in res:
            inv_line = self.env['account.invoice.line'].browse(line['invl_id'])
            line.update({
                'plantation_location_type_id': inv_line.plantation_location_type_id and inv_line.plantation_location_type_id.id or (default_loc_type and default_loc_type[0].id or False),
                'plantation_location_id': inv_line.plantation_location_id and inv_line.plantation_location_id.id or False,
                'plantation_activity_id': inv_line.plantation_activity_id and inv_line.plantation_activity_id.id or False,
                })    
        return res

    @api.model
    def line_get_convert(self, line, part):
        res = super(AccountInvoice, self).line_get_convert(line, part)
        default_loc_type = self.env['lhm.location.type'].search([('name','=','-')])
        res.update({
            'plantation_location_type_id': line.get('plantation_location_type_id', default_loc_type and default_loc_type[0].id or False),
            'plantation_location_id': line.get('plantation_location_id', False),
            'plantation_activity_id': line.get('plantation_activity_id', False),
        })
        return res

    @api.multi
    def invoice_print_plantation(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'c10i_lhm.report_invoice_lhm')

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    plantation_location_type_id = fields.Many2one(comodel_name="lhm.location.type", string="Tipe Lokasi", ondelete="restrict")
    plantation_location_id      = fields.Many2one(comodel_name="lhm.location", string="Lokasi", ondelete="restrict")
    plantation_activity_id      = fields.Many2one(comodel_name="lhm.activity", string="Aktivitas", ondelete="restrict")
    plantation_validator        = fields.Boolean(string="Plantation Validator", related="plantation_location_type_id.no_line")

    @api.onchange('plantation_location_type_id')
    def _onchange_plantation_location_type_id(self):
        if self.plantation_location_type_id:
            self.plantation_location_id = False
            self.plantation_activity_id = False
            if self.plantation_location_type_id.no_line and self.product_id:
                self.account_id = (self.product_id.property_stock_account_input or (self.product_id.categ_id and self.product_id.categ_id.property_stock_account_input_categ_id)) or False
            elif self.plantation_location_type_id.no_line and (self.plantation_location_type_id.general_charge or self.plantation_location_type_id.indirect):
                self.account_id = False
            else:
                self.account_id = self.plantation_location_type_id.account_id and self.plantation_location_type_id.account_id.id or False

    @api.onchange('plantation_location_id')
    def _onchange_plantation_location_id(self):
        if self.plantation_location_id:
            self.plantation_activity_id = False

    @api.onchange('plantation_activity_id')
    def _onchange_plantation_activity_id(self):
        if self.plantation_activity_id and (self.plantation_location_type_id.general_charge or self.plantation_location_type_id.indirect):
            self.account_id = self.plantation_activity_id.account_id and self.plantation_activity_id.account_id.id or False

class AccountVoucher(models.Model):
    _inherit = "account.voucher"

    @api.multi
    def first_move_line_get(self, move_id, company_currency, current_currency):
        default_loc_type = self.env['lhm.location.type'].search([('name','=','-')])
        move_line = super(AccountVoucher, self).first_move_line_get(move_id, company_currency, current_currency)
        if self.partner_id.commercial_partner_id.id == self.company_id.id:
            move_line.update({
                'partner_id': self.partner_id.id,
                'plantation_location_type_id': default_loc_type and default_loc_type[0].id or False,
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
        default_loc_type = self.env['lhm.location.type'].search([('name','=','-')])
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
                'credit': credit,
                'debit': debit,
                'date': self.account_date,
                'tax_ids': [(4,t.id) for t in line.tax_ids],
                'amount_currency': sign*line.price_subtotal if current_currency != company_currency else 0.0,
                'currency_id': company_currency != current_currency and current_currency or False,
                'plantation_location_type_id': line.plantation_location_type_id and line.plantation_location_type_id.id or (default_loc_type and default_loc_type[0].id or False),
                'plantation_location_id': line.plantation_location_id and line.plantation_location_id.id or False,
                'plantation_activity_id': line.plantation_activity_id and line.plantation_activity_id.id or False,
                'payment_id': self._context.get('payment_id'),
            }
            self.env['account.move.line'].with_context(apply_taxes=True).create(move_line)
            line_total += (debit - credit)
        return line_total

class AccountVoucherLine(models.Model):
    _inherit = "account.voucher.line"

    plantation_location_type_id = fields.Many2one(comodel_name="lhm.location.type", string="Tipe Lokasi", ondelete="restrict")
    plantation_location_id      = fields.Many2one(comodel_name="lhm.location", string="Lokasi", ondelete="restrict")
    plantation_activity_id      = fields.Many2one(comodel_name="lhm.activity", string="Aktivitas", ondelete="restrict")
    plantation_validator        = fields.Boolean(string="Plantation Validator", related="plantation_location_type_id.no_line")

    @api.onchange('plantation_location_type_id')
    def _onchange_plantation_location_type_id(self):
        if self.plantation_location_type_id:
            self.plantation_location_id = False
            self.plantation_activity_id = False
            if self.plantation_location_type_id.no_line and (self.plantation_location_type_id.general_charge or self.plantation_location_type_id.indirect):
                self.account_id = False
            else:
                self.account_id = self.plantation_location_type_id.account_id and self.plantation_location_type_id.account_id.id or False

    @api.onchange('plantation_location_id')
    def _onchange_plantation_location_id(self):
        if self.plantation_location_id:
            self.plantation_activity_id = False

    @api.onchange('plantation_activity_id')
    def _onchange_plantation_activity_id(self):
        if self.plantation_activity_id and (self.plantation_location_type_id.general_charge or self.plantation_location_type_id.indirect):
            self.account_id = self.plantation_activity_id.account_id and self.plantation_activity_id.account_id.id or False


class AccountSettlementAdvanceLine(models.Model):
    _inherit = 'account.settlement.advance.line'

    plantation_location_type_id = fields.Many2one(comodel_name="lhm.location.type", string="Tipe Lokasi", ondelete="restrict")
    plantation_location_id      = fields.Many2one(comodel_name="lhm.location", string="Lokasi", ondelete="restrict")
    plantation_activity_id      = fields.Many2one(comodel_name="lhm.activity", string="Aktivitas", ondelete="restrict")
    plantation_validator        = fields.Boolean(string="Plantation Validator", related="plantation_location_type_id.no_line")

    @api.onchange('plantation_location_type_id')
    def _onchange_plantation_location_type_id(self):
        if self.plantation_location_type_id:
            self.plantation_location_id = False
            self.plantation_activity_id = False
            if self.plantation_location_type_id.no_line and (self.plantation_location_type_id.general_charge or self.plantation_location_type_id.indirect):
                self.account_id = False
            else:
                self.account_id = self.plantation_location_type_id.account_id and self.plantation_location_type_id.account_id.id or False

    @api.onchange('plantation_location_id')
    def _onchange_plantation_location_id(self):
        if self.plantation_location_id:
            self.plantation_activity_id = False

    @api.onchange('plantation_activity_id')
    def _onchange_plantation_activity_id(self):
        if self.plantation_activity_id and (self.plantation_location_type_id.general_charge or self.plantation_location_type_id.indirect):
            self.account_id = self.plantation_activity_id.account_id and self.plantation_activity_id.account_id.id or False

    def _prepare_expense_move_line(self, move):
        move_vals = super(AccountSettlementAdvanceLine, self)._prepare_expense_move_line(move)
        move_vals.update({
            'plantation_location_type_id': self.plantation_location_type_id and self.plantation_location_type_id.id or False,
            'plantation_location_id': self.plantation_location_id and self.plantation_location_id.id or False,
            'plantation_activity_id': self.plantation_activity_id and self.plantation_activity_id.id or False,
            'plantation_validator': self.plantation_validator,
            })
        return move_vals

class SplitSettlementAdvanceLine(models.Model):
    _inherit = 'split.settlement.advance.line'

    plantation_location_type_id = fields.Many2one(comodel_name="lhm.location.type", string="Tipe Lokasi", ondelete="restrict")
    plantation_location_id      = fields.Many2one(comodel_name="lhm.location", string="Lokasi", ondelete="restrict")
    plantation_activity_id      = fields.Many2one(comodel_name="lhm.activity", string="Aktivitas", ondelete="restrict")
    plantation_validator        = fields.Boolean(string="Plantation Validator", related="plantation_location_type_id.no_line")

    @api.onchange('plantation_location_type_id')
    def _onchange_plantation_location_type_id(self):
        if self.plantation_location_type_id:
            self.plantation_location_id = False
            self.plantation_activity_id = False
            if self.plantation_location_type_id.no_line and (self.plantation_location_type_id.general_charge or self.plantation_location_type_id.indirect):
                self.account_id = False
            else:
                self.account_id = self.plantation_location_type_id.account_id and self.plantation_location_type_id.account_id.id or False

    @api.onchange('plantation_location_id')
    def _onchange_plantation_location_id(self):
        if self.plantation_location_id:
            self.plantation_activity_id = False

    @api.onchange('plantation_activity_id')
    def _onchange_plantation_activity_id(self):
        if self.plantation_activity_id and (self.plantation_location_type_id.general_charge or self.plantation_location_type_id.indirect):
            self.account_id = self.plantation_activity_id.account_id and self.plantation_activity_id.account_id.id or False

    def _prepare_expense_split_move_line(self, settlement_line, move):
        move_vals = super(SplitSettlementAdvanceLine, self)._prepare_expense_split_move_line(settlement_line, move)
        move_vals.update({
            'plantation_location_type_id': self.plantation_location_type_id and self.plantation_location_type_id.id or False,
            'plantation_location_id': self.plantation_location_id and self.plantation_location_id.id or False,
            'plantation_activity_id': self.plantation_activity_id and self.plantation_activity_id.id or False,
            'plantation_validator': self.plantation_validator,
            })
        return move_vals