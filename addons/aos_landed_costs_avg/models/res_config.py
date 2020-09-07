# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class PurchaseConfigSettings(models.TransientModel):
    _inherit = 'purchase.config.settings'

    group_purchase_inland_costs = fields.Selection([
        (0, 'No Landed Costs'),
        (1, "Use a 'Landed Costs' with 'Average' price costing method")
        ], "Average Costing",
        implied_group='purchase.group_purchase_user',
        help="""Allows you to compute product cost price based on average cost.""")
    purchase_landed_cost_calculate = fields.Selection([
        (0, 'By Weight'),
        (1, 'By Volume'),
        (2, 'By Quantity'),
        (3, 'By Amount'),
        ], "Manage Landed Cost Calculation")
    
    group_landed_cost_by_weight_x = fields.Boolean('Landed Cost by Weight', implied_group='aos_landed_costs_avg.group_landed_cost_by_weight_x')
    group_landed_cost_by_volume_x = fields.Boolean('Landed Cost by Volume', implied_group='aos_landed_costs_avg.group_landed_cost_by_volume_x')
    group_landed_cost_by_quantity_x = fields.Boolean('Landed Cost by Quantity', implied_group='aos_landed_costs_avg.group_landed_cost_by_quantity_x')
    group_landed_cost_by_amount_x = fields.Boolean('Landed Cost by Amount', implied_group='aos_landed_costs_avg.group_landed_cost_by_amount_x')

    @api.onchange('purchase_landed_cost_calculate')
    def onchange_warehouse_and_location_usage_level(self):
        self.group_landed_cost_by_weight_x = self.purchase_landed_cost_calculate == 0
        self.group_landed_cost_by_volume_x = self.purchase_landed_cost_calculate == 1
        self.group_landed_cost_by_quantity_x = self.purchase_landed_cost_calculate == 2
        self.group_landed_cost_by_amount_x = self.purchase_landed_cost_calculate == 3
