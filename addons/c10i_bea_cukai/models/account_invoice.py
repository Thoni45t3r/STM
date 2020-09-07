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

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def write(self, vals):
        for inv in self:
            purchases = self.env['purchase.order'].sudo()
            for x in inv.invoice_line_ids:
                if x.purchase_line_id:
                    purchases |= x.purchase_line_id.order_id
            for purchase in purchases.filtered(lambda x: x.bea_cukai_id):
                if vals.get('nomer_seri_faktur_pajak_bill'):
                    if inv.nomer_seri_faktur_pajak_bill and inv.nomer_seri_faktur_pajak_bill!=vals['nomer_seri_faktur_pajak_bill']:
                        current_fp = self.env['bea.cukai.faktur.pajak'].sudo().search([
                            ('bea_cukai_id','=',purchase.bea_cukai_id.id),
                            ('faktur_pajak','=',inv.nomer_seri_faktur_pajak_bill)
                        ])
                        if current_fp:
                            current_fp.write({'faktur_pajak': vals['nomer_seri_faktur_pajak_bill'],
                                    'faktur_pajak_date': vals.get('date_faktur_pajak_bill', inv.date_faktur_pajak_bill)})
                        else:
                            bea_cukai_ids = purchase.sudo().picking_ids.mapped('bea_cukai_ids').filtered(
                                lambda x: x.id == purchase.bea_cukai_id.id)
                            for doc in bea_cukai_ids:
                                if not (doc.faktur_pajak_ids.filtered(
                                        lambda x: x.faktur_pajak == vals.get('nomer_seri_faktur_pajak_bill'))):
                                    doc.faktur_pajak_ids = [(0, 0, {
                                        'bea_cukai_id': doc.id,
                                        'faktur_pajak': vals.get('nomer_seri_faktur_pajak_bill'),
                                        'faktur_pajak_date': vals.get('date_faktur_pajak_bill', inv.date_faktur_pajak_bill)})]
                    elif not inv.nomer_seri_faktur_pajak_bill:
                        bea_cukai_ids = purchase.sudo().picking_ids.mapped('bea_cukai_ids').filtered(
                            lambda x: x.id == purchase.bea_cukai_id.id)
                        for doc in bea_cukai_ids:
                            if not (doc.faktur_pajak_ids.filtered(
                                    lambda x: x.faktur_pajak == vals.get('nomer_seri_faktur_pajak_bill'))):
                                doc.faktur_pajak_ids = [(0, 0, {
                                        'bea_cukai_id': doc.id,
                                        'faktur_pajak': vals.get('nomer_seri_faktur_pajak_bill'),
                                        'faktur_pajak_date': vals.get('date_faktur_pajak_bill')})]
                    else:
                        current_fp = self.env['bea.cukai.faktur.pajak'].sudo().search([
                            ('bea_cukai_id', '=', purchase.bea_cukai_id.id),
                            ('faktur_pajak', '=', inv.nomer_seri_faktur_pajak_bill)])
                        if current_fp:
                            current_fp.unlink()
                elif inv.nomer_seri_faktur_pajak_bill and vals.get('date_faktur_pajak_bill'):
                    current_fp = self.env['bea.cukai.faktur.pajak'].sudo().search([
                        ('bea_cukai_id','=',purchase.bea_cukai_id.id),
                        ('faktur_pajak','=',inv.nomer_seri_faktur_pajak_bill)])
                    if current_fp:
                        current_fp.write({'faktur_pajak_date': vals['date_faktur_pajak_bill']})
        return super(AccountInvoice, self).write(vals)

    @api.model
    def create(self, vals):
        res = super(AccountInvoice, self).create(vals)
        purchases = self.env['purchase.order'].sudo()
        for x in res.invoice_line_ids:
            purchases |= x.purchase_line_id.order_id
        for purchase in purchases.filtered(lambda x: x.bea_cukai_id):
            if vals.get('nomer_seri_faktur_pajak_bill',False):
                bea_cukai_ids = purchase.filtered(lambda x: x.bea_cukai_id).sudo().picking_ids.mapped('bea_cukai_ids').filtered(lambda x: x.id==purchase.bea_cukai_id.id)
                for doc in bea_cukai_ids:
                    if not (doc.faktur_pajak_ids.filtered(lambda x: x.faktur_pajak==vals.get('nomer_seri_faktur_pajak_bill'))):
                        doc.faktur_pajak_ids = [(0,0,{'bea_cukai_id': doc.id,
                                'faktur_pajak': vals.get('nomer_seri_faktur_pajak_bill'),
                                'faktur_pajak_date': vals.get('date_faktur_pajak_bill')})]
        return res