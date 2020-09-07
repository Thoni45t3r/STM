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
from odoo.addons import decimal_precision as dp
import time

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _account_entry_move(self, move):
        res = super(StockQuant, self)._account_entry_move(move)
        
        location_from = move.location_id
        location_to = self[0].location_id  # TDE FIXME: as the accounting is based on this value, should probably check all location_to to be the same
        company_from = location_from.usage == 'internal' and location_from.company_id or False
        company_to = location_to and (location_to.usage == 'internal') and location_to.company_id or False
        if not res and move.location_id.usage=='supplier' and move.location_dest_id.usage=='internal' \
                and move.product_id.type=='product' and move.product_id.valuation=='manual_periodic':
            # Create Journal Entry for products arriving in the company; in case of routes making the link between several
            journal_id, acc_src, acc_dest, acc_valuation = move._get_accounting_data_for_valuation()
            purchase_account = move.product_id.purchase_account_id or move.product_id.categ_id.purchase_account_categ_id
            if not purchase_account:
                raise UserError(_('You don\'t have any Purchase Account defined on your product category. You must define one before processing this operation.'))
            acc_valuation = purchase_account.id
            self.with_context(force_company=company_to.id)._create_account_move_line(move, acc_src, acc_valuation, journal_id)
