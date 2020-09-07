# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

{
    'name': 'Faktur Pajak Indonesia',
    'depends': ['c10i_account', 'c10i_account_invoice_advance'],
    'description': """
Faktur Pajak Indonesia
==========================
Add a new feature of Indonesian Taxes Regulation
- Register a new Faktur Pajak Masukan numbers
- Customer Invoice, link to Faktur Pajak Keluaran (VAT OUT)
- Bill Vendor, link to Faktur Pajak Masukan (VAT IN)
    """,
    'author'    : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "www.consult10indonesia.com",
    'category'  : 'Accounting',
    'sequence'  : 32,
    'license'   : 'AGPL-3',
    'data': [
        'data/ir_sequence.xml',
        'security/ir.model.access.csv',
        'security/faktur_pajak.xml',
        'views/faktur_pajak_views.xml',
        'views/res_partner_views.xml',
        'views/account_invoice_views.xml',
        'views/account_invoice_advance_views.xml',
    ],
    'installable': True,
    'application': True,
}
