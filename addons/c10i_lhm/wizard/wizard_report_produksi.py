from odoo import models, fields, tools, api, _
from datetime import datetime
import time
import datetime

class WizardReportProduksi(models.TransientModel):
    _name           = "wizard.report.produksi"
    _description    = "Laporan Produksi"

    date_start     = fields.Date("Periode Dari Tgl", required=True)
    date_end       = fields.Date("Sampai Tgl", required=True)
    afdeling_ids   = fields.Many2many(comodel_name="res.afdeling", string="Afdeling", ondelete="restrict")
    company_id     = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    panen_ids      = fields.One2many(comodel_name='wizard.report.produksi.panen', inverse_name='produksi_id', string='Laporan Panen', copy=False)
    restan_ids     = fields.One2many(comodel_name='wizard.report.produksi.restan', inverse_name='produksi_id', string='Laporan Restan', copy=False)
    nab_perblock_ids= fields.One2many(comodel_name='wizard.report.produksi.nab.perblock', inverse_name='produksi_id', string='Laporan NAB Per Blok', copy=False)
    nab_detail_ids = fields.One2many(comodel_name='wizard.report.produksi.nab.detail', inverse_name='produksi_id', string='Laporan NAB Detail', copy=False)
    nab_rekap_ids  = fields.One2many(comodel_name='wizard.report.produksi.nab.rekap', inverse_name='produksi_id', string='Laporan NAB Rekap', copy=False)
    rotasi_ids     = fields.One2many(comodel_name='wizard.report.produksi.rotasi.panen', inverse_name='produksi_id', string='Laporan Rotasi Panen', copy=False)

    @api.multi
    def create_report(self):
        # Laporan Panen
        if self.panen_ids:
            for data in self.panen_ids:
                data.unlink()
        
        str_sql = """
            select
                lt.kemandoran_id
                ,ltpl.date
                ,ltpl.location_id
                ,ltpl.uom_id
                ,ltpl.nilai
                ,ltpl.uom2_id
                ,ltpl.nilai2
                ,ltpl.realization
                ,ltpl.work_day
            FROM lhm_transaction lt
            LEFT JOIN lhm_transaction_process_line ltpl ON lt.id=ltpl.lhm_id
            LEFT JOIN hr_foreman hf on hf.id=lt.kemandoran_id
            LEFT JOIN lhm_activity la on la.id=ltpl.activity_id
            where la.is_panen is True and ltpl.date between %s and %s and state in('done','close')
        """

        str_sql2 = ''
        if self.afdeling_ids:
            str_afdeling_id = ''
            for data in self.afdeling_ids:
                str_afdeling_id += str(data.id)+","
            str_sql2 = ' and hf.afdeling_id in ('+str_afdeling_id[:-1]+')'

        str_sql = str_sql + str_sql2 + ' ORDER BY ltpl.date, lt.kemandoran_id '
        self.env.cr.execute(str_sql, (self.date_start, self.date_end))

        for report in self.env.cr.fetchall():
            new_lines = {
                'hr_foreman_id' : report[0],
                'date'          : report[1],
                'location_id'   : report[2],
                'uom_id'        : report[3],
                'nilai'         : report[4],
                'uom_id2'       : report[5],
                'nilai2'        : report[6],
                'total'         : report[7],
                'hk'            : report[8],
                'produksi_id': self.id,
            }
            if new_lines:
                self.env['wizard.report.produksi.panen'].create(new_lines)

        #Laporan NAB Detail
        if self.nab_detail_ids:
            for data in self.nab_detail_ids:
                data.unlink()

        str_sql = """
            SELECT
            date_nab,
            no_nab,
            ln.afdeling_id,
            lnl.block_id,
            lnl.qty_nab,
            lnl.tgl_panen,
            ((lnl.qty_nab*lb.value)/(sum(lnl.qty_nab*lb.value) over (partition by ln.id))*ln.timbang_tara_kbn) as kbn_kg,
            ((lnl.qty_nab*lb.value)/(sum(lnl.qty_nab*lb.value) over (partition by ln.id))*timbang_tara_kbn)/lnl.qty_nab as kbn_bjr,
            date_pks,
            ((lnl.qty_nab*lb.value)/(sum(lnl.qty_nab*lb.value) over (partition by ln.id))*timbang_tara_pks) as pks_kg,
            ((lnl.qty_nab*lb.value)/(sum(lnl.qty_nab*lb.value) over (partition by ln.id))*grading) as pks_grading,
            ((lnl.qty_nab*lb.value)/(sum(lnl.qty_nab*lb.value) over (partition by ln.id))*netto) as netto,
            ((lnl.qty_nab*lb.value)/(sum(lnl.qty_nab*lb.value) over (partition by ln.id))*netto /lnl.qty_nab) as pks_bjr,
            ln.id as nab_id,
            lb.id as bjr_id
            from lhm_nab ln
            LEFT JOIN lhm_nab_line lnl ON lnl.lhm_nab_id=ln."id"
            LEFT JOIN lhm_bjr lb ON lb.id=(select id from lhm_bjr where date <= lnl.tgl_panen and block_id = lnl.block_id ORDER BY date desc limit 1)
            where date_pks between %s and %s and state in('confirmed','done') and lnl.block_id is not null
        """
        str_sql2 = ''
        if self.afdeling_ids:
            str_afdeling_id = ''
            for data in self.afdeling_ids:
                str_afdeling_id += str(data.id)+","
            str_sql2 = ' and afdeling_id in ('+str_afdeling_id[:-1]+')'

        str_sql = str_sql + str_sql2 + ' order by ln.id,lnl.id '
        self.env.cr.execute(str_sql, (self.date_start, self.date_end))

        for report in self.env.cr.fetchall():
            new_lines = {
                'tgl_nab'       : report[0] ,
                'no_nab'        : report[1],
                'afdeling_id'   : report[2],
                'block_id'      : report[3],
                'kbn_qty_jjg'   : report[4],
                'tgl_panen'     : report[5],
                'kbn_qty_kg'    : report[6],
                'kbn_bjr'       : report[7],
                'pks_tgl'       : report[8],
                'pks_bruto'     : report[9],
                'pks_grading'   : report[10],
                'pks_netto'     : report[11],
                'pks_bjr'       : report[12],
                'nab_id'        : report[13],
                'bjr_id'        : report[14],
                'produksi_id'     : self.id,
            }
            if new_lines:
                self.env['wizard.report.produksi.nab.detail'].create(new_lines)

        # Laporan NAB Rekap
        if self.nab_rekap_ids:
            for data in self.nab_rekap_ids:
                data.unlink()

        str_sql = """
            SELECT
            date_nab as tgl_nab,
            no_nab,
            afdeling_id,
            vehicle_id,
            driver,
            ownership,
            date_nab as tgl_nab2,
            janjang_jml as kbn_qty_jjg,
            timbang_tara_kbn as kbn_qty_kg,
            pks_id,
            date_pks as pks_tgl,
            timbang_tara_pks as pks_bruto,
            grading as pks_grading,
            netto as pks_netto,
            id as nab_id
            from lhm_nab
            where date_pks between %s and %s and state in('confirmed','done')
        """

        str_sql2 = ''
        if self.afdeling_ids:
            str_afdeling_id = ''
            for data in self.afdeling_ids:
                str_afdeling_id += str(data.id) + ","
            str_sql2 = ' and afdeling_id in (' + str_afdeling_id[:-1] + ')'

        str_sql = str_sql + str_sql2 + ' order by date_pks,no_nab '
        self.env.cr.execute(str_sql, (self.date_start, self.date_end))

        for report in self.env.cr.fetchall():
            new_lines = {
                'tgl_nab'       : report[0],
                'no_nab'        : report[1],
                'afdeling_id'   : report[2],
                'vehicle_id'    : report[3],
                'driver'        : report[4],
                'ownership'     : report[5],
                'tgl_nab2'      : report[6],
                'kbn_qty_jjg'   : report[7],
                'kbn_qty_kg'    : report[8],
                'pks_id'        : report[9],
                'pks_tgl'       : report[10],
                'pks_bruto'     : report[11],
                'pks_grading'   : report[12],
                'pks_netto'     : report[13],
                'nab_id'        : report[14],
                'produksi_id'   : self.id,
            }
            if new_lines:
                self.env['wizard.report.produksi.nab.rekap'].create(new_lines)

        # Laporan NAB PerBlock
        if self.nab_perblock_ids:
            for data in self.nab_perblock_ids:
                data.unlink()

        str_sql = """
                select lpb.afdeling_id,
                wrpnd.block_id,
                sum(case when pks_tgl = wrp.date_end then kbn_qty_kg else 0 end) kbn_hi_kg,
                sum(case when pks_tgl between wrp.date_start and wrp.date_end then kbn_qty_kg else 0 end) kbn_shi_kg,
                sum(case when pks_tgl = wrp.date_end then kbn_qty_jjg else 0 end) kbn_hi_jjg,
                sum(case when pks_tgl between wrp.date_start and wrp.date_end then kbn_qty_jjg else 0 end) kbn_shi_jjg,
                sum(case when pks_tgl = wrp.date_end then pks_bruto else 0 end) pks_hi_bruto,
                sum(case when pks_tgl between wrp.date_start and wrp.date_end then pks_bruto else 0 end) pks_shi_bruto,
                sum(case when pks_tgl = wrp.date_end then pks_grading else 0 end) pks_hi_grading,
                sum(case when pks_tgl between wrp.date_start and wrp.date_end then pks_grading else 0 end) pks_shi_grading,
                sum(case when pks_tgl = wrp.date_end then pks_netto else 0 end) pks_hi_netto,
                sum(case when pks_tgl between wrp.date_start and wrp.date_end then pks_netto else 0 end) pks_shi_netto
                from wizard_report_produksi_nab_detail wrpnd
                left join wizard_report_produksi wrp on wrp.id=wrpnd.produksi_id
                left join lhm_plant_block lpb on lpb.id=wrpnd.block_id
                left join res_afdeling ra on ra.id=lpb.afdeling_id
                where produksi_id=%s
                group by lpb.afdeling_id, wrpnd.block_id, ra.code, lpb.code
                order by  ra.code, lpb.code
            """

        self.env.cr.execute(str_sql, (self.id,))

        kbn_hi_bjr = 0
        kbn_shi_bjr = 0
        pks_hi_bjr = 0
        pks_shi_bjr = 0
        for report in self.env.cr.fetchall():
            if report[4]:
                kbn_hi_bjr = report[2]/report[4]
            if report[5]:
                kbn_shi_bjr = report[3]/report[5]
            if report[4]:
                pks_hi_bjr = report[10]/report[4]
            if report[5]:
                pks_shi_bjr = report[11]/report[5]

            new_lines = {
                'afdeling_id'   : report[0],
                'block_id'      : report[1],
                'kbn_hi_kg'     : report[2],
                'kbn_shi_kg'    : report[3],
                'kbn_hi_jjg'    : report[4],
                'kbn_shi_jjg'   : report[5],
                'kbn_hi_bjr'    : kbn_hi_bjr,
                'kbn_shi_bjr'   : kbn_shi_bjr,
                'pks_hi_bruto'  : report[6],
                'pks_shi_bruto' : report[7],
                'pks_hi_grading': report[8],
                'pks_shi_grading':report[9],
                'pks_hi_netto'  : report[10],
                'pks_shi_netto' : report[11],
                'pks_hi_bjr'    : pks_hi_bjr,
                'pks_shi_bjr'   : pks_shi_bjr,
                'produksi_id'   : self.id,
            }
            if new_lines:
                self.env['wizard.report.produksi.nab.perblock'].create(new_lines)

        #Laporan Restan
        if self.restan_ids:
            for data in self.restan_ids:
                data.unlink()

        str_sql = """
            select header.tgl_panen
            ,header.block_id
            ,header.qty_saw
            ,header.qty_panen
            ,header.qty_nab
            ,header.qty_naf
            ,header.qty_restan
            ,case when header.qty_restan = 0 then 0 else header.umur_restan end as umur_restan
            ,detail.tgl_trans
            ,detail.qty_nab2
            ,detail.qty_naf2
            from
            (select tgl_panen,block_id,sum(qty_saw) as qty_saw,sum(qty_panen)qty_panen,sum(qty_nab)qty_nab,sum(qty_naf)qty_naf,
            sum(qty_saw+qty_panen-qty_nab-qty_naf)qty_restan,
            date_part('day',%s::timestamp - tgl_panen::timestamp) umur_restan
            from
            (select tgl_panen,block_id,sum(jjg_qty) as qty_saw,(0)qty_panen,(0)qty_nab,(0)qty_naf
            from vdata_panen_nab_naf vpnn
            where tgl_trans < %s and jjg_qty <>0
            group by tgl_panen,block_id
            having sum(jjg_qty)<>0
            union all
            select tgl_panen,block_id,(0)qty_saw
            ,sum(case when grp='panen' and tgl_trans between %s and %s then jjg_qty else 0 end) as qty_panen
            ,sum(case when grp='nab' and tgl_trans between %s and %s then -jjg_qty else 0 end) as qty_nab
            ,sum(case when grp='naf' and tgl_trans between %s and %s then -jjg_qty else 0 end) as qty_naf
            from vdata_panen_nab_naf vpnn
            where tgl_trans between %s and %s and jjg_qty <>0
            group by tgl_panen,block_id
            having sum(jjg_qty)<>0) dat_saw_trans
            group by tgl_panen,block_id) header
            left join
            (select tgl_panen,block_id,tgl_trans
            ,sum(case when grp='nab' and tgl_trans between %s and %s then -jjg_qty else 0 end) as qty_nab2
            ,sum(case when grp='naf' and tgl_trans between %s and %s then -jjg_qty else 0 end) as qty_naf2
            from vdata_panen_nab_naf
            where grp<>'panen' and tgl_trans between %s and %s and jjg_qty <>0
            group by tgl_panen,block_id,tgl_trans,grp) detail
            on header.tgl_panen=detail.tgl_panen and header.block_id=detail.block_id
            order by header.tgl_panen,header.block_id,detail.tgl_trans
        """

        self.env.cr.execute(str_sql, (self.date_end,self.date_start,
              self.date_start, self.date_end,
              self.date_start, self.date_end,
              self.date_start, self.date_end,
              self.date_start, self.date_end,
              self.date_start, self.date_end,
              self.date_start, self.date_end,
              self.date_start, self.date_end,))

        no_urut = 0
        xtgl_panen = False
        xblock_id = False

        for report in self.env.cr.fetchall():
            if (xtgl_panen == report[0] and xblock_id == report[1]):
                no_urut = no_urut
            else:
                no_urut += 1

            xtgl_panen = report[0]
            xblock_id = report[1]

            new_lines = {
                'tgl_panen'     : xtgl_panen or False,
                'block_id'      : xblock_id or False,
                'qty_saw'       : report[2] or False,
                'qty_panen'     : report[3] or False,
                'qty_nab'       : report[4] or False,
                'qty_naf'       : report[5] or False,
                'qty_restan'    : report[6] or False,
                'umur_restan'   : report[7] or False,
                'tgl_trans'     : report[8] or False,
                'qty_nab2'      : report[9] or False,
                'qty_naf2'      : report[10] or False,
                'no_urut'       : no_urut,
                'produksi_id'   : self.id,
            }
            if new_lines:
                new_values_restan = self.env['wizard.report.produksi.restan'].create(new_lines)

        #Laporan Rotasi
        if self.rotasi_ids:
            for data in self.rotasi_ids:
                data.unlink()

        year_now = datetime.datetime.strptime(self.date_end, '%Y-%m-%d').year
        n_day = datetime.datetime.strptime(self.date_end, '%Y-%m-%d').day

        period_id = self.env['account.period'].search([('date_start', '<', self.date_start), ('special', '=', False)], order='date_stop desc', limit=1)

        rotasi_hd = self.env['lhm.rotasi.panen.balance'].search([('period_id', '=', period_id.id)])

        data_block = self.env['lhm.plant.block'].search([('planted', '>', 0.0)], order='code')
        if data_block:
            for block in data_block:
                status = ''
                umur_tbs = year_now - block.year
                if umur_tbs == 0.0:
                    status = 'TBM-0'
                elif umur_tbs == 1:
                    status = 'TBM-1'
                elif umur_tbs == 2:
                    status = 'TBM-2'
                elif umur_tbs == 3:
                    status = 'TBM-3'
                elif umur_tbs == 4:
                    status = 'TM-1'
                elif umur_tbs == 5:
                    status = 'TM-2'
                elif umur_tbs == 6:
                    status = 'TM-3'
                elif umur_tbs == 7:
                    status = 'TM-4'
                elif umur_tbs == 8:
                    status = 'TM-5'
                else:
                    status = ''

                rotasi_dt = self.env['lhm.rotasi.panen.balance.nomor'].search([('block_id', '=', block.id),
                                                                               ('nomor_id', '=', rotasi_hd.id)])

                new_lines = {
                    'afdeling_id' : block.afdeling_id.id,
                    'section'     : block.section,
                    'block_id'    : block.id,
                    'luas'        : block.planted,
                    'pokok'       : block.total_plant,
                    'sph'         : block.total_plant/block.planted,
                    'status'      : status,
                    't00'         : rotasi_dt.value or False,
                    'produksi_id' : self.id,
                }

                if new_lines:
                    self.env['wizard.report.produksi.rotasi.panen'].create(new_lines)


        #Flag Panen dari LHM range tgl
        str_sql = """
            select
            ltpl.date as tgl_panen
            ,lpb.id as block_id
            FROM lhm_transaction lt
            LEFT JOIN lhm_transaction_process_line ltpl ON lt.id=ltpl.lhm_id
            left join lhm_plant_block lpb on lpb.location_id=ltpl.location_id
            LEFT JOIN lhm_activity la on la.id=ltpl.activity_id
            where la.is_panen is True and ltpl.date between %s and %s and state in ('done','close')
            group by ltpl.date,lpb.id
            order by lpb.id,ltpl.date
        """
        self.env.cr.execute(str_sql, (self.date_start, self.date_end))

        old_grp_block = 0
        old_tgl_panen = False
        val_panen = 0
        sel_tgl = 0
        for flag_panen in self.env.cr.fetchall():
            if flag_panen:
                if flag_panen[1] != old_grp_block:
                    val_panen = 1
                    old_tgl_panen = flag_panen[0]
                else:
                    sel_tgl = abs((datetime.datetime.strptime(flag_panen[0], '%Y-%m-%d') - datetime.datetime.strptime(
                        old_tgl_panen, '%Y-%m-%d')).days)

                    if sel_tgl < 4:
                        val_panen = 2
                    else:
                        val_panen = 3
                        old_tgl_panen = flag_panen[0]

                old_grp_block = flag_panen[1]
                str_tgl = datetime.datetime.strptime(flag_panen[0], '%Y-%m-%d').strftime('%d')
                str_sql = """
                    update wizard_report_produksi_rotasi_panen set t""" + str_tgl + """= %s where block_id = %s and produksi_id = %s;
                    update wizard_report_produksi_rotasi_panen set z""" + str_tgl + """= %s where block_id = %s and produksi_id = %s;
                """
                self.env.cr.execute(str_sql, (val_panen, old_grp_block, self.id, val_panen, old_grp_block, self.id))

        data_rotasi = self.env['wizard.report.produksi.rotasi.panen'].search([('produksi_id', '=', self.id)],)

        col_names = ['z01','z02', 'z03','z04','z05','z06','z07','z08','z09','z10','z11','z12','z13','z14','z15',
                     'z16','z17','z18','z19','z20','z21','z22','z23','z24','z25','z26','z27','z28','z29','z30','z31']

        z_col_names = col_names[:n_day]

        for block in data_rotasi:
            flag_merah = block.t00
            for col in sorted(z_col_names):
                flag_merah += 1
                if eval('block.%s' % col) in (1, 2, 3):
                    flag_merah = 0

                if flag_merah > 10:
                    str_sql = """
                        update wizard_report_produksi_rotasi_panen set """ + col + """ = 4 where block_id = %s and produksi_id = %s;
                    """
                    self.env.cr.execute(str_sql, (block.block_id.id, self.id))


        col_names = ['t01','t02', 't03','t04','t05','t06','t07','t08','t09','t10','t11','t12','t13','t14','t15',
                     't16','t17','t18','t19','t20','t21','t22','t23','t24','t25','t26','t27','t28','t29','t30','t31']

        z_col_names = col_names[:n_day]

        data_block = {}
        for block in data_rotasi:
            if block.block_id.id not in data_block.keys():
                data_block.update({block.block_id.id: dict(map(lambda x: (x, 0), col_names))})
                op = block.t00
                for col in sorted(z_col_names):
                    try:
                        op += 1
                        if eval('block.%s'%col) in (1, 3):
                            data_block[block.block_id.id][col] = 1
                            op = 1
                        else:
                            data_block[block.block_id.id][col] = op
                    except:
                        continue

                block.write(data_block[block.block_id.id])

    @api.multi
    def gen_no_akhir_rotasi(self):
        n_day       = datetime.datetime.strptime(self.date_end, '%Y-%m-%d').day
        period_id   = self.env['account.period'].search([('date_start', '=', self.date_start), ('special', '=', False)], order='date_stop desc', limit=1)
        Nomor       = self.env['lhm.rotasi.panen.balance'].search([('period_id', '=', period_id.id)],)
        NomorLine   = self.env['lhm.rotasi.panen.balance.nomor']
        data_rotasi = self.env['wizard.report.produksi.rotasi.panen'].search([('produksi_id', '=', self.id)],)

        if not Nomor:
            nomor_vals = {
                'period_id': period_id.id,
                'company_id': self.company_id.id,
            }
            nomor = Nomor.create(nomor_vals)
            nomor_id = nomor.id
        else:
            nomor_id = Nomor.id

        if Nomor.rotasi_ids:
            for data in Nomor.rotasi_ids:
                data.unlink()

        col_names = ['t01','t02', 't03','t04','t05','t06','t07','t08','t09','t10','t11','t12','t13','t14','t15',
                     't16','t17','t18','t19','t20','t21','t22','t23','t24','t25','t26','t27','t28','t29','t30','t31']

        data_block = {}
        for block in data_rotasi:
            data_block.update({block.block_id.id: dict(map(lambda x: (x, 0), col_names))})
            for col in sorted(col_names):
                try:
                    if col == col_names[n_day-1]:
                        nomor_line_vals = {
                            'block_code'    : block.block_id.code,
                            'block_id'      : block.block_id.id,
                            'value'         : block[col],
                            'nomor_id'      : nomor_id,
                        }
                        NomorLine.create(nomor_line_vals)
                except:
                    continue

