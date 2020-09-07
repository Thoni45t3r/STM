# -*- coding: utf-8 -*-# -*- coding: utf-8 -*-
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


class BeaCukaiDocumentType(models.Model):
    _name = 'bea.cukai.document.type'
    _description = 'Bea Cukai Document Type'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    company_id = fields.Many2one('res.company', string='Company', index=True,
                                 default=lambda self: self.env.user.company_id)
    active = fields.Boolean("Active", default=True)


class BeaCukai(models.Model):
    _name = 'bea.cukai'
    _description = 'Form Bea Cukai'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'submission_number ASC'

    name = fields.Char('Name', related='registration_number', required=False, store=True, readonly=True,
                       states={'draft': [('readonly', False)]})
    date = fields.Date('Tanggal Daftar', required=True, track_visibility='onchange',
                       default=lambda self: self._context.get('Date', fields.Date.context_today(self)), readonly=True,
                       states={'draft': [('readonly', False)]})
    type = fields.Many2one(comodel_name='bea.cukai.document.type', string='Type', readonly=True,
                           states={'draft': [('readonly', False)]})
    submission_number = fields.Char('Nomor Pengajuan', required=True, track_visibility='onchange', readonly=True,
                                    states={'draft': [('readonly', False)]})
    submission_date = fields.Date('Tanggal Pengajuan', required=True, track_visibility='onchange', readonly=True,
                                  states={'draft': [('readonly', False)]})
    registration_number = fields.Char('Nomor Pendaftaran', required=True, track_visibility='onchange', readonly=True,
                                      states={'draft': [('readonly', False)]})
    stock_picking_ids = fields.Many2many('stock.picking', 'bea_cukai_picking_rel', 'bea_cukai_id', 'stock_picking_id',
                                         string='Pickings', ondelete="restrict", copy=False, readonly=True,
                                         states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company', string='Company', index=True,
                                 default=lambda self: self.env.user.company_id, readonly=True,
                                 states={'draft': [('readonly', False)]})
    note = fields.Text("Note", readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection(selection=[('draft', 'Draft'), ('done', 'Locked')], string='Status',
                             copy=False, default='draft', index=False, readonly=False, track_visibility='always', )
    amount = fields.Float('Harga Pemberian', default=0.0, readonly=True, states={'draft': [('readonly', False)]})
    sale_id = fields.Many2one('sale.order', 'Sale Order', copy=False, readonly=True,
                              states={'draft': [('readonly', False)]})
    purchase_id = fields.Many2one('purchase.order', 'Purchase Order', copy=False, readonly=True,
                                  states={'draft': [('readonly', False)]})
    faktur_pajak_ids = fields.One2many('bea.cukai.faktur.pajak', 'bea_cukai_id', string='Faktur Pajak', readonly=True,
                                       states={'draft': [('readonly', False)]})
    source_bc_ids = fields.One2many('source.bea.cukai', 'bea_cukai_id', 'Asal BC', readonly=True, copy=False)
    bea_cukai_product_lines = fields.One2many('bea.cukai.product.line', 'bea_cukai_id', 'Detail Products', copy=False,
                                              readonly=True, states={'draft': [('readonly', False)]})

    @api.onchange('sale_id', 'purchase_id')
    def _onchange_sale_purchase(self):
        if self.sale_id:
            self.purchase_id = False
            self.amount = self.sale_id.amount_total
            detail_lines = []
            for line in self.sale_id.order_line:
                vals = {'product_id': line.product_id.id,
                        'price_unit': line.price_unit,
                        'product_uom': line.product_uom.id,
                        'currency_id': self.sale_id.pricelist_id.currency_id.id}
                if self.sale_id.pricelist_id.currency_id.id != self.company_id.currency_id.id:
                    vals.update({'price_unit_base_currency': 0.0})
                else:
                    vals.update({'price_unit_base_currency': line.price_unit})
                detail_lines.append(vals)
            self.bea_cukai_product_lines = detail_lines
        elif self.purchase_id:
            self.sale_id = False
            self.amount = self.purchase_id.amount_total
            detail_lines = []
            for line in self.purchase_id.order_line:
                vals = {'product_id': line.product_id.id,
                        'price_unit': line.price_unit,
                        'product_uom': line.product_uom.id,
                        'currency_id': self.purchase_id.currency_id.id}
                if self.purchase_id.currency_id.id != self.company_id.currency_id.id:
                    vals.update({'price_unit_base_currency': 0.0})
                else:
                    vals.update({'price_unit_base_currency': line.price_unit})
                detail_lines.append(vals)
            self.bea_cukai_product_lines = detail_lines

    @api.model
    def create(self, vals):
        res = super(BeaCukai, self).create(vals)
        res.ensure_one()
        if 'sale_id' in vals and vals.get('sale_id'):
            self.env['sale.order'].browse(res.sale_id.id).bea_cukai_id = res.id
            for do in res.sale_id.picking_ids.filtered(lambda x: not x.bea_cukai_ids and x.state == 'done'):
                do.bea_cukai_ids = [(4, res.id)]
        elif 'purchase_id' in vals and vals.get('purchase_id'):
            self.env['purchase.order'].browse(res.purchase_id.id).bea_cukai_id = res.id
            for grn in res.purchase_id.picking_ids.filtered(lambda x: not x.bea_cukai_ids and x.state == 'done'):
                grn.bea_cukai_ids = [(4, res.id)]
        return res

    @api.multi
    def write(self, vals):
        res = super(BeaCukai, self).write(vals)
        for bc in self:
            if 'sale_id' in vals:
                if not vals.get('sale_id', False):
                    self.env['sale.order'].browse(bc.sale_id.id).write({'bea_cukai_id': False})
                else:
                    self.env['sale.order'].browse(vals['sale_id']).bea_cukai_id = bc.id
            elif 'purchase_id' in vals:
                if not vals.get('purchase_id', False):
                    self.env['purchase.order'].browse(bc.purchase_id.id).write({'bea_cukai_id': False})
                else:
                    self.env['purchase.order'].browse(vals['purchase_id']).bea_cukai_id = bc.id
        return res

    @api.multi
    def action_lock(self):
        for doc in self:
            doc.state = 'done'

    @api.multi
    def action_unlock(self):
        for doc in self:
            doc.state = 'draft'

    @api.multi
    def compute_source_bc(self):
        src_bcs = self.env['source.bea.cukai']
        for doc in self:
            if not doc.stock_picking_ids:
                raise ValidationError(_("Dokumen ini belum terhubung dengan Delivery Order."))
            prev_line_dict = {}
            for prev_src in doc.source_bc_ids:
                prev_line_dict.update({(prev_src.product_id.id, prev_src.src_bea_cukai_id.id): prev_src})
            source_quants = self.env['stock.quant']
            for picking in doc.stock_picking_ids.filtered(lambda x: x.picking_type_id.code == 'outgoing'):
                for quant in picking.move_lines.mapped('quant_ids'):
                    source_quants |= quant
            source_line_dict = {}
            for quant in source_quants:
                for src_move in quant.history_ids:
                    if src_move.unbuild_id and src_move.unbuild_id.consume_line_ids:
                        consume_move = src_move.unbuild_id.consume_line_ids[0]

                        for in_quant in consume_move.quant_ids:
                            incoming_move = in_quant.history_ids.filtered(lambda x: x.location_id.usage == 'supplier' \
                                                                                    and x.picking_id and x.picking_id.bea_cukai_ids)
                            if not incoming_move:
                                continue
                            bea_cukai = incoming_move[0].picking_id.bea_cukai_ids[0]
                            key = (consume_move.product_id.id, bea_cukai.id)
                            if key not in source_line_dict.keys():
                                source_line_dict.update({key: {
                                    'bea_cukai_id': doc.id,
                                    'src_bea_cukai_id': bea_cukai.id,
                                    'product_id': consume_move.product_id.id,
                                    'product_qty': 0.0,
                                }})
                            source_line_dict[key]['product_qty'] += quant.qty * (
                                        in_quant.qty / sum(consume_move.quant_ids.mapped('qty')))
            updated_keys = []
            for k, values in source_line_dict.items():
                if k not in prev_line_dict.keys():
                    src_bcs.create(values)
                else:
                    updated_keys.append(k)
                    prev_line_dict[k].write({'product_qty': values['product_qty']})
            # DELETE PREV SOURCE BC
            for pkey in prev_line_dict.keys():
                if pkey not in updated_keys:
                    prev_line_dict[pkey].unlink()
        return True


class SourceBeaCukai(models.Model):
    _name = 'source.bea.cukai'

    bea_cukai_id = fields.Many2one('bea.cukai', 'Bea Cukai')
    src_bea_cukai_id = fields.Many2one('bea.cukai', 'Source Bea Cukai')
    product_id = fields.Many2one('product.product', 'Product')
    product_qty = fields.Float('Quantity')


class FakturPajak(models.Model):
    _name = 'bea.cukai.faktur.pajak'
    _description = 'Faktur Pajak BeaCukai'

    bea_cukai_id = fields.Many2one('bea.cukai', 'Bea Cukai')
    faktur_pajak = fields.Char("No. Faktur Pajak")
    faktur_pajak_date = fields.Date("Tanggal Faktur")


class BeaCukaiProductLine(models.Model):
    _name = 'bea.cukai.product.line'
    _description = 'Detail Products'

    bea_cukai_id = fields.Many2one('bea.cukai', 'Bea Cukai', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', 'Produk')
    product_uom = fields.Many2one('product.uom', 'Satuan')
    price_unit = fields.Float('Harga Satuan', digits=(16,3))
    currency_id = fields.Many2one('res.currency', 'Mata Uang')
    # price_unit_base_currency = fields.Float('Unit Price IDR')
    doc_rate = fields.Float('Kurs Dokumen')


