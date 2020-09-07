# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
from odoo import api, fields, models
from odoo.addons.jasper_reports import JasperDataParser
from odoo.addons.jasper_reports import jasper_report
# from odoo.addons.account.report import account_report_financial

class jasper_report_financial(JasperDataParser.JasperDataParser):
    def __init__(self, cr, uid, ids, data, context):
        super(jasper_report_financial, self).__init__(cr, uid, ids, data, context)
    
    def _compute_account_balance(self, cr, uid, ids, accounts, context=None):
        """ compute the balance, debit and credit for the provided accounts
        """
        if context is None:
            context = {}
        mapping = {
            'init_balance': "COALESCE(SUM(init_balance), 0) as init_balance",
            'debit': "COALESCE(SUM(debit), 0) as debit",
            'credit': "COALESCE(SUM(credit), 0) as credit",
            'balance': "COALESCE(SUM(init_balance),0) + COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
        }
        mapping1 = {
            'init_balance': "SUM(0) as init_balance",
            'debit': "COALESCE(SUM(debit), 0) as debit",
            'credit': "COALESCE(SUM(credit), 0) as credit",
            # 'balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
        }
        mapping2 = {
            'init_balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as init_balance",
            'debit': "SUM(0) as debit",
            'credit': "SUM(0) as credit",
            # 'balance': "SUM(0) as balance",
        }

        if not (context.get('date_from') or context.get('date_from_cmp')):
            dont_show_initial_bal = " 1=0 AND "
        else:
            dont_show_initial_bal = " account_id is not NULL AND "
        env1 = api.Environment(cr, uid, context)
        
        ctx = context.copy()
        ctx.update({'initial_bal': True})
        env2 = api.Environment(cr, uid, ctx)
        res = {}
        for account in accounts:
            res[account.id] = dict((fn, 0.0) for fn in mapping.keys())
        if accounts:
            tables1, where_clause1, where_params1 = env1['account.move.line']._query_get()
            tables2, where_clause2, where_params2 = env2['account.move.line']._query_get()
            tables1 = tables1.replace('"', '') if tables1 else "account_move_line"
            tables2 = tables2.replace('"', '') if tables2 else "account_move_line"
            wheres1 = [""]
            wheres2 = [""]
            if where_clause1.strip():
                wheres1.append(where_clause1.strip())
            if where_clause2.strip():
                wheres2.append(where_clause2.strip())
            filters1 = " AND ".join(wheres1)
            filters2 = " AND ".join(wheres2)
            request = "SELECT id, " + ', '.join(mapping.values()) + \
                " FROM ( " \
                    "SELECT account_id as id, " + ', '.join(mapping1.values()) + \
                       " FROM " + tables1 + \
                       " WHERE account_id IN %s " \
                            + filters1 + \
                       " GROUP BY account_id" \
                    " UNION ALL " \
                    "SELECT account_id as id, " + ', '.join(mapping2.values()) + \
                       " FROM " + tables2 + \
                            ", (select a.id from account_account a inner join  account_account_type aat ON aat.id=a.user_type_id where aat.include_initial_balance) bs_acc " \
                       " WHERE " +dont_show_initial_bal+ \
                            " account_id IN %s " \
                            " AND (account_move_line.account_id=bs_acc.id) "\
                            + filters2 + \
                       " GROUP BY account_id" \
                    ") sub " \
                "GROUP BY id"
            # params = (tuple(accounts._ids),) + tuple(where_params)
            params = (tuple(accounts._ids),) + tuple(where_params1) + \
                (tuple(accounts._ids),) + tuple(where_params2)
            env1.cr.execute(request, params)
            for row in env1.cr.dictfetchall():
                res[row['id']] = row
        return res

    def _compute_report_balance(self, cr, uid, ids, reports, context=None):
        '''returns a dictionary with key=the ID of a record and value=the credit, debit and balance amount
           computed for this record. If the record is of type :
               'accounts' : it's the sum of the linked accounts
               'account_type' : it's the sum of leaf accoutns with such an account_type
               'account_report' : it's the amount of the related report
               'sum' : it's the sum of the children of this record (aka a 'view' record)'''
        env = api.Environment(cr, uid, {})
        res = {}
        fields = ['init_balance','credit', 'debit', 'balance']
        # fields = ['credit', 'debit', 'balance']
        for report in reports:
            if report.id in res:
                continue
            res[report.id] = dict((fn, 0.0) for fn in fields)
            if report.type == 'accounts':
                # it's the sum of the linked accounts
                res[report.id]['account'] = self._compute_account_balance(cr, uid, ids, report.account_ids, context=context)
                for value in res[report.id]['account'].values():
                    for field in fields:
                        res[report.id][field] += value.get(field)
            elif report.type == 'account_type':
                # it's the sum the leaf accounts with such an account type
                accounts = env['account.account'].search([('user_type_id', 'in', report.account_type_ids.ids)])
                res[report.id]['account'] = self._compute_account_balance(cr, uid, ids, accounts, context=context)
                for value in res[report.id]['account'].values():
                    for field in fields:
                        res[report.id][field] += value.get(field)
            elif report.type == 'account_report' and report.account_report_id:
                # it's the amount of the linked report
                res2 = self._compute_report_balance(cr, uid, ids, report.account_report_id, context=context)
                for key, value in res2.items():
                    for field in fields:
                        res[report.id][field] += value[field]
            elif report.type == 'sum':
                # it's the sum of the children of this account.report
                res2 = self._compute_report_balance(cr, uid, ids, report.children_ids, context=context)
                for key, value in res2.items():
                    for field in fields:
                        res[report.id][field] += value[field]
        return res

    def get_account_lines(self, cr, uid, ids, data, context):
        lines = []
        env = api.Environment(cr, uid, context or {})
        account_report = env['account.financial.report'].search([('id', '=', data['account_report_id'][0])])
        child_reports = account_report._get_children_by_order()
        res = self._compute_report_balance(cr, uid, ids, child_reports, context=data.get('used_context'))
        if data['enable_filter']:
            comparison_res = self._compute_report_balance(cr, uid, ids, child_reports, context=data.get('comparison_context'))
            for report_id, value in comparison_res.items():
                res[report_id]['comp_bal'] = value['balance']
                report_acc = res[report_id].get('account')
                if report_acc:
                    for account_id, val in comparison_res[report_id].get('account').items():
                        report_acc[account_id]['comp_bal'] = val['balance']

        for report in child_reports:
            vals = {
                'account_code': '',
                'account_name': report.name,
                'name': report.name,
                'balance': res[report.id]['balance'] * report.sign,
                'type': 'report',
                'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
                'account_type': report.type or False, #used to underline the financial report balances
            }
            if data['debit_credit']:
                vals['init_balance'] = res[report.id]['init_balance']
                vals['debit'] = res[report.id]['debit']
                vals['credit'] = res[report.id]['credit']

            if data['enable_filter']:
                vals['balance_cmp'] = res[report.id]['comp_bal'] * report.sign

            lines.append(vals)
            if report.display_detail == 'no_detail':
                #the rest of the loop is used to display the details of the financial report, so it's not needed here.
                continue

            if res[report.id].get('account'):
                sub_lines = []
                for account_id, value in res[report.id]['account'].items():
                    #if there are accounts to display, we add them to the lines with a level equals to their level in
                    #the COA + 1 (to avoid having them with a too low level that would conflicts with the level of data
                    #financial reports for Assets, liabilities...)
                    flag = False
                    account = env['account.account'].browse(account_id)
                    vals = {
                        'account_code': account.code,
                        'account_name': account.name,
                        'name': str(account.id) + ' ' + account.name,
                        'balance': value['balance'] * report.sign or 0.0,
                        'type': 'account',
                        'level': report.display_detail == 'detail_with_hierarchy' and 4,
                        'account_type': account.internal_type,
                    }
                    if data['debit_credit']:
                        vals['init_balance'] = value['init_balance']
                        vals['debit'] = value['debit']
                        vals['credit'] = value['credit']
                        if not account.company_id.currency_id.is_zero(vals['debit']) or not account.company_id.currency_id.is_zero(vals['credit']):
                            flag = True
                    if not account.company_id.currency_id.is_zero(vals['balance']):
                        flag = True
                    if data['enable_filter']:
                        vals['balance_cmp'] = value['comp_bal'] * report.sign
                        if not account.company_id.currency_id.is_zero(vals['balance_cmp']):
                            flag = True
                    if flag:
                        sub_lines.append(vals)
                lines += sorted(sub_lines, key=lambda sub_line: sub_line['name'])
        return lines

    # @api.model
    def generate_data_source(self, cr, uid, ids, data, context):
        return 'records'

    # @api.model
    def generate_parameters(self, cr, uid, ids, data, context):
        env = api.Environment(cr, uid, {})
        account_report = env['account.financial.report'].search([('id', '=', data['form']['account_report_id'][0])])
        company = env['res.company'].browse(data['form']['company_id'][0])
        param = {
                'account_report' : account_report and account_report.name or 'None',
                'company_name' : company.name,
                'company_id' : str(data['form']['company_id'][0]),
                }
        return param

    # @api.model
    def generate_properties(self, cr, uid, ids, data, context):
        return {}

    # @api.model
    def generate_output(self,cr, uid, ids, data, context):
        return data['form']['report_type']
    
    # @api.model
    def generate_records(self, cr, uid, ids, data, context):
        return self.get_account_lines(cr, uid, ids, data.get('form'), context)

jasper_report.ReportJasper('report.accounting_report_jasper', 'accounting.report', parser=jasper_report_financial,)
jasper_report.ReportJasper('report.accounting_report_jasper_4c', 'accounting.report', parser=jasper_report_financial,)
jasper_report.ReportJasper('report.accounting_report_jasper_comp', 'accounting.report', parser=jasper_report_financial,)

class jasper_account_legal_report_parser(JasperDataParser.JasperDataParser):
    def __init__(self, cr, uid, ids, data, context):
        super(jasper_account_legal_report_parser, self).__init__(cr, uid, ids, data, context)

    def generate_data_source(self, cr, uid, ids, data, context):
        return 'parameters'

    def generate_parameters(self, cr, uid, ids, data, context):
        return data['form']

    def generate_properties(self, cr, uid, ids, data, context):
        return {}

    def generate_output(self,cr, uid, ids, data, context):
        # return data['report_type']
        return 'xlsx'

    def generate_records(self, cr, uid, ids, data, context):
        return {}

jasper_report.ReportJasper('report.account_report_balance_sheet', 'account.legal.report', parser=jasper_account_legal_report_parser,)
jasper_report.ReportJasper('report.account_report_profit_loss', 'account.legal.report', parser=jasper_account_legal_report_parser,)
