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
    'name': 'Account Custom',
    'depends': ['account_accountant', 'account_period', 'account_voucher', 'c10i_base', 'account_cancel', "account_parent", "payment"],
    'description': """
Assets Custom
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
        # 'data/ir_sequence.xml',
        'security/ir.model.access.csv',
        'security/account_security.xml',
        'wizard/wizard_general_ledger_account_view.xml',
        'wizard/wizard_trial_balance_10c_view.xml',
        'wizard/wizard_cash_bank_book_view.xml',
        'wizard/account_financial_report_view.xml',
        'wizard/wizard_aging.xml',
        'wizard/wizard_profit_loss_view.xml',
        'wizard/wizard_balance_sheet_view.xml',
        'wizard/wizard_sales_view.xml',
        'wizard/account_register_payment_view.xml',
        'views/res_currency_views.xml',
        'views/res_config_views.xml',
        'views/account_view.xml',
        'views/account_payment_views.xml',
        'views/account_voucher_views.xml',
        'views/account_menuitem.xml',
    ],
    'installable': True,
    'application': True,
}
