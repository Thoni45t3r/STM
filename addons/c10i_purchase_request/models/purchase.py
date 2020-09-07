# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Dion Martin
#   @modifier Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import models, fields, api, _
from odoo.exceptions import except_orm, Warning, RedirectWarning

class purchase_order(models.Model):
    _inherit = 'purchase.order'

    purchase_request_ids	= fields.Many2many('purchase.request')
    purchase_rfq_ids		= fields.Many2many('purchase.rfq')
    service_order           = fields.Boolean('Service Order')
    state                   = fields.Selection([('draft', 'New'),
                                                ('sent', 'RFQ Sent'),
                                                ('to approve', 'To Approve'),
                                                ('purchase', 'Purchase Order'),
                                                ('done', 'Locked'),
                                                ('cancel', 'Cancelled')], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')

    @api.model
    def create(self, vals):
        result  = super(purchase_order, self).create(vals)
        if vals.get('name', _('New')) == _('New'):
            if vals.get('service_order', False):
                sequence_code = 'purchase.order.service'
            else:
                return super(purchase_order, self).create(vals)
            vals['name'] = (vals.get('name','/')=='/' or  'name' not in vals.keys()) and self.env['ir.sequence'].next_by_code(sequence_code) or vals['name']
        return result

    @api.multi
    def button_confirm(self):
        for order in self:
            for line in order.order_line:
                if line.request_line_id:
                    if line.product_qty > line.request_line_id.residual:
                        raise Warning(_("Terjadi kesalahan (T.T). \n"
                                            "Sisa Qty Produk %s Di PR tinggal %s %s.") % (line.product_id.name, line.request_line_id.residual, line.product_uom.name))
            if order.state not in ['draft', 'sent']:
                continue
            order._add_supplier_to_product()
            # Deal with double validation process
            if order.company_id.po_double_validation == 'one_step' \
                    or (order.company_id.po_double_validation == 'two_step' \
                        and order.amount_total < self.env.user.company_id.currency_id.compute(
                        order.company_id.po_double_validation_amount, order.currency_id)) \
                    or order.user_has_groups('purchase.group_purchase_manager'):
                order.button_approve()
            else:
                order.button_approve()
            if order.purchase_request_ids:
                for request in order.purchase_request_ids:
                    if request.finished == True:
                        request.button_done()
                    else:
                        request.write({'state': 'approved'})
            if order.purchase_rfq_ids:
                for rfq in order.purchase_rfq_ids:
                    if rfq.finished == True:
                        rfq.write({'state': 'purchased'})
                    else:
                        rfq.write({'state': 'sent'})
        return True

    @api.multi
    def button_cancel(self):
        result = super(purchase_order, self).button_cancel()
        for order in self:
            if order.purchase_request_ids:
                for request in order.purchase_request_ids:
                    if request.finished == True:
                        request.button_done()
                    else:
                        request.write({'state': 'approved'})
            if order.purchase_rfq_ids:
                for rfq in order.purchase_rfq_ids:
                    if rfq.finished == True:
                        rfq.write({'state': 'purchased'})
                    else:
                        rfq.write({'state': 'sent'})
        return result

    @api.onchange('purchase_request_ids')
    def onchange_purchase_request(self):
        detail_lines = [(5, 0, 0)]
        for each in self.purchase_request_ids:
            purchase_request = self.env['purchase.request'].search([('id','=',each.id)])
            for x in purchase_request:
                for lines in x.order_line:
                    vals = {
                        'order_id'          : self.id,
                        'name'		        : lines.product_id.name,
                        'product_id'	    : lines.product_id.id,
                        'scheduled_date'    : lines.scheduled_date,
                        'price_unit'	    : lines.product_id.last_purchase_price,
                        'product_qty'	    : lines.product_qty,
                        'product_uom'	    : lines.product_uom.id,
                    }
                    detail_lines.append((0,0,vals))
                self.order_line = detail_lines

    @api.onchange('purchase_rfq_ids')
    def onchange_purchase_rfq(self):
        detail_lines = [(5,0,0)]
        for each in self.purchase_rfq_ids:
            purchase_rfq = self.env['purchase.rfq'].search([('id','=',each.id)])
            for x in purchase_rfq:
                for lines in x.order_line:
                    vals = {
                        'order_id' 			: self.id,
                        'product_id'		: lines.product_id.id,
                        'scheduled_date' 	: lines.scheduled_date,
                        'price_unit'		: lines.unit_price,
                        'product_qty'		: lines.product_qty,
                        'product_uom'		: lines.product_uom.id,
                    }
                    detail_lines.append((0, 0, vals))
                self.order_line = detail_lines


class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'

    request_id		= fields.Many2one('purchase.request','PR')
    request_line_id	= fields.Many2one('purchase.request.line','PR Line')
    rfq_id 			= fields.Many2one('purchase.rfq', 'RFQ')
    rfq_line_id 	= fields.Many2one('purchase.rfq.line', 'RFQ Line')