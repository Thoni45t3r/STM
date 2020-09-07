# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
import odoo.addons.decimal_precision as dp

SPLIT_METHOD = [
    ('equal', 'by Equal'),
    ('by_quantity', 'By Quantity'),
    ('by_current_cost_price', 'By Current Cost'),
    ('by_weight', 'By Weight'),
    ('by_volume', 'By Volume'),
]

class ProductProduct(models.Model):
    _inherit = "product.product"
      
    standard_price = fields.Float(
        'Cost Price', company_dependent=True,
        digits=dp.get_precision('Product Cost Price'),
        groups="base.group_user",
        help="Cost of the product template used for standard stock valuation in accounting and used as a base price on purchase orders. "
             "Expressed in the default unit of measure of the product.")
    standard_price_temp = fields.Float(string='Cost Price', related='standard_price',
        digits=dp.get_precision('Product Price'),
        groups="base.group_user",
        help="Cost of the product template used for standard stock valuation in accounting and used as a base price on purchase orders. "
             "Expressed in the default unit of measure of the product.")
    
class ProductTemplate(models.Model):
    _inherit = "product.template"

    standard_price = fields.Float(
        'Cost Price', compute='_compute_standard_price',
        inverse='_set_standard_price', search='_search_standard_price',
        digits=dp.get_precision('Product Cost Price'), groups="base.group_user",
        help="Cost of the product, in the default unit of measure of the product.")
    standard_price_temp = fields.Float('Cost Price', related='standard_price',
        digits=dp.get_precision('Product Price'), groups="base.group_user",
        help="Cost of the product, in the default unit of measure of the product.")
    landed_avg_ok = fields.Boolean('Landed Costs Avg')
    split_method_avg = fields.Selection(
        selection=SPLIT_METHOD, string='Split Method', default='by_weight',
        help="By Weight : Cost will be divided depending on its weight.\n"
             "By Volume : Cost will be divided depending on its volume.")
