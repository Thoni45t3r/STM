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
from odoo.tools import float_compare, float_is_zero


class AccountAssetAsset(models.Model):
    _inherit = 'account.asset.asset'

    move_id = fields.Many2one('stock.move', 'Source Receipt Move', readonly=True)
    reclass_move_id = fields.Many2one('account.move', 'Reclass Entry', readonly=True)

    # @api.multi
    # def validate(self):
    #     for asset in self:
    #         if asset.move_id and not asset.reclass_move_id:
    #             asset.process()
    #     return super(AccountAssetAsset, self).validate()
    # @api.multi
    # def process(self):
    #     move_ids = []
    #     for asset in self:
    #         if asset.move_id:
    #             if asset.reclass_move_id:
    #                 raise UserError(_('This Asset has already had a Reclass Entry'))

    #             valuation_method = asset.move_id.product_id.property_valuation or asset.move_id.product_id.categ_id.property_valuation
    #             if valuation_method != 'real_time':
    #                 continue
    #             debit_account = asset.move_id.product_id.categ_id.account_asset_id or (asset.move_id.asset_category_id and asset.move_id.asset_category_id.account_asset_id or False)
    #             # credit_account = asset.move_id.product_id.categ_id.property_stock_valuation_account_id
    #             credit_account = asset.move_id.product_id.property_stock_account_output or  asset.move_id.product_id.categ_id.property_stock_account_output_categ_id
    #             if not debit_account:
    #                 raise UserError(_('Please define Asset Account inside Asset Type or Product Category of this product (%s).')%line.product_id.name)
    #             if not credit_account:
    #                 raise UserError(_('Please define Stock Valuation Account inside Product Category of this product (%s).')%line.product_id.name)
                
    #             # debit
    #             move_line_dict1 = {
    #                 'name': asset.name,
    #                 'account_id': debit_account.id,
    #                 'debit': asset.value,
    #                 'credit': 0.0,
    #                 'journal_id': asset.category_id.journal_id.id,
    #                 'partner_id': asset.partner_id and asset.partner_id.id or False,
    #                 'analytic_account_id': False,
    #                 'currency_id': False,
    #                 'amount_currency': 0.0,
    #             }
    #             # credit
    #             move_line_dict2 = move_line_dict1.copy()
    #             move_line_dict2['account_id'] = credit_account.id
    #             move_line_dict2['credit'] = move_line_dict2['debit']
    #             move_line_dict2['debit'] = 0
    #             move_vals = {
    #                 'ref': asset.code,
    #                 'date': asset.move_id.date or False,
    #                 'journal_id': asset.category_id.journal_id.id,
    #                 'line_ids': [(0, 0, move_line_dict1),(0, 0, move_line_dict2)],
    #             }
    #             account_move = self.env['account.move'].create(move_vals)
    #             asset.write({'reclass_move_id': account_move.id})
    #             move_ids.append(account_move)
    #             asset.validate()
    #     return True