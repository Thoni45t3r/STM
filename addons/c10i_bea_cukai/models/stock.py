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


class Picking(models.Model):
    _inherit = 'stock.picking'

    bea_cukai_ids = fields.Many2many('bea.cukai', 'bea_cukai_picking_rel', 'stock_picking_id', 'bea_cukai_id',
                                     string='Doc. Bea Cukai', ondelete="restrict", copy=False)
    nomer_bukti = fields.Char('Nomer Bukti Pemasukan/Pengeluaran')


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def action_done(self):
        res = super(StockMove, self).action_done()

        for move in self:
            if move.location_id.kawasan_berikat or move.location_dest_id.kawasan_berikat:
                if move.procurement_id.sale_line_id and move.procurement_id.sale_line_id.order_id.bea_cukai_id:
                    move.picking_id.bea_cukai_ids = [(4, move.procurement_id.sale_line_id.order_id.bea_cukai_id.id)]
                elif move.purchase_line_id and move.purchase_line_id.order_id.bea_cukai_id:
                    move.picking_id.bea_cukai_ids = [(4, move.purchase_line_id.order_id.bea_cukai_id.id)]
        return res


