from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import timedelta
import calendar
import time


class WizardCreateContractorBook(models.TransientModel):
    _name           = "wizard.create.contractor.book"
    _description    = "Create Contractor Book"

    contractor_id   = fields.Many2one("res.partner", "Kontraktor", ondelete="restrict", required=True)
    account_period_id = fields.Many2one('account.period', 'Account Period', required=True, ondelete="restrict", copy=True)
    payment_type    = fields.Selection([('payment0', 'Pembayaran 1 Bulan Penuh'),('payment1','Pembayaran Ke-1'),('payment2','Pembayaran Ke-2')], string='Pembayaran', index=False, readonly=False)
    date_start      = fields.Date("Tanggal Pembayaran Mulai")
    date_end        = fields.Date("Tanggal Pembayaran Selesai")
    product_id      = fields.Many2one('product.template', string='Product', change_default=True, ondelete='restrict', required=True, domain="[('is_nab','=',True)]", track_visibility='onchange')
    company_id      = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    default_lines   = fields.One2many('create.contractor.book.default.line', 'wizard_id', string='Defailt Lines', copy=False)
    contractor_lines    = fields.One2many('create.contractor.book.line', 'wizard_id', string='Contractor Book Lines', copy=False)
    transaction     = fields.Selection([('angkut', 'Biaya Angkut'),('uang_jalan','Uang Jalan')], string='Transaksi', index=False, default='angkut')

    @api.model
    def default_get(self, fields):
        res = super(WizardCreateContractorBook, self).default_get(fields)
        default_lines = [
            (0, 0, {'name': 'Biaya Angkut', 'location_type_id': False, 'location_type_id': False, 'pks_id': False, 
                'location_id': False, 'activity_id': False, 'pricelist_id': False, 'price_unit': 0.0}),
            (0, 0, {'name': 'Transport TBS', 'location_type_id': False, 'location_type_id': False, 'pks_id': False, 
                'location_id': False, 'activity_id': False, 'pricelist_id': False, 'price_unit': 0.0}),
            ]
        if 'default_lines' in fields:
            res.update({'default_lines': default_lines})
        return res
    
    @api.onchange('contractor_id','account_period_id','payment_type','transaction', 'date_start', 'date_end')
    def onchange_validate(self):
        # if self.contractor_id and self.account_period_id and self.payment_type:
        if self.contractor_id and self.account_period_id and self.transaction and self.date_start and self.date_end:
            # other_ids = self.env['lhm.contractor'].search([('account_period_id', '=', self.account_period_id.id), 
            #     ('supplier_id', '=', self.contractor_id.id), 
            #     ('payment_type', '=', self.payment_type), 
            #     ('total_type','=','result'), 
            #     ('contractor_vehicle','=',True)])
            # if other_ids:
            #     self.account_period_id  = False
            #     self.supplier_id        = False
            #     self.date_start         = False
            #     self.date_end           = False
            #     return {
            #         'warning': {'title': _('Kesalahan Input Data'),
            #                     'message': _("Dokumen sudah ada: %s.") % other_ids.name, },
            #     }
            if self.payment_type:
                month       = datetime.strptime(self.account_period_id.date_start, '%Y-%m-%d').strftime('%m')
                year        = datetime.strptime(self.account_period_id.date_start, '%Y-%m-%d').strftime('%Y')
                last_day    = calendar.monthrange(int(year), int(month))[1]
                if self.payment_type=='payment1':
                    self.date_start  = time.strftime(str(year) + '-' + str(month) + '-' + '01')
                    self.date_end    = time.strftime(str(year) + '-' + str(month) + '-' + '15')
                elif self.payment_type=='payment2':
                    self.date_start  = time.strftime(str(year) + '-' + str(month) + '-' + '16')
                    self.date_end    = time.strftime(str(year) + '-' + str(month) + '-' + str(last_day))
                else:
                    self.date_start = self.account_period_id.date_start
                    self.date_end = self.account_period_id.date_stop
            if self.date_start and self.date_end:
                if self.transaction=='angkut':
                    nab_datas = self.env['lhm.nab'].search([('date_pks', '>=', self.date_start),
                                                  ('date_pks', '<=', self.date_end), 
                                                  ('contractor_id', '=', self.contractor_id.id), 
                                                  ('state', 'in', ('confirmed','done'))],  order='date_pks')
                    grouped_pks = {}
                    for nab in nab_datas:
                        if nab.pks_id.id not in grouped_pks.keys():
                            grouped_pks.update({nab.pks_id.id:
                                [(0, 0, {'name': 'Biaya Angkut', 'location_type_id': False, 'pks_id': nab.pks_id.id, 
                                    'activity_id': False, 'pricelist_id': False, 'price_unit': 0.0}),
                                (0, 0, {'name': 'Transport TBS', 'location_type_id': False, 'pks_id': nab.pks_id.id, 
                                    'activity_id': False, 'pricelist_id': False, 'price_unit': 0.0})]
                                })
                    lines = []
                    for x in grouped_pks.values():
                        lines.append(x[0])
                        lines.append(x[1])
                    self.default_lines = lines
                    # buku_kontraktor_old = self.env['lhm.contractor'].search([
                    #         # ('account_period_id', '<=', self.account_period_id.id),
                    #         ('supplier_id','=',self.contractor_id.id), ('state','in',('confirmed','done')),
                    #         ('contractor_vehicle','=',True), 
                    #         ('total_type','=','result')
                    #         ], order='id desc', limit=1)
                    # if buku_kontraktor_old:
                    #     activities = [x.activity_id for x in buku_kontraktor_old[-1].mapped('line_vehicle_ids')]
                    #     if len(set(activities))==2:
                    #         activities = list(set(activities))
                    #         self.default_lines = [
                    #                 (0, 0, {'name': activities[0].name, 'activity_id': activities[0].id, 
                    #                     'location_type_id': activities[0].type_id.id, 'pricelist_id': False}),
                    #                 (0, 0, {'name': activities[1].name, 'activity_id': activities[1].id, 
                    #                     'location_type_id': activities[1].type_id.id, 'pricelist_id': False}),
                    #         ]
                    #     else:
                    #         self.default_lines = [
                    #             (0, 0, {'name': 'Biaya Angkut', 'location_type_id': False, 
                    #                 'activity_id': False, 'pricelist_id': False}),
                    #             (0, 0, {'name': 'Transport TBS', 'location_type_id': False, 
                    #                 'activity_id': False, 'pricelist_id': False}),
                    #         ]
                elif self.transaction=='uang_jalan':
                    nab_datas = self.env['lhm.nab'].search([('date_pks', '>=', self.date_start),
                                                  ('date_pks', '<=', self.date_end), 
                                                  ('contractor_id', '=', self.contractor_id.id), 
                                                  ('state', 'in', ('confirmed','done'))],  order='date_pks')
                    grouped_pks = {}
                    for nab in nab_datas:
                        if nab.pks_id.id not in grouped_pks.keys():
                            grouped_pks.update({nab.pks_id.id:(0, 0, {'name': 'Uang Jalan', 'location_type_id': False, 
                                    'pks_id': nab.pks_id.id, 'activity_id': False, 
                                    'pricelist_id': False, 'price_unit': 0.0})})
                    self.default_lines = grouped_pks.values()

    @api.multi  
    def _get_price(self, pricelist):
        final_price, rule_id = pricelist.get_product_price_rule(self.product_id, 1.0, self.contractor_id, date=self._context.get('date_pks'))
        return final_price

    @api.multi
    def generate_line(self):
        if self.contractor_lines:
            self.contractor_lines = [(5, None, None)]
        date_from   = self.date_start
        date_to     = self.date_end
        nab_datas = []
        if self.transaction == 'angkut':
            nab_datas = self.env['lhm.nab'].search([('date_pks', '>=', date_from),
                                                  ('date_pks', '<=', date_to), 
                                                  ('contractor_id', '=', self.contractor_id.id), 
                                                  ('state', 'in', ('confirmed','done')), 
                                                  '|',('lhm_contractor_id.state','=','cancel'),
                                                  ('lhm_contractor_id','=',False)],  order='date_pks')
        elif self.transaction == 'uang_jalan':
            nab_datas = self.env['lhm.nab'].search([('date_pks', '>=', date_from),
                                                  ('date_pks', '<=', date_to), 
                                                  ('contractor_id', '=', self.contractor_id.id), 
                                                  ('state', 'in', ('confirmed','done'))],  order='date_pks')
        to_write = {}
        for nab in nab_datas.sorted(key= lambda x: x.vehicle_id.code):
            if self.transaction=='angkut':
                for block in list(set([x.block_id for x in nab.line_ids])):
                    total_nabxbjr = sum([xx.qty_nab*xx.block_id.with_context({'date': nab.date_pks})._get_rate_bjr() for xx in nab.line_ids])
                    if not total_nabxbjr:
                        continue
                    
                    nab_lines = nab.line_ids.filtered(lambda x:x.block_id.id==block.id)
                    qty = 0.0
                    for line in nab_lines:
                        qty += ((line.qty_nab*block.with_context({'date': nab.date_pks})._get_rate_bjr())/total_nabxbjr) * nab.timbang_tara_pks
                    
                    if not qty:
                        continue
                    for default in self.default_lines.filtered(lambda x: x.location_type_id.oil_palm and x.pks_id.id==nab.pks_id.id):
                        vals = {
                            'wizard_id': self.id,
                            'location_type_id': default.location_type_id.id,
                            'location_id': block.location_id.id,
                            'activity_id': default.activity_id.id,
                            'pks_id': default.pks_id and default.pks_id.id or False,
                            'qty': qty,
                            'uom_id': self.product_id.uom_id.id,
                            # 'price_unit': default.price_unit,
                            'price_unit': self.with_context({'date_pks': nab.date_pks})._get_price(default.pricelist_id),
                            'vehicle_id': nab.vehicle_id.id,
                            'date': nab.date_pks,
                            'nab_id': nab.id,
                            }
                        self.env['create.contractor.book.line'].create(vals)
                for default in self.default_lines.filtered(lambda x: x.location_type_id.general_charge and x.pks_id.id==nab.pks_id.id):
                    cost_center = self.env['account.cost.center'].search([('group_progress_id','=',nab.afdeling_id.group_progress_id.id)])
                    vals = {
                        'wizard_id': self.id,
                        'location_type_id': default.location_type_id.id,
                        'location_id': cost_center and cost_center[-1].location_id.id or nab.afdeling_id.location_id.id,
                        'activity_id': default.activity_id.id,
                        'pks_id': default.pks_id and default.pks_id.id or False,
                        'qty': nab.timbang_tara_pks,
                        'uom_id': self.product_id.uom_id.id,
                        # 'price_unit': default.price_unit,
                        'price_unit': self.with_context({'date_pks': nab.date_pks})._get_price(default.pricelist_id),
                        'vehicle_id': nab.vehicle_id.id,
                        'date': nab.date_pks,
                        'nab_id': nab.id,
                        }
                    self.env['create.contractor.book.line'].create(vals)
            elif self.transaction=='uang_jalan':
                total_nabxbjr = sum([xx.qty_nab*xx.block_id.with_context({'date': nab.date_pks})._get_rate_bjr() for xx in nab.line_ids])
                for block in nab.line_ids.mapped('block_id'):
                    if not total_nabxbjr:
                        continue
                    nab_lines = nab.line_ids.filtered(lambda x:x.block_id.id==block.id)
                    qty = 0.0
                    for line in nab_lines:
                        qty += ((line.qty_nab*block.with_context({'date': nab.date_pks})._get_rate_bjr())/total_nabxbjr) * nab.netto
                    
                    if not qty:
                        continue
                    for default in self.default_lines.filtered(lambda x: x.location_type_id.oil_palm and x.pks_id.id==nab.pks_id.id):
                        vals = {
                            'wizard_id': self.id,
                            'location_type_id': default.location_type_id.id,
                            'location_id': block.location_id.id,
                            'activity_id': default.activity_id.id,
                            'pks_id': default.pks_id and default.pks_id.id or False,
                            'qty': 1,
                            # 'uom_id': self.product_id.uom_id.id,
                            'price_unit': (qty/nab.netto)*default.price_unit,
                            'vehicle_id': nab.vehicle_id.id,
                            'date': nab.date_pks,
                            'nab_id': nab.id,
                            }
                        self.env['create.contractor.book.line'].create(vals)
        return True

    @api.multi
    def create_contractor_book(self):
        ContractorBook = self.env['lhm.contractor']
        ContractorBookLine = self.env['lhm.contractor.vehicle.line']
        nab_datas = list(set([x.nab_id for x in self.contractor_lines]))
        for nab in nab_datas:
            if nab.lhm_contractor_id:
                if nab.lhm_contractor_id.state=='cancel':
                    nab.lhm_contractor_id.sudo().unlink()
                    continue
                else:
                    raise UserError(_('NAB %s ini sudah digunakan di Buku Kontraktor %s')%(nab.name, nab.lhm_contractor_id.name))
        if not self.contractor_lines:
            raise UserError(_('Tidak memiliki Detail NAB yg akan dibuatkan ke Buku Kontraktor'))
        header_vals = {
            'name': '',
            'contractor_vehicle': True,
            'payment_type': self.payment_type,
            'total_type': 'result',
            'type': 'vendor',
            'supplier_id': self.contractor_id.id,
            'account_period_id': self.account_period_id.id,
            'date_start': self.date_start,
            'date_end': self.date_end,
            'company_id': self.company_id.id,
        }
        header_id = ContractorBook.create(header_vals)

        for line in self.contractor_lines:
            line_vals = {
                'contractor_id': header_id.id,
                'location_type_id': line.location_type_id.id,
                'location_id': line.location_id.id,
                'activity_id': line.activity_id.id,
                'date': line.date,
                'vehicle_id': line.vehicle_id.id,
                'uom_id': line.uom_id.id,
                'nilai': line.qty,
                'unit_price': line.price_unit,
            }
            line_id = ContractorBookLine.create(line_vals)

        # Update all related Buku Kontraktor
        # for nab in nab_datas:
            # nab.write({'lhm_contractor_id': header_id.id})

        # Redirect to show ContractorBook
        # action = self.env.ref('account.ContractorBook_supplier_tree').read()[0]
        action = self.env.ref('c10i_lhm.action_lhm_contractor').read()[0]
        action['views'] = [(self.env.ref('c10i_lhm.view_lhm_contractor_form').id, 'form')]
        action['res_id'] = header_id.id
        return action


