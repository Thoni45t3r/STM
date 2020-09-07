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

# class StockMove(models.Model):
#     _inherit = 'stock.move'

#     @api.multi
#     def get_price_unit(self):
#         """ Returns the unit price to store on the quant """
#         if self.unbuild_id and self.unbuild_id.mill_order:
#             order = self.unbuild_id
#             #if the currency of the PO is different than the company one, the price_unit on the move must be reevaluated
#             #(was created at the rate of the PO confirmation, but must be valuated at the rate of stock move execution)
#             if order.currency_id != self.company_id.currency_id:
#                 #we don't pass the move.date in the compute() for the currency rate on purpose because
#                 # 1) get_price_unit() is supposed to be called only through move.action_done(),
#                 # 2) the move hasn't yet the correct date (currently it is the expected date, after
#                 #    completion of action_done() it will be now() )
#                 price_unit = self.purchase_line_id._get_stock_move_price_unit()
#                 self.write({'price_unit': price_unit})
#                 return price_unit
#             return self.price_unit
#         return super(StockMove, self).get_price_unit()