class WizardReportProduksiPanen(models.TransientModel):
    _name           = 'wizard.report.produksi.panen'
    _description    = 'Laporan Panen'

    hr_foreman_id    = fields.Many2one(comodel_name="hr.foreman", string="Kemandoran/Kontraktor", ondelete="restrict", readonly=True)
    date             = fields.Date(string="Tgl. Progres")
    location_code    = fields.Char(string="Kode", related="location_id.code")
    location_id      = fields.Many2one(comodel_name="lhm.location", string="Lokasi", ondelete="restrict", readonly=True)
    uom_id           = fields.Many2one(comodel_name="product.uom", string="Satuan", readonly=True)
    nilai            = fields.Float(digits=(16,2), string="Hasil Kerja", readonly=True)
    uom_id2          = fields.Many2one(comodel_name="product.uom", string="Satuan2", readonly=True)
    nilai2           = fields.Float(digits=(16,2), string="Hasil Kerja2", readonly=True)
    total            = fields.Float(digits=(16,2), string="Realisasi", readonly=True)
    hk               = fields.Float(digits=(16,2), string="HK", readonly=True)
    produksi_id       = fields.Many2one(comodel_name='wizard.report.produksi', string='Laporan Produksi', required=True, ondelete="cascade", copy=False)

class WizardReportProduksiRestan(models.TransientModel):
    _name            = 'wizard.report.produksi.restan'
    _description     = 'Laporan Restan'

    no_urut     = fields.Float("No Urut")
    block_id    = fields.Many2one(comodel_name="lhm.plant.block", string="BLOK", ondelete="restrict", readonly=True)
    tgl_panen   = fields.Date(string="TGL PANEN", readonly=True)
    qty_saw     = fields.Float(digits=(16,0), string="QTY SAW", readonly=True)
    qty_panen   = fields.Float(digits=(16,0), string="QTY PANEN", readonly=True)
    qty_nab     = fields.Float(digits=(16,0), string="QTY NAB", readonly=True)
    qty_naf     = fields.Float(digits=(16,0), string="QTY AFKIR", readonly=True)
    qty_restan  = fields.Float(digits=(16,0), string="QTY RESTAN", readonly=True)
    umur_restan = fields.Float(digits=(16,0), string="UMUR RESTAN (Hari)", readonly=True)
    tgl_trans   = fields.Date(string="TGL TRANS", readonly=True)
    qty_nab2    = fields.Float(digits=(16,0), string="QTY NAB2", readonly=True)
    qty_naf2    = fields.Float(digits=(16,0), string="QTY AFKIR2", readonly=True)
    produksi_id = fields.Many2one(comodel_name='wizard.report.produksi', string='Laporan Produksi', required=True, ondelete="cascade", copy=False)

