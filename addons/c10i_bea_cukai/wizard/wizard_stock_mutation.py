# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF

from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import timedelta

class BeacukaiStockMutation(models.TransientModel):
    _name = "beacukai.stock.mutation"
    _description = "Laporan Mutasi Barang"

    report_type = fields.Selection([('pdf','PDF'),('xlsx','Excel')], string='Tipe File', required=True, default='pdf')
    product_type = fields.Many2one('product.type', string='Tipe', required=True)
    date_start = fields.Date('Dari Tanggal', required=True)
    date_stop = fields.Date('Sampai Tanggal', required=True)
    company_id      = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    line_ids = fields.One2many('beacukai.stock.mutation.line', 'wizard_id', 'Mutasi Barang')

    @api.multi
    def action_generate_value(self):
        self.ensure_one()
        for line in self.line_ids:
            line.unlink()

        StockMove = self.env['stock.move'].sudo()
        WIPLine = self.env['beacukai.stock.mutation.line']
        OtherStockLine = self.env['other.stock.line'].sudo()
        
        products = self.env['product.product'].sudo().search([('categ_id.product_type','=',self.product_type.id)])
        date_start = datetime.strptime(self.date_start, DF).strftime('%Y-%m-%d 00:00:00')
        date_stop = datetime.strptime(self.date_stop, DF).strftime('%Y-%m-%d 23:59:59')
        for product in products:
            line_vals = {'product_id': product.id, 'wizard_id': self.id}
            default_domain = [('product_id','=',product.id), ('state','=','done')]
            default_domain_incoming = [('location_id.usage','!=','internal'),('location_dest_id.usage','=','internal'),('location_dest_id.kawasan_berikat','=',True)]
            default_domain_outgoing = [('location_id.usage','=','internal'),('location_dest_id.usage','!=','internal'),('location_id.kawasan_berikat','=',True)]

            # Take Opening Entries
            # 1. From Stock Move
            op_domain_move_in = default_domain[:] + default_domain_incoming[:]
            op_domain_move_in.extend([('date','<',date_start)])
            move_in = StockMove.search(op_domain_move_in)
            
            op_domain_move_out = default_domain[:] + default_domain_outgoing[:]
            op_domain_move_out.extend([('date','<',date_start)])
            move_out = StockMove.search(op_domain_move_out)
            opening_qty = sum(move_in.mapped('product_uom_qty'))-sum(move_out.mapped('product_uom_qty'))
            # 2. From Other Stock
            op_other_stock_in = OtherStockLine.search([('product_id','=',product.id),('other_stock_id.state','=','done'), \
                    ('other_stock_id.type','in',('opening','incoming')),('other_stock_id.date','<',self.date_start)])
            op_other_stock_out = OtherStockLine.search([('product_id','=',product.id),('other_stock_id.state','=','done'), \
                    ('other_stock_id.type','=','outgoing'),('other_stock_id.date','<',self.date_start)])
            opening_qty += sum(op_other_stock_in.mapped('product_qty'))-sum(op_other_stock_out.mapped('product_qty'))
            
            line_vals.update({'opening_qty': opening_qty})

            # Take Incoming Entries
            # 1. From Stock Move
            domain_move_in = default_domain[:]
            domain_move_in.extend([('date','>=',date_start),('date','<=',date_stop)])
            if self.product_type.code == 'finish_good':
                domain_move_in.extend([('location_id.usage','in',['production','customer']),('location_dest_id.usage','=','internal'),('location_dest_id.kawasan_berikat','=',True)])
            elif self.product_type.code == 'raw_material':
                domain_move_in.extend([('location_id.usage','in',['procurement','production','supplier']),('location_dest_id.usage','=','internal'),('location_dest_id.kawasan_berikat','=',True)])
                domain_move_in.extend([('picking_id.bea_cukai_ids','!=',False)])
            else:
                domain_move_in.extend([('location_id.usage','in',['procurement','supplier']),('location_dest_id.usage','=','internal'),('location_dest_id.kawasan_berikat','=',True)])
            move_incoming = StockMove.search(domain_move_in)
            # 2. From Stock Move
            other_stock_in = OtherStockLine.search([('product_id','=',product.id),('other_stock_id.state','=','done'), \
                    ('other_stock_id.type','=','incoming'),('other_stock_id.date','>=',self.date_start),('other_stock_id.date','<=',self.date_stop)])
            
            line_vals.update({'incoming_qty': sum(move_incoming.mapped('product_uom_qty'))+sum(other_stock_in.mapped('product_qty')) })

            # Take Outgoing Entries
            # 1. From Stock Move
            domain_move_out = default_domain[:]
            domain_move_out.extend([('date','>=',date_start),('date','<=',date_stop)])
            if self.product_type.code == 'finish_good':
                domain_move_out.extend([('location_id.usage','=','internal'),('location_dest_id.usage','in',['customer','production']),('location_id.kawasan_berikat','=',True)])
                domain_move_out.extend([('picking_id.bea_cukai_ids','!=',False)])
            elif self.product_type.code == 'raw_material':
                domain_move_out.extend([('location_id.usage','=','internal'),('location_dest_id.usage','in',['supplier','production','procurement']),('location_id.kawasan_berikat','=',True)])
            else:
                domain_move_out.extend([('location_id.usage','=','internal'),('location_dest_id.usage','in',['supplier','procurement']),('location_id.kawasan_berikat','=',True)])
            move_outgoing = StockMove.search(domain_move_out)
            # 2. From Stock Move
            other_stock_out = OtherStockLine.search([('product_id','=',product.id),('other_stock_id.state','=','done'), \
                    ('other_stock_id.type','=','outgoing'),('other_stock_id.date','>=',self.date_start),('other_stock_id.date','<=',self.date_stop)])

            line_vals.update({'outgoing_qty': sum(move_outgoing.mapped('product_uom_qty'))+sum(other_stock_out.mapped('product_qty')) })

            # Take Adjustment Entries
            # UNTUK SAAT INI BELUM DIDEFINISIKAN
            
            # Take Opname Entries
            domain_move_adj_in = default_domain[:]
            domain_move_adj_in.extend([('date','>=',date_start),('date','<=',date_stop),('picking_id','=',False)])
            domain_move_adj_in.extend([('location_id.usage','=','inventory'),('location_dest_id.usage','=','internal'),('location_dest_id.kawasan_berikat','=',True)])
            move_adj_in = StockMove.search(domain_move_adj_in)
            domain_move_adj_out = default_domain[:]
            domain_move_adj_out.extend([('date','>=',date_start),('date','<=',date_stop),('picking_id','=',False)])
            domain_move_adj_out.extend([('location_id.usage','=','internal'),('location_dest_id.usage','=','inventory'),('location_id.kawasan_berikat','=',True)])
            move_adj_out = StockMove.search(domain_move_adj_out)
            line_vals.update({'opname_qty': sum(move_adj_in.mapped('product_uom_qty'))-sum(move_adj_out.mapped('product_uom_qty')),
                'is_opname': True if (len(move_adj_in.ids)>1 or len(move_adj_out.ids)>1) else False})
            if line_vals['opening_qty']>0.0 or line_vals['incoming_qty']>0.0 or line_vals['outgoing_qty']>0.0 \
                    or line_vals['opname_qty']>0.0:
                WIPLine.create(line_vals)
        return True

    def print_report(self):
        report_name = 'beacukai_laporan_mutasi'
        if self.report_type == 'xlsx':
            report_name = 'beacukai_laporan_mutasi_xls'
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : report_name,
            'datas'         : {
                'model'         : 'beacukai.stock.mutation',
                'date_start'    : self.date_start,
                'date_stop'     : self.date_stop,
                'company_id'    : self.company_id.id,
                'company_name'  : self.company_id.name,
                'wizard_id'     : self.id,
                'product_type'  : self.product_type.name,
                'ids'           : [self.id],
                'report_type'   : self.report_type,
                'form'          : {},
                },
            'nodestroy': False
        }


