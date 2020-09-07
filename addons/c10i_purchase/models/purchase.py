# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Dion Martin
#   @modifier Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError, except_orm, Warning, RedirectWarning, ValidationError
import odoo.addons.decimal_precision as dp
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF

class PurchaseType(models.Model):
    _name = 'purchase.type'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True, size=10, copy=False)
    sequence_id = fields.Many2one('ir.sequence', 'Sequence', copy=False)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id.id)
    active = fields.Boolean('Active', default=True)

    @api.multi
    def write(self, vals):
        for purchase_type in self:
            if ('code' in vals and purchase_type.code != vals['code']):
                if self.env['purchase.order'].search([('purchase_type_id', 'in', self.ids)], limit=1):
                    raise UserError(_('This Purchase Type already contains Purchase Order, therefore you cannot modify its short name.'))
                new_prefix = vals['code'].upper()+'/%(range_year)s/%(month)s/'
                purchase_type.sequence_id.write({'prefix': new_prefix})
        result = super(PurchaseType, self).write(vals)
        return result

    @api.model
    def create(self, vals):
        if not vals.get('sequence_id'):
            vals.update({'sequence_id': self.sudo()._create_sequence(vals).id})
        purchase_type = super(PurchaseType, self).create(vals)
        return purchase_type

    @api.model
    def _create_sequence(self, vals):
        prefix = vals['code'].upper()+'/%(range_year)s/%(month)s/'
        seq = {
            'name': vals['name'],
            'implementation': 'no_gap',
            'prefix': prefix,
            'padding': 4,
            'number_increment': 1,
            'use_date_range': True,
        }
        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        return self.env['ir.sequence'].create(seq)

class PurchaseOrder(models.Model):
    _inherit        = 'purchase.order'

    shipping_partner_id = fields.Many2one('res.partner', 'Delivery Address', default=lambda self: self.env.user.company_id.default_purchase_shipping_partner_id and self.env.user.company_id.default_purchase_shipping_partner_id.id or False)
    invoice_partner_id 	= fields.Many2one('res.partner', 'Invoice Address', default=lambda self: self.env.user.company_id.default_purchase_invoice_partner_id and self.env.user.company_id.default_purchase_invoice_partner_id.id or False)
    product_type        = fields.Selection([('stockable', 'Stockable'), ('service', 'Service'), ('all', 'All')], 'Product Type', default="all", compute="_get_product_type", store=True)
    purchase_type_id    = fields.Many2one('purchase.type', 'Purchase Type', copy=False, readonly=True, states={'draft': [('readonly',False)]})
    report_sign_1       = fields.Char("Sign 1", default="Purchasing")
    report_sign_2       = fields.Char("Sign 2", default="Accounting")
    report_sign_3       = fields.Char("Sign 3", default="Accounting")
    report_sign_4       = fields.Char("Sign 4", default="Accounting")
    report_sign_5       = fields.Char("Sign 5", default="Finance")
    report_sign_6       = fields.Char("Sign 6", default="Finance")

    @api.multi
    def print_report_purchase(self):
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : 'report_nota_purchase_order',
            'datas'         : {
                'model'         : 'purchase.order',
                'id'            : self.id,
                'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or [],
                'name'          : self.name or "---",
                },
            'nodestroy'     : False
        }

    @api.depends('order_line')
    def _get_product_type(self):
        for res in self:
            for line in res.order_line:
                if all(line.product_id.type == 'product' for line in res.order_line):
                    res.product_type = 'stockable'
                elif all(line.product_id.type == 'service' for line in res.order_line):
                    res.product_type = 'service'
                else:
                    res.product_type = 'all'

    # @api.model
    # def create(self, vals):
        # maaf ya ndra sementara dulu
        # purchase = super(PurchaseOrder,self).create(vals)
        # if vals.get('purchase_type_id'):
        #     new_name = self.env['purchase.type'].browse(vals['purchase_type_id']).with_context(ir_sequence_date=datetime.strptime(vals['date_order'],DT).strftime(DF)).sequence_id.next_by_id()
        #     purchase.write({'name': new_name})
        # return purchase

    @api.multi
    def write(self, update_vals):
        for order in self:
            if 'purchase_type_id' in update_vals and order.purchase_type_id!=update_vals['purchase_type_id']:
                new_name = self.env['purchase.type'].browse(update_vals['purchase_type_id']).with_context(ir_sequence_date=order.date_order).sequence_id.next_by_id()
                order.name = new_name
        return super(PurchaseOrder,self).write(update_vals)