class WizardReportProduksiNabPerblock(models.TransientModel):
    _name            = 'wizard.report.produksi.nab.perblock'
    _description     = 'Laporan NAB Detail PerBlok'

    afdeling_id = fields.Many2one(comodel_name="res.afdeling", string="Afdeling",  ondelete="restrict", readonly=True)
    block_id    = fields.Many2one(comodel_name="lhm.plant.block", string="Lokasi",  ondelete="restrict", readonly=True)
    kbn_hi_kg = fields.Float(digits=(16,2), string="KBN HI KG", readonly=True)
    kbn_hi_jjg = fields.Float(digits=(16,0), string="KBN HI JJG", readonly=True)
    kbn_hi_bjr = fields.Float(digits=(16,2), string="KBN HI BJR", readonly=True)
    kbn_shi_kg = fields.Float(digits=(16,2), string="KBN SHI KG", readonly=True)
    kbn_shi_jjg = fields.Float(digits=(16,2), string="KBN SHI JJG", readonly=True)
    kbn_shi_bjr = fields.Float(digits=(16,2), string="KBN SHI BJR", readonly=True)
    pks_hi_bruto = fields.Float(digits=(16,2), string="PKS HI BRUTO", readonly=True)
    pks_hi_grading = fields.Float(digits=(16,2), string="PKS HI GRADING", readonly=True)
    pks_hi_netto = fields.Float(digits=(16,2), string="PKS HI NETTO", readonly=True)
    pks_hi_bjr = fields.Float(digits=(16,2), string="PKS HI BJR", readonly=True)
    pks_shi_bruto = fields.Float(digits=(16,2), string="PKS SHI BRUTO", readonly=True)
    pks_shi_grading = fields.Float(digits=(16,2), string="PKS SHI GRADING", readonly=True)
    pks_shi_netto = fields.Float(digits=(16,2), string="PKS SHI NETTO", readonly=True)
    pks_shi_bjr = fields.Float(digits=(16,2), string="PKS SHI BJR", readonly=True)
    produksi_id = fields.Many2one(comodel_name='wizard.report.produksi', string='Laporan Produksi', required=True, ondelete="cascade", copy=False)

