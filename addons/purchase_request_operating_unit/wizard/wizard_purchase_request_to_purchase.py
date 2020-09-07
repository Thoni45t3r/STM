# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Dion Martin H
#   @modifier Hendra Saputra <hendrasapura0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
import time
import datetime
from odoo import api, fields, models, SUPERUSER_ID, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError

class WizardPurchaseRequestToPurchase(models.TransientModel):
    _inherit    = "wizard.purchase.request.to.purchase"

    @api.model
    def default_get(self, fields):
        record_ids  = self._context.get('active_ids')
        result      = super(WizardPurchaseRequestToPurchase, self).default_get(fields)
        if record_ids:
            purchase_request    = self.env['purchase.request'].browse(self._context.get('active_ids', []))
            if len(list(set([pr.operating_unit_id for pr in purchase_request]))) > 1:
                raise UserError(_("You can only create RFQ of the same Operating Unit"))
        return result

    @api.multi
    def create_purchase(self):
        ctx = self.env.context.copy()
        purchase_request    = self.env['purchase.request'].browse(self._context.get('active_ids', []))
        for pr in purchase_request:
            ctx.update({'operating_unit_id' : pr.operating_unit_id.id})
            result      = super(WizardPurchaseRequestToPurchase, self.with_context(ctx)).create_purchase()
            if result['domain'][-1]:
                data_po = self.env['purchase.order'].search([result['domain'][-1]])
                for data_po_line in data_po:
                    data_po_line.write({
                        'operating_unit_id'     : self.line_ids[-1] and self.line_ids[-1].request_id and self.line_ids[-1].request_id.operating_unit_id and self.line_ids[-1].request_id.operating_unit_id.id or False
                    })
                    for line in data_po_line.order_line:
                        line.write({
                            'operating_unit_id' : line.request_id and line.request_id.operating_unit_id and line.request_id.operating_unit_id.id or False,
                        })
            return result