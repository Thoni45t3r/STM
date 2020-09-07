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

class StockMove(models.Model):
    _inherit = 'stock.move'

    gross_weight = fields.Float('Gross Weight', digits=(15,2))
    net_weight = fields.Float('Net Weight', digits=(15,2))

    @api.multi
    def action_done(self):
        res = super(StockMove, self).action_done()

        for move in self:
            if move.procurement_id.sale_line_id and move.procurement_id.sale_line_id.order_id.bea_cukai_id:
                move.picking_id.incoterm_id = move.procurement_id.sale_line_id.order_id.incoterm.id
            elif move.purchase_line_id and move.purchase_line_id.order_id.bea_cukai_id:
    			move.picking_id.incoterm_id = move.purchase_line_id.order_id.incoterm_id.id
        return res