# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


import time

from odoo import api, fields, models, SUPERUSER_ID, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class PrMakePO(models.TransientModel):
    _name = "pr.make.po"
    _description = "PR Make PO"

    type_id 	= fields.Selection([('all','All Product'),
    								('several','Several')],'Type', default="all")
    partner_id = fields.Many2one('res.partner','Supplier', domain=[('supplier','=',True)])
    pr_line_ids	= fields.One2many('pr.make.po.line','pr_line_id','Detail')

    @api.onchange('type_id')
    def onchange_type(self):
    	purchase_request = self.env['purchase.request'].browse(self._context.get('active_ids', []))
    	detail_lines = [(5,0,0)]
    	for x in purchase_request:
    		for lines in x.order_line:
    			vals = {
    				'pr_id' : x.id,
    				'product_id' : lines.product_id.id,
    				'unit_price' : lines.unit_price,
	        		'product_uom' : lines.product_uom.id,
	        		'product_qty' : lines.product_qty,
	        		'total_price'	: lines.total_price,
	        		'pr_line_id'	: lines.id,
    			}
    			detail_lines.append((0,0,vals))
    	self.pr_line_ids = detail_lines

    @api.multi
    def create_po(self):
    	purchase_order_obj = self.env['purchase.order']
    	purchase_order_line_obj = self.env['purchase.order.line']
    	purchase_request = self.env['purchase.request'].browse(self._context.get('active_ids', []))
    	if any(pr.state != 'approval2' for pr in purchase_request):
            raise UserError(_("You can only create order when PR has already Approval 2 State"))
    	if any(pr.partner_id.id != purchase_request[0].partner_id.id and self.type_id == 'all' for pr in purchase_request):
            raise UserError(_("Sorry, Supplier must be same"))

        pr_ids = []
        for pr in purchase_request:
        	pr_id = pr.id
        	pr_ids.append(pr_id)

        if self.type_id == 'all':
	        purchase_order = purchase_order_obj.create({
	        		'partner_id' : self.partner_id.id,
	        		'purchase_request_ids'	: [(6,0,[pr_ids])]
	        	})
	        for x in purchase_request:
	        	for pr_line in x.order_line:
		        	purchase_order_line = purchase_order_line_obj.create({
		        		'order_id' : purchase_order.id,
		        		'pr_id'		: x.id,
		        		'product_id' : pr_line.product_id.id,
		        		'name'		: pr_line.product_id.name,
		        		'date_planned' : fields.Date.today(),
		        		'price_unit' : pr_line.unit_price,
		        		'product_uom' : pr_line.product_uom.id,
		        		'product_qty' : pr_line.product_qty,
		        		'total_price'	: pr_line.total_price,
		        		'pr_line_id'	: pr_line.id,
		        		})
	        #purchase_order.button_confirm()
		        #x.order_created = True:
	        	#self._create_order(x,purchase_order_line)
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
                'purchase_request_ids'	: [(6,0,[pr_ids])]
            })
			for x in self.pr_line_ids:
				purchase_order_line = purchase_order_line_obj.create({
				'order_id' : purchase_order.id,
				'pr_id'		: x.id,
				'product_id' : x.product_id.id,
				'name'		: x.product_id.name,
				'date_planned' : fields.Date.today(),
				'price_unit' : x.unit_price,
				'product_uom' : x.product_uom.id,
				'product_qty' : x.product_qty,
				'total_price'	: x.total_price,
				'pr_line_id' : x.pr_line_id.id,
				})
			#purchase_order.button_confirm()
			return {
				'name' : ('Request for Quotation'),
				'view_type'	: 'form',
				'view_mode'	: 'form',
				'res_model'	: 'purchase.order',
				'res_id'	: purchase_order.id,
				'type'		: 'ir.actions.act_window',
			}

class PrMakePOLine(models.TransientModel):
    _name = "pr.make.po.line"
    _description = "PR Make po Line"



    pr_line_id 					= fields.Many2one('pr.make.po',' ')
    pr_id 						= fields.Many2one('purchase.request','Purchase Request')
    product_id 					= fields.Many2one('product.product','Product')
    unit_price 					= fields.Float('Unit Price')
    product_qty 				= fields.Float('Product Qty')
    product_uom					= fields.Many2one('product.uom','UoM')
    total_price 				= fields.Float('Total Price')
    pr_line_id 					= fields.Many2one('purchase.request.line','PR Line')