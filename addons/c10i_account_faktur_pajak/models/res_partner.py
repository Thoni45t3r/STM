# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

import calendar
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import float_compare, float_is_zero

from faktur_pajak import KODE_TRANSAKSI_FAKTUR_PAJAK

class Partner(models.Model):
    _inherit = 'res.partner'

    default_kode_transaksi = fields.Selection(selection=KODE_TRANSAKSI_FAKTUR_PAJAK, string='Default Kode Transaksi')
    has_npwp = fields.Boolean('Memiliki NPWP?')
    npwp_number = fields.Char('NPWP', size=20)
    npwp_address = fields.Text('Alamat NPWP')
    has_nppkp = fields.Boolean('Memiliki NPPKP?')
    nppkp_number = fields.Char('NPPKP', size=20)
    # property_account_payable_id = fields.Many2one('account.account', company_dependent=True,
    #     string="Account Payable", oldname="property_account_payable",
    #     domain="['|',('reconcile', '=', True), ('internal_type', '=', 'payable'), ('internal_type', '!=', 'receivable'), ('deprecated', '=', False)]",
    #     help="This account will be used instead of the default one as the payable account for the current partner",
    #     required=True)
    # property_account_receivable_id = fields.Many2one('account.account', company_dependent=True,
    #     string="Account Receivable", oldname="property_account_receivable",
    #     domain="['|',('reconcile', '=', True), ('internal_type', '=', 'receivable'), ('internal_type', '!=', 'payable'), ('deprecated', '=', False)]",
    #     help="This account will be used instead of the default one as the receivable account for the current partner",
    #     required=True)