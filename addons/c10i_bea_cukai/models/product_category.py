# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import api, fields, models, _

class ProductType(models.Model):
	_name = 'product.type'
	_description = 'Product Type'

	name = fields.Char('Name')
	code = fields.Char('Code')

class ProductCategory(models.Model):
	_inherit = 'product.category'

	product_type = fields.Many2one('product.type', 'Product Type')