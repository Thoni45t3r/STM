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
from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError

class WizardRequestToRfq(models.TransientModel):
    _name           = "wizard.request.to.rfq"
    _description    = "Purchase Request To RFQ"

    @api.model
    def default_get(self, fields):
        record_ids  = self._context.get('active_ids')
        result      = super(WizardRequestToRfq, self).default_get(fields)
        if record_ids:
            purchase_request    = self.env['purchase.request'].browse(self._context.get('active_ids', []))
            detail_lines        = []
            if any(pr.picking_type_id.id != purchase_request[-1].picking_type_id.id for pr in purchase_request):
                raise UserError(_("Sorry, 'Picking Type' must be same"))
            if any(pr.state != 'approved' for pr in purchase_request):
                raise UserError(_("You can only create RFQ when PR has already Approved State"))
            for request in purchase_request:
                for lines in request.line_ids:
                    vals = {
                        'request_id'            : request.id,
                        'product_id'            : lines.product_id.id,
                        'last_purchase_price'   : lines.last_purchase_price,
                        'product_uom_id'        : lines.product_uom_id.id,
                        'product_qty'           : lines.residual,
                        'scheduled_date'        : lines.scheduled_date,
                        'request_line_id'       : lines.id,
                    }
                    detail_lines.append((0, 0, vals))
            result['line_ids'] = detail_lines
        return result

    partner_ids         = fields.Many2many('res.partner', string='Vendor', domain=[('supplier', '=', True)])
    line_ids	        = fields.One2many('wizard.request.to.rfq.line', 'wizard_id', 'Detail')

    @api.multi
    def create_request_for_quotation(self):
        rfq_obj         = self.env['purchase.rfq']
        rfq_line_obj    = self.env['purchase.rfq.line']
        request_ids     = []
        self_ids        = []
        for header in self.partner_ids:
            values_header = {
                'partner_id'            : header and header.id or False,
                'picking_type_id'       : self.line_ids[-1] and self.line_ids[-1].request_id and self.line_ids[-1].request_id.picking_type_id and self.line_ids[-1].request_id.picking_type_id.id or False,
                'request_ids'           : [(6, 0, [request.request_id.id for request in self.line_ids])]
            }
            new_rfq_id  = rfq_obj.create(values_header)
            if new_rfq_id:
                self_ids.append(new_rfq_id.id)
                for line in self.line_ids:
                    request_ids.append(line.request_id and line.request_id.id)
                    values_line = {
                        'rfq_id'                : new_rfq_id.id,
                        'product_id'            : line.product_id and line.product_id.id or False,
                        'name'                  : line.request_line_id.name,
                        'last_purchase_price'   : line.last_purchase_price,
                        'scheduled_date'        : line.scheduled_date,
                        'product_qty'           : line.product_qty,
                        'product_uom_id'        : line.product_uom_id and line.product_uom_id.id or False,
                        'request_id'            : line.request_id and line.request_id.id or False,
                        'request_line_id'       : line.request_line_id and line.request_line_id.id or False,
                        'state'                 : 'draft',
                    }
                    rfq_line_obj.create(values_line)
        action              = self.env.ref('c10i_purchase_request.action_purchase_rfq').read()[0]
        action['context']   = {'search_default_request_ids' : list(set(request_ids))}
        action['domain']    = [('id', 'in', self_ids)]
        return action

class PrMakeRfqLine(models.TransientModel):
    _name           = "wizard.request.to.rfq.line"
    _description    = "Purchase Request To RFQ Line"

    wizard_id           = fields.Many2one('wizard.request.to.rfq','Parent Wizard')
    request_id		    = fields.Many2one('purchase.request','Purchase Request')
    request_line_id     = fields.Many2one('purchase.request.line','PR Line')
    product_id 		    = fields.Many2one('product.product','Product')
    product_qty 	    = fields.Float('Product Qty')
    product_uom_id	    = fields.Many2one('product.uom','UoM')
    scheduled_date      = fields.Date('Date Planned')
    last_purchase_price = fields.Float('Last Price', related='product_id.product_tmpl_id.last_purchase_price')
