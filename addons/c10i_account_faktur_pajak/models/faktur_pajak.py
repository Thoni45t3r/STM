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

KODE_TRANSAKSI_FAKTUR_PAJAK = [
    ('01','01'),
    ('02','02'),
    ('03','03'),
    ('04','04'),
    ('05','05'),
    ('06','06'),
    ('07','07'),
    ('08','08'),
    ('09','09'),
]

class BatchFakturPajakKeluaran(models.Model):
    _name = 'batch.faktur.pajak.keluaran'
    _description = "Input Faktur Pajak Keluaran"

    name = fields.Char('No.', readonly=True, required=True, default='/')
    nomer_perusahaan = fields.Char('Nomer Perusahaan', size=3, required=True, readonly=True, states={'draft': [('readonly',False)]})
    tahun_buat = fields.Char('Tahun Diterbitkan', size=2,  required=True, readonly=True, states={'draft': [('readonly',False)]})
    nomer_awal = fields.Integer('Nomer Awal', size=8, required=True, readonly=True, states={'draft': [('readonly',False)]})
    nomer_akhir = fields.Integer('Nomer Akhir', size=8, required=True, readonly=True, states={'draft': [('readonly',False)]})
    faktur_keluaran_ids = fields.One2many('faktur.pajak.keluaran', 'batch_id', string='Faktur Pajak Keluaran', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('validated', 'Validated'), ('cancel', 'Cancelled')], 'Status', default='draft')
    create_date = fields.Date('Date', default=datetime.today())
    company_id = fields.Many2one('res.company', 'Company', default=lambda self:self.env.user.company_id)

    @api.one
    def generate_faktur(self):
        if self.faktur_keluaran_ids:
            return True
        nomer_awal = self.nomer_awal
        while (nomer_awal <= self.nomer_akhir):
            seri = ''
            if (len(str(nomer_awal)) >= 8):
                seri = str(nomer_awal)
            else:
                seri = (8-len(str(nomer_awal)))*'0' + str(nomer_awal)
            
            val = {
                'nomer_perusahaan': self.nomer_perusahaan,
                'tahun_buat': self.tahun_buat,
                'nomer_seri': seri,
                'batch_id': self.id,
                'state': 'draft',
            }
            self.env['faktur.pajak.keluaran'].create(val)
            nomer_awal += 1
        return True

    @api.one
    def action_validate(self):
        if not self.faktur_keluaran_ids:
            self.generate_faktur()
        return self.write({'state': 'validated'})

    @api.one
    def action_cancel(self):
        return self.write({'state': 'cancel'})

    @api.one
    def action_set_to_draft(self):
        return self.write({'state': 'draft'})

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code(self._name)
        return super(BatchFakturPajakKeluaran, self).create(vals)

    @api.model
    def unlink(self):
        not_allowed = False
        for batch in self:
            for faktur in batch.faktur_keluaran_ids:
                if faktur.invoice_ids:
                    not_allowed = True
            if batch.state!='draft':
                not_allowed = True
        if not_allowed:
            raise osv.except_osv(_('Error Deletion'), _("You cannot delete this because it is already linked with Invoice"))
        else:
            return super(BatchFakturPajakKeluaran, self).unlink()

    @api.model
    def copy(self, default_val):
        default_val = {
            'name': '/',
            'state': 'draft',
            'nomer_awal': 0,
            'nomer_akhir': 0,
            'create_date': datetime.today(),
            'faktur_keluaran_ids': [],
        }
        return super(BatchFakturPajakKeluaran, self).copy(default_val)


class FakturPajakKeluaran(models.Model):
    _name = 'faktur.pajak.keluaran'
    _description = "Faktur Pajak Keluaran"

    nomer_perusahaan = fields.Char('Nomer Perusahaan', size=3, readonly=True)
    tahun_buat = fields.Char('Tahun Diterbitkan', size=2, readonly=True)
    nomer_seri = fields.Char('Nomer Seri', readonly=True)
    name = fields.Char(compute='_nomer_faktur', string="Nomer Faktur", store=True, readonly=True)
    state = fields.Selection(compute='_get_state', selection=[('draft','Not Available'), ('available','Available'), 
        ('invoiced','Invoiced'), ('returned','Returned'), ('cancel','Cancelled')], string='Status', store=True)
    active = fields.Boolean("Active", default=True, readonly=True)
    invoice_ids = fields.One2many('account.invoice', 'faktur_keluaran_id', string='Account Invoice', readonly=True)
    batch_id = fields.Many2one('batch.faktur.pajak.keluaran', string='Batch Ref', ondelete='cascade')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self:self.env.user.company_id)

    #related fields
    invoice_id = fields.Many2one(compute='_get_last_invoice', comodel_name="account.invoice", string="Invoice", store=True)
    partner_id = fields.Many2one(related='invoice_id.partner_id', comodel_name="res.partner", string='Customer')
    customer_npwp = fields.Char(related='invoice_id.partner_id.npwp_number', size=20, string='NPWP')
    # period_id = fields.Many2one(related='invoice_id.move_id.period_id', comodel_name="account.period", string="Masa Pajak")

    @api.one
    @api.depends('nomer_perusahaan', 'tahun_buat', 'nomer_seri')
    def _nomer_faktur(self):
        self.name = "%s.%s.%s" % (self.nomer_perusahaan, self.tahun_buat, self.nomer_seri)

    @api.one
    @api.depends('invoice_ids.faktur_keluaran_id', 'batch_id.state', 'active')
    def _get_state(self):
        if self.batch_id.state == 'validated':
            state = 'available'
        else:
            state = 'draft'
        
        for invoice in self.invoice_ids:
            if invoice.type == 'out_invoice':
                state = 'invoiced'
            elif invoice.type == 'out_refund':
                state = 'returned'

        if not self.active:
            state = 'cancel'
        
        self.state = state

    @api.one
    @api.depends('invoice_ids.state')
    def _get_last_invoice(self):
        self.invoice_id = False
        for invoice in self.invoice_ids:
            if invoice.type == 'out_invoice':
                self.invoice_id = invoice.id
            elif invoice.type == 'out_refund':
                self.invoice_id = invoice.id

    @api.model
    def unlink(self):
        not_allowed = False
        if self.invoice_ids:
            not_allowed = True
        if self.batch_id:
            not_allowed = True
        
        if not_allowed:
            raise osv.except_osv(_('Error Deletion'), _("You cannot delete this because it is already linked with Invoice"))
        else:
            return super(FakturPajakKeluaran, self).unlink()

    @api.model
    def copy(self, default_val):
        raise osv.except_osv(_('Error Duplication'), _("Duplicate feature for this document is not allowed"))

