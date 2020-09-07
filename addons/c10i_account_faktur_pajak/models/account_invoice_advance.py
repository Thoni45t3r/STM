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
from lxml import etree

from faktur_pajak import KODE_TRANSAKSI_FAKTUR_PAJAK


class AccountInvoiceAdvance(models.Model):
    _inherit = 'account.invoice.advance'

    # Faktur Pajak Keluaran
    kode_transaksi = fields.Selection(selection=KODE_TRANSAKSI_FAKTUR_PAJAK, string='Kode Transaksi', readonly=True,
                                      states={'draft': [('readonly', False)]})
    kode_status_faktur = fields.Selection([('0', 'Normal'), ('1', 'Pengembalian')], string='Kode Status Faktur',
                                          readonly=True, states={'draft': [('readonly', False)]})
    faktur_keluaran_id = fields.Many2one('faktur.pajak.keluaran', 'Nomer Seri Faktur Pajak', readonly=True,
                                         states={'draft': [('readonly', False)]})
    nomer_seri_faktur_pajak = fields.Char(compute='_get_nsfp', string='NSFP Lengkap', store=True)
    # Faktur Pajak Masukan
    nomer_seri_faktur_pajak_bill = fields.Char(string='No. Faktur Pajak')
    date_faktur_pajak_bill = fields.Date('Tanggal Faktur')
    # qr_url_efaktur = fields.Text('QR Scanned Efaktur', readonly=True, states={'draft': [('readonly', False)]})
    # faktur_masukan_ids = fields.One2many('faktur.pajak.masukan', 'invoice_id', 'Scanned Faktur Pajak', readonly=True,
    #                                      states={'draft': [('readonly', False)]})

    @api.one
    @api.depends('faktur_keluaran_id', 'kode_transaksi', 'kode_status_faktur', 'nomer_seri_faktur_pajak_bill')
    def _get_nsfp(self):
        res = []
        if self.faktur_keluaran_id:
            self.nomer_seri_faktur_pajak = '%s%s.%s' % (self.kode_transaksi, \
                                                        self.kode_status_faktur, self.faktur_keluaran_id.name)
        elif self.nomer_seri_faktur_pajak_bill:
            self.nomer_seri_faktur_pajak = self.nomer_seri_faktur_pajak_bill

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        res = super(AccountInvoiceAdvance, self)._onchange_partner_id()
        self.kode_transaksi = self.partner_id.default_kode_transaksi
        return res