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

from odoo import models, fields, api
from odoo.exceptions import except_orm, Warning, RedirectWarning

STATUS = [('draft', 'Draft'),
			('sent', 'RFQ Sent'),
			('purchased', 'Purchased'),
			('rejected', 'Rejected')]

class purchase_rfq(models.Model):
    _name 			= 'purchase.rfq'
    _description 	= 'Form Permintaan Penawaran'
    _inherit 		= ['mail.thread', 'ir.needaction_mixin']

    @api.model
    def _company_get(self):
	    company_id = self.env['res.company']._company_default_get(self._name)
	    return self.env['res.company'].browse(company_id.id)

    name 					= fields.Char('Name', default="New", track_visibility='onchange')
    company_id				= fields.Many2one('res.company', 'Company', default=_company_get, track_visibility='onchange')
    currency_id				= fields.Many2one('res.currency', 'Currency', default=lambda self: self.env['res.company']._company_default_get().currency_id, track_visibility='onchange')
    partner_id				= fields.Many2one('res.partner', 'Vendor', domain=[('supplier', '=', True)], track_visibility='onchange')
    date 					= fields.Date('Tangggal', default=fields.Date.today(), track_visibility='onchange')
    state 					= fields.Selection(selection=STATUS, string='State', default='draft', track_visibility='onchange')
    count_purchase			= fields.Integer('Purchase Order', compute='_compute_purchase')
    request_ids				= fields.Many2many('purchase.request')
    finished                = fields.Boolean('Finished', compute="_compute_finished")
    product_service         = fields.Boolean('Service Product', default=False, copy=False, compute='_checked_type_product')
    product_other           = fields.Boolean('Non Service Product', default=False, copy=False, compute='_checked_type_product')
    line_ids 				= fields.One2many(comodel_name='purchase.rfq.line', inverse_name='rfq_id', string='RFQ Lines', copy=True)
    picking_type_id 		= fields.Many2one('stock.picking.type', 'Picking Type', required=True, track_visibility='onchange')

    @api.multi
    @api.depends('line_ids.product_id')
    def _checked_type_product(self):
        for pr_line in self.line_ids:
            if pr_line.product_id.type == 'service':
                self.product_service = True
            else:
                self.product_other = True

    @api.multi
    def _compute_finished(self):
        for rfq_self in self:
            if rfq_self.state in ['sent', 'purchased']:
                residual = 0
                for rfq in rfq_self.line_ids:
                    residual += rfq.request_residual
                if residual == 0:
                    rfq_self.finished = True
                else:
                    rfq_self.finished = False

    @api.multi
    def _compute_purchase(self):
        for order in self:
            po_obj = self.env['purchase.order'].search([('id','!=',0)])
            count = 0
            for x in po_obj:
                if order.id in x.purchase_rfq_ids.ids:
                    count += 1
            self.count_purchase = count

    @api.multi
    def action_view_purchase(self):
        self.ensure_one()
        action 				= self.env.ref('purchase.purchase_form_action').read()[0]
        action['context'] 	= {'search_default_purchase_rfq_ids': self.id}
        return action

    @api.model
    def create(self, vals):
        vals['name'] = (vals.get('name','New')=='New' or 'name' not in vals.keys()) and self.env['ir.sequence'].next_by_code('seq.purchase.rfq') or vals.get('name','New')
        return super(purchase_rfq, self).create(vals)

	@api.onchange('request_ids')
	def onchange_purchase_request(self):
		detail_lines = [(5, 0, 0)]
		for each in self.request_ids:
			purchase_request = self.env['purchase.request'].search([('id', '=', each.id)])
			for x in purchase_request:
				for lines in x.line_ids:
					vals = {
						'order_id'          : self.id,
						'product_id'	    : lines.product_id.id,
						'scheduled_date'    : lines.scheduled_date,
						'product_qty'	    : lines.product_qty,
						'product_uom'	    : lines.product_uom.id,
						'pr_id'			    : lines.order_id.id,
					}
					detail_lines.append((0, 0, vals))
				self.order_line = detail_lines

    @api.one
    def button_sent(self):
        self.state = 'sent'

    @api.one
    def button_rejected(self):
        self.state = 'rejected'

class purchase_rfq_line(models.Model):
    _name = 'purchase.rfq.line'

    product_id 			= fields.Many2one('product.product','Product')
    name                = fields.Char('Name')
    unit_price 			= fields.Float('Unit Price')
    last_purchase_price	= fields.Float('Last Price')
    scheduled_date		= fields.Date('Scheduled Date')
    product_qty 		= fields.Float('Product Qty')
    product_uom_id		= fields.Many2one('product.uom','UoM')
    total_price 		= fields.Float('Total Price', compute='_compute_total_price', store=True)
    rfq_id 				= fields.Many2one('purchase.rfq')
    request_id			= fields.Many2one('purchase.request','PR')
    request_line_id		= fields.Many2one('purchase.request.line','PR Line')
    request_residual    = fields.Float('PR Residual', related="request_line_id.residual", readonly=True)
    state 				= fields.Selection(selection=STATUS, string='State', related="rfq_id.state")

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.unit_price 		= self.product_id.product_tmpl_id.last_purchase_price
        self.product_uom_id 	= self.product_id.uom_po_id.id

    @api.depends('unit_price', 'product_qty')
    def _compute_total_price(self):
        for rfq in self:
            rfq.total_price = rfq.unit_price * rfq.product_qty