class FakturPajakMasukan(models.Model):
    _name = 'faktur.pajak.masukan'
    _description = 'Faktur Pajak Masukan'

    kdJenisTransaksi = fields.Char('Kode Jenis Transaksi', size=2)
    fgPengganti = fields.Char('Faktur Pengganti', size=1)
    nomorFaktur = fields.Char('Nomor Faktur', size=15)
    tanggalFaktur = fields.Date('Tgl. Faktur')
    npwpPenjual = fields.Char('NPWP Penjual',size=15)
    namaPenjual = fields.Char('Penjual', size=128)
    alamatPenjual = fields.Text('Alamat Penjual')
    npwpLawanTransaksi = fields.Char('NPWP Partner Transaksi')
    namaLawanTransaksi = fields.Char('Partner Transaksi',size=128)
    alamatLawanTransaksi = fields.Text('Alamat Partner Transaksi')
    jumlahDpp = fields.Float('Total DPP',digits=(16,0))
    jumlahPpn = fields.Float('Total PPn',digits=(16,0))
    jumlahPpnBm = fields.Float('Total PPnBM',digits=(16,0))
    statusApproval = fields.Char('Status Approval',size=256)
    statusFaktur = fields.Char('Status Faktur',size=256)
    referensi = fields.Char('Referensi',size=256)
    detailTransaksi = fields.One2many('faktur.pajak.masukan.line','faktur_masukan_id','Efaktur Lines')
    invoice_id = fields.Many2one('account.invoice', 'Vendor Bill')
    
    name = fields.Char(compute='_nomer_faktur', string="Nomer Faktur", store=True, readonly=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self:self.env.user.company_id)
    url = fields.Text('URL')

    @api.one
    @api.depends('nomorFaktur', 'fgPengganti', 'kdJenisTransaksi')
    def _nomer_faktur(self):
        self.name = "%s%s.%s"%(str(self.kdJenisTransaksi), str(self.fgPengganti), str(self.nomorFaktur))
        # self.name = "%s%s.%s-%s.%s"%(str(self.kdJenisTransaksi), str(self.fgPengganti), \
            # self.nomorFaktur[:3],self.nomorFaktur[:5][-2:],self.nomorFaktur[5:])

    @api.model
    def parse_url(self, url):
        ulib3 = urllib3.PoolManager()
        res = ulib3.request('GET', url)
        faktur_masukan = {}
        faktur_masukan_lines = []
        if res.status==200 and res.data:
            tree = etree.fromstring(res.data)
            for subtree in tree:
                if subtree.tag!='detailTransaksi':
                    if subtree.tag=="tanggalFaktur":
                        tanggal_faktur = datetime.strptime(subtree.text,"%d/%m/%Y").strftime('%Y-%m-%d')
                        faktur_masukan.update({subtree.tag: tanggal_faktur})
                    else:
                        faktur_masukan.update({subtree.tag: subtree.text})
                else:
                    dumpy = {}
                    for line in subtree.getchildren():
                        dumpy.update({line.tag: line.text})
                        if line.tag=='ppnbm':
                            faktur_masukan_lines.append(dumpy)
                            dumpy={}
            
            faktur_masukan.update({
                'detailTransaksi': faktur_masukan_lines,
                'url': url,
                })
        else:
            raise osv.except_osv(_('Error Connecting to Server'), _("The connection to http://svc.efaktur.pajak.go.id/ can not be established."))
        return faktur_masukan

class FakturPajakMasukanLine(models.Model):
    _name = 'faktur.pajak.masukan.line'
    _description = 'Detail Faktur Pajak Masukan'
    
    faktur_masukan_id = fields.Many2one('faktur.pajak.masukan', 'Efaktur', ondelete='cascade')
    nama = fields.Char('Nama Barang',size=256)
    hargaSatuan = fields.Float('Price Unit', digits=(16,4))
    jumlahBarang = fields.Float('Qty', digits=(16,4))
    hargaTotal = fields.Float('Subtotal', digits=(16,4))
    diskon = fields.Float('Discount', digits=(16,2))
    dpp = fields.Float('DPP', digits=(16,2))
    ppn = fields.Float('PPn', digits=(16,2))
    tarifPpnbm = fields.Float('Tarif PPnBM', digits=(16,4))
    ppnbm = fields.Float('PPnBM', digits=(16,4))