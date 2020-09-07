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
    'name': 'Multi-Currency Revaluation',
    'depends': ['c10i_account'],
    'description': """
===========================
 Multicurrency revaluation
===========================

The *Multicurrency revaluation* module allows you generate automatically
multicurrency revaluation journal entries. You will also find here a
Revaluation report

Note that an extra aggregation by currency on general ledger & partner ledger
(from module : *account_financial_report*) has been added in order to get more
details.

---------------
 Main Features
---------------

* A checkbox *Allow currency revaluation* on accounts.
* A wizard to generate the revaluation journal entries. It adjusts account
balance having *Allow currency revaluation* checked.
* A wizard to print a report of revaluation.

The report uses webkit report system.

---------------
 Configuration
---------------

Due to the various legislation according the country, in the Company settings
you can set the way you want to generate revaluation journal entries.

Please, find below adviced account settings for 3 countries :

For UK (Revaluation)
====================
(l10n_uk Chart of account)

::

                          LOSS    GAIN
  Revaluation account    [7700]  [7700]
  Provision B.S account  [    ]  [    ]
  Provision P&L account  [    ]  [    ]

For CH (Provision)
==================
(l10n_ch Chart of account)

::

                          LOSS    GAIN
  Revaluation account    [    ]  [    ]
  Provision B.S account  [2331]  [2331]
  Provision P&L account  [3906]  [4906]

For FR
======
(l10n_fr Chart of account)

::

                          LOSS    GAIN
  Revaluation account    [ 476]  [ 477]
  Provision B.S account  [1515]  [    ]
  Provision P&L account  [6865]  [    ]
""",
    'author'    : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "www.consult10indonesia.com",
    'category'  : 'Accounting',
    'sequence'  : 32,
    'license'   : 'AGPL-3',
    'data': [
        # 'data/ir_sequence.xml',
        # 'security/ir.model.access.csv',
        'wizard/wizard_currency_revaluation_view.xml',
        'views/res_config_view.xml',
        'views/account_views.xml',
    ],
    'installable': True,
    'application': True,
}