class CreateContractorBookDefaultLine(models.TransientModel):
    _name           = "create.contractor.book.default.line"
    _description    = "Default Lines"

    wizard_id           = fields.Many2one('wizard.create.contractor.book', 'Wizard', required=True, ondelete="cascade", copy=False)
    name                = fields.Char("Description")
    pks_id              = fields.Many2one("res.partner", "PKS")
    location_type_id    = fields.Many2one("lhm.location.type", "Tipe", required=True)
    # location_id         = fields.Many2one("lhm.location", "Lokasi", ondelete="restrict")
    activity_id         = fields.Many2one("lhm.activity", "Aktivitas", required=True)
    pricelist_id        = fields.Many2one('product.pricelist', 'Pricelist', required=False)
    price_unit          = fields.Float('Unit Price')

class CreateContractorBookLine(models.TransientModel):
    _name           = "create.contractor.book.line"
    _description    = "Contractor Book Lines"

    wizard_id           = fields.Many2one('wizard.create.contractor.book', 'Wizard', required=True, ondelete="cascade", copy=False)
    nab_id              = fields.Many2one("lhm.nab", "Source NAB")
    date                = fields.Date("Tanggal")
    vehicle_id          = fields.Many2one("lhm.utility", "Alat")
    pks_id              = fields.Many2one("res.partner", "PKS")
    location_type_id    = fields.Many2one("lhm.location.type", "Tipe")
    location_id         = fields.Many2one("lhm.location", "Lokasi")
    activity_id         = fields.Many2one("lhm.activity", "Aktivitas")
    qty                 = fields.Float('Hasil NAB')
    uom_id              = fields.Many2one("product.uom", "Satuan")
    price_unit          = fields.Float('Tarif Satuan')
    amount              = fields.Float('Nilai', compute='_compute_harga_satuan', store=True, readonly=True)
    
    @api.depends('price_unit', 'qty')
    def _compute_harga_satuan(self):
        for harga in self:
            if harga.qty and harga.price_unit:
                harga.amount = harga.price_unit * harga.qty