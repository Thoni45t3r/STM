# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

import json
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang

from odoo.exceptions import UserError, RedirectWarning, ValidationError

import odoo.addons.decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
	_inherit = "account.invoice"

	def action_move_create(self):
		res = super(AccountInvoice, self).action_move_create()
		AccountAsset = self.env['account.asset.asset']
		AccountAssetDeprLine = self.env['account.asset.depreciation.line']
		sold_assets = AccountAsset.search([('disposal_invoice_id','in',self.ids)])
		for asset in sold_assets:
			depr_line = asset.depreciation_line_ids.filtered(lambda x:x.disposal_method=='asset_sale')
			if depr_line:
				depr_line[0].write({'move_id': asset.disposal_invoice_id.move_id.id})
		return res