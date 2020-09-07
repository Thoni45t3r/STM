# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
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
            if self._context.get('doc_type_id', False):
                if self.env['res.document.type'].browse(self._context.get('doc_type_id')).sequence_id:
                    vals['name'] = self.env['res.document.type'].browse(self._context.get('doc_type_id')).sequence_id.next_by_id() or _('New')
            return super(PurchaseOrder, self).create(vals)
        else:
            return super(PurchaseOrder, self).create(vals)

    @api.multi
    def create_downpayment(self):
        downpayment = super(PurchaseOrder, self.sudo()).create_downpayment()
        self.advance_invoice_id.sudo().operating_unit_id = self.operating_unit_id.id
        return downpayment

    @api.onchange('operating_unit_id')
    def _onchange_operating_unit_id(self):
        type_obj = self.env['stock.picking.type']
        if self.operating_unit_id:
            types = type_obj.search([('code', '=', 'incoming'),
                                     ('warehouse_id.operating_unit_id', '=',
                                      self.operating_unit_id.id)])
            if types:
                self.picking_type_id = self.doc_type_id.picking_type_id.id or types[:1]
            else:
                raise UserError(
                    _("No Warehouse found with the Operating Unit indicated "
                      "in the Purchase Order")
                )