class WizardReportProduksiNabDetail(models.TransientModel):
    _name           = 'wizard.report.produksi.nab.detail'
    _description    = 'Laporan NAB Detail'

    tgl_nab         = fields.Date(string="TGL. NAB", readonly=True)
    no_nab          = fields.Char(string="REF. NAB", readonly=True)
    afdeling_id     = fields.Many2one(comodel_name="res.afdeling", string="AFDELING", ondelete="restrict", readonly=True)
    block_id        = fields.Many2one(comodel_name="lhm.plant.block", string="LOKASI", ondelete="restrict", readonly=True)
    kbn_qty_jjg     = fields.Float(digits=(16,0), string="KBN QTY JJG", readonly=True)
    tgl_panen       = fields.Date(string="TGL PANEN", readonly=True)
    kbn_qty_kg      = fields.Float(digits=(16,2), string="KBN QTY KG", readonly=True)
    kbn_bjr         = fields.Float(digits=(16,2), string="KBN BJR", readonly=True)
    bjr_id          = fields.Many2one(comodel_name="lhm.bjr", string="BJR", ondelete="restrict")
    pks_tgl         = fields.Date("PKS TGL", readonly=True)
    pks_bruto       = fields.Float(digits=(16,2), string="PKS BRUTO", readonly=True)
    pks_grading     = fields.Float(digits=(16,2), string="PKS GRADING", readonly=True)
    pks_netto       = fields.Float(digits=(16,2), string="PKS NETTO", readonly=True)
    pks_bjr         = fields.Float(digits=(16,2), string="PKS BJR", readonly=True)
    nab_id          = fields.Many2one(comodel_name="lhm.nab", string="NAB", ondelete="restrict")
    produksi_id     = fields.Many2one(comodel_name='wizard.report.produksi', string='Laporan Produksi', required=True, ondelete="cascade", copy=False)

