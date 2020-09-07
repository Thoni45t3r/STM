# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

import logging
import time
import datetime
import calendar
import base64
import xlrd
from odoo.tools.translate import _
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo.addons import decimal_precision as dp
from odoo import models, fields, tools, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

class report_wp_cost(models.Model):
    _name           = 'report.wp.cost'
    _inherit        = ['mail.thread', 'ir.needaction_mixin']
    _description    = 'Report WP Cost'

    name                = fields.Char("Name", readonly=True)
    account_period_id   = fields.Many2one("account.period", string="Accounting Periode", ondelete="restrict", track_visibility='onchange')
    line_ids            = fields.One2many("report.wp.cost.line", inverse_name="report_id", string="Details")
    company_id          = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)

    @api.onchange('account_period_id')
    def onchange_account_period_id(self):
        if self.account_period_id:
            self.name = "WP COST " + self.account_period_id.name

    @api.multi
    def print_report(self):
        self.calculate()
        # return {
        #     'type'          : 'ir.actions.report.xml',
        #     'report_name'   : 'report_wp_cost',
        #     'datas'         : {
        #                     'model'         : 'report.wp.cost',
        #                     'id'            : self._context.get('active_ids') and self._context.get('active_ids')[0] or self.id,
        #                     'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or [],
        #                     'report_type'   : 'xlsx',
        #     },
        #     'nodestroy': False
        # }

    @api.multi
    def calculate(self):
        line_obj        = self.env['report.wp.cost.line']
        if self.line_ids != []:
            for hapus in self.line_ids:
                hapus.unlink()
        # Total BIAYA PRODUKSI - TBM - INVESTASI
        total_all   = line_obj.create({'name': "BIAYA PRODUKSI - TBM - INVESTASI", 'level': 'level0', 'symbol': 'Rp', 'report_id': self.id})
        # Biaya Pokok TBS
        line_obj.create({'name': "Biaya Pokok TBS", 'level': 'level1', 'symbol': '', 'report_id': self.id})
        total_biaya_penjualan_tbs   = line_obj.create({'name': "Biaya Penjualan TBS - Exc Biaya HO", 'level': 'level2', 'symbol': 'Rp', 'report_id': self.id})
        total_biaya_produksi_tbs    = line_obj.create({'name': "Biaya Produksi TBS - Exc Biaya HO", 'level': 'level2', 'symbol': 'Rp', 'report_id': self.id})
        # Harga Pokok TBS
        line_obj.create({'name': "Harga Pokok TBS", 'level': 'level1', 'symbol': '', 'report_id': self.id})
        total_harga_penjualan_tbs   = line_obj.create({'name': "Harga Pokok Penjualan TBS - Exc Biaya HO", 'level': 'level2', 'symbol': 'Rp/Kg TBS ', 'report_id': self.id})
        total_harga_produksi_tbs    = line_obj.create({'name': "Harga Pokok Produksi TBS - Exc Biaya HO", 'level': 'level2', 'symbol': 'Rp/Kg TBS ', 'report_id': self.id})
        # Hektar Tertanam
        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'inti'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'plasma'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "Hektar Tertanam", 'level': 'level1', 'symbol': 'Ha', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'inti' AND status='tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND status='tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM", 'level': 'level2', 'symbol': 'Ha', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'inti' AND (planting_time < 8) and status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND (planting_time < 8) and status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM Young (TM1-4)", 'level': 'level3', 'symbol': 'Ha', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=4 AND status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=4 AND status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM1", 'level': 'level4', 'symbol': 'Ha', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=5 AND status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=5 AND status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM2", 'level': 'level4', 'symbol': 'Ha', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=6 AND status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=6 AND status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM3", 'level': 'level4', 'symbol': 'Ha', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=7 AND status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=7 AND status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM4", 'level': 'level4', 'symbol': 'Ha', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'inti' AND (planting_time >= 8 AND planting_time < 18) and status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND (planting_time >= 8 AND planting_time < 18) and status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM Prime (TM5-14)", 'level': 'level3', 'symbol': 'Ha', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time >= 18 AND status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time >= 18 AND status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM Old (>TM15)", 'level': 'level3', 'symbol': 'Ha', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'inti' AND status='tbm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND status='tbm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TBM", 'level': 'level2', 'symbol': 'Ha', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=0 AND status = 'tbm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=0 AND status = 'tbm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TBM-0", 'level': 'level3', 'symbol': 'Ha', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=1 AND status = 'tbm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=1 AND status = 'tbm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TBM-1", 'level': 'level3', 'symbol': 'Ha', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=2 AND status = 'tbm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=2 AND status = 'tbm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TBM-2", 'level': 'level3', 'symbol': 'Ha', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=3 AND status = 'tbm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(planted) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=3 AND status = 'tbm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TBM-3", 'level': 'level3', 'symbol': 'Ha', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})
        # Pokok Tanam
        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'inti'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'plasma'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "Pokok Tanam", 'level': 'level1', 'symbol': 'Pokok', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'inti' AND status='tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND status='tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM", 'level': 'level2', 'symbol': 'Pokok', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'inti' AND (planting_time < 8) and status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND (planting_time < 8) and status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM Young (TM1-4)", 'level': 'level3', 'symbol': 'Pokok', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=4 AND status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=4 AND status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM1", 'level': 'level4', 'symbol': 'Pokok', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=5 AND status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=5 AND status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM2", 'level': 'level4', 'symbol': 'Pokok', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=6 AND status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=6 AND status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM3", 'level': 'level4', 'symbol': 'Pokok', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})
        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=7 AND status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=7 AND status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM4", 'level': 'level4', 'symbol': 'Pokok', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'inti' AND (planting_time >= 8 AND planting_time < 18) and status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND (planting_time >= 8 AND planting_time < 18) and status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM Prime (TM5-14)", 'level': 'level3', 'symbol': 'Pokok', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time >= 18 AND status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time >= 18 AND status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM Old (>TM15)", 'level': 'level3', 'symbol': 'Pokok', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'inti' AND status='tbm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND status='tbm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TBM", 'level': 'level2', 'symbol': 'Pokok', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=0 AND status = 'tbm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=0 AND status = 'tbm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TBM-0", 'level': 'level3', 'symbol': 'Pokok', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=1 AND status = 'tbm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=1 AND status = 'tbm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TBM-1", 'level': 'level3', 'symbol': 'Pokok', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=2 AND status = 'tbm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=2 AND status = 'tbm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TBM-2", 'level': 'level3', 'symbol': 'Pokok', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})

        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=3 AND status = 'tbm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select sum(total_plant) as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=3 AND status = 'tbm'")
        plasma = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TBM-3", 'level': 'level3', 'symbol': 'Pokok', 'inti': inti, 'plasma': plasma, 'total': inti+plasma, 'report_id': self.id})
        # SPH Tanam
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'inti'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'plasma'")
        plasma = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block")
        total = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "SPH Tanam", 'level': 'level1', 'symbol': 'Pokok/Ha', 'inti': inti, 'plasma': plasma, 'total': total, 'report_id': self.id})

        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'inti' AND status='tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'plasma' AND status='tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE status='tm'")
        total = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM", 'level': 'level2', 'symbol': 'Pokok/Ha', 'inti': inti, 'plasma': plasma, 'total': total, 'report_id': self.id})

        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'inti' AND (planting_time < 8) and status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'plasma' AND (planting_time < 8) and status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE (planting_time < 8) and status = 'tm'")
        total = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM Young (TM1-4)", 'level': 'level3', 'symbol': 'Pokok/Ha', 'inti': inti, 'plasma': plasma, 'total': total, 'report_id': self.id})

        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=4 AND status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=4 AND status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE planting_time=4 AND status = 'tm'")
        total = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM1", 'level': 'level4', 'symbol': 'Pokok/Ha', 'inti': inti, 'plasma': plasma, 'total': total, 'report_id': self.id})
        
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=5 AND status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=5 AND status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE planting_time=5 AND status = 'tm'")
        total = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM2", 'level': 'level4', 'symbol': 'Pokok/Ha', 'inti': inti, 'plasma': plasma, 'total': total, 'report_id': self.id})
        
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=6 AND status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=6 AND status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE planting_time=6 AND status = 'tm'")
        total = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM3", 'level': 'level4', 'symbol': 'Pokok/Ha', 'inti': inti, 'plasma': plasma, 'total': total, 'report_id': self.id})
        
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=7 AND status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=7 AND status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE planting_time=7 AND status = 'tm'")
        total = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM4", 'level': 'level4', 'symbol': 'Pokok/Ha', 'inti': inti, 'plasma': plasma, 'total': total, 'report_id': self.id})

        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'inti' AND (planting_time >= 8 AND planting_time < 18) and status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'plasma' AND (planting_time >= 8 AND planting_time < 18) and status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE (planting_time >= 8 AND planting_time < 18) and status = 'tm'")
        total = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM Prime (TM5-14)", 'level': 'level3', 'symbol': 'Pokok/Ha', 'inti': inti, 'plasma': plasma, 'total': total, 'report_id': self.id})

        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time >= 18 AND status = 'tm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time >= 18 AND status = 'tm'")
        plasma = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE planting_time >= 18 AND status = 'tm'")
        total = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TM Old (>TM15)", 'level': 'level3', 'symbol': 'Pokok/Ha', 'inti': inti, 'plasma': plasma, 'total': total, 'report_id': self.id})

        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'inti' AND status='tbm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'plasma' AND status='tbm'")
        plasma = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE status='tbm'")
        total = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TBM", 'level': 'level2', 'symbol': 'Pokok/Ha', 'inti': inti, 'plasma': plasma, 'total': total, 'report_id': self.id})

        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=0 AND status = 'tbm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=0 AND status = 'tbm'")
        plasma = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE planting_time=0 AND status = 'tbm'")
        total = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TBM-0", 'level': 'level3', 'symbol': 'Pokok/Ha', 'inti': inti, 'plasma': plasma, 'total': total, 'report_id': self.id})

        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=1 AND status = 'tbm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=1 AND status = 'tbm'")
        plasma = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE planting_time=1 AND status = 'tbm'")
        total = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TBM-1", 'level': 'level3', 'symbol': 'Pokok/Ha', 'inti': inti, 'plasma': plasma, 'total': total, 'report_id': self.id})

        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=2 AND status = 'tbm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=2 AND status = 'tbm'")
        plasma = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE planting_time=2 AND status = 'tbm'")
        total = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TBM-2", 'level': 'level3', 'symbol': 'Pokok/Ha', 'inti': inti, 'plasma': plasma, 'total': total, 'report_id': self.id})

        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'inti' AND planting_time=3 AND status = 'tbm'")
        inti = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE owner_type = 'plasma' AND planting_time=3 AND status = 'tbm'")
        plasma = self._cr.fetchone()[0] or 0.00
        self._cr.execute("select CASE WHEN (sum(total_plant) = 0 or sum(planted)=0) THEN 0 ELSE sum(total_plant)/sum(planted) END as planted from lhm_plant_block WHERE planting_time=3 AND status = 'tbm'")
        total = self._cr.fetchone()[0] or 0.00
        line_obj.create({'name': "TBM-3", 'level': 'level3', 'symbol': 'Pokok/Ha', 'inti': inti, 'plasma': plasma, 'total': total, 'report_id': self.id})

        # Penjualan TBS - Netto
        line_obj.create({'name': "Penjualan TBS - Netto", 'level': 'level1', 'symbol': 'Ton', 'report_id': self.id})
        line_obj.create({'name': "Kirim", 'level': 'level2', 'symbol': 'Ton', 'report_id': self.id})
        line_obj.create({'name': "Susut", 'level': 'level3', 'symbol': 'Ton', 'report_id': self.id})
        line_obj.create({'name': "Greading", 'level': 'level3', 'symbol': 'Ton', 'report_id': self.id})
        line_obj.create({'name': "Afkir/TBS dikembalikan", 'level': 'level3', 'symbol': 'Ton', 'report_id': self.id})
        # Variance Penjualan Netto Terhadap Produksi TBS
        line_obj.create({'name': "Variance Penjualan Netto Terhadap Produksi TBS", 'level': 'level1', 'symbol': 'Ton', 'report_id': self.id})
        line_obj.create({'name': "Produksi TBS", 'level': 'level2', 'symbol': 'Ton', 'report_id': self.id})
        line_obj.create({'name': "TBM", 'level': 'level3', 'symbol': 'Ton', 'report_id': self.id})
        line_obj.create({'name': "TM", 'level': 'level3', 'symbol': 'Ton', 'report_id': self.id})
        line_obj.create({'name': "TM Young (TM1-4)", 'level': 'level3', 'symbol': 'Ton', 'report_id': self.id})
        line_obj.create({'name': "TM1", 'level': 'level4', 'symbol': 'Ton', 'report_id': self.id})
        line_obj.create({'name': "TM2", 'level': 'level4', 'symbol': 'Ton', 'report_id': self.id})
        line_obj.create({'name': "TM3", 'level': 'level4', 'symbol': 'Ton', 'report_id': self.id})
        line_obj.create({'name': "TM4", 'level': 'level4', 'symbol': 'Ton', 'report_id': self.id})
        line_obj.create({'name': "TM Prime (TM5-14)", 'level': 'level3', 'symbol': 'Ton', 'report_id': self.id})
        line_obj.create({'name': "TM Old (>TM15)", 'level': 'level3', 'symbol': 'Ton', 'report_id': self.id})
        line_obj.create({'name': "Janjang TBS Inti", 'level': 'level2', 'symbol': 'Jjg', 'report_id': self.id})
        line_obj.create({'name': "TBM", 'level': 'level3', 'symbol': 'Jjg', 'report_id': self.id})
        line_obj.create({'name': "TM", 'level': 'level3', 'symbol': 'Jjg', 'report_id': self.id})
        line_obj.create({'name': "TM Young (TM1-4)", 'level': 'level3', 'symbol': 'Jjg', 'report_id': self.id})
        line_obj.create({'name': "TM1", 'level': 'level4', 'symbol': 'Jjg', 'report_id': self.id})
        line_obj.create({'name': "TM2", 'level': 'level4', 'symbol': 'Jjg', 'report_id': self.id})
        line_obj.create({'name': "TM3", 'level': 'level4', 'symbol': 'Jjg', 'report_id': self.id})
        line_obj.create({'name': "TM4", 'level': 'level4', 'symbol': 'Jjg', 'report_id': self.id})
        line_obj.create({'name': "TM Prime (TM5-14)", 'level': 'level3', 'symbol': 'Jjg', 'report_id': self.id})
        line_obj.create({'name': "TM Old (>TM15)", 'level': 'level3', 'symbol': 'Jjg', 'report_id': self.id})
        line_obj.create({'name': "BJR TBS Inti", 'level': 'level2', 'symbol': 'Kg/Jjg', 'report_id': self.id})
        line_obj.create({'name': "TBM", 'level': 'level3', 'symbol': 'Kg/Jjg', 'report_id': self.id})
        line_obj.create({'name': "TM", 'level': 'level3', 'symbol': 'Kg/Jjg', 'report_id': self.id})
        line_obj.create({'name': "TM Young (TM1-4)", 'level': 'level3', 'symbol': 'Kg/Jjg', 'report_id': self.id})
        line_obj.create({'name': "TM1", 'level': 'level4', 'symbol': 'Kg/Jjg', 'report_id': self.id})
        line_obj.create({'name': "TM2", 'level': 'level4', 'symbol': 'Kg/Jjg', 'report_id': self.id})
        line_obj.create({'name': "TM3", 'level': 'level4', 'symbol': 'Kg/Jjg', 'report_id': self.id})
        line_obj.create({'name': "TM4", 'level': 'level4', 'symbol': 'Kg/Jjg', 'report_id': self.id})
        line_obj.create({'name': "TM Prime (TM5-14)", 'level': 'level3', 'symbol': 'Kg/Jjg', 'report_id': self.id})
        line_obj.create({'name': "TM Old (>TM15)", 'level': 'level3', 'symbol': 'Kg/Jjg', 'report_id': self.id})
        line_obj.create({'name': "Yield Kebun Inti", 'level': 'level2', 'symbol': 'Ton/Ha', 'report_id': self.id})
        line_obj.create({'name': "TBM", 'level': 'level3', 'symbol': 'Ton/Ha', 'report_id': self.id})
        line_obj.create({'name': "TM", 'level': 'level3', 'symbol': 'Ton/Ha', 'report_id': self.id})
        line_obj.create({'name': "TM Young (TM1-4)", 'level': 'level3', 'symbol': 'Ton/Ha', 'report_id': self.id})
        line_obj.create({'name': "TM1", 'level': 'level4', 'symbol': 'Ton/Ha', 'report_id': self.id})
        line_obj.create({'name': "TM2", 'level': 'level4', 'symbol': 'Ton/Ha', 'report_id': self.id})
        line_obj.create({'name': "TM3", 'level': 'level4', 'symbol': 'Ton/Ha', 'report_id': self.id})
        line_obj.create({'name': "TM4", 'level': 'level4', 'symbol': 'Ton/Ha', 'report_id': self.id})
        line_obj.create({'name': "TM Prime (TM5-14)", 'level': 'level3', 'symbol': 'Ton/Ha', 'report_id': self.id})
        line_obj.create({'name': "TM Old (>TM15)", 'level': 'level3', 'symbol': 'Ton/Ha', 'report_id': self.id})
        line_obj.create({'name': "Janjang/Pokok Inti", 'level': 'level2', 'symbol': 'Jjg/Pokok', 'report_id': self.id})
        line_obj.create({'name': "TBM", 'level': 'level3', 'symbol': 'Jjg/Pokok', 'report_id': self.id})
        line_obj.create({'name': "TM", 'level': 'level3', 'symbol': 'Jjg/Pokok', 'report_id': self.id})
        line_obj.create({'name': "TM Young (TM1-4)", 'level': 'level3', 'symbol': 'Jjg/Pokok', 'report_id': self.id})
        line_obj.create({'name': "TM1", 'level': 'level4', 'symbol': 'Jjg/Pokok', 'report_id': self.id})
        line_obj.create({'name': "TM2", 'level': 'level4', 'symbol': 'Jjg/Pokok', 'report_id': self.id})
        line_obj.create({'name': "TM3", 'level': 'level4', 'symbol': 'Jjg/Pokok', 'report_id': self.id})
        line_obj.create({'name': "TM4", 'level': 'level4', 'symbol': 'Jjg/Pokok', 'report_id': self.id})
        line_obj.create({'name': "TM Prime (TM5-14)", 'level': 'level3', 'symbol': 'Jjg/Pokok', 'report_id': self.id})
        line_obj.create({'name': "TM Old (>TM15)", 'level': 'level3', 'symbol': 'Jjg/Pokok', 'report_id': self.id})
        line_obj.create({'name': "Output Panen", 'level': 'level2', 'symbol': 'Kg/HK', 'report_id': self.id})
        line_obj.create({'name': "TBM", 'level': 'level3', 'symbol': 'Kg/HK', 'report_id': self.id})
        line_obj.create({'name': "TM", 'level': 'level3', 'symbol': 'Kg/HK', 'report_id': self.id})
        line_obj.create({'name': "TM Young (TM1-4)", 'level': 'level3', 'symbol': 'Kg/HK', 'report_id': self.id})
        line_obj.create({'name': "TM Prime (TM5-14)", 'level': 'level3', 'symbol': 'Kg/HK', 'report_id': self.id})
        line_obj.create({'name': "TM Old (>TM15)", 'level': 'level3', 'symbol': 'Kg/HK', 'report_id': self.id})
        line_obj.create({'name': "HK Panen", 'level': 'level2', 'symbol': 'HK', 'report_id': self.id})
        line_obj.create({'name': "TBM", 'level': 'level3', 'symbol': 'HK', 'report_id': self.id})
        line_obj.create({'name': "TM", 'level': 'level3', 'symbol': 'HK', 'report_id': self.id})
        line_obj.create({'name': "TM Young (TM1-4)", 'level': 'level3', 'symbol': 'HK', 'report_id': self.id})
        line_obj.create({'name': "TM Prime (TM5-14)", 'level': 'level3', 'symbol': 'HK', 'report_id': self.id})
        line_obj.create({'name': "TM Old (>TM15)", 'level': 'level3', 'symbol': 'HK', 'report_id': self.id})
        #### Transport Penjualan TBS ####
        line_obj.create({'name': "1 Transport Penjualan TBS", 'level': 'level1', 'symbol': 'Rp', 'report_id': self.id})
        line_obj.create({'name': "", 'level': 'level1', 'symbol': 'Rp/Kg TBS', 'report_id': self.id})
        #### Biaya Produksi Langsung ####
        line_obj.create({'name': "2 Biaya Produksi Langsung", 'level': 'level2', 'symbol': 'Rp', 'report_id': self.id})
        line_obj.create({'name': "", 'level': 'level2', 'symbol': 'Rp/Kg TBS', 'report_id': self.id})
        line_obj.create({'name': "2a Panen", 'level': 'level3', 'symbol': 'Rp', 'report_id': self.id})
        line_obj.create({'name': "", 'level': 'level3', 'symbol': 'Rp/Kg TBS', 'report_id': self.id})
        line_obj.create({'name': "2b Transport Panen", 'level': 'level3', 'symbol': 'Rp', 'report_id': self.id})
        line_obj.create({'name': "", 'level': 'level3', 'symbol': 'Rp/Kg TBS', 'report_id': self.id})
        #### Biaya Produksi Tidak Langsung ####


class report_wp_cost_line(models.Model):
    _name           = 'report.wp.cost.line'
    _description    = 'Report WP Cost Line'

    name            = fields.Char("Name")
    level           = fields.Selection(selection=[('level0','Total'), ('level1','Level 1'), ('level2','Level 2'), ('level3','Level 3'), ('level4', 'Level 4'), ('level5','Level 5'), ('level6','Level 6')] , string='Level')
    symbol          = fields.Char("Symbol")
    inti            = fields.Float("Inti")
    plasma          = fields.Float("Plasma")
    total           = fields.Float("Total")
    report_id       = fields.Many2one("report.wp.cost", string="Report ID", ondelete="cascade")