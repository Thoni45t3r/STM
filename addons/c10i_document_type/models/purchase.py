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
from odoo.exceptions import UserError, except_orm, Warning, RedirectWarning, ValidationError
import odoo.addons.decimal_precision as dp
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF


class PurchaseOrder(models.Model):
    _inherit        = 'purchase.order'

    @api.multi
    @api.depends('order_line.price_total', 'downpayment')
    def _amount_downpayment(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                if order.company_id.tax_calculation_rounding_method == 'round_globally':
                    price           = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    down_payment    = amount_untaxed * ((order.downpayment or 0.0) / 100.0)
                    taxes           = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=order.partner_shipping_id)
                    amount_tax      += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax
            order.update({
                'downpayment_value': amount_untaxed * ((order.downpayment or 0.0) / 100.0),
            })

    doc_type_id         = fields.Many2one("res.document.type", "Type", ondelete="restrict", readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, required=True, change_default=True, index=True, track_visibility='always')
    downpayment         = fields.Float("Down Payment", readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, change_default=True, index=True, track_visibility='always')
    downpayment_value   = fields.Float("Down Payment Amount", store=True, readonly=True, compute='_amount_downpayment', track_visibility='always')
    downpayment_date    = fields.Date("Down Payment Date", readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, change_default=True, index=True, track_visibility='always')
    auto_downpayment    = fields.Boolean(related="doc_type_id.auto_downpayment", string="Auto Down Payment")
    user_id             = fields.Many2one('res.users', string='Responsible', index=True, track_visibility='onchange', default=lambda self: self.env.user)
    advance_invoice_id  = fields.Many2one('account.invoice.advance', string='Advance Invoice', track_visibility='onchange')

    @api.multi
    def print_report_purchase(self):
        if self.doc_type_id and self.doc_type_id.report_id:
            report_name = self.doc_type_id.report_id.report_name
        else:
            report_name = 'report_nota_purchase_order'
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : report_name,
            'datas'         : {
                'model'         : 'purchase.order',
                'id'            : self.id,
                'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or [],
                'name'          : self.name or "---",
                },
            'nodestroy'     : False
        }

    @api.onchange('partner_id', 'company_id', 'doc_type_id')
    def onchange_partner_id(self):
        if not self.partner_id and not self.doc_type_id:
            self.fiscal_position_id = False
            self.payment_term_id    = False
            self.currency_id        = False
            self.ref                = False
            self.incoterm_id        = False
            self.shipping_partner_id= False
            self.invoice_partner_id = False
            self.report_sign_1      = False
            self.report_sign_2      = False
            self.report_sign_3      = False
            self.report_sign_4      = False
            self.report_sign_5      = False
            self.report_sign_6      = False
        elif self.partner_id and not self.doc_type_id:
            self.fiscal_position_id = self.env['account.fiscal.position'].with_context(company_id=self.company_id.id).get_fiscal_position(self.partner_id.id)
            self.payment_term_id    = self.partner_id.property_supplier_payment_term_id.id
            self.currency_id        = self.partner_id.property_purchase_currency_id.id or self.env.user.company_id.currency_id.id
            self.partner_ref        = self.partner_id.ref
            self.incoterm_id        = False
            self.shipping_partner_id= False
            self.invoice_partner_id = False
            self.report_sign_1      = False
            self.report_sign_2      = False
            self.report_sign_3      = False
            self.report_sign_4      = False
            self.report_sign_5      = False
            self.report_sign_6      = False
        elif self.partner_id and self.doc_type_id:
            self.payment_term_id    = self.partner_id.property_supplier_payment_term_id.id or self.doc_type_id.payment_term_id.id
            self.currency_id        = self.partner_id.property_purchase_currency_id.id or self.env.user.company_id.currency_id.id
            self.partner_ref        = self.partner_id.ref
            self.picking_type_id    = self.doc_type_id.picking_type_id and self.doc_type_id.picking_type_id.id or False
            self.incoterm_id        = self.doc_type_id.incoterm_id and self.doc_type_id.incoterm_id.id or False
            self.shipping_partner_id= self.doc_type_id.shipping_partner_id and self.doc_type_id.shipping_partner_id.id or False
            self.invoice_partner_id = self.doc_type_id.invoice_partner_id and self.doc_type_id.invoice_partner_id.id or False
            self.report_sign_1      = self.doc_type_id.purchase_report_sign_1 or "-"
            self.report_sign_2      = self.doc_type_id.purchase_report_sign_2 or "-"
            self.report_sign_3      = self.doc_type_id.purchase_report_sign_3 or "-"
            self.report_sign_4      = self.doc_type_id.purchase_report_sign_4 or "-"
            self.report_sign_5      = self.doc_type_id.purchase_report_sign_5 or "-"
            self.report_sign_6      = self.doc_type_id.purchase_report_sign_6 or "-"
            if self.auto_downpayment:
                self.downpayment        = self.doc_type_id.downpayment_default or 0.0
        elif self.doc_type_id and not self.partner_id:
            self.payment_term_id    = self.doc_type_id.payment_term_id and self.doc_type_id.payment_term_id.id or False
            self.picking_type_id    = self.doc_type_id.picking_type_id and self.doc_type_id.picking_type_id.id or False
            self.incoterm_id        = self.doc_type_id.incoterm_id and self.doc_type_id.incoterm_id.id or False
            self.shipping_partner_id= self.doc_type_id.shipping_partner_id and self.doc_type_id.shipping_partner_id.id or False
            self.invoice_partner_id = self.doc_type_id.invoice_partner_id and self.doc_type_id.invoice_partner_id.id or False
            self.report_sign_1      = self.doc_type_id.purchase_report_sign_1 or "-"
            self.report_sign_2      = self.doc_type_id.purchase_report_sign_2 or "-"
            self.report_sign_3      = self.doc_type_id.purchase_report_sign_3 or "-"
            self.report_sign_4      = self.doc_type_id.purchase_report_sign_4 or "-"
            self.report_sign_5      = self.doc_type_id.purchase_report_sign_5 or "-"
            self.report_sign_6      = self.doc_type_id.purchase_report_sign_6 or "-"
            if self.auto_downpayment:
                self.downpayment    = self.doc_type_id.downpayment_default or 0.0
        else:
            return {}
        return {}

    @api.multi
    def create_downpayment(self):
        invoice_advance_obj         = self.env['account.invoice.advance']
        invoice_advance_line_obj    = self.env['account.invoice.advance.line']
        if self.doc_type_id.auto_downpayment:
            header_values = {
                'partner_id'        : self.partner_id and self.partner_id.id or False,
                'payment_term_id'   : self.payment_term_id and self.payment_term_id.id or False,
                'name'              : self.name or "",
                'date_invoice'      : self.downpayment_date or False,
                'type'              : 'in_advance',
                'reference'         : self.partner_ref,
                'currency_id'       : self.currency_id and self.currency_id.id or False,
                'journal_id'        : self.doc_type_id.downpayment_journal_id and self.doc_type_id.journal_id.id or False,
                'account_id'        : self.partner_id.property_account_payable_id and self.partner_id.property_account_payable_id.id or False,
            }
            new_invoice_advance = invoice_advance_obj.sudo().create(header_values)
            if new_invoice_advance:
                if new_invoice_advance:
                    lines_value     = {
                        'name'              : "Uang Muka " + self.name,
                        'quantity'          : 1,
                        'price_unit'        : self.downpayment_value,
                        'price_subtotal'    : self.downpayment_value,
                        'account_id'        : self.doc_type_id.downpayment_account_id and self.doc_type_id.downpayment_account_id.id or False,
                        'invoice_id'        : new_invoice_advance.id
                    }
                    invoice_advance_line_obj.sudo().create(lines_value)
                self.advance_invoice_id = new_invoice_advance.id
            if new_invoice_advance:
                return {
                    'name'          : ('Advance Bills'),
                    'view_type'	    : 'form',
                    'view_mode'	    : 'form',
                    'res_model'	    : 'account.invoice.advance',
                    'res_id'	    : new_invoice_advance.id,
                    'type'		    : 'ir.actions.act_window',
                }

    @api.model
    def create(self, vals):
        if self._context.get('doc_type_id') and self.env['res.document.type'].browse(self._context.get('doc_type_id')).id:
            document_type   = self._context.get('doc_type_id') and self.env['res.document.type'].browse(self._context.get('doc_type_id'))
            vals['doc_type_id']   = document_type.id
            vals['report_sign_1']   = document_type.purchase_report_sign_1
            vals['report_sign_2']   = document_type.purchase_report_sign_2
            vals['report_sign_3']   = document_type.purchase_report_sign_3
            vals['report_sign_4']   = document_type.purchase_report_sign_4
            vals['report_sign_5']   = document_type.purchase_report_sign_5
            vals['report_sign_6']   = document_type.purchase_report_sign_6
        if vals.get('doc_type_id') and self.env['res.document.type'].browse(vals['doc_type_id']) and self.env['res.document.type'].browse(vals['doc_type_id']).sequence_id:
            if vals.get('name', _('New')) == _('New'):
                if 'company_id' in vals:
                    vals['name'] = self.env['res.document.type'].browse(vals['doc_type_id']).sequence_id.with_context(force_company=vals['company_id']).next_by_id() or _('New')
                else:
                    vals['name'] = self.env['res.document.type'].browse(vals['doc_type_id']).sequence_id.next_by_id() or _('New')
        result = super(PurchaseOrder, self).create(vals)
        return result

    @api.multi
    def _create_picking(self):
        if self.doc_type_id.no_create_picking:
            return False
        else:
            result = super(PurchaseOrder, self)._create_picking()
            return result