class WizardReportProduksiNabRekap(models.TransientModel):
    _name           = 'wizard.report.produksi.nab.rekap'
    _description    = 'Laporan NAB Rekap'

    tgl_nab         = fields.Date(string="DOC. TGL", readonly=True)
    no_nab          = fields.Char(string="REF. NAB", readonly=True)
    afdeling_id     = fields.Many2one(comodel_name="res.afdeling", string="AFDELING", ondelete="restrict", readonly=True)
    vehicle_id     = fields.Many2one(comodel_name="lhm.utility", string="KENDARAAN",
                                     ondelete="restrict", readonly=True, domain=[('type', '=', 'vh')])
    driver          = fields.Char(string="SUPIR", readonly=True)
    ownership       = fields.Selection('KEPEMILIKAN', readonly=True, related="vehicle_id.ownership", store=True)
    tgl_nab2        = fields.Date(string="TGL NAB", readonly=True)
    kbn_qty_jjg     = fields.Float(digits=(16,0), string="KBN QTY JJG", readonly=True)
    kbn_qty_kg      = fields.Float(digits=(16,2), string="KBN QTY KG", readonly=True)
    kbn_bjr         = fields.Float(digits=(16,2), string="KBN BJR", readonly=True)
    pks_id          = fields.Many2one(comodel_name="res.partner", string="PKS NAMA", ondelete="restrict")
    pks_tgl         = fields.Date("PKS TGL", readonly=True)
    pks_bruto       = fields.Float(digits=(16,2), string="PKS BRUTO", readonly=True)
    pks_grading     = fields.Float(digits=(16,2), string="PKS GRADING", readonly=True)
    pks_netto       = fields.Float(digits=(16,2), string="PKS NETTO", readonly=True)
    nab_id          = fields.Many2one(comodel_name="lhm.nab", string="NAB", ondelete="restrict")
    produksi_id = fields.Many2one(comodel_name='wizard.report.produksi', string='Laporan Produksi', required=True, ondelete="cascade", copy=False)

