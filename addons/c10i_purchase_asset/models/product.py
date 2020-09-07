# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

import odoo.addons.decimal_precision as dp


class ProductCategory(models.Model):
	_inherit = "product.category"
	
	asset_category = fields.Boolean('Asset Category')
	asset_category_id = fields.Many2one('account.asset.category', string='Linked Asset Category')
	asset_journal_id = fields.Many2one('account.journal', string='Asset Journal')
	account_asset_id = fields.Many2one('account.account', string='Asset Account', domain=[('internal_type','=','other'), ('deprecated', '=', False)], help="Account used to record the purchase of the asset at its original price.")
	account_depreciation_id = fields.Many2one('account.account', string='Depreciation Entries: Asset Account', domain=[('internal_type','=','other'), ('deprecated', '=', False)], help="Account used in the depreciation entries, to decrease the asset value.")
	account_depreciation_expense_id = fields.Many2one('account.account', string='Depreciation Entries: Expense Account', domain=[('internal_type','=','other'), ('deprecated', '=', False)], oldname='account_income_recognition_id', help="Account used in the periodical entries, to record a part of the asset as expense.")
	
	method = fields.Selection([('linear', 'Linear'), ('degressive', 'Degressive')], string='Computation Method',
		help="Choose the method to use to compute the amount of depreciation lines.\n"
			"  * Linear: Calculated on basis of: Gross Value / Number of Depreciations\n"
			"  * Degressive: Calculated on basis of: Residual Value * Degressive Factor")
	method_number = fields.Integer(string='Number of Depreciations', help="The number of depreciations needed to depreciate your asset")
	method_period = fields.Integer(string='Period Length', help="State here the time between 2 depreciations, in months")
	method_progress_factor = fields.Float('Degressive Factor')
	method_time = fields.Selection([('number', 'Number of Depreciations')], string='Time Method',
		help="Choose the method to use to compute the dates and number of depreciation lines.\n"
		   "  * Number of Depreciations: Fix the number of depreciation lines and the time between 2 depreciations.\n"
		   "  * Ending Date: Choose the time between 2 depreciations and the date the depreciations won't go beyond.")
	depreciation_start_control = fields.Selection([('before_half', 'Date of service less or equal than 15'), 
		('after_half', 'Date of service greater than 15')], string='Depreciation Policy', default='after_half',
		help="Choose the policy to use to define start date service of the asset.\n"
			"  * Date of service less or equal than 15: If the asset was bought before date 15th of the month, then depreciation will start on the month of the service date\n"
			"  * Date of service greater than 15: If the asset was bought after date 16th of the month, then depreciation will start on one month after")

	@api.model
	def value_get_from_parent(self, field, parent_id, ftype=None):
		res = False
		parent = self.browse(parent_id)
		if parent:
			try:
				if ftype=='object':
					res = eval("parent.%s and parent.%s.id or False"%(field, field))
				else:
					res = eval("parent.%s or False"%(field))
			except:
				raise UserError(_('Field %s is not found in model %s')%(field, parent._name))
			if not res and parent.parent_id:
				res = self.value_get_from_parent(field, parent.parent_id.id)
		return res

	@api.model
	def create(self, vals):
		if vals.get('asset_category'):
			AssetType = self.env['account.asset.category']
			cat = AssetType.create({
				'name': vals.get('name'),
				'account_asset_id': vals.get('account_asset_id') or self.value_get_from_parent('account_asset_id', vals.get('parent_id'), ftype='object'),
				'account_depreciation_id': vals.get('account_depreciation_id') or self.value_get_from_parent('account_depreciation_id', vals.get('parent_id'), ftype='object'),
				'account_depreciation_expense_id': vals.get('account_depreciation_expense_id') or self.value_get_from_parent('account_depreciation_expense_id', vals.get('parent_id'), ftype='object'),
				'journal_id': vals.get('asset_journal_id') or self.value_get_from_parent('asset_journal_id', vals.get('parent_id'), ftype='object'),
				'method': vals.get('method') or self.value_get_from_parent('method', vals.get('parent_id')),
				'method_number': vals.get('method_number') or self.value_get_from_parent('method_number', vals.get('parent_id')),
				'method_period': vals.get('method_period') or self.value_get_from_parent('method_period', vals.get('parent_id')),
				'method_progress_factor': vals.get('method_progress_factor') or self.value_get_from_parent('method_progress_factor', vals.get('parent_id')),
				'method_time': vals.get('method_time') or self.value_get_from_parent('method_time', vals.get('parent_id')),
				'company_id': self.env.user.company_id.id,
			})
			vals.update({'asset_category_id': cat.id})
		return super(ProductCategory, self).create(vals)

	@api.one
	def write(self, vals):
		if 'asset_category' in vals.keys():
			if not vals['asset_category'] or self.asset_journal_id:
				raise UserError(_('You cannot modify attribute Asset Category because it is already linked with Asset Type'))
			else:
				# Create a new Asset Type
				AssetType = self.env['account.asset.category']
				parent = vals.get('parent_id') or self.parent_id.id
				cat = AssetType.create({
					'name': vals.get('name', self.name),
					'account_asset_id': vals.get('account_asset_id', self.account_asset_id and self.account_asset_id.id or False) or self.value_get_from_parent('account_asset_id', parent),
					'account_depreciation_id': vals.get('account_depreciation_id', self.account_depreciation_id and self.account_depreciation_id.id or False) or self.value_get_from_parent('account_depreciation_id', parent),
					'account_depreciation_expense_id': vals.get('account_depreciation_expense_id', self.account_depreciation_expense_id and self.account_depreciation_expense_id.id or False) or self.value_get_from_parent('account_depreciation_expense_id', parent),
					'journal_id': vals.get('asset_journal_id', self.asset_journal_id and self.asset_journal_id.id or False) or self.value_get_from_parent('asset_journal_id', parent),
					'method': vals.get('method', self.method or False) or self.value_get_from_parent('method', parent),
					'method_number': vals.get('method_number', self.method_number or False) or self.value_get_from_parent('method_number', parent),
					'method_period': vals.get('method_period', self.method_period or False) or self.value_get_from_parent('method_period', parent),
					'method_progress_factor': vals.get('method_progress_factor', self.method_progress_factor or False) or self.value_get_from_parent('method_progress_factor', parent),
					'method_time': vals.get('method_time', self.method_time or False) or self.value_get_from_parent('method_time', parent),
					'company_id': self.env.user.company_id.id,
				})
				vals.update({'asset_category_id': cat.id})
		else:
			dict_update_assettype = {}
			if 'name' in vals.keys():
				dict_update_assettype.update({'name': vals.get('name')})
			if 'account_asset_id' in vals.keys():
				dict_update_assettype.update({'account_asset_id': vals.get('account_asset_id')})
			if 'account_depreciation_id' in vals.keys():
				dict_update_assettype.update({'account_depreciation_id': vals.get('account_depreciation_id')})
			if 'account_depreciation_expense_id' in vals.keys():
				dict_update_assettype.update({'account_depreciation_expense_id': vals.get('account_depreciation_expense_id')})
			if 'asset_journal_id' in vals.keys():
				dict_update_assettype.update({'journal_id': vals.get('asset_journal_id')})
			if 'method' in vals.keys():
				dict_update_assettype.update({'method': vals.get('method')})
			if 'method_number' in vals.keys():
				dict_update_assettype.update({'method_number': vals.get('method_number')})
			if 'method_period' in vals.keys():
				dict_update_assettype.update({'method_period': vals.get('method_period')})
			if 'method_progress_factor' in vals.keys():
				dict_update_assettype.update({'method_progress_factor': vals.get('method_progress_factor')})
			if 'method_time' in vals.keys():
				dict_update_assettype.update({'method_time': vals.get('method_time')})
			
			if self.asset_category_id:
				self.asset_category_id.write(dict_update_assettype)

		return super(ProductCategory, self).write(vals)