class BeacukaiStockWIPLine(models.TransientModel):
    _name = "beacukai.stock.mutation.line"
    _description = "Mutasi Barang"

    wizard_id = fields.Many2one('beacukai.stock.mutation', 'Wizard')
    product_id = fields.Many2one('product.product', 'Product')
    product_name = fields.Char(related='product_id.name', string='Nama Barang')
    product_code = fields.Char(related='product_id.default_code', string='Kode Barang')
    product_uom = fields.Many2one('product.uom', related='product_id.uom_id', string='Satuan')
    opening_qty = fields.Float('Saldo Awal', digits=(15,2))
    incoming_qty = fields.Float('Pemasukan Barang', digits=(15,2))
    outgoing_qty = fields.Float('Pengeluaran Barang', digits=(15,2))
    adjustment_qty = fields.Float('Penyesuaian', digits=(15,2))
    closing_qty = fields.Float(compute='_compute_closing', string='Saldo Akhir', digits=(15,2), store=True)
    opname_qty = fields.Float('Stock Opname', digits=(15,2))
    is_opname = fields.Boolean('Is Opname?')
    diff_qty = fields.Float(compute='_compute_closing', string='Selisih', digits=(15,2), store=True)

    @api.multi
    @api.depends('opening_qty', 'incoming_qty', 'outgoing_qty', 'adjustment_qty', 'opname_qty', 'is_opname')
    def _compute_closing(self):
        for line in self:
            line.closing_qty = line.opening_qty + line.incoming_qty - line.outgoing_qty + line.adjustment_qty
            line.diff_qty = (line.opening_qty + line.incoming_qty - line.outgoing_qty + line.adjustment_qty - line.opname_qty) if line.is_opname else 0.0

