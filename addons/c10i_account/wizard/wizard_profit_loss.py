# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
from odoo.addons.jasper_reports import JasperDataParser
from odoo import models, fields, tools, api, _
from datetime import datetime
import time
from datetime import date

class wizard_profit_loss(models.TransientModel):
    _name           = "wizard.profit.loss"
    _description    = "Report Profit Loss"
    
    period_id_curr      = fields.Many2one(comodel_name="account.period", string="Current Period", ondelete="restrict")
    from_date_curr      = fields.Date("From Date")
    to_date_curr        = fields.Date("To Date")
    period_id_prev      = fields.Many2one(comodel_name="account.period", string="Previuos Period", ondelete="restrict")
    from_date_prev      = fields.Date("From Date")
    to_date_prev        = fields.Date("To Date")
    report_group        = fields.Selection([('summary','Summary'),('detail','Detail')],string='Report Group',default='summary')
    company_id          = fields.Many2one(comodel_name='res.company', string="Company", default=lambda self: self.env['res.company']._company_default_get('account.account'))
    report_type         = fields.Selection(JasperDataParser.REPORT_TYPE, string="Document Type", default=lambda *a: 'xlsx')

    @api.onchange('period_id_curr')
    def _onchange_period_id_curr(self):
        if self.period_id_curr:
            period_ids_curr = self.env['account.period'].search([('id', '=', self.period_id_curr.id)])
            self.from_date_curr = period_ids_curr[-1].date_start
            self.to_date_curr = period_ids_curr[-1].date_stop

    @api.onchange('period_id_prev')
    def _onchange_period_id_prev(self):
        if self.period_id_prev:
            period_ids_prev = self.env['account.period'].search([('id', '=', self.period_id_prev.id)])
            self.from_date_prev = period_ids_prev[-1].date_start
            self.to_date_prev = period_ids_prev[-1].date_stop

    @api.multi
    def create_report(self):
        data        = self.read()[-1]
        name        = 'report_profit_loss'

        tools.drop_view_if_exists(self._cr, 'data_pl')
        self._cr.execute("""
            CREATE VIEW data_pl AS (
                select aa.id,aa.parent_id,aa.code
                ,aa.name 
                ,aat.name as type
                ,COALESCE(sum(CASE WHEN aat.name ='Income' THEN -c1 ELSE c1 END),0) AS c1
                ,COALESCE(sum(CASE WHEN aat.name ='Income' THEN -c2 ELSE c2 END),0) AS c2
                ,COALESCE(sum(CASE WHEN aat.name ='Income' THEN -c3 ELSE c3 END),0) AS c3
                from account_account aa
                left join account_account_type aat on aat.id=aa.user_type_id AND aat.include_initial_balance IS FALSE
                left outer join
                (
                select account_id
                ,case when sum(debit-credit) > 0 then sum(debit-credit) else sum(debit-credit) end as c1,(0) as c2,(0) as c3
                from account_move_line aml
                inner join account_move am on am.id = aml.move_id
                and aml.date BETWEEN %s::date AND %s::date 
                and am.state in ('posted')
                group by account_id
                UNION ALL
                select account_id,(0) c1
                ,case when sum(debit-credit) > 0 then sum(debit-credit) else sum(debit-credit) end as c2,(0) as c3
                from account_move_line aml
                inner join account_move am on am.id = aml.move_id
                AND aml.date BETWEEN %s::date AND %s::date 
                and am.state in ('posted')
                group by account_id
                UNION ALL
                select account_id,(0) c1,(0) c2
                ,case when sum(debit-credit) > 0 then sum(debit-credit) else sum(debit-credit) end as c3
                from account_move_line aml
                inner join account_move am on am.id = aml.move_id
                AND aml.date <= %s::date   
                and am.state in ('posted')
                group by account_id
                ) data on data.account_id=aa.id
                WHERE aa.code > (SELECT aa.code 
                FROM account_account aa
                LEFT JOIN account_account_type aat ON aat."id"=aa.user_type_id 
                WHERE aat.include_initial_balance IS TRUE 
                ORDER BY aa.code DESC LIMIT 1)
                GROUP BY aa.id,aa.parent_id,aa.code,aa.name,aat.name 
                order by aa.code            
                )""",(self.from_date_curr,self.to_date_curr,self.from_date_prev,self.to_date_prev,self.to_date_curr))


        name_report = False
        if self.report_group == "summary":
            name_report = "report_profit_loss_summary"
        else:
            name_report = "report_profit_loss_detail"

        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : name_report,
            'datas': {
                    'model'         :'wizard.profit.loss',
                    'id'            : self._context.get('active_ids') and self._context.get('active_ids')[0] or  self.id,
                    'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or[],
                    'report_type'   : data['report_type'],
                    'form'          : data
                },
            'nodestroy'     : False
            }
wizard_profit_loss()