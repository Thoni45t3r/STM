# -*- coding: utf-8 -*-# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2019 Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError, except_orm, Warning, RedirectWarning, ValidationError

class OtherStock(models.Model):
    _name = 'other.stock'
    _description = 'Stok Lainnya'

    name = fields.Char('Name', required=False)
    date = fields.Date('Tanggal Transaksi', required=True)
    state = fields.Selection([('draft','Draft'),('done','Done')], string='State', default='draft')
    line_ids = fields.One2many('other.stock.line', 'other_stock_id', 'Detail Stok', required=True)
    type = fields.Selection([('opening','Saldo Awal'),('incoming','Pemasukan'),('outgoing','Pengeluaran')], string='Tipe Transaksi', default='incoming')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id, readonly=True, states={'draft': [('readonly',False)]})

    @api.multi
    def action_done(self):
    	self.write({'state': 'done'})
    	return True

    @api.multi
    def action_draft(self):
    	self.write({'state': 'draft'})
    	return True

class OtherStockLine(models.Model):
	_name = 'other.stock.line'
	_description = 'Detail Stok Lainnya'

	other_stock_id = fields.Many2one('other.stock', 'Reference')
	# name = fields.Char('Description')
	product_id =fields.Many2one('product.product', 'Product', required=True)
	product_uom = fields.Many2one('product.uom', 'Unit of Measure', required=True)
	product_qty = fields.Float('Quantity')

	@api.onchange('product_id')
	def onchange_product(self):
		self.product_uom = self.product_id.uom_id