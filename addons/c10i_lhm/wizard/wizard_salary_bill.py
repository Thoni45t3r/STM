from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import timedelta
import calendar


class LhmSalaryBill(models.TransientModel):
    _name           = "lhm.salary.bill.wizard"
    _description    = "Contractor Bill Wizard"

    def _get_partner_payroll(self):
        partner   = self.env['res.partner'].search([('name','=','Payroll Kebun')])
        if partner:
            return partner[0].id
        else:
            return False
    
    def _get_partner_insurance(self):
        partner   = self.env['res.partner'].search([('name','=','BPJS Kesehatan')])
        if partner:
            return partner[0].id
        else:
            return False

    def _get_partner_insurance2(self):
        partner   = self.env['res.partner'].search([('name','=','BPJS Ketenagakerjaan')])
        if partner:
            return partner[0].id
        else:
            return False


    payroll_partner_id = fields.Many2one("res.partner", "Partner Payroll", ondelete="restrict", required=True, default=_get_partner_payroll)
    insurance_partner_id = fields.Many2one("res.partner", "Partner BPJS", ondelete="restrict", required=True, default=_get_partner_insurance)
    insurance_partner_id2 = fields.Many2one("res.partner", "Partner BPJS", ondelete="restrict", required=True, default=_get_partner_insurance2)
    date_invoice = fields.Date('Accrual Date', required=True)
    account_period_id = fields.Many2one('account.period', 'Account Period', required=True, ondelete="restrict", copy=True)
    
    company_id      = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)

    @api.model
    def view_init(self, fields):
        for du in self.env['plantation.salary'].browse(self._context.get('active_ids', [])):
            if du.invoice_ids:
                raise UserError(_("Payroll Invoice telah dibuat. Silahkan Cancel dan Delete Invoice tersebut terlebih dahulu."))
        return False

    @api.model
    def default_get(self, default_fields):
        DaftarUpahObj = self.env['plantation.salary']
        context = self._context
        
        data = super(LhmSalaryBill, self).default_get(default_fields)
        if context.get('active_id'):
            du = DaftarUpahObj.browse(context['active_id'])
            data['account_period_id'] = du.period_id and du.period_id.id or False
            data['date_invoice'] = du.to_date
        return data

    @api.multi
    def create_invoice(self):
        DaftarUpahObj = self.env['plantation.salary']
        context = self._context
        du = DaftarUpahObj.browse(context['active_id'])

        res = []
        date_from   = self.account_period_id.date_start
        date_to     = self.account_period_id.date_stop
        lhm_datas   = self.env['lhm.transaction'].search([('date', '>=', date_from),
                                                  ('date', '<=', date_to), 
                                                  ('state', '=', 'done')],  order='name', )
        type_lokasi_null   = self.env['lhm.location.type'].search([('name','=','-')], limit=1)
        Activity = self.env['lhm.activity']
        activity_datas = Activity.search([('id','>',0)])
        activity_dict = {}
        for x in activity_datas:
            activity_dict.update({x.id: x})
        query1 = """SELECT lt.id as lhm_id, he.id, he.no_induk, lt.date, ll.code as loc, 
            ltl.location_type_id, ltl.location_id, ltl.activity_id, la.account_id, 
            hmw.umr_month as gp, 
            (CASE 
                WHEN (hat.type_hk = 'hke' and het.monthly_employee = true and coalesce(ltl.work_day,0) > 0) 
                    THEN (coalesce(ltl.min_wage_value,0) * coalesce(ltl.work_day,0)) 
                WHEN (hat.type_hk = 'hke' and het.sku_employee = true and coalesce(ltl.work_day,0) > 0) 
                    THEN (coalesce(ltl.min_wage_value,0) * coalesce(ltl.work_day,0))
                WHEN (hat.type_hk = 'hke' and het.contract_employee = true and coalesce(ltl.work_day,0) > 0) 
                    THEN (coalesce(ltl.min_wage_value,0) * coalesce(ltl.work_day,0)) 
                WHEN (hat.type_hk = 'hke' and het.bhl_employee = true and coalesce(ltl.work_day,0) > 0) 
                    THEN (coalesce(ltl.min_wage_value,0) * coalesce(ltl.work_day,0)) 
                ELSE 0 
            END) AS HKE_BYR, 
            (CASE 
                WHEN hat.type_hk = 'hkne' and het.monthly_employee = true and coalesce(ltl.non_work_day,0) > 0 
                    THEN (coalesce(ltl.min_wage_value,0) * coalesce(ltl.non_work_day,0)) 
                WHEN hat.type_hk = 'hkne' and het.sku_employee = true and coalesce(ltl.non_work_day,0) > 0 
                    THEN (coalesce(ltl.min_wage_value,0) * coalesce(ltl.non_work_day,0)) 
                WHEN hat.type_hk = 'hkne' and het.contract_employee = true and coalesce(ltl.non_work_day,0) > 0 
                    THEN (coalesce(ltl.min_wage_value,0) * coalesce(ltl.non_work_day,0)) 
                ELSE 0 
            END) AS HKNE_BYR, coalesce(ltl.premi,0.0) as premi, 
            coalesce(ltl.overtime_value,0.0) as overtime_value, 
            coalesce(ltl.penalty,0.0) as penalty 
            FROM lhm_transaction lt 
                INNER JOIN hr_foreman hf ON lt.kemandoran_id=hf.id 
                INNER JOIN lhm_transaction_line ltl ON ltl.lhm_id=lt.id 
                INNER JOIN hr_employee he ON he.id = ltl.employee_id 
                INNER JOIN resource_resource rr ON rr.id = he.resource_id 
                INNER JOIN hr_employee_type het ON het.id = he.type_id 
                LEFT OUTER JOIN hr_division hd ON he.division_id=hd.id 
                INNER JOIN hr_attendance_type hat ON ltl.attendance_id=hat.id 
                INNER JOIN hr_ptkp hp ON he.ptkp_id=hp.id 
                INNER JOIN hr_minimum_wage hmw ON ltl.min_wage_id=hmw.id 
                LEFT OUTER JOIN lhm_location_type llt ON ltl.location_type_id=llt.id 
                LEFT OUTER JOIN lhm_location ll ON ltl.location_id=ll.id 
                LEFT OUTER JOIN lhm_activity la ON ltl.activity_id=la.id 
                INNER JOIN res_users ru ON ru.id= lt.create_uid 
                INNER JOIN res_partner rp ON rp.id=ru.partner_id 
            WHERE lt.date::date BETWEEN '%s'::date and '%s'::date and 
                lt.state in ('done','in_progress', 'close') and 
                ltl.attendance_id is not null 
            ORDER BY he.id"""
        self.env.cr.execute(query1%(date_from, date_to))
        q_res = self.env.cr.dictfetchall()
        employee_datas = list(map(lambda x: (x, self.env['hr.employee'].browse(x)), list(set([l['id'] for l in q_res if l.get('id',False)])) ))
        # HKE
        grouped_hke = {}
        # total_hke = 0.0
        # total_premi = 0.0
        # total_overtime = 0.0
        # total_penalty = 0.0
        for line in q_res:
            if (line.get('hke_byr', 0.0) + line.get('premi', 0.0) + line.get('overtime_value', 0.0) - line.get('penalty', 0.0))==0.0:
                continue
            # print line['no_induk'], line['date'], line['loc'], \
                # line['hke_byr'], line['premi'], line['overtime_value'], line['penalty']
            if not line.get('account_id', False):
                activity = activity_dict.get(line['activity_id'],False)
                raise UserError(_('Aktivitas [%s] %s tidak memiliki Account Allocation')%(activity.code, activity.name))

            key = (line.get('location_type_id', False), line.get('location_id', False), line.get('activity_id', False), line.get('account_id', False))
            if key not in grouped_hke.keys():
                grouped_hke.update({
                    key: {
                        'name': 'Total Upah HKE yang dibayar',
                        'plantation_location_type_id': line.get('location_type_id', False),
                        'plantation_location_id': line.get('location_id', False),
                        'plantation_activity_id': line.get('activity_id', False),
                        'account_id': line.get('account_id', False),
                        'amount': 0.0,
                        }
                    })
            grouped_hke[key]['amount'] += line.get('hke_byr', 0.0) + line.get('premi', 0.0) + line.get('overtime_value', 0.0) - line.get('penalty', 0.0)
            # total_hke+=line.get('hke_byr', 0.0)
            # total_premi+=line.get('premi', 0.0)
            # total_overtime+=line.get('overtime_value', 0.0)
            # total_penalty+=line.get('penalty', 0.0)
        # print "::::::::::::::::::::::::::::::::", total_hke
        # print "::::::::::::::::::::::::::::::::", total_premi
        # print "::::::::::::::::::::::::::::::::", total_overtime
        # print "::::::::::::::::::::::::::::::::", total_penalty
        # print "::::::::::::::::::::::::::::::::", sum([x['amount'] for x in grouped_hke.values()])
        query2 = """SELECT he.id, he.no_induk, he.ptkp_id, he.type_id, he.division_id,
                he.plantation_location_type_id, he.plantation_location_id, he.plantation_activity_hkne_id, he.plantation_activity_natura_id,
                SUM(CASE WHEN hat.type_hk = 'hkne' and het.monthly_employee = true and coalesce(ltl.non_work_day,0) > 0 THEN (coalesce(ltl.min_wage_value,0) * coalesce(ltl.non_work_day,0))
                    WHEN hat.type_hk = 'hkne' and het.sku_employee = true and coalesce(ltl.non_work_day,0) > 0 THEN (coalesce(ltl.min_wage_value,0) * coalesce(ltl.non_work_day,0))
                    WHEN hat.type_hk = 'hkne' and het.contract_employee = true and coalesce(ltl.non_work_day,0) > 0 THEN (coalesce(ltl.min_wage_value,0) * coalesce(ltl.non_work_day,0))
                    ELSE 0 END) AS HKNE_BYR,
                coalesce(hn.nature,0) - COALESCE(SUM(CASE WHEN hat.type_hk is null AND hat.type is null THEN  1 END) * coalesce(hn.potongan_rp,0), 0) as natura
            FROM lhm_transaction lt
                INNER JOIN hr_foreman hf ON lt.kemandoran_id=hf.id
                INNER JOIN lhm_transaction_line ltl ON ltl.lhm_id=lt.id
                INNER JOIN hr_employee he ON he.id = ltl.employee_id
                INNER JOIN resource_resource rr ON rr.id = he.resource_id
                INNER JOIN hr_employee_type het ON het.id = he.type_id
                INNER JOIN hr_nature hn ON hn.ptkp_id = he.ptkp_id
                LEFT OUTER JOIN hr_division hd ON he.division_id=hd.id
                INNER JOIN hr_attendance_type hat ON ltl.attendance_id=hat.id
                INNER JOIN hr_ptkp hp ON he.ptkp_id=hp.id
                INNER JOIN hr_minimum_wage hmw ON ltl.min_wage_id=hmw.id
                LEFT OUTER JOIN lhm_location_type llt ON ltl.location_type_id=llt.id
                LEFT OUTER JOIN lhm_location ll ON ltl.location_id=ll.id
                LEFT OUTER JOIN lhm_activity la ON ltl.activity_id=la.id 
                INNER JOIN res_users ru ON ru.id= lt.create_uid 
                INNER JOIN res_partner rp ON rp.id=ru.partner_id
            WHERE lt.date::DATE BETWEEN '%s'::DATE AND '%s'::DATE
            AND lt.state in ('done','in_progress', 'close')
            AND ltl.attendance_id is not null
            GROUP BY he.id, he.no_induk, he.ptkp_id, he.type_id, he.division_id, hmw.umr_month, hn.nature, hn.potongan_rp,
                he.plantation_location_type_id, he.plantation_location_id, he.plantation_activity_hkne_id, 
                he.plantation_activity_natura_id
            ORDER BY he.id"""
        self.env.cr.execute(query2%(date_from, date_to))
        q_res2 = self.env.cr.dictfetchall()
        # HKNE
        grouped_hkne = {}
        # total_hkne = 0.0
        for line in q_res2:
            if line.get('hkne_byr',0.0)<=0.0:
                continue
            # print line['no_induk'], line['hkne_byr']
            key = (line.get('plantation_location_type_id', False), line.get('plantation_location_id', False), \
                line.get('plantation_activity_hkne_id', False))
            if key not in grouped_hkne.keys():
                account_id = activity_dict.get(line.get('plantation_activity_hkne_id', False), False) and \
                    activity_dict[line['plantation_activity_hkne_id']]._get_account() or False
                if not account_id:
                    raise UserError(_('Karyawan dengan NIK %s tidak memiliki Alokasi Activitas untuk Hari Kerja Non-Efektif')%(line.get('no_induk','Kosong')))
                grouped_hkne.update({
                    key: {
                        'name': 'Total Upah HKNE yang dibayar',
                        'plantation_location_type_id': line.get('plantation_location_type_id', False),
                        'plantation_location_id': line.get('plantation_location_id', False),
                        'plantation_activity_id': line.get('plantation_activity_hkne_id', False),
                        'account_id': account_id and account_id.id or False,
                        'amount': 0.0,
                        }
                    })
            grouped_hkne[key]['amount'] += line.get('hkne_byr', 0.0)
            # total_hkne += line.get('hkne_byr', 0.0)
        # print ":::::::::::::::::", total_hkne
        # Natura
        grouped_natura = {}
        for line in q_res2:
            employee = dict(employee_datas).get(line.get('id',False))
            if employee.type_id and (employee.type_id.sku_employee or employee.type_id.monthly_employee \
                    or employee.type_id.contract_employee):
                natura = line.get('natura',0.0)
            else:
                natura = 0.0
            if natura<=0.0:
                continue
            # print line['no_induk'], natura
            key = (line.get('plantation_location_type_id', False), line.get('plantation_location_id', False), \
                line.get('plantation_activity_natura_id', False))
            if key not in grouped_natura.keys():
                account_id = activity_dict.get(line.get('plantation_activity_natura_id', False), False) and \
                    activity_dict[line['plantation_activity_natura_id']]._get_account() or False
                if not account_id:
                    raise UserError(_('Karyawan dengan NIK %s tidak memiliki Alokasi Activitas untuk beban Natura')%(line.get('no_induk','Kosong')))
                grouped_natura.update({
                    key: {
                        'name': 'Total Natura yang dibayar',
                        'plantation_location_type_id': line.get('plantation_location_type_id', False),
                        'plantation_location_id': line.get('plantation_location_id', False),
                        'plantation_activity_id': line.get('plantation_activity_natura_id', False),
                        'account_id': account_id and account_id.id or False,
                        'amount': 0.0,
                        }
                    })
            grouped_natura[key]['amount'] += natura
        # BPJS TENAGA KERJA
        grouped_bpjs_tk = {} 
        grouped_bpjs_tk2 = {} 
        bpjs_tk         = self.env['hr.insurance'].search([('type', '=', 'ketenagakerjaan'), ("date_from", '<=', date_from), ("date_to", '>=', date_to)], limit=1)
        if bpjs_tk and not bpjs_tk.tunjangan_account_id:
            raise UserError(_('Akun Pembebanan pada Tunjangan BPJS Ketenagakerjaan belum didefinisikan'))
        elif bpjs_tk and not bpjs_tk.setoran_account_id:
            raise UserError(_('Akun Piutang Setoran BPJS Ketenagakerjaan belum didefinisikan'))
        # BPJS PENSIUN
        grouped_bpjs_pens = {} 
        grouped_bpjs_pens2 = {} 
        bpjs_pensiun    = self.env['hr.insurance'].search([('type', '=', 'pensiun'), ("date_from", '<=', date_from), ("date_to", '>=', date_to)], limit=1)
        if bpjs_pensiun and not bpjs_pensiun.tunjangan_account_id:
            raise UserError(_('Akun Pembebanan pada Tunjangan BPJS Pensiun belum didefinisikan'))
        elif bpjs_pensiun and not bpjs_pensiun.setoran_account_id:
            raise UserError(_('Akun Piutang Setoran BPJS Pensiun belum didefinisikan'))
        # BPJS KESEHATAN
        grouped_bpjs_kes = {} 
        grouped_bpjs_kes2 = {} 
        bpjs_kesehatan  = self.env['hr.insurance'].search([('type', '=', 'kesehatan'), ("date_from", '<=', date_from), ("date_to", '>=', date_to)], limit=1)
        if bpjs_kesehatan and not bpjs_kesehatan.tunjangan_account_id:
            raise UserError(_('Akun Pembebanan pada Tunjangan BPJS Kesehatan belum didefinisikan'))
        elif bpjs_kesehatan and not bpjs_kesehatan.setoran_account_id:
            raise UserError(_('Akun Piutang Setoran BPJS Kesehatan belum didefinisikan'))
        if employee_datas:
            for employee_id, employee in employee_datas:
                if not employee.resource_id.active:
                    continue
                # GAJI POKOK
                min_wage = False
                if employee and employee.basic_salary_type == 'employee':
                    min_wage = self.env['hr.minimum.wage'].search([('employee_id', '=', employee.id), ('date_from', '<=', self.account_period_id.date_start), ('date_to', '>=', self.account_period_id.date_stop)], limit=1)
                elif employee and employee.basic_salary_type == 'employee_type':
                    min_wage = self.env['hr.minimum.wage'].search([('employee_type_id', '=', employee.type_id.id), ('date_from', '<=', self.account_period_id.date_start), ('date_to', '>=', self.account_period_id.date_stop)], limit=1)

                # ALOKASI KETENAGAKERJAAN
                if bpjs_tk and employee.ketenagakerjaan:
                    if not employee.cost_center_id:
                        raise UserError(_('Cost Center pada Karyawan %s belum didefinisikan'%employee.name))
                    tipe_lokasi = employee.cost_center_id.location_type_id
                    lokasi = employee.cost_center_id.location_id

                    key = (employee.plantation_location_type_id.id, employee.plantation_location_id.id, \
                        employee.plantation_activity_bpjs_tk_id.id)
                    activity_bpjs = Activity.search([('account_id','=',bpjs_tk.tunjangan_account_id.id)], limit=1)
                    if key not in grouped_bpjs_tk.keys():
                        grouped_bpjs_tk.update({
                            key: {
                                'name': 'Tunjangan BPJS Ketenagakerjaan yg dibayarkan',
                                'plantation_location_type_id': tipe_lokasi.id,
                                'plantation_location_id': lokasi.id,
                                'plantation_activity_id': activity_bpjs and activity_bpjs[-1].id or False,
                                'account_id': bpjs_tk.tunjangan_account_id.id,
                                'amount': 0.0,
                                }
                            })
                    grouped_bpjs_tk[key]['amount'] += min_wage.umr_month * bpjs_tk.tunjangan/100
                    key = bpjs_tk.setoran_account_id.id
                    if key not in grouped_bpjs_tk2.keys():
                        grouped_bpjs_tk2.update({
                            key: {
                                'name': 'Setoran BPJS Ketenagakerjaan dari Pegawai',
                                'plantation_location_type_id': type_lokasi_null and type_lokasi_null[0].id or False,
                                'plantation_location_id': False,
                                'plantation_activity_id': False,
                                'account_id': bpjs_tk.setoran_account_id.id,
                                'amount': 0.0,
                                }
                            })
                    grouped_bpjs_tk2[key]['amount'] += min_wage.umr_month * (bpjs_tk.potongan - bpjs_tk.tunjangan)/100
                if bpjs_pensiun and employee.ketenagakerjaan:
                    if not employee.cost_center_id:
                        raise UserError(_('Cost Center pada Karyawan %s belum didefinisikan'%employee.name))
                    tipe_lokasi = employee.cost_center_id.location_type_id
                    lokasi = employee.cost_center_id.location_id
                    key = (employee.plantation_location_type_id.id, employee.plantation_location_id.id, \
                        employee.plantation_activity_bpjs_tk_id.id)
                    activity_bpjs = Activity.search([('account_id','=',bpjs_pensiun.tunjangan_account_id.id)], limit=1)
                    if key not in grouped_bpjs_pens.keys():
                        grouped_bpjs_pens.update({
                            key: {
                                'name': 'Tunjangan BPJS Pensiun yg dibayarkan',
                                'plantation_location_type_id': tipe_lokasi.id,
                                'plantation_location_id': lokasi.id,
                                'plantation_activity_id': activity_bpjs and activity_bpjs[-1].id or False,
                                'account_id': bpjs_pensiun.tunjangan_account_id.id,
                                'amount': 0.0,
                                }
                            })
                    grouped_bpjs_pens[key]['amount'] += min_wage.umr_month * bpjs_pensiun.tunjangan/100
                    key = bpjs_pensiun.setoran_account_id.id
                    if key not in grouped_bpjs_pens2.keys():
                        grouped_bpjs_pens2.update({
                            key: {
                                'name': 'Setoran BPJS Pensiun dari Pegawai',
                                'plantation_location_type_id': type_lokasi_null and type_lokasi_null[0].id or False,
                                'plantation_location_id': False,
                                'plantation_activity_id': False,
                                'account_id': bpjs_pensiun.setoran_account_id.id,
                                'amount': 0.0,
                                }
                            })
                    grouped_bpjs_pens2[key]['amount'] += min_wage.umr_month * (bpjs_pensiun.potongan - bpjs_pensiun.tunjangan)/100
                if bpjs_kesehatan and employee.kesehatan:
                    # print employee.no_induk,(min_wage.umr_month * bpjs_kesehatan.potongan/100)
                    if not employee.cost_center_id:
                        raise UserError(_('Cost Center pada Karyawan %s belum didefinisikan'%employee.name))
                    tipe_lokasi = employee.cost_center_id.location_type_id
                    lokasi = employee.cost_center_id.location_id
                    key = (employee.plantation_location_type_id.id, employee.plantation_location_id.id, \
                        employee.plantation_activity_bpjs_kes_id.id)
                    activity_bpjs = Activity.search([('account_id','=',bpjs_kesehatan.tunjangan_account_id.id)], limit=1)
                    if key not in grouped_bpjs_kes.keys():
                        grouped_bpjs_kes.update({
                            key: {
                                'name': 'Tunjangan BPJS Kesehatan yg dibayarkan',
                                'plantation_location_type_id': tipe_lokasi.id,
                                'plantation_location_id': lokasi.id,
                                'plantation_activity_id': activity_bpjs and activity_bpjs[-1].id or False,
                                'account_id': bpjs_kesehatan.tunjangan_account_id.id,
                                'amount': 0.0,
                                }
                            })
                    grouped_bpjs_kes[key]['amount'] += min_wage.umr_month * bpjs_kesehatan.tunjangan/100
                    key = bpjs_kesehatan.setoran_account_id.id
                    if key not in grouped_bpjs_kes2.keys():
                        grouped_bpjs_kes2.update({
                            key: {
                                'name': 'Setoran BPJS Kesehatan dari Pegawai',
                                'plantation_location_type_id': type_lokasi_null and type_lokasi_null[0].id or False,
                                'plantation_location_id': False,
                                'plantation_activity_id': False,
                                'account_id': bpjs_kesehatan.setoran_account_id.id,
                                'amount': 0.0,
                                }
                            })
                    grouped_bpjs_kes2[key]['amount'] += min_wage.umr_month * (bpjs_kesehatan.potongan - bpjs_kesehatan.tunjangan)/100
        ############################## CREATE INVOICE ###################################
        ####### INVOICE GAJI #########
        AccountInvoice = self.env['account.invoice']
        InvoiceLine = self.env['account.invoice.line']
        journal_id = AccountInvoice.with_context({'type': 'in_invoice'}).default_get(['journal_id'])['journal_id']
        if not journal_id:
            raise UserError(_('Please define an accounting purchase journal for this company.'))
        # BUAT INVOICE GAJI (HKE + HKNE + NATURA - BPJS TUNJANGAN)
        invoice_vals = {
            'name': '',
            'type': 'in_invoice',
            'reference': 'GAJI: LHM %s'%(datetime.strptime(self.date_invoice, '%Y-%m-%d').strftime('%d/%m/%Y')),
            'date_invoice': self.date_invoice,
            'account_id': self.payroll_partner_id.property_account_payable_id.id,
            'partner_id': self.payroll_partner_id.id,
            'partner_shipping_id': False,
            'journal_id': journal_id,
            'currency_id': self.company_id.currency_id.id,
            'company_id': self.company_id.id,
            # 'operating_unit_id': contractor_datas and contractor_datas[0].operating_unit_id and contractor_datas[0].operating_unit_id.id or False,
        }
        invoice = AccountInvoice.create(invoice_vals)
        for values in grouped_hke.values()+grouped_hkne.values()+grouped_natura.values():
            invoice_line_vals = {
                'invoice_id': invoice.id,
                'name': values.get('name','/'),
                'plantation_location_type_id': values.get('plantation_location_type_id', False),
                'plantation_location_id': values.get('plantation_location_id', False),
                'plantation_activity_id': values.get('plantation_activity_id', False),
                'account_id': values.get('account_id', False),
                'product_id': False,
                'uom_id': False,
                'quantity': 1,
                'price_unit': values.get('amount', 0.0),
            }
            invoice_line_id = InvoiceLine.create(invoice_line_vals)
        # Dikurangkan dengan Setoran Asuransi
        for values in grouped_bpjs_tk2.values() + grouped_bpjs_pens2.values() + grouped_bpjs_kes2.values():
            invoice_line_vals = {
                'invoice_id': invoice.id,
                'name': values.get('name','/'),
                'plantation_location_type_id': values.get('plantation_location_type_id', False),
                'plantation_location_id': values.get('plantation_location_id', False),
                'plantation_activity_id': values.get('plantation_activity_id', False),
                'account_id': values.get('account_id', False),
                'product_id': False,
                'uom_id': False,
                'quantity': 1,
                'price_unit': -1* values.get('amount', 0.0),
            }
            invoice_line_id = InvoiceLine.create(invoice_line_vals)
        # Dikurangkan dengan Potongan dan atau Ditambahkan Tunjangan/Rapel/THR
        for allow_type in du.allowance_ids.mapped('allowance_type_id'):
            if not allow_type.account_id:
                raise UserError(_("Allowance %s tidak memiliki Account atau Account Pembebanan.\n Silahkan diisi terlebih dahulu")%allow_type.name)
            allowance_amount = 0.0
            if allow_type.tunjangan:
                allowance_amount += sum(du.allowance_ids.filtered(lambda x: x.allowance_type_id.id==allow_type.id).mapped('tunjangan_lain'))
            if allow_type.potongan:
                allowance_amount -= sum(du.allowance_ids.filtered(lambda x: x.allowance_type_id.id==allow_type.id).mapped('potongan_lain'))
            if allow_type.koperasi:
                allowance_amount -= sum(du.allowance_ids.filtered(lambda x: x.allowance_type_id.id==allow_type.id).mapped('koperasi'))
            if allow_type.rapel:
                allowance_amount += sum(du.allowance_ids.filtered(lambda x: x.allowance_type_id.id==allow_type.id).mapped('rapel'))
            invoice_line_vals = {
                'invoice_id': invoice.id,
                'name': allow_type.name,
                # 'plantation_location_type_id': False,
                'plantation_location_type_id': type_lokasi_null and type_lokasi_null[0].id or False,
                'plantation_location_id': False,
                'plantation_activity_id': False,
                'account_id': allow_type.account_id.id,
                'product_id': False,
                'uom_id': False,
                'quantity': 1,
                'price_unit': allowance_amount,
            }
            invoice_line_id = InvoiceLine.create(invoice_line_vals)
        ####### END: INVOICE GAJI #########
        lhm_to_update = self.env['lhm.transaction'].search([('id','in',[x['lhm_id'] for x in q_res])])
        lhm_to_update.write({'state': 'close', 'invoice_id': invoice.id})
        res.append(invoice)
        ####### INVOICE POTONGAN/TUNJANGAN DLL #########
        for allow_type in du.allowance_ids.mapped('allowance_type_id'):
            if not allow_type.create_invoice:
                continue
            if not allow_type.account_id:
                raise UserError(_("Allowance %s tidak memiliki Account atau Account Pembebanan.\n Silahkan diisi terlebih dahulu")%allow_type.name)
            allowance_amount = 0.0
            if allow_type.tunjangan:
                allowance_amount += sum(du.allowance_ids.filtered(lambda x: x.allowance_type_id.id==allow_type.id).mapped('tunjangan_lain'))
            if allow_type.potongan:
                allowance_amount -= sum(du.allowance_ids.filtered(lambda x: x.allowance_type_id.id==allow_type.id).mapped('potongan_lain'))
            if allow_type.koperasi:
                allowance_amount -= sum(du.allowance_ids.filtered(lambda x: x.allowance_type_id.id==allow_type.id).mapped('koperasi'))
            if allow_type.rapel:
                allowance_amount += sum(du.allowance_ids.filtered(lambda x: x.allowance_type_id.id==allow_type.id).mapped('rapel'))
            invoice_vals2 = {
                'name': '',
                'type': 'in_invoice',
                'date_invoice': self.date_invoice,
                'account_id': allow_type.default_partner_id.property_account_payable_id.id,
                'partner_id': allow_type.default_partner_id.id,
                'partner_shipping_id': False,
                'journal_id': journal_id,
                'currency_id': self.company_id.currency_id.id,
                'company_id': self.company_id.id,
                # 'operating_unit_id': contractor_datas and contractor_datas[0].operating_unit_id and contractor_datas[0].operating_unit_id.id or False,
            }
            invoice = AccountInvoice.create(invoice_vals2)
            tipe_lokasi = employee.cost_center_id.location_type_id
            lokasi = employee.cost_center_id.location_id
            activity_ = Activity.search([('account_id','=',allow_type.account_id.id)], limit=1)
            invoice_line_vals = {
                'invoice_id': invoice.id,
                'name': allow_type.name,
                'plantation_location_type_id': type_lokasi_null and type_lokasi_null[0].id or False,
                # 'plantation_location_type_id': type_lokasi and type_lokasi.id or (type_lokasi_null and type_lokasi_null[0].id or False),
                'plantation_location_id': False,
                # 'plantation_location_id': type_lokasi and lokasi.id or False,
                'plantation_activity_id': False,
                'account_id': allow_type.account_id.id,
                'product_id': False,
                'uom_id': False,
                'quantity': 1,
                'price_unit': -1*allowance_amount,
            }
            invoice_line_id = InvoiceLine.create(invoice_line_vals)
        ####### END: INVOICE POTONGAN #########
        res.append(invoice)
        ####### INVOICE BPJS TENAGA KERJA #########
        invoice_vals = {
            'name': '',
            'type': 'in_invoice',
            'date_invoice': self.date_invoice,
            'reference': 'BPJS TK: LHM %s'%(datetime.strptime(self.date_invoice, '%Y-%m-%d').strftime('%d/%m/%Y')),
            'account_id': self.insurance_partner_id2.property_account_payable_id.id,
            'partner_id': self.insurance_partner_id2.id,
            'partner_shipping_id': False,
            'journal_id': journal_id,
            'currency_id': self.company_id.currency_id.id,
            'company_id': self.company_id.id,
            # 'operating_unit_id': contractor_datas and contractor_datas[0].operating_unit_id and contractor_datas[0].operating_unit_id.id or False,
        }
        invoice = AccountInvoice.create(invoice_vals)
        for values in grouped_bpjs_tk.values() + grouped_bpjs_tk2.values():
            invoice_line_vals = {
                'invoice_id': invoice.id,
                'name': values.get('name','/'),
                'plantation_location_type_id': values.get('plantation_location_type_id', False),
                'plantation_location_id': values.get('plantation_location_id', False),
                'plantation_activity_id': values.get('plantation_activity_id', False),
                'account_id': values.get('account_id', False),
                'product_id': False,
                'uom_id': False,
                'quantity': 1,
                'price_unit': values.get('amount', 0.0),
            }
            invoice_line_id = InvoiceLine.create(invoice_line_vals)
        ####### END: INVOICE BPJS TENAGA KERJA #########
        res.append(invoice)
        ####### INVOICE BPJS PENSIUN #########
        invoice_vals = {
            'name': '',
            'type': 'in_invoice',
            'reference': 'BPJS PENSIUN: LHM %s'%(datetime.strptime(self.date_invoice, '%Y-%m-%d').strftime('%d/%m/%Y')),
            'date_invoice': self.date_invoice,
            'account_id': self.insurance_partner_id2.property_account_payable_id.id,
            'partner_id': self.insurance_partner_id2.id,
            'partner_shipping_id': False,
            'journal_id': journal_id,
            'currency_id': self.company_id.currency_id.id,
            'company_id': self.company_id.id,
            # 'operating_unit_id': contractor_datas and contractor_datas[0].operating_unit_id and contractor_datas[0].operating_unit_id.id or False,
        }
        invoice = AccountInvoice.create(invoice_vals)
        for values in grouped_bpjs_pens.values() + grouped_bpjs_pens2.values():
            invoice_line_vals = {
                'invoice_id': invoice.id,
                'name': values.get('name','/'),
                'plantation_location_type_id': values.get('plantation_location_type_id', False),
                'plantation_location_id': values.get('plantation_location_id', False),
                'plantation_activity_id': values.get('plantation_activity_id', False),
                'account_id': values.get('account_id', False),
                'product_id': False,
                'uom_id': False,
                'quantity': 1,
                'price_unit': values.get('amount', 0.0),
            }
            invoice_line_id = InvoiceLine.create(invoice_line_vals)
        ####### END: INVOICE BPJS PENSIUN #########
        res.append(invoice)
        ####### INVOICE BPJS KESEHATAN #########
        invoice_vals = {
            'name': '',
            'type': 'in_invoice',
            'date_invoice': self.date_invoice,
            'account_id': self.insurance_partner_id.property_account_payable_id.id,
            'reference': 'BPJS KESEHATAN: LHM %s'%(datetime.strptime(self.date_invoice, '%Y-%m-%d').strftime('%d/%m/%Y')),
            'partner_id': self.insurance_partner_id.id,
            'partner_shipping_id': False,
            'journal_id': journal_id,
            'currency_id': self.company_id.currency_id.id,
            'company_id': self.company_id.id,
            # 'operating_unit_id': contractor_datas and contractor_datas[0].operating_unit_id and contractor_datas[0].operating_unit_id.id or False,
        }
        invoice = AccountInvoice.create(invoice_vals)
        for values in grouped_bpjs_kes.values() + grouped_bpjs_kes2.values():
            invoice_line_vals = {
                'invoice_id': invoice.id,
                'name': values.get('name','/'),
                'plantation_location_type_id': values.get('plantation_location_type_id', False),
                'plantation_location_id': values.get('plantation_location_id', False),
                'plantation_activity_id': values.get('plantation_activity_id', False),
                'account_id': values.get('account_id', False),
                'product_id': False,
                'uom_id': False,
                'quantity': 1,
                'price_unit': values.get('amount', 0.0),
            }
            invoice_line_id = InvoiceLine.create(invoice_line_vals)
        ####### END: INVOICE BPJS KESEHATAN #########
        res.append(invoice)

        # Necessary to force computation of taxes. In account_invoice, they are triggered
        # by onchanges, which are not triggered when doing a create.
        for inv in res:
            inv.compute_taxes()
            inv.message_post('This invoice has been created from Buku Kontraktor')

        if self._context.get('active_id', False):
            self.env['plantation.salary'].browse(self._context.get('active_id')).write({
                'invoice_ids': [(6, 0, [x.id for x in res])],
                'state': 'done'})
        # Redirect to show Invoice
        action = self.env.ref('account.action_invoice_tree2').read()[0]
        action['domain'] = [('id','in',[x.id for x in res])]
        return action