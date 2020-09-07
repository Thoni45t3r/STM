# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   @modifier Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError, except_orm, Warning, RedirectWarning, ValidationError
import odoo.addons.decimal_precision as dp

class Company(models.Model):
    _inherit        = 'res.company'
    
    default_purchase_shipping_partner_id    = fields.Many2one('res.partner', 'Delivery Address')
    default_purchase_invoice_partner_id 	= fields.Many2one('res.partner', 'Invoice Address')