class BeacukaiStockWIP(models.TransientModel):
    _name = "beacukai.stock.wip"
    _description = "Laporan Barang Dalam Proses"

    report_type = fields.Selection([('pdf','PDF'),('xlsx','Excel')], string='Tipe File', required=True, default='pdf')
    # product_type = fields.Many2one('product.type', string='Tipe', required=True)
    date_start = fields.Date('Dari Tanggal', required=True)
    date_stop = fields.Date('Sampai Tanggal', required=True)
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    line_ids = fields.One2many('beacukai.stock.wip.line', 'wizard_id', 'Mutasi Barang')

    @api.multi
    def action_generate_value(self):
        self.ensure_one()
        for line in self.line_ids:
            line.unlink()

        StockMove = self.env['stock.move'].sudo()
        WIPLine = self.env['beacukai.stock.wip.line']
        
        products = self.env['product.product'].sudo().search([('categ_id.product_type.code','=','finish_good')])
        date_start = datetime.strptime(self.date_start, DF).strftime('%Y-%m-%d 00:00:00')
        date_stop = datetime.strptime(self.date_stop, DF).strftime('%Y-%m-%d 23:59:59')
        for product in products:
            line_vals = {
                'wizard_id': self.id,
                'product_id': product.id,
                'product_qty': 0.0,
            }
            WIPLine.create(line_vals)
        return True

    def print_report(self):
        report_name = 'beacukai_laporan_wip'
        if self.report_type == 'xlsx':
            report_name = 'beacukai_laporan_wip_xls'
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : report_name,
            'datas'         : {
                'model'         : 'beacukai.stock.wip',
                'date_start'    : self.date_start,
                'date_stop'     : self.date_stop,
                'company_id'    : self.company_id.id,
                'company_name'  : self.company_id.name,
                'wizard_id'     : self.id,
                'ids'           : [self.id],
                'report_type'   : self.report_type,
                'form'          : {},
                },
            'nodestroy': False
        }


class BeacukaiStockWIPLine(models.TransientModel):
    _name = "beacukai.stock.wip.line"
    _description = "Detail WIP"

    wizard_id = fields.Many2one('beacukai.stock.wip', 'Wizard')
    product_id = fields.Many2one('product.product', 'Product')
    product_name = fields.Char(related='product_id.name', string='Nama Barang')
    product_code = fields.Char(related='product_id.default_code', string='Kode Barang')
    product_uom = fields.Many2one('product.uom', related='product_id.uom_id', string='Satuan')
    product_qty = fields.Float(string='Quantity', digits=(15,2))