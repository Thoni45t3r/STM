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


import time
import datetime
from odoo import api, fields, models, SUPERUSER_ID, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError

class WizardRfqToPurchase(models.TransientModel):
    _name 			= "wizard.rfq.to.purchase"
    _description 	= "RFQ To Purchase Order"

    @api.model
    def default_get(self, fields):
        record_ids = self._context.get('active_ids')
        result = super(WizardRfqToPurchase, self).default_get(fields)
        if record_ids:
            purchase_rfq    = self.env['purchase.rfq'].browse(self._context.get('active_ids', []))
            detail_lines    = []
            if self._context.get('service_order', False):
                result['service_order'] = True
            else:
                if any(pr.line_ids.filtered(lambda i: i.request_id and i.request_id.state!='approved') for pr in purchase_rfq):
                    raise UserError(_("You can only create PO when PR has already in Approved State"))
                if any(pr.state != 'sent' for pr in purchase_rfq):
                    raise UserError(_("You can only create PO when RFQ has already Sent State"))
                if any(pr.picking_type_id.id != purchase_rfq[-1].picking_type_id.id for pr in purchase_rfq):
                    raise UserError(_("Sorry, 'Picking Type' must be same"))
            for rfq in purchase_rfq:
                if rfq.partner_id:
                    result['partner_id']    = rfq.partner_id.id
                    result['currency_id']   = rfq.currency_id.id
                for lines in rfq.line_ids:
                    if self._context.get('service_order', False):
                        if lines.product_id.type == 'service':
                            vals = {
                                'product_id'			: lines.product_id.id,
                                'last_purchase_pric'	: lines.last_purchase_price,
                                'product_uom_id'		: lines.product_uom_id.id,
                                'product_qty'			: lines.product_qty,
                                'scheduled_date'		: lines.scheduled_date,
                                'request_id'		    : lines.request_id.id,
                                'unit_price'            : lines.unit_price,
                                'request_line_id'		: lines.request_line_id.id,
                                'rfq_id'		        : rfq.id,
                                'rfq_line_id'		    : lines.id,
                            }
                            detail_lines.append((0, 0, vals))
                    else:
                        if lines.product_id.type <> 'service':
                            vals = {
                                'product_id'			: lines.product_id.id,
                                'last_purchase_pric'	: lines.last_purchase_price,
                                'product_uom_id'		: lines.product_uom_id.id,
                                'product_qty'			: lines.product_qty,
                                'scheduled_date'		: lines.scheduled_date,
                                'request_id'		    : lines.request_id.id,
                                'unit_price'            : lines.unit_price,
                                'request_line_id'		: lines.request_line_id.id,
                                'rfq_id'		        : rfq.id,
                                'rfq_line_id'		    : lines.id,
                            }
                            detail_lines.append((0, 0, vals))
                    result['picking_type_id'] = rfq.picking_type_id.id or False
                result['line_ids'] = detail_lines
            return result

    partner_id 	    = fields.Many2one('res.partner', string='Vendor', domain=[('supplier', '=', True)])
    picking_type_id = fields.Many2one('stock.picking.type', string='Picking', domain=[('code', 'in', ['incoming'] )])
    currency_id     = fields.Many2one('res.currency', string='Currency')
    line_ids 		= fields.One2many('wizard.rfq.to.purchase.line', 'wizard_id', 'Detail')
    service_order   = fields.Boolean('Service Order')

    @api.multi
    def create_purchase(self):
        po_obj          = self.env['purchase.order']
        po_line_obj     = self.env['purchase.order.line']
        request_ids     = []
        self_ids        = []
        values_header = {
            'partner_id'            : self.partner_id and self.partner_id.id or False,
            'partner_ref'           : self.partner_id and self.partner_id.ref or '',
            'currency_id'           : self.currency_id and self.currency_id.id or '',
            'purchase_request_ids'  : [(6, 0, list(set([rfq.request_id.id for rfq in self.line_ids])))],
            'purchase_rfq_ids'      : [(6, 0, list(set([rfq.rfq_id.id for rfq in self.line_ids])))],
            'picking_type_id'       : self.line_ids[-1] and self.line_ids[-1].rfq_id and self.line_ids[-1].rfq_id.picking_type_id and self.line_ids[-1].rfq_id.picking_type_id.id or False
        }
        if self.service_order:
            values_header.update({'service_order': True})
        new_purchase_id = po_obj.create(values_header)
        if new_purchase_id and not self.service_order:
            self_ids.append(new_purchase_id.id)
            for line in self.line_ids:
                fpos = new_purchase_id.fiscal_position_id
                if self.env.uid == SUPERUSER_ID:
                    company_id = self.env.user.company_id.id
                    taxes_ids = fpos.map_tax(line.product_id.supplier_taxes_id.filtered(lambda r: r.company_id.id == company_id))
                else:
                    taxes_ids = fpos.map_tax(line.product_id.supplier_taxes_id)
                request_ids.append(line.request_id and line.request_id.id)
                if line.product_id.type <> 'service':
                    values_line = {
                        'order_id'          : new_purchase_id.id,
                        'product_id'        : line.product_id and line.product_id.id or False,
                        'request_id'        : line.request_id and line.request_id.id or False,
                        'request_line_id'   : line.request_line_id and line.request_line_id.id or False,
                        'rfq_id'            : line.rfq_id and line.rfq_id.id or False,
                        'rfq_line_id'       : line.rfq_line_id and line.rfq_line_id.id or False,
                        'name'              : line.request_line_id.name or '/',
                        'date_planned'      : line.scheduled_date or datetime.datetime.now().strftime('%Y-%m-%d'),
                        'product_qty'       : line.product_qty,
                        'product_uom'       : line.product_uom_id and line.product_uom_id.id or False,
                        'price_unit'        : line.unit_price,
                        'taxes_id'          : [(6, 0, taxes_ids.ids)],
                        'state'             : 'draft',
                    }
                    po_line_obj.create(values_line)
        if new_purchase_id and self.service_order:
            self_ids.append(new_purchase_id.id)
            for line in self.line_ids:
                fpos = new_purchase_id.fiscal_position_id
                if self.env.uid == SUPERUSER_ID:
                    company_id = self.env.user.company_id.id
                    taxes_ids = fpos.map_tax(line.product_id.supplier_taxes_id.filtered(lambda r: r.company_id.id == company_id))
                else:
                    taxes_ids = fpos.map_tax(line.product_id.supplier_taxes_id)
                request_ids.append(line.request_id and line.request_id.id)
                if line.product_id.type == 'service':
                    values_line = {
                        'order_id'          : new_purchase_id.id,
                        'product_id'        : line.product_id and line.product_id.id or False,
                        'request_id'        : line.request_id and line.request_id.id or False,
                        'request_line_id'   : line.request_line_id and line.request_line_id.id or False,
                        'rfq_id'            : line.rfq_id and line.rfq_id.id or False,
                        'rfq_line_id'       : line.rfq_line_id and line.rfq_line_id.id or False,
                        'name'              : line.request_line_id.name or '/',
                        'date_planned'      : line.scheduled_date or datetime.datetime.now().strftime('%Y-%m-%d'),
                        'product_qty'       : line.product_qty,
                        'product_uom'       : line.product_uom_id and line.product_uom_id.id or False,
                        'price_unit'        : line.unit_price,
                        'taxes_id'          : [(6, 0, taxes_ids.ids)],
                        'state'             : 'draft',
                    }
                    po_line_obj.create(values_line)
        action              = self.env.ref('purchase.purchase_form_action').read()[0]
        action['context']   = {'search_default_purchase_request_ids': list(set(request_ids))}
        action['domain']    = [('id', 'in', self_ids)]
        return action

class WizardRfqToPurchaseLine(models.TransientModel):
    _name 			= "wizard.rfq.to.purchase.line"
    _description 	= "RFQ To Purchase Order Line"

    wizard_id           = fields.Many2one('wizard.rfq.to.purchase', 'Parent Wizard')
    request_id          = fields.Many2one('purchase.request', 'Purchase Request')
    request_line_id     = fields.Many2one('purchase.request.line', 'PR Line')
    rfq_id              = fields.Many2one('purchase.rfq', 'RFQ')
    rfq_line_id         = fields.Many2one('purchase.rfq.line', 'RFQ Line')
    product_id          = fields.Many2one('product.product', 'Product')
    product_qty         = fields.Float('Product Qty')
    product_uom_id      = fields.Many2one('product.uom', 'UoM')
    scheduled_date      = fields.Date('Date Planned')
    unit_price          = fields.Float('Unit Price')
    last_purchase_price = fields.Float('Last Price', related='product_id.product_tmpl_id.last_purchase_price')