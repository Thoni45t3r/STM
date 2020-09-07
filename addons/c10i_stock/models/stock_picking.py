# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
from collections import OrderedDict, defaultdict
from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp

class StockPicking(models.Model):
    _inherit        = 'stock.picking'

    date_done = fields.Datetime('Date of Transfer', copy=False, readonly=False, states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}, help="Completion Date of Transfer")