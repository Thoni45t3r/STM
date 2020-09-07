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
from odoo.exceptions import UserError, ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

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

    doc_type_id         = fields.Many2one("res.document.type", "Type", ondelete="restrict", readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, required=True, change_default=True, index=True, track_visibility='always', copy=True)
    downpayment         = fields.Float("Down Payment", readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, change_default=True, index=True, track_visibility='always', copy=False)
    downpayment_value   = fields.Float("Down Payment Amount", store=True, readonly=True, compute='_amount_downpayment', track_visibility='always', copy=False)
    downpayment_date    = fields.Date("Down Payment Date", readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, change_default=True, index=True, track_visibility='always', copy=False)
    auto_downpayment    = fields.Boolean(related="doc_type_id.auto_downpayment", string="Auto Down Payment", copy=False)
    user_id             = fields.Many2one('res.users', string='Responsible', index=True, track_visibility='onchange', default=lambda self: self.env.user)
    advance_invoice_id  = fields.Many2one('account.invoice.advance', string='Advance Invoice', track_visibility='onchange', copy=False)

    @api.multi
    def print_report_sale(self):
        if self.doc_type_id and self.doc_type_id.report_id:
            report_name = self.doc_type_id.report_id.report_name
        else:
            raise ValidationError(_("Terjadi kesalahan (T.T). \n"
                                        "Report Tidak Ditemukan!"))
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : report_name,
            'datas'         : {
                'model'         : 'sale.order',
                'id'            : self._context.get('active_ids') and self._context.get('active_ids')[0] or self.id,
                'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or [],
                'name'          : self.name or "---",
                },
            'nodestroy'     : False
        }

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
                'type'              : 'out_advance',
                'user_id'           : self.env.user.id or False,
                # 'reference'         : self.partner_ref,
                'currency_id'       : self.currency_id and self.currency_id.id or False,
                'journal_id'        : self.doc_type_id.downpayment_journal_id and self.doc_type_id.journal_id.id or False,
                'account_id'        : self.partner_id.property_account_receivable_id and self.partner_id.property_account_receivable_id.id or False,
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
                    'name'          : ('Advance Customer'),
                    'view_type'	    : 'form',
                    'view_mode'	    : 'form',
                    'res_model'	    : 'account.invoice.advance',
                    'res_id'	    : new_invoice_advance.id,
                    'type'		    : 'ir.actions.act_window',
                }

    @api.model
    def create(self, vals):
        if vals.get('doc_type_id') and self.env['res.document.type'].browse(vals['doc_type_id']) and self.env['res.document.type'].browse(vals['doc_type_id']).sequence_id:
            if vals.get('name', _('New')) == _('New'):
                if 'company_id' in vals:
                    vals['name'] = self.env['res.document.type'].browse(vals['doc_type_id']).sequence_id.with_context(force_company=vals['company_id']).next_by_id() or _('New')
                else:
                    vals['name'] = self.env['res.document.type'].browse(vals['doc_type_id']).sequence_id.next_by_id() or _('New')
        result = super(SaleOrder, self).create(vals)
        return result

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _action_procurement_create(self):
        for sale_line in self:
            if sale_line.order_id.doc_type_id.no_create_picking:
                return False
            else:
                result = super(SaleOrderLine, self)._action_procurement_create()
                return result