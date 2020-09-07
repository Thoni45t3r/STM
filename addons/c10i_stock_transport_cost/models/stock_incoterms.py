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

class Incoterms(models.Model):
    _inherit = 'stock.incoterms'

    transport_cost_sale = fields.Boolean('Sale Transport Cost')
    sale_account_id = fields.Many2one('account.account', string='Transport Purchase Account')
    transport_cost_purchase = fields.Boolean('Purchase Transport Cost')
    purchase_account_id = fields.Many2one('account.account', string='Transport Sale Account')

# class 

# 	incoterm_id = fields.Many2one('stock.incoterms', 'Incoterm')
# 	product_id = fields.Many2one('product.product')
#     sale_account_id = fields.Many2one('account.account', string='Transport Purchase Account')
#     purchase_account_id = fields.Many2one('account.account', string='Transport Sale Account')