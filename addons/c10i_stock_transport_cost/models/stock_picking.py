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

    transporter_id = fields.Many2one('res.partner', string='Transporter')
    transport_cost_id = fields.Many2one('stock.transport.cost', string='Transport Cost')
    incoterm_id = fields.Many2one('stock.incoterms', string='Incoterm', domain=[('transport_cost','=',True)])

    vehicle_number = fields.Char('Vehicle Number')
    driver_name = fields.Char('Driver Name')