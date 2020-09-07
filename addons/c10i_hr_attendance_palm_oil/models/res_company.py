# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import models, fields, tools, api, exceptions, _

class ResCompany(models.Model):
    _inherit        = 'res.company'

    attendance_partner_id              = fields.Many2one('res.partner', string="Payroll", ondelete="restrict")
    attendance_partner_kesehatan       = fields.Many2one('res.partner', string="BPJS Kesehatan", ondelete="restrict")
    attendance_partner_ketenagakerjaan = fields.Many2one('res.partner', string="BPJS Ketenagakerjaan", ondelete="restrict")
    attendance_partner_pensiun         = fields.Many2one('res.partner', string="BPJS Pensiun", ondelete="restrict")
    attendance_partner_keselamatan     = fields.Many2one('res.partner', string="JKK + JKM", ondelete="restrict")