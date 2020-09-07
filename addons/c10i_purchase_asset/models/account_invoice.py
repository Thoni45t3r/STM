# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import UserError, RedirectWarning, ValidationError

import odoo.addons.decimal_precision as dp


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def _prepare_invoice_line_from_po_line(self, line):
        data = super(AccountInvoice, self)._prepare_invoice_line_from_po_line(line)
        if line.product_id.categ_id.asset_category and line.product_id.categ_id.asset_category_id:
            data['asset_category_id'] = line.product_id.categ_id.asset_category_id.id
        return data

    @api.model
    def invoice_line_move_line_get(self):
        res = super(AccountInvoice, self).invoice_line_move_line_get()
        for line in self.invoice_line_ids:
            if line.quantity==0:
                continue
            if line.product_id and line.purchase_line_id and line.purchase_line_id.product_id and \
                    line.purchase_line_id.product_id.categ_id.asset_category_id:
                valuation_method = line.product_id.property_valuation or line.product_id.categ_id.property_valuation
                if valuation_method != 'real_time':
                    continue
                debit_account = line.product_id.categ_id.account_asset_id or (line.asset_category_id and line.asset_category_id.account_asset_id or False)
                credit_account = line.product_id.categ_id.property_stock_valuation_account_id
                if not debit_account:
                    raise UserError(_('Please define Asset Account inside Asset Type or Product Category of this product (%s).')%line.product_id.name)
                if not credit_account:
                    raise UserError(_('Please define Stock Valuation Account inside Product Category of this product (%s).')%line.product_id.name)

                tax_ids = []
                for tax in line.invoice_line_tax_ids:
                    tax_ids.append((4, tax.id, None))
                    for child in tax.children_tax_ids:
                        if child.type_tax_use != 'none':
                            tax_ids.append((4, child.id, None))
                analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in line.analytic_tag_ids]
                # debit
                move_line_dict = {
                    'invl_id': line.id,
                    'type': 'src',
                    'name': line.name.split('\n')[0][:64],
                    'price_unit': line.price_unit,
                    'quantity': line.quantity,
                    'price': line.price_subtotal,
                    'account_id': debit_account.id,
                    'product_id': line.product_id.id,
                    'uom_id': line.uom_id.id,
                    'account_analytic_id': line.account_analytic_id.id,
                    'tax_ids': tax_ids,
                    'invoice_id': self.id,
                    'analytic_tag_ids': analytic_tag_ids
                }
                if line['account_analytic_id']:
                    move_line_dict['analytic_line_ids'] = [(0, 0, line._get_analytic_line())]
                res.append(move_line_dict)

                # credit
                move_line_dict2 = move_line_dict.copy()
                move_line_dict2['account_id'] = credit_account.id
                move_line_dict2['price'] = -move_line_dict['price']
                res.append(move_line_dict2)
        return res