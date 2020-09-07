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
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT

from datetime import datetime


class wizard_report_stock_cukai(models.TransientModel):
    _name = 'wizard.report.stock.cukai'
    _description = 'Bea Cukai Report'

    name = fields.Char("Name", default="Report Bea Cukai")
    from_date = fields.Date("From Date")
    to_date = fields.Date("To Date")
    type = fields.Selection(selection=[('in', 'In'), ('out', 'Out')], string="Type")
    report_type = fields.Selection([('pdf', 'PDF'), ('xlsx', 'Excel')], string='Report Type', required=True,
                                   default='pdf')
    company_id = fields.Many2one('res.company', string='Company', index=True,
                                 default=lambda self: self.env.user.company_id)
    type_doc_ids = fields.Many2many(comodel_name='bea.cukai.document.type', string='Document Type BC')
    line_ids = fields.One2many('wizard.report.stock.cukai.line', 'wizard_id', string="Details")

    @api.multi
    def action_generate_value(self):
        self.ensure_one()
        for line in self.line_ids:
            line.unlink()
        if self.type_doc_ids:
            bea_cukai_list = self.type_doc_ids.ids
        else:
            bea_cukai_list = [x.id for x in self.env['bea.cukai.document.type'].search([])]
        StockMove = self.env['stock.move'].sudo()
        WizardLine = self.env['wizard.report.stock.cukai.line']

        date_start = datetime.strptime(self.from_date, DF).strftime('%Y-%m-%d 00:00:00')
        date_stop = datetime.strptime(self.to_date, DF).strftime('%Y-%m-%d 23:59:59')

        domain = [('state', '=', 'done'), ('date', '>=', date_start), ('date', '<=', date_stop),
                  ('picking_id', '!=', False)]
        if self.type == 'in':
            domain.extend([('location_id.usage', '=', 'supplier'), ('location_dest_id.usage', '=', 'internal'),
                           ('location_dest_id.kawasan_berikat', '=', True)])
        else:
            domain.extend([('location_id.usage', '=', 'internal'), ('location_dest_id.usage', '=', 'customer'),
                           ('location_id.kawasan_berikat', '=', True)])
        move_lines = StockMove.search(domain)
        for move in move_lines:
            beacukai_doc = move.picking_id.bea_cukai_ids and move.picking_id.bea_cukai_ids[0] or []
            if not beacukai_doc:
                continue
            # total_qty = sum(beacukai_doc.mapped('stock_picking_ids.move_lines').mapped('product_qty'))
            # total_qty_per_product = sum(beacukai_doc.mapped('stock_picking_ids.move_lines').filtered(lambda x: x.product_id.id==move.product_id.id).mapped('product_qty'))
            # amount_per_product = (total_qty_per_product/total_qty) * beacukai_doc.amount if total_qty else 0.0
            # amount_subtotal = (amount_per_product/total_qty_per_product)*move.product_qty if total_qty_per_product else 0.0

            bc_lines = beacukai_doc.mapped('bea_cukai_product_lines').filtered(
                lambda x: x.product_id.id == move.product_id.id)
            # amount_subtotal = move.price_unit * move.product_qty
            if bc_lines:
                bc_lines.ensure_one()
                company_currency = bc_lines.bea_cukai_id.company_id.currency_id
                current_currency = bc_lines.currency_id
                price_unit = bc_lines.product_uom._compute_quantity(bc_lines.price_unit, move.product_uom, round=False)
                if current_currency.id != company_currency.id:
                    if bc_lines.doc_rate:
                        amount_subtotal = move.product_qty * price_unit * bc_lines.doc_rate
                    else:
                        amount_subtotal = company_currency.with_context(date=bc_lines.bea_cukai_id.date).compute(
                            move.product_qty * price_unit, current_currency, round=False)
                else:
                    amount_subtotal = bc_lines.price_unit * move.product_qty
            else:
                amount_subtotal = move.price_unit * move.product_qty

            line_vals = {
                'product_id': move.product_id.id,
                'product_code': move.product_id.default_code,
                'name': move.product_id.name,
                'uom_id': move.product_id.uom_id.id,
                'qty': move.product_qty,
                'stock_picking_id': move.picking_id.id,
                'picking_date': datetime.strptime(move.date, DT).strftime(DF),
                'partner_id': move.picking_id.partner_id.id,
                'bea_cukai_id': beacukai_doc and beacukai_doc.id or False,
                'bea_document_type_id': beacukai_doc and beacukai_doc.type.id or False,
                'bea_cukai_date': beacukai_doc and beacukai_doc.date or False,
                'currency_id': self.company_id.currency_id.id,
                'wizard_id': self.id,
                'value': amount_subtotal,
            }
            for i in beacukai_doc:
                if i.type and i.type.id in bea_cukai_list:
                    WizardLine.create(line_vals)
        return True

    def print_report(self):
        name = 'report_stock_cukai'
        if self.report_type == 'xlsx':
            name = 'report_stock_cukai_xls'
        return {
            'type': 'ir.actions.report.xml',
            'report_name': name,
            'datas': {
                'model': 'wizard.report.stock.cukai',
                'id': self.id,
                'ids': [self.id],
                'report_type': self.report_type,
                'form': {},
            },
            'nodestroy': False
        }


