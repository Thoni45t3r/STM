# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

import calendar
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import float_compare, float_is_zero
import urllib3
import odoo.addons.decimal_precision as dp
from lxml import etree

# from faktur_pajak import KODE_TRANSAKSI_FAKTUR_PAJAK

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def advance_outstanding(self):
        self.ensure_one()
        if self.type=='in_invoice':
            advance_type = 'in_advance'
        elif self.type=='out_invoice':
            advance_type = 'out_advance'
        else:
            return False

        advance_line = self.env['account.invoice.advance.line'].search([
            ('invoice_id.partner_id','=',self.partner_id.id),('invoice_id.type','=',advance_type),
            ('reconciled','=',False),('invoice_id.operating_unit_id','=',self.operating_unit_id.id)])
        company_currency = self.journal_id.company_id.currency_id
        invoice_currenct = self.currency_id
        advance_lines = []
        for line in advance_line:
            vals = {
                'invoice_id': self.id,
                'advance_line_id': line.id,
                'amount_total': line.price_subtotal,
                'residual': line.residual,
                'amount': line.residual,
            }
            advance_lines.append(vals)
        self.register_advance_ids = list(map(lambda x: (0,0,x), advance_lines))
        # Compute Taxes
        taxes_grouped = self.get_taxes_values()
        tax_lines = self.tax_line_ids.filtered('manual')
        for tax in taxes_grouped.values():
            tax_lines += tax_lines.new(tax)
        self.tax_line_ids = tax_lines

class AccountInvoiceRegisterAdvance(models.Model):
    _inherit = 'account.invoice.register.advance'

    operating_unit_id = fields.Many2one('operating.unit',
                                        related='invoice_id.operating_unit_id',
                                        string='Operating Unit', store=True,
                                        readonly=True)