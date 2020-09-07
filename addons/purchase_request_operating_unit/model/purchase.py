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
from odoo.exceptions import except_orm, Warning, RedirectWarning, ValidationError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if not vals.get('doc_type_id', False):
                if vals.get('operating_unit_id', False):
                    seq = self.env['ir.sequence'].with_context({'force_operating_unit':vals['operating_unit_id']})
                elif self._context.get('operating_unit_id',False):
                    seq = self.env['ir.sequence'].with_context({'force_operating_unit': self._context.get('operating_unit_id')})
                    vals.update({'operating_unit_id' : self._context.get('operating_unit_id')})
                else:
                    seq = self.env['ir.sequence']
                if vals.get('service_order', False):
                    sequence_code = 'purchase.order.service'
                else:
                    sequence_code = 'purchase.order'
                vals['name'] = (vals.get('name','/')=='/' or  'name' not in vals.keys()) and self.env['ir.sequence'].with_context({'force_operating_unit':vals['operating_unit_id']}).next_by_code(sequence_code) or vals['name']
            return super(PurchaseOrder, self).create(vals)
        else:
            return super(PurchaseOrder, self).create(vals)