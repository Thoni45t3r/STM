# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import api, fields, models

class StateCity(models.Model):
    _description = "City of State"
    _name        = 'res.state.city'
    _order       = 'state_id'

    name        = fields.Char(string='City Name', required=True, help='Administrative divisions of a province. E.g. Surabaya')
    country_id  = fields.Many2one('res.country', string='Country', required=True)
    state_id    = fields.Many2one('res.country.state', string='State', required=True)
    company_id  = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    active      = fields.Boolean('Aktif', required=True, default=True)