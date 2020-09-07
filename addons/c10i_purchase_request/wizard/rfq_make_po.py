# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


import time

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class RFQMakePO(models.TransientModel):
    _name = "rfq.make.po"
    _description = "RFQ Make PO"

    type_id 	    = fields.Selection([('all','All Product'),
    								('several','Several')],'Type', default="all")
    partner_id      = fields.Many2one('res.partner','Supplier', domain=[('supplier','=',True)])
    rfq_line_ids	= fields.One2many('rfq.make.po.line','rfq_line_id','Detail')


    @api.onchange('type_id')
    def onchange_type(self):
    	purchase_rfq = self.env['purchase.rfq'].browse(self._context.get('active_ids', []))
    	detail_lines = [(5,0,0)]
    	for x in purchase_rfq:
    		for lines in x.order_line:
    			vals = {
    				'rfq_id' : x.id,
    				'product_id' : lines.product_id.id,
    				'unit_price' : lines.unit_price,
	        		'product_uom' : lines.product_uom.id,
	        		'product_qty' : lines.product_qty,
	        		'total_price'	: lines.total_price,
    			}
    			detail_lines.append((0,0,vals))
    	self.rfq_line_ids = detail_lines


    @api.multi
    def create_po(self):
    	purchase_order_obj = self.env['purchase.order']
    	purchase_order_line_obj = self.env['purchase.order.line']
    	purchase_rfq = self.env['purchase.rfq'].browse(self._context.get('active_ids', []))
    	if any(rfq.state != 'approval1' for rfq in purchase_rfq):
            raise UserError(_("You can only create order when RFQ has already Approval 1 State"))
    	if any(rfq.partner_id.id != purchase_rfq[0].partner_id.id and self.type_id == 'all' for rfq in purchase_rfq):
            raise UserError(_("Sorry, Supplier must be same"))
        rfq_ids = []
        for rfq in purchase_rfq:
        	rfq_id = rfq.id
        	rfq_ids.append(rfq_id)

        if self.type_id == 'all':
	        purchase_order = purchase_order_obj.create({
	        		'partner_id' : self.partner_id.id,
	        		'purchase_rfq_ids'	: [(6,0,[rfq_ids])]
	        	})
	        for x in purchase_rfq:
	        	for rfq_line in x.order_line:
		        	purchase_order_line_obj.create({
		        		'order_id'      : purchase_order.id,
		        		'product_id'    : pr_line.product_id.id,
		        		'name'		    : pr_line.product_id.name,
		        		'date_planned'  : fields.Date.today(),
		        		'price_unit'    : pr_line.unit_price,
		        		'product_uom'   : pr_line.product_uom.id,
		        		'product_qty'   : pr_line.product_qty,
		        		'total_price'	: pr_line.total_price,
		        		})
	        purchase_order.button_confirm()
	        return {
				'name' : ('Request for Quotation'),
				'view_type'	: 'form',
				'view_mode'	: 'form',
				'res_model'	: 'purchase.order',
				'res_id'	: purchase_order.id,
				'type'		: 'ir.actions.act_window',
			}
        else:
			purchase_order = purchase_order_obj.create({
                'partner_id' : self.partner_id.id,
                'purchase_rfq_ids'	: [(6,0,[rfq_ids])]
            })
			for x in self.rfq_line_ids:
				purchase_order_line = purchase_order_line_obj.create({
                            'order_id'      : purchase_order.id,
                            'product_id'    : x.product_id.id,
                            'name'		    : x.product_id.name,
                            'date_planned'  : fields.Date.today(),
                            'price_unit'    : x.unit_price,
                            'product_uom'   : x.product_uom.id,
                            'product_qty'   : x.product_qty,
                            'total_price'	: x.total_price,
                            })
			#purchase_order.button_confirm()
			return {
				'name'      : ('Request for Quotation'),
				'view_type'	: 'form',
				'view_mode'	: 'form',
				'res_model'	: 'purchase.order',
				'res_id'	: purchase_order.id,
				'type'		: 'ir.actions.act_window',
			}

class RFQMakePOLine(models.TransientModel):
    _name = "rfq.make.po.line"
    _description = "RFQ Make po Line"

    rfq_line_id                 = fields.Many2one('rfq.make.po', 'RFQ Lines')
    rfq_id 						= fields.Many2one('purchase.rfq','Purchase RFQ')
    product_id 					= fields.Many2one('product.product','Product')
    unit_price 					= fields.Float('Unit Price')
    product_qty 				= fields.Float('Product Qty')
    product_uom					= fields.Many2one('product.uom','UoM')
    total_price 				= fields.Float('Total Price')