class WizardReportProduksiRotasi(models.TransientModel):
    _name           = 'wizard.report.produksi.rotasi.panen'
    _description    = 'Laporan Rotasi Panen'

    afdeling_id     = fields.Many2one(comodel_name="res.afdeling", string="Afdeling",  ondelete="restrict", readonly=True)
    section         = fields.Char("Seksi", readonly=True)
    block_id        = fields.Many2one(comodel_name="lhm.plant.block", string="Lokasi",  ondelete="restrict", readonly=True)
    luas            = fields.Float(digits=(16,2), string="Luas", readonly=True)
    pokok           = fields.Float(digits=(16,2), string="Pokok", readonly=True)
    sph             = fields.Float(digits=(16,2), string="SPH", readonly=True)
    status          = fields.Char("Status", readonly=True)
    t00             = fields.Integer(string="Rotasi BL", readonly=True)
    t01             = fields.Integer(string="01", readonly=True)
    t02             = fields.Integer(string="02", readonly=True)
    t03             = fields.Integer(string="03", readonly=True)
    t04             = fields.Integer(string="04", readonly=True)
    t05             = fields.Integer(string="05", readonly=True)
    t06             = fields.Integer(string="06", readonly=True)
    t07             = fields.Integer(string="07", readonly=True)
    t08             = fields.Integer(string="08", readonly=True)
    t09             = fields.Integer(string="09", readonly=True)
    t10             = fields.Integer(string="10", readonly=True)
    t11             = fields.Integer(string="11", readonly=True)
    t12             = fields.Integer(string="12", readonly=True)
    t13             = fields.Integer(string="13", readonly=True)
    t14             = fields.Integer(string="14", readonly=True)
    t15             = fields.Integer(string="15", readonly=True)
    t16             = fields.Integer(string="16", readonly=True)
    t17             = fields.Integer(string="17", readonly=True)
    t18             = fields.Integer(string="18", readonly=True)
    t19             = fields.Integer(string="19", readonly=True)
    t20             = fields.Integer(string="20", readonly=True)
    t21             = fields.Integer(string="21", readonly=True)
    t22             = fields.Integer(string="22", readonly=True)
    t23             = fields.Integer(string="23", readonly=True)
    t24             = fields.Integer(string="24", readonly=True)
    t25             = fields.Integer(string="25", readonly=True)
    t26             = fields.Integer(string="26", readonly=True)
    t27             = fields.Integer(string="27", readonly=True)
    t28             = fields.Integer(string="28", readonly=True)
    t29             = fields.Integer(string="29", readonly=True)
    t30             = fields.Integer(string="30", readonly=True)
    t31             = fields.Integer(string="31", readonly=True)
    z01             = fields.Integer(string="01", readonly=True)
    z02             = fields.Integer(string="02", readonly=True)
    z03             = fields.Integer(string="03", readonly=True)
    z04             = fields.Integer(string="04", readonly=True)
    z05             = fields.Integer(string="05", readonly=True)
    z06             = fields.Integer(string="06", readonly=True)
    z07             = fields.Integer(string="07", readonly=True)
    z08             = fields.Integer(string="08", readonly=True)
    z09             = fields.Integer(string="09", readonly=True)
    z10             = fields.Integer(string="10", readonly=True)
    z11             = fields.Integer(string="11", readonly=True)
    z12             = fields.Integer(string="12", readonly=True)
    z13             = fields.Integer(string="13", readonly=True)
    z14             = fields.Integer(string="14", readonly=True)
    z15             = fields.Integer(string="15", readonly=True)
    z16             = fields.Integer(string="16", readonly=True)
    z17             = fields.Integer(string="17", readonly=True)
    z18             = fields.Integer(string="18", readonly=True)
    z19             = fields.Integer(string="19", readonly=True)
    z20             = fields.Integer(string="20", readonly=True)
    z21             = fields.Integer(string="21", readonly=True)
    z22             = fields.Integer(string="22", readonly=True)
    z23             = fields.Integer(string="23", readonly=True)
    z24             = fields.Integer(string="24", readonly=True)
    z25             = fields.Integer(string="25", readonly=True)
    z26             = fields.Integer(string="26", readonly=True)
    z27             = fields.Integer(string="27", readonly=True)
    z28             = fields.Integer(string="28", readonly=True)
    z29             = fields.Integer(string="29", readonly=True)
    z30             = fields.Integer(string="30", readonly=True)
    z31             = fields.Integer(string="31", readonly=True)
    produksi_id = fields.Many2one(comodel_name='wizard.report.produksi', string='Laporan Produksi', required=True, ondelete="cascade", copy=False)

