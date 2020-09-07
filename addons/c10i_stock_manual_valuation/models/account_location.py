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

class AccountLocation(models.Model):
    _inherit = 'account.location'

    product_cost_value_categ_ids = fields.Many2many('product.category', 'product_categ_account_location_rel', 'account_location_id', 'product_categ_id', string='For Product Category Costing')
    product_tmpl_cost_value_ids = fields.Many2many('product.template', 'product_tmpl_account_location_rel', 'account_location_id', 'product_tmpl_id', string='For Product Costing')
