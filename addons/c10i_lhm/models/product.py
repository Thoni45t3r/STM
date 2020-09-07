# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class Product(models.Model):
    _inherit        = 'product.template'
    _description    = 'Product Inherit'

    is_nab              = fields.Boolean('Is NAB')
    capitalized_tax_id  = fields.Many2many('account.tax', 'product_capitalized_tax_rel', 'prod_id', 'tax_id', string='Capitalized Taxes', domain=[('type_tax_use', '=', 'purchase')])

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    @api.one
    @api.constrains('default_code')
    def _check_default_code(self):
        if self.search([('id','!=',self.id),('default_code','=',self.default_code)]):
            raise ValidationError(_('Invalid Internal Reference!\nYou cannot have more than one Product with the same Internal Reference. Please put different Internal Reference for this Product'))

class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    partner_id = fields.Many2one('res.partner', 'Only for Partner')
    plantation_pricelist_type = fields.Selection([('pricelist_plasma', 'Pricelist for Product Plasma'),
        ('pricelist_transport', 'Pricelist for Plantation Transport')], 'Plantation Pricelist Type',
        default=lambda self: self.env.context.get('plantation_pricelist_type', False))
    pks_id = fields.Many2one('res.partner', 'Destination PKS')