class wizard_report_stock_cukai_line(models.TransientModel):
    _name = 'wizard.report.stock.cukai.line'
    _description = 'Bea Cukai Report Details'

    name = fields.Char("Name")
    bea_document_type_id = fields.Many2one(comodel_name='bea.cukai.document.type', string="Jenis Dokumen")
    bea_cukai_id = fields.Many2one(comodel_name='bea.cukai', string="Bea Cukai")
    bea_cukai_date = fields.Date(string="Bea Cukai Date")
    stock_picking_id = fields.Many2one(comodel_name='stock.picking', string="Picking")
    picking_date = fields.Date(string="Picking Date")
    partner_id = fields.Many2one(comodel_name='res.partner', string="Partner")
    product_id = fields.Many2one(comodel_name='product.product', string="Product")
    product_code = fields.Char(string="Code")
    uom_id = fields.Many2one(comodel_name='product.uom', string="UoM")
    currency_id = fields.Many2one(comodel_name='res.currency', string="Currency")
    qty = fields.Float("Quantity", digits=(15, 2))
    value = fields.Float("Value", digits=(15, 2))
    wizard_id = fields.Many2one(comodel_name='wizard.report.stock.cukai', string="Wizard")


class wizard_report_stock_cukai_production(models.TransientModel):
    _name = 'wizard.report.stock.cukai.production'
    _description = 'Bea Cukai Report'

    name = fields.Char("Name", default="Report Bea Cukai")
    from_date = fields.Date("From Date")
    product_type = fields.Many2one('product.type', string='Tipe')
    to_date = fields.Date("To Date")
    type = fields.Selection(selection=[('in', 'Penerimaan'), ('out', 'Pengeluaran')], string="Type")
    report_type = fields.Selection([('pdf', 'PDF'), ('xlsx', 'Excel')], string='Report Type', required=True,
                                   default='pdf')
    company_id = fields.Many2one('res.company', string='Company', index=True,
                                 default=lambda self: self.env.user.company_id)
    line_ids = fields.One2many('wizard.report.stock.cukai.production.line', 'wizard_id', string="Details")

    @api.multi
    def action_generate_value(self):
        self.ensure_one()
        for line in self.line_ids:
            line.unlink()

        StockMove = self.env['stock.move'].sudo()
        WizardLine = self.env['wizard.report.stock.cukai.production.line']

        date_start = datetime.strptime(self.from_date, DF).strftime('%Y-%m-%d 00:00:00')
        date_stop = datetime.strptime(self.to_date, DF).strftime('%Y-%m-%d 23:59:59')

        domain = [('state', '=', 'done'), ('date', '>=', date_start), ('date', '<=', date_stop)]
        if self.type == 'in':
            domain.extend([('location_id.usage', 'in', ('production', 'procurement')),
                           ('location_dest_id.usage', '=', 'internal'),
                           ('location_dest_id.kawasan_berikat', '=', True)])
        else:
            domain.extend([('location_id.usage', '=', 'internal'),
                           ('location_dest_id.usage', 'in', ('production', 'procurement')),
                           ('location_id.kawasan_berikat', '=', True)])
        if self.product_type:
            domain.extend([('product_id.categ_id.product_type', '=', self.product_type.id)])
        move_lines = StockMove.search(domain)
        for move in move_lines:
            line_vals = {
                'name': move.picking_id and move.picking_id.name or move.origin or move.name,
                'unbuild_id': move.unbuild_id and move.unbuild_id.id or False,
                'product_id': move.product_id.id,
                'product_code': move.product_id.default_code,
                'uom_id': move.product_id.uom_id.id,
                'qty': move.product_qty,
                'picking_date': datetime.strptime(move.date, DT).strftime(DF),
                'wizard_id': self.id,
            }
            WizardLine.create(line_vals)
        return True

    def print_report(self):
        name = 'report_stock_cukai_production'
        if self.report_type == 'xlsx':
            name = 'report_stock_cukai_production_xls'
        return {
            'type': 'ir.actions.report.xml',
            'report_name': name,
            'datas': {
                'model': 'wizard.report.stock.cukai.production',
                'id': self.id,
                'ids': [self.id],
                'report_type': self.report_type,
                'form': {},
            },
            'nodestroy': False
        }


class wizard_report_stock_cukai_production_line(models.TransientModel):
    _name = 'wizard.report.stock.cukai.production.line'
    _description = 'Bea Cukai Report Details'

    name = fields.Char("Transaction")
    unbuild_id = fields.Many2one('mrp.unbuild', string='Mills')
    picking_date = fields.Date(string="Picking Date")
    product_id = fields.Many2one(comodel_name='product.product', string="Product")
    product_code = fields.Char(string="Code")
    uom_id = fields.Many2one(comodel_name='product.uom', string="UoM")
    qty = fields.Float("Quantity", digits=(15, 2))
    adjustment_qty = fields.Float("Stock Opnname", digits=(15, 2))
    difference_qty = fields.Float("Selisih", digits=(15, 2))
    note = fields.Text("Keterangan", digits=(15, 2))
    wizard_id = fields.Many2one(comodel_name='wizard.report.stock.cukai.production', string="Wizard")