class WizardReportProduksiSelect(models.TransientModel):
    _name = "wizard.report.produksi.select"
    _description = "Laporan Produksi Select"
    
    name = fields.Selection([('produksi_panen', 'Laporan Panen'),
                             ('produksi_panen_rekap', 'Laporan Rekap Panen'),
                             ('produksi_restan', 'Laporan Restan'),
                             ('produksi_nab_perblock', 'Laporan NAB Per Blok'),
                             ('produksi_nab_detail', 'Laporan NAB Detail'),
                             ('produksi_nab_rekap', 'Laporan NAB Rekap'),
                             ('produksi_nab_afkir', 'Laporan BA TBS Afkir'),
                             ('produksi_rotasi', 'Laporan Rotasi Panen'),
                             ], string='Choose Report', default='produksi_panen')
    
    report_type = fields.Selection([('html', 'HTML'), ('csv', 'CSV'), ('xlsx', 'XLSX'), ('rtf', 'RTF'),
                                    ('odt', 'ODT'), ('ods', 'ODS'), ('txt', 'Text'), ('pdf', 'PDF'),
                                    ('jrprint', 'Jasper Print')], string='Type'
                                   , default='xlsx')
    
    @api.multi
    def create_report(self):
        data = self.read()[-1]
        name_report = False
        if self.name == "produksi_panen":
            name_report = "report_produksi_panen"
        elif self.name == "produksi_panen_rekap":
            name_report = "report_produksi_panen_rekap"
        elif self.name == "produksi_restan":
            name_report = "report_produksi_restan"
        elif self.name == "produksi_nab_perblock":
            name_report = "report_produksi_nab_perblock"
        elif self.name == "produksi_nab_detail":
            name_report = "report_produksi_nab_detail"
        elif self.name == "produksi_nab_rekap":
            name_report = "report_produksi_nab_rekap"
        elif self.name == "produksi_nab_afkir":
            name_report = "report_produksi_nab_afkir"
        elif self.name == "produksi_rotasi":
            name_report = "report_produksi_panen_rotasi"
        else:
            return True
        return {
            'type': 'ir.actions.report.xml',
            'report_name': name_report,
            'datas': {
                'model': 'wizard.report.produksi.select',
                'id': self._context.get('active_ids') and self._context.get('active_ids')[0] or self.id,
                'ids': self._context.get('active_ids') and self._context.get('active_ids') or [],
                'report_type': data['report_type'],
                'form': data
            },
            'nodestroy': False
        }