# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import api, fields, models, tools, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # type = fields.Selection(selection_add=[('asset', _('Asset'))])
    
    # @api.onchange('type', 'sale_ok')
    # def _onchange_ptype_asset(self):
    #     if self.type == 'asset':
    #         self.sale_ok = False