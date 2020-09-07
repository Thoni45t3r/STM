import time
import calendar
from dateutil.relativedelta import relativedelta
from openerp.tools.translate import _
from odoo import models, fields, tools, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from openerp import models, fields, api, exceptions, tools
import base64
import xlrd
from datetime import time
from odoo import api, fields, models, tools

####################################################### Start of Plantation_Salary #######################################################
class plantation_salary(models.Model):
    _inherit = 'plantation.salary'
    
    lhm_input_type  = fields.Selection([('reguler','Reguler'),('work_target','Target Pekerjaan')], 'Transaction Type', default=lambda self: self.env.context.get('lhm_input_type','reguler'))

    @api.onchange('period_id')
    def _onchange_period_id(self):
        if self.period_id:
            period_ids = self.env['account.period'].search([('id', '=', self.period_id.id)])
            if len(period_ids) > 1:
                return {
                    'warning': {'title': _('Kesalahan Input'),
                                'message': _("Period ada 2. Hubungi Administrator untuk perbaikan.") },
                }
            else:
                self.from_date  = period_ids[-1].date_start
                self.to_date    = period_ids[-1].date_stop

    @api.multi
    def button_confirm(self):
        if self.lhm_input_type=='reguler':
            self.generate_data_upah()
        elif self.lhm_input_type=='work_target':
            wiz_val = {'salary_id': self.id}
            ############### VALIDATION RESTAN ##################
            line_nab_lhm_lines = self.env['lhm.transaction.line.nab.line'].search([
                ('lhm_line_id.lhm_input_type','=','work_target'), 
                ('date','>=',self.from_date), ('date','<=',self.to_date), 
                ('lhm_line_id.lhm_id.state','in',['done','in_progress', 'close']), 
                ('lhm_line_id.attendance_id','!=',False)])
            lhm_lines = self.env['lhm.transaction.line'].search([('lhm_id.lhm_input_type','=','work_target'), 
                ('lhm_id.date','>=',self.from_date), ('lhm_id.date','<=',self.to_date), 
                ('lhm_id.state','in',['done','in_progress', 'close']), ('attendance_id','!=',False)])
            for link in line_nab_lhm_lines:
                if link.lhm_line_id.id in lhm_lines.ids:
                    continue
                lhm_lines |= link.lhm_line_id
            # Detail LHM dibulan yg sama, untuk cek BPJS
            lhm_lines_other = self.env['lhm.transaction.line'].search([('lhm_id.account_period_id','=',self.period_id.id),
                ('lhm_id.date','<',self.from_date), ('attendance_id','!=',False), 
                ('lhm_id.state','in',['done','in_progress', 'close']),
                ('id','not in',(lhm_lines and lhm_lines.ids or [0,0]))])

            lhm_not_valid = self.env['lhm.transaction']
            for line in lhm_lines:
                if line.dummy_skip:
                    # ini biasanya adalah data import periode sebelumnya yg selalu dianggap valid
                    continue
                if line.activity_id.is_panen and line.pending_work_result>0.0:
                    lhm_not_valid |= line.lhm_id
            ############### END: VALIDATION RESTAN ##################
            if lhm_not_valid:
                tittle = "Restan Ditemukan"
                message = _("Ditemukan LHM Target yang belum terkirim di Nota Angkut Buah.\n"
                    "LHM tersebut diantaranya adalah: \n%s\n"
                    "Apakah Anda ingin melanjutkan penghitungan Upah ini?") % "\n".join(lhm_not_valid.mapped('name'))
                wiz_val.update({
                    'restan_found': True, 
                    'tittle': tittle,
                    'message': message})
            else:
                wiz_val.update({'tittle': 'Apakah anda yakin?'})
            view = self.env.ref('c10i_lhm_work_target.view_salary_target_confirmation')
            wiz = self.env['plantation.salary.target.confirmation'].create(wiz_val)
            return {
                'name': _('Confirmation'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'plantation.salary.target.confirmation',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }
        self.state = 'confirmed'

    @api.multi
    def generate_data_upah(self):
        # Start BPJS*******************************************************************************
        if self.bpjs_ids:
            self._cr.execute("DELETE FROM plantation_salary_bpjs WHERE salary_id=%s", (self.id,))
        # Loop Data Karyawan Filter active=True
        # data_employee   = self.env['hr.employee'].search(['&', ('active', '=', True), '|', ('kesehatan', '=', True), ('ketenagakerjaan', '=', True)], order='no_induk',)
        data_employee   = self.env['hr.employee'].search(['|', ('kesehatan', '=', True), ('ketenagakerjaan', '=', True)], order='no_induk',)

        pkwt_employee = self.env['hr.employee.type'].search([('pkwt_employee', '=', True)])
        bpjs_tk_kontrak = self.env['hr.insurance'].search([('type', '=', 'ketenagakerjaan'),
                                                           ('employee_type_id', '=', pkwt_employee.id),
                                                           ("date_from", '<=', self.from_date), ("date_to", '>=', self.to_date)])

        bpjs_tk = self.env['hr.insurance'].search([('type', '=', 'ketenagakerjaan'),
                                                           ('employee_type_id', '=', False),
                                                           ("date_from", '<=', self.from_date), ("date_to", '>=', self.to_date)])

        bpjs_pensiun    = self.env['hr.insurance'].search([('type', '=', 'pensiun'), ("date_from", '<=', self.from_date), ("date_to", '>=', self.to_date)], limit=1)
        bpjs_kesehatan  = self.env['hr.insurance'].search([('type', '=', 'kesehatan'), ("date_from", '<=', self.from_date), ("date_to", '>=', self.to_date)], limit=1)
        if data_employee:
            for employee in data_employee:
                min_wage = False
                if employee and employee.basic_salary_type == 'employee':
                    min_wage = self.env['hr.minimum.wage'].search([('employee_id', '=', employee.id), ('date_from', '<=', self.from_date), ('date_to', '>=', self.to_date)], limit=1)
                elif employee and employee.basic_salary_type == 'employee_type':
                    min_wage = self.env['hr.minimum.wage'].search([('employee_type_id', '=', employee.type_id.id), ('date_from', '<=', self.from_date), ('date_to', '>=', self.to_date)], limit=1)
                bpjs_tk_tunj        = 0
                bpjs_tk_pot         = 0
                bpjs_tk_setor       = 0
                bpjs_pensiun_tunj   = 0
                bpjs_pensiun_pot    = 0
                bpjs_pensiun_setor  = 0
                bpjs_kesehatan_tunj = 0
                bpjs_kesehatan_pot  = 0
                bpjs_kesehatan_setor= 0
                if employee.ketenagakerjaan and employee.bpjs_tk_date_start<=self.to_date:
                    if employee.type_id.id == pkwt_employee.id:
                        bpjs_tk_tunj            = min_wage.umr_month * bpjs_tk_kontrak.tunjangan/100
                        bpjs_tk_pot             = min_wage.umr_month * bpjs_tk_kontrak.potongan/100
                    else:
                        bpjs_tk_tunj            = min_wage.umr_month * bpjs_tk.tunjangan/100
                        bpjs_tk_pot             = min_wage.umr_month * bpjs_tk.potongan/100
                    bpjs_tk_setor           = bpjs_tk_pot

                if employee.pensiun:
                    bpjs_pensiun_tunj       = min_wage.umr_month * bpjs_pensiun.tunjangan/100
                    bpjs_pensiun_pot        = min_wage.umr_month * bpjs_pensiun.potongan/100
                    bpjs_pensiun_setor      = bpjs_pensiun_pot
                if employee.kesehatan and employee.bpjs_kes_date_start<=self.to_date:
                    bpjs_kesehatan_tunj     = min_wage.umr_month * bpjs_kesehatan.tunjangan/100
                    bpjs_kesehatan_pot      = min_wage.umr_month * bpjs_kesehatan.potongan/100
                    bpjs_kesehatan_setor    = bpjs_kesehatan_pot
                new_lines = {
                    'employee_id'           : employee.id or False,
                    'employee_type_id'      : employee.type_id and employee.type_id.id or False,
                    'no_induk'              : employee.no_induk or False,
                    'bpjs_tk_id'            : employee.bpjs_ketenagakerjaan or False,
                    'bpjs_tk_tunj'          : bpjs_tk_tunj or False,
                    'bpjs_tk_pot'           : bpjs_tk_pot or False,
                    'bpjs_tk_setor'         : bpjs_tk_setor or False,
                    'bpjs_pensiun_id'       : employee.bpjs_ketenagakerjaan or False,
                    'bpjs_pensiun_tunj'     : bpjs_pensiun_tunj or False,
                    'bpjs_pensiun_pot'      : bpjs_pensiun_pot or False,
                    'bpjs_pensiun_setor'    : bpjs_pensiun_setor or False,
                    'bpjs_kesehatan_id'     : employee.bpjs_kesehatan or False,
                    'bpjs_kesehatan_tunj'   : bpjs_kesehatan_tunj or False,
                    'bpjs_kesehatan_pot'    : bpjs_kesehatan_pot or False,
                    'bpjs_kesehatan_setor'  : bpjs_kesehatan_setor or False,
                    'salary_id'             : self.id,
                }
                if new_lines:
                    self.env['plantation.salary.bpjs'].create(new_lines)
        # End BPJS *******************************************************************************

        # Start Natura*******************************************************************************
        if self.natura_ids:
            self._cr.execute("DELETE FROM plantation_salary_natura WHERE salary_id=%s", (self.id,))
        # Loop Data Lhm
        self.env.cr.execute("""
            SELECT he.id AS employee_id
            , het.id AS type_id
            , he.no_induk AS no_induk
            , hp.id AS ptkp_id
            , hn.nature AS natura_rp
            FROM lhm_transaction_line lhm2
            LEFT JOIN lhm_transaction lhm ON lhm.id=lhm2.lhm_id
            LEFT JOIN hr_attendance_type hat ON hat.id=lhm2.attendance_id
            LEFT JOIN hr_employee he ON lhm2.employee_id=he.id
            LEFT JOIN resource_resource rr ON he.resource_id=rr.id
            LEFT JOIN hr_employee_type het ON het.id=he.type_id
            LEFT JOIN hr_ptkp hp ON hp.id=he.ptkp_id
            LEFT JOIN hr_nature hn ON he.ptkp_id=hn.ptkp_id
            WHERE rr.company_id = %s 
            and lhm.lhm_input_type='reguler'
            AND (het.monthly_employee = TRUE or het.sku_employee = TRUE or het.contract_employee = TRUE)
            AND lhm.date BETWEEN %s::DATE AND %s::DATE 
            GROUP BY he.no_induk, he.id, het.id, hp.id, hn.nature
            having SUM(lhm2.work_day) > 0
            order by he.no_induk
            """, (self.company_id.id, self.from_date, self.to_date))
        for natura in self.env.cr.fetchall():
            new_lines = {
                'employee_id'     : natura[0] or False,
                'employee_type_id': natura[1] or False,
                'no_induk'        : natura[2] or False,
                'ptkp_id'         : natura[3] or False,
                'natura_rp'       : natura[4],
                'salary_id'       : self.id,
            }
            if new_lines:
                self.env['plantation.salary.natura'].create(new_lines)
        # End Natura
        # Start Potongan Lain*******************************************************************************
        if self.allowance_ids:
            self._cr.execute("DELETE FROM plantation_salary_allowance WHERE salary_id=%s", (self.id,))
        # Loop Data Potongan
        # Original
        # self.env.cr.execute("""
        #         SELECT paol.employee_id
        #         , CASE WHEN pat.potongan = TRUE THEN sum(paol.amount) ELSE 0 END AS potongan
        #         , CASE WHEN pat.tunjangan = TRUE THEN sum(paol.amount) ELSE 0 END AS tunjangan
        #         , CASE WHEN pat.koperasi = TRUE THEN sum(paol.amount) ELSE 0 END AS koperasi
        #         , CASE WHEN pat.rapel = TRUE THEN sum(paol.amount) ELSE 0 END AS rapel
        #         FROM plantation_allowance_other_line paol
        #         INNER JOIN plantation_allowance_other pao ON pao.id = paol.other_id
        #         INNER JOIN plantation_allowance_type pat ON pat.id = pao.allowance_type_id
        #         WHERE pao.company_id = %s AND pao.date BETWEEN %s AND %s
        #         GROUP BY paol.employee_id, pat.potongan, pat.tunjangan, pat.koperasi, pat.rapel
        #         ORDER BY paol.employee_id ASC
        #     """, (self.company_id.id, self.from_date, self.to_date))
        self.env.cr.execute("""
                SELECT paol.employee_id, pat.id
                , CASE WHEN pat.potongan = TRUE THEN sum(paol.amount) ELSE 0 END AS potongan
                , CASE WHEN pat.tunjangan = TRUE THEN sum(paol.amount) ELSE 0 END AS tunjangan
                , CASE WHEN pat.koperasi = TRUE THEN sum(paol.amount) ELSE 0 END AS koperasi
                , CASE WHEN pat.rapel = TRUE THEN sum(paol.amount) ELSE 0 END AS rapel
                FROM plantation_allowance_other_line paol
                INNER JOIN plantation_allowance_other pao ON pao.id = paol.other_id
                INNER JOIN plantation_allowance_type pat ON pat.id = pao.allowance_type_id
                WHERE pao.company_id = %s AND pao.date BETWEEN %s AND %s
                GROUP BY paol.employee_id, pat.id, pat.potongan, pat.tunjangan, pat.koperasi, pat.rapel
                ORDER BY paol.employee_id, pat.id ASC
            """, (self.company_id.id, self.from_date, self.to_date))
        karyawan_id     = False
        new_lines_id    = False
        new_lines       = {}
        for allow_other in self.env.cr.fetchall():
            # if karyawan_id == allow_other[0] and allow_other[1] > 0 and new_lines_id:
            #     new_lines_id.write({'potongan_lain' : allow_other[1]})
            # elif karyawan_id == allow_other[0] and allow_other[2] > 0 and new_lines_id:
            #     new_lines_id.write({'tunjangan_lain' : allow_other[2]})
            # elif karyawan_id == allow_other[0] and allow_other[3] > 0 and new_lines_id:
            #     new_lines_id.write({'koperasi' : allow_other[3]})
            # elif karyawan_id == allow_other[0] and allow_other[4] > 0 and new_lines_id:
            #     new_lines_id.write({'rapel' : allow_other[4]})
            # if karyawan_id != allow_other[0]:
                # karyawan_id                 = allow_other[0]
                # new_lines_id                = False
                new_lines['salary_id']      = self.id
                new_lines['employee_id']    = allow_other[0]
                new_lines['allowance_type_id'] = allow_other[1]
                new_lines['potongan_lain']  = allow_other[2] if allow_other[2] > 0 else 0
                new_lines['tunjangan_lain'] = allow_other[3] if allow_other[3] > 0 else 0
                new_lines['koperasi']       = allow_other[4] if allow_other[4] > 0 else 0
                new_lines['rapel']          = allow_other[5] if allow_other[5] > 0 else 0
                # if new_lines:
                new_lines_id = self.env['plantation.salary.allowance'].create(new_lines)
        # End Potongan Lain ##########################################################
        # Start Daftar Upah*******************************************************************************
        if self.upah_ids:
            for line in self.upah_ids:
                line.unlink()

        # Loop Data employee
        self.env.cr.execute("""
            SELECT he.kemandoran_id
            , he.id
            , he.ptkp_id
            , he.type_id
            , he.division_id
            , SUM(ltl.work_day) AS HKE
            , SUM(ltl.non_work_day) AS HKNE
            , SUM(CASE WHEN hat.type_hk = 'hke' and het.monthly_employee = true and ltl.work_day > 0 THEN (ltl.min_wage_value * ltl.work_day)
                WHEN hat.type_hk = 'hke' and het.sku_employee = true and ltl.work_day > 0 THEN (ltl.min_wage_value * ltl.work_day)
                WHEN hat.type_hk = 'hke' and het.bhl_employee = true and ltl.work_day > 0 THEN (ltl.min_wage_value * ltl.work_day)
                WHEN hat.type_hk = 'hke' and het.contract_employee = true and ltl.work_day > 0 THEN (ltl.min_wage_value * ltl.work_day)
                ELSE 0
                END) AS HKE_BYR
            , SUM(CASE WHEN hat.type_hk = 'hkne' and het.monthly_employee = true and ltl.non_work_day > 0 THEN (ltl.min_wage_value * ltl.non_work_day)
                WHEN hat.type_hk = 'hkne' and het.sku_employee = true and ltl.non_work_day > 0 THEN (ltl.min_wage_value * ltl.non_work_day)
                WHEN hat.type_hk = 'hkne' and het.contract_employee = true and ltl.non_work_day > 0 THEN (ltl.min_wage_value * ltl.non_work_day)
                ELSE 0
                END) AS HKNE_BYR
            , hmw.umr_month
            , SUM(ltl.premi+ltl.overtime_value-ltl.penalty) AS premi_lebur            
            , (CASE WHEN (sum(COALESCE(ltl.work_day,0)+COALESCE(ltl.non_work_day,0))) >= 25 THEN hn.nature 
                ELSE (hn.nature - ((25 - sum(COALESCE(ltl.work_day,0)+COALESCE(ltl.non_work_day,0))) * hn.potongan_rp)) 
              END) as natura 
            , (select bpjs_pensiun_tunj FROM plantation_salary_bpjs WHERE employee_id = he.id AND salary_id = %s)
            , (select bpjs_kesehatan_tunj FROM plantation_salary_bpjs WHERE employee_id = he.id AND salary_id = %s)
            , (select bpjs_tk_tunj FROM plantation_salary_bpjs WHERE employee_id = he.id AND salary_id = %s)
            , (select bpjs_pensiun_pot FROM plantation_salary_bpjs WHERE employee_id = he.id AND salary_id = %s)
            , (select bpjs_kesehatan_pot FROM plantation_salary_bpjs WHERE employee_id = he.id AND salary_id = %s)
            , (select bpjs_tk_pot FROM plantation_salary_bpjs WHERE employee_id = he.id AND salary_id = %s)
            , (select sum(potongan_lain) FROM plantation_salary_allowance WHERE employee_id = he.id AND salary_id = %s)
            FROM lhm_transaction lt
            INNER JOIN hr_foreman hf ON lt.kemandoran_id=hf.id
            INNER JOIN lhm_transaction_line ltl ON ltl.lhm_id=lt.id
            INNER JOIN hr_employee he ON he.id = ltl.employee_id
            INNER JOIN resource_resource rr ON rr.id = he.resource_id
            INNER JOIN hr_employee_type het ON het.id = he.type_id
            INNER JOIN hr_nature hn ON hn.ptkp_id = he.ptkp_id
            LEFT JOIN hr_division hd ON he.division_id=hd.id
            INNER JOIN hr_attendance_type hat ON ltl.attendance_id=hat.id
            INNER JOIN hr_ptkp hp ON he.ptkp_id=hp.id
            INNER JOIN hr_minimum_wage hmw ON ltl.min_wage_id=hmw.id
            LEFT JOIN lhm_location_type llt ON ltl.location_type_id=llt.id
            LEFT JOIN lhm_location ll ON ltl.location_id=ll.id
            LEFT JOIN lhm_activity la ON ltl.activity_id=la.id 
            INNER JOIN res_users ru ON ru.id= lt.create_uid 
            INNER JOIN res_partner rp ON rp.id=ru.partner_id
            WHERE lt.date::DATE BETWEEN %s::DATE AND %s::DATE
            and lt.lhm_input_type='reguler'
            AND lt.state in ('done','in_progress', 'close')
            AND ltl.attendance_id is not null
            GROUP BY he.kemandoran_id, he.id, he.ptkp_id, he.type_id, he.division_id, hmw.umr_month, hn.nature, hn.potongan_rp
            ORDER BY he.kemandoran_id, he.id
        """, (self.id, self.id, self.id, self.id, self.id, self.id, self.id, self.from_date, self.to_date))

        for upah in self.env.cr.fetchall():
            employee_stat       = self.env['hr.employee'].search([('id', '=', upah[1])], limit=1)
            hke                 = upah[5] or float(0.0)
            hkne                = upah[6] or float(0.0)
            total_hk            = hke + hkne
            hke_rp              = upah[7] or float(0.0)
            hkne_rp             = upah[8] or float(0.0)
            total_hk_rp         = hke_rp + hkne_rp
            basic_salary        = upah[9] or float(0.0)
            premi_lembur        = upah[10] or float(0.0)
            if employee_stat.type_id and (employee_stat.type_id.sku_employee or employee_stat.type_id.monthly_employee or employee_stat.type_id.contract_employee):
                natura          = upah[11] or float(0.0)
            else:
                natura          = float(0.0)
            tunj_bpjs_pensiun   = upah[12] or float(0.0)
            tunj_bpjs_kesehatan = upah[13] or float(0.0)
            tunj_bpjs_tk        = upah[14] or float(0.0)

            tunj_lebih_hari     = 0
            pot_kurang_hari     = 0
            if total_hk_rp > basic_salary:
                tunj_lebih_hari = total_hk_rp - basic_salary
            if total_hk_rp < basic_salary:
                pot_kurang_hari = basic_salary - total_hk_rp
            gaji_bruto          = total_hk_rp + premi_lembur + natura + tunj_bpjs_pensiun + tunj_bpjs_kesehatan + tunj_bpjs_tk
            pot_bpjs_pensiun    = upah[15] or float(0.0)
            pot_bpjs_kesehatan  = upah[16] or float(0.0)
            pot_bpjs_tk         = upah[17] or float(0.0)
            pot_lain            = upah[18] or float(0.0)
            total_potongan      = pot_bpjs_pensiun + pot_bpjs_kesehatan + pot_bpjs_tk + pot_lain
            upah_diterima       = gaji_bruto - total_potongan
            new_lines = {
                'kemandoran_id'     : upah[0],
                'employee_id'       : upah[1],
                'ptkp_id'           : upah[2],
                'employee_type_id'  : upah[3],
                'division_id'       : upah[4],
                'hke'               : hke,
                'hkne'              : hkne,
                'total_hk'          : total_hk,
                'hke_rp'            : hke_rp,
                'hkne_rp'           : hkne_rp,
                'total_hk_rp'       : total_hk_rp,
                'basic_salary'      : basic_salary,
                'tunjangan_lain'    : 0,
                'premi_lembur'      : premi_lembur,
                'natura'            : natura,
                'rapel'             : 0,
                'tunj_bpjs_pensiun' : tunj_bpjs_pensiun,
                'tunj_bpjs_kesehatan': tunj_bpjs_kesehatan,
                'tunj_bpjs_tk'      : tunj_bpjs_tk,
                'tunj_lebih_hari'   : tunj_lebih_hari,
                'gaji_bruto'        : gaji_bruto,
                'pot_bpjs_pensiun'  : pot_bpjs_pensiun,
                'pot_bpjs_kesehatan': pot_bpjs_kesehatan,
                'pot_bpjs_tk'       : pot_bpjs_tk,
                'pot_lain'          : pot_lain,
                'pot_kurang_hari'  : pot_kurang_hari,
                'pph_21'            : 0,
                'total_potongan'    : total_potongan,
                'upah_diterima'     : upah_diterima,
                'salary_id'         : self.id,
            }
            if new_lines:
                self.env['plantation.salary.daftar.upah'].create(new_lines)
        # End Daftar Upah ##########################################################
        return False

    @api.multi
    def generate_data_upah_target(self):
        line_nab_lhm_lines = self.env['lhm.transaction.line.nab.line'].search([
            ('lhm_line_id.lhm_input_type','=','work_target'), 
            ('date','>=',self.from_date), ('date','<=',self.to_date), 
            ('lhm_line_id.lhm_id.state','in',['done','in_progress', 'close']), 
            ('lhm_line_id.attendance_id','!=',False)])
        lhm_lines = self.env['lhm.transaction.line'].search([('lhm_id.lhm_input_type','=','work_target'), 
            ('lhm_id.date','>=',self.from_date), ('lhm_id.date','<=',self.to_date), 
            ('lhm_id.state','in',['done','in_progress', 'close']), ('attendance_id','!=',False)])
        for link in line_nab_lhm_lines:
            if link.lhm_line_id.id in lhm_lines.ids:
                continue
            lhm_lines |= link.lhm_line_id
        # Detail LHM dibulan yg sama, untuk cek BPJS
        lhm_lines_other = self.env['lhm.transaction.line'].search([('lhm_id.account_period_id','=',self.period_id.id),
            ('lhm_id.date','<',self.from_date), ('attendance_id','!=',False), 
            ('lhm_id.state','in',['done','in_progress', 'close']),
            ('id','not in',(lhm_lines and lhm_lines.ids or [0,0]))])
        # VALIDASI PANEN
        # lhm_not_valid = self.env['lhm.transaction']
        # for line in lhm_lines:
        #     if line.dummy_skip:
        #         # ini biasanya adalah data import periode sebelumnya yg selalu dianggap valid
        #         continue
        #     if line.activity_id.is_panen and not line.lhm_nab_ids:
        #         lhm_not_valid |= line.lhm_id
        # if lhm_not_valid:
        #     raise ValidationError(_("Tidak dapat mengolah Daftar Upah. \n"
        #         "Ditemukan LHM Target yang belum terkirim di Nota Angkut Buah.\n"
        #         "%s") % "\n".join(lhm_not_valid.mapped('name')))
        # # Start BPJS*******************************************************************************
        for bpjs in self.bpjs_ids:
            bpjs.unlink()
        data_employee = lhm_lines.mapped('employee_id').filtered(lambda x: x.kesehatan or x.ketenagakerjaan)
        if lhm_lines_other:
            data_employee = data_employee.filtered(lambda x: x.id not in lhm_lines_other.mapped('employee_id').filtered(lambda x: x.kesehatan or x.ketenagakerjaan).ids)
        bpjs_tk = self.env['hr.insurance'].search([('type', '=', 'ketenagakerjaan'), ("date_from", '<=', self.from_date), ("date_to", '>=', self.to_date)], limit=1)
        bpjs_pensiun = self.env['hr.insurance'].search([('type', '=', 'pensiun'), ("date_from", '<=', self.from_date), ("date_to", '>=', self.to_date)], limit=1)
        bpjs_kesehatan = self.env['hr.insurance'].search([('type', '=', 'kesehatan'), ("date_from", '<=', self.from_date), ("date_to", '>=', self.to_date)], limit=1)
        for employee in data_employee:
            xbpjs_tk = self.env['hr.insurance'].search([('employee_type_id','=',employee.type_id.id), ('type', '=', 'ketenagakerjaan'), ("date_from", '<=', self.from_date), ("date_to", '>=', self.to_date)])
            if not xbpjs_tk:
                xbpjs_tk = bpjs_tk
            xbpjs_pensiun = self.env['hr.insurance'].search([('employee_type_id','=',employee.type_id.id), ('type', '=', 'pensiun'), ("date_from", '<=', self.from_date), ("date_to", '>=', self.to_date)])
            if not xbpjs_pensiun:
                xbpjs_pensiun = bpjs_pensiun
            xbpjs_kesehatan = self.env['hr.insurance'].search([('employee_type_id','=',employee.type_id.id), ('type', '=', 'kesehatan'), ("date_from", '<=', self.from_date), ("date_to", '>=', self.to_date)])
            if not xbpjs_kesehatan:
                xbpjs_kesehatan = bpjs_kesehatan
            min_wage = False
            if employee and employee.basic_salary_type == 'employee':
                min_wage = self.env['hr.minimum.wage'].search([('employee_id', '=', employee.id), ('date_from', '<=', self.from_date), ('date_to', '>=', self.to_date)], limit=1)
            elif employee and employee.basic_salary_type == 'employee_type':
                min_wage = self.env['hr.minimum.wage'].search([('employee_type_id', '=', employee.type_id.id), ('date_from', '<=', self.from_date), ('date_to', '>=', self.to_date)], limit=1)
            bpjs_tk_tunj        = 0.0
            bpjs_tk_pot         = 0.0
            bpjs_tk_setor       = 0.0
            bpjs_kesehatan_tunj = 0.0
            bpjs_kesehatan_pot  = 0.0
            bpjs_kesehatan_setor= 0.0
            if employee.ketenagakerjaan and employee.bpjs_tk_date_start<=self.to_date:
                bpjs_tk_tunj            = min_wage.umr_month * xbpjs_tk.tunjangan/100
                bpjs_tk_pot             = min_wage.umr_month * xbpjs_tk.potongan/100
                bpjs_tk_setor           = bpjs_tk_tunj+bpjs_tk_pot
            if employee.kesehatan and employee.bpjs_kes_date_start<=self.to_date:
                bpjs_kesehatan_tunj     = min_wage.umr_month * xbpjs_kesehatan.tunjangan/100
                bpjs_kesehatan_pot      = min_wage.umr_month * xbpjs_kesehatan.potongan/100
                bpjs_kesehatan_setor    = bpjs_kesehatan_tunj+bpjs_kesehatan_pot
            new_lines = {
                'employee_id'           : employee.id or False,
                'employee_type_id'      : employee.type_id and employee.type_id.id or False,
                'no_induk'              : employee.no_induk or False,
                'bpjs_tk_id'            : employee.bpjs_ketenagakerjaan or False,
                'bpjs_tk_tunj'          : bpjs_tk_tunj or False,
                'bpjs_tk_pot'           : bpjs_tk_pot or False,
                'bpjs_tk_setor'         : bpjs_tk_setor or False,
                'bpjs_pensiun_id'       : employee.bpjs_ketenagakerjaan or False,
                'bpjs_kesehatan_id'     : employee.bpjs_kesehatan or False,
                'bpjs_kesehatan_tunj'   : bpjs_kesehatan_tunj or False,
                'bpjs_kesehatan_pot'    : bpjs_kesehatan_pot or False,
                'bpjs_kesehatan_setor'  : bpjs_kesehatan_setor or False,
                'salary_id'             : self.id,
            }
            if new_lines:
                self.env['plantation.salary.bpjs'].create(new_lines)
        # # End BPJS *******************************************************************************

        # Start Natura*******************************************************************************
        for natura in self.natura_ids:
            natura.unlink()
        # Loop Data Lhm
        self.env.cr.execute("""
            SELECT he.id AS employee_id, het.id AS type_id, he.no_induk AS no_induk, hp.id AS ptkp_id
                , hn.nature AS natura_rp
                FROM lhm_transaction_line lhm_line
                    LEFT JOIN lhm_transaction lhm ON lhm.id=lhm_line.lhm_id
                    LEFT JOIN hr_attendance_type hat ON hat.id=lhm_line.attendance_id
                    LEFT JOIN hr_employee he ON lhm_line.employee_id=he.id
                    LEFT JOIN resource_resource rr ON he.resource_id=rr.id
                    LEFT JOIN hr_employee_type het ON het.id=he.type_id
                    LEFT JOIN hr_ptkp hp ON hp.id=he.ptkp_id
                    LEFT JOIN hr_nature hn ON he.ptkp_id=hn.ptkp_id
                WHERE rr.company_id = %s
                    AND lhm.lhm_input_type = 'work_target' 
                    -- AND het.contract_employee = TRUE
                    AND lhm.date BETWEEN %s::DATE AND %s::DATE 
                GROUP BY he.no_induk, he.id, het.id, hp.id, hn.nature
                having SUM(lhm_line.work_day) > 0
                ORDER BY he.no_induk
            """, (self.company_id.id, self.from_date, self.to_date))
        for natura in self.env.cr.dictfetchall():
            new_lines = {
                'employee_id'     : natura.get('employee_id',False),
                'employee_type_id': natura.get('type_id',False),
                'no_induk'        : natura.get('no_induk',''),
                'ptkp_id'         : natura.get('ptkp_id',False),
                'natura_rp'       : natura.get('natura_rp', 0.0),
                'salary_id'       : self.id,
            }
            self.env['plantation.salary.natura'].create(new_lines)
        # End Natura
        # Start Potongan Lain*******************************************************************************
        for allowance in self.allowance_ids:
            allowance.unlink()
        # Loop Data Potongan
        allowance_lines = self.env['plantation.allowance.other.line'].search([('other_id.company_id','=',self.company_id.id),
            ('other_id.date','>=',self.from_date),('other_id.date','<=',self.to_date), 
            ('employee_id','in',lhm_lines.mapped('employee_id').ids)])
        
        for emp in allowance_lines.mapped('employee_id'):
            for allow_type in allowance_lines.filtered(lambda x: x.employee_id.id==emp.id).mapped('allowance_type_id'):
                amount = sum(allowance_lines.filtered(lambda x: x.employee_id.id==emp.id and x.allowance_type_id.id==allow_type.id).mapped('amount'))
                if not amount:
                    continue
                new_lines = {
                    'employee_id'    : emp.id,
                    'employee_type_id': allow_type.id,
                    'salary_id'      : self.id,
                    'potongan_lain': 0.0,
                    'tunjangan_lain': 0.0,
                    'koperasi': 0.0,
                    'rapel': 0.0,
                }
                if allow_type.potongan:
                    new_lines['potongan_lain'] += amount
                if allow_type.tunjangan:
                    new_lines['tunjangan_lain'] += amount
                if allow_type.koperasi:
                    new_lines['koperasi'] += amount
                if allow_type.rapel:
                    new_lines['rapel'] += amount
                self.env['plantation.salary.allowance'].create(new_lines)
        # End Potongan Lain ##########################################################
        # Start Daftar Upah*******************************************************************************
        for line in self.upah_ids:
            line.unlink()
        for employee in sorted(lhm_lines.mapped('employee_id'), key=lambda x:x.id):
            values = {
                'kemandoran_id'     : employee.kemandoran_id and employee.kemandoran_id.id or False,
                'employee_id'       : employee.id,
                'ptkp_id'           : employee.ptkp_id and employee.ptkp_id.id or False,
                'employee_type_id'  : employee.type_id and employee.type_id.id or False,
                'division_id'       : employee.division_id and employee.division_id.id or False,
                'hke' : 0.0, 'hkne' : 0.0, 'total_hk' : 0.0,
                'hke_rp' : 0.0, 'hkne_rp' : 0.0, 'total_hk_rp' : 0.0,
                'basic_salary' : 0.0, 'tunjangan_lain' : 0.0, 'premi_lembur' : 0.0,
                'natura' : 0.0, 'rapel' : 0.0, 'tunj_bpjs_pensiun' : 0.0,
                'tunj_bpjs_kesehatan': 0.0, 'tunj_bpjs_tk' : 0.0,
                'tunj_lebih_hari' : 0.0, 'gaji_bruto' : 0.0, 'pot_bpjs_pensiun' : 0.0,
                'pot_bpjs_kesehatan': 0.0, 'pot_bpjs_tk' : 0.0, 'pot_lain' : 0.0,
                'pot_kurang_hari' : 0.0, 'pph_21' : 0.0, 'total_potongan' : 0.0,
                'upah_diterima' : 0.0, 'salary_id' : self.id,
                'prev_pending_hke': 0.0,
            }
            if employee.ptkp_id:
                natura_ids = self.env['hr.nature'].search([('ptkp_id','=',employee.ptkp_id.id)], limit=1)
                if natura_ids:
                    # values['natura'] = natura_ids[-1].nature
                    values['natura'] = 0.0
                    potongan_natura = natura_ids[-1].potongan_rp
            else:
                values['natura'] = 0.0
                potongan_natura = 0.0
            for line in lhm_lines.filtered(lambda x:x.employee_id.id==employee.id):
                values['basic_salary'] = line.min_wage_id.umr_month
                # values['natura'] -= (not line.attendance_id.type and not line.attendance_id.type_hk) and potongan_natura or 0.0
                if line.activity_id.is_panen and line.lhm_nab_ids:
                    # sebelum bugs
                    # prev_salary_period = line.lhm_nab_ids.filtered(lambda x: x.date<self.from_date)
                    # jika tidak memiliki Link di periode Penggajian sebelumnya,
                    # maka HK pasti dihitung 1
                    # if not prev_salary_period:
                    #     values['hke'] += line.work_day
                    #     values['hkne'] += line.non_work_day
                    xpremi = 0.0
                    xpenalty = 0.0
                    xtotal_amount = 0.0
                    for link in line.lhm_nab_ids.filtered(lambda x: x.date>=self.from_date and x.date<=self.to_date):
                        # sebelum bugs
                        # if prev_salary_period:
                        if line.lhm_id.date<self.from_date:
                            xpremi += link.amount
                        else:
                            xtotal_amount += link.amount

                        xpenalty += link.penalty_nab
                    # sebelum bugs
                    # jika tidak memiliki Link di periode Penggajian sebelumnya,
                    # maka HK 1 dikali dengan Gaji kemudian Premi dan Penalty disesuaikan dengan Hasil Kerja
                    # terhadap gaji
                    # if not prev_salary_period:
                    #     xpremi = xtotal_amount > line.min_wage_value and (xtotal_amount-line.min_wage_value) or 0.0
                    #     xpenalty = xtotal_amount < line.min_wage_value and (line.min_wage_value-xtotal_amount) or 0.0
                    # jika panen tidak terjadi di periode sebelumnya,
                    # maka HK pasti dihitung 1
                    if not (line.lhm_id.date<self.from_date) and line.lhm_nab_ids.filtered(lambda x: x.date>=self.from_date and x.date<=self.to_date):
                        values['hke'] += line.work_day
                        values['hkne'] += line.non_work_day
                        values['total_hk'] += (line.work_day+line.non_work_day)
                        values['hke_rp'] += (line.work_day*line.min_wage_value)
                        values['hkne_rp'] += (line.non_work_day*line.min_wage_value)
                        values['total_hk_rp'] += ((line.work_day*line.min_wage_value) + (line.non_work_day*line.min_wage_value))
                        xpremi = xtotal_amount > (line.work_day*line.min_wage_value) and (xtotal_amount-(line.work_day*line.min_wage_value)) or 0.0
                        if xpenalty:
                            xpenalty += xtotal_amount < (line.work_day*line.min_wage_value) and ((line.work_day*line.min_wage_value)-xtotal_amount) or 0.0
                        else:
                            xpenalty = xtotal_amount < (line.work_day*line.min_wage_value) and ((line.work_day*line.min_wage_value)-xtotal_amount) or 0.0
                    values['premi_lembur'] += xpremi - xpenalty
                else:
                    values['hke'] += line.work_day
                    values['hkne'] += line.non_work_day
                    values['total_hk'] += (line.work_day+line.non_work_day)
                    values['hke_rp'] += (line.work_day*line.min_wage_value)
                    values['hkne_rp'] += (line.non_work_day*line.min_wage_value)
                    values['total_hk_rp'] += ((line.work_day*line.min_wage_value) + (line.non_work_day*line.min_wage_value))
                    values['premi_lembur'] += line.premi + line.premi_other + line.overtime_value - \
                                line.penalty

                if not (line.lhm_id.date<self.from_date) and line.penalty_other:
                    values['premi_lembur'] -= line.penalty_other
            # if values['total_hk_rp'] > values['basic_salary']:
                # values['tunj_lebih_hari'] = values['total_hk_rp'] - values['basic_salary']
            # if values['total_hk_rp'] < values['basic_salary']:
                # values['pot_kurang_hari'] = values['basic_salary'] - values['total_hk_rp']
            bpjs = self.bpjs_ids.filtered(lambda x:x.employee_id.id==employee.id)
            if bpjs:
                values['tunj_bpjs_pensiun'] = bpjs[-1].bpjs_pensiun_tunj
                values['tunj_bpjs_kesehatan'] = bpjs[-1].bpjs_kesehatan_tunj
                values['tunj_bpjs_tk'] = bpjs[-1].bpjs_tk_tunj
                values['pot_bpjs_pensiun'] = bpjs[-1].bpjs_pensiun_pot
                values['pot_bpjs_kesehatan'] = bpjs[-1].bpjs_kesehatan_pot
                values['pot_bpjs_tk'] = bpjs[-1].bpjs_tk_pot
            values['gaji_bruto'] = values['total_hk_rp'] + values['premi_lembur'] + values['natura'] + values['tunj_bpjs_pensiun'] + values['tunj_bpjs_kesehatan'] + values['tunj_bpjs_tk']
            values['pot_lain'] = sum(self.allowance_ids.filtered(lambda x: x.employee_id.id==employee.id).mapped('potongan_lain'))
            values['total_potongan'] = values['pot_bpjs_pensiun'] + values['pot_bpjs_kesehatan'] + values['pot_bpjs_tk'] + values['pot_lain']
            values['upah_diterima'] = values['gaji_bruto'] - values['total_potongan']
            
            self.env['plantation.salary.daftar.upah'].create(values)
        # End Daftar Upah ##########################################################
        return False

################################################### End Of Plantation_Salary ####################################################