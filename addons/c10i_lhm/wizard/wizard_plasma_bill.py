from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar

class LhmPlasmaProfitSharing(models.Model):
    _name           = "lhm.plasma.profit.sharing"
    _description    = "Pembagian Hasil Penjualan Plasma"

    date = fields.Date('Berlaku sejak Tanggal', required=True)
    partner_id = fields.Many2one('res.partner', 'Partner', required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    line_ids = fields.One2many('lhm.plasma.profit.sharing.line', 'share_id', 'Detail Pembagian')

    @api.model
    def default_get(self, fields):
        res = super(LhmPlasmaProfitSharing, self).default_get(fields)
        default_share_composition = [
            (0, 0, {'name': 'Biaya Perawatan', 'percentage_value': 40.0, 'to_pay': False}),
            (0, 0, {'name': 'Biaya Angsuran', 'percentage_value': 30.0, 'to_pay': False}),
            (0, 0, {'name': 'Hasil', 'percentage_value': 30.0, 'to_pay': True})
            ]
        if 'line_ids' in fields:
            res.update({'line_ids': default_share_composition})
        return res

class LhmPlasmaProfitSharingDetail(models.Model):
    _name           = "lhm.plasma.profit.sharing.line"

    share_id = fields.Many2one('lhm.plasma.profit.sharing', 'Reference')
    name = fields.Char('Description', required=True)
    account_id = fields.Many2one('account.account', 'Account', required=True)
    percentage_value = fields.Float('Sharing Percentage', required=True)
    to_pay = fields.Boolean('Hasi ke Partner')

class LhmBillPlasma(models.TransientModel):
    _name           = "wizard.lhm.bill.plasma"
    _description    = "Generate Invoice Plasma"

    partner_id      = fields.Many2one('res.partner', 'Partner', required=True)
    period_id       = fields.Many2one('account.period', 'Account Period', required=True)
    date_invoice    = fields.Date('Invoice Date', required=True)
    date_from       = fields.Date('Dari Tanggal', required=True)
    date_to         = fields.Date('Sampai Tanggal', required=True)
    product_id      = fields.Many2one('product.template', 'Product', required=True, domain="[('is_nab','=',True)]")
    company_id      = fields.Many2one('res.company', 'Company', index=True, default=lambda self: self.env.user.company_id)
    sharing_profit_id = fields.Many2one('lhm.plasma.profit.sharing', 'Formula Sharing Profit')
    
    header_nab_ids  = fields.One2many('wizard.lhm.bill.plasma.header', 'wizard_id', 'Header NAB')
    line_nab_ids    = fields.One2many('wizard.lhm.bill.plasma.detail', 'wizard_id', 'Detail NAB')

    @api.onchange('period_id')
    def onchange_period(self):
        if self.period_id:
            self.date_from = self.period_id.date_start
            self.date_to = self.period_id.date_stop

    @api.onchange('date_to', 'partner_id')
    def onchange_date_to(self):
        if self.partner_id and self.date_to:
            shareprof = self.env['lhm.plasma.profit.sharing'].search([('partner_id','<=',self.partner_id.id), ('date','<=',self.date_to)], limit=1, order='date desc')
            if shareprof:
                self.sharing_profit_id = shareprof.id
        else:
            self.sharing_profit_id = False

    @api.multi  
    def _get_price(self, block):
        if not block.plasma_pricelist_id:
            return 0.0
        final_price, rule_id = block.plasma_pricelist_id.get_product_price_rule(self.product_id, 1.0, self.partner_id, date=self._context.get('date_pks'))
        return final_price

    @api.multi
    def generate_detail(self):
        if self.header_nab_ids:
            for delete in self.header_nab_ids:
                delete.unlink()
        if self.line_nab_ids:
            for delete in self.line_nab_ids:
                delete.unlink()

        data_nab = self.env['lhm.nab.line'].search([ \
            ('lhm_nab_id.date_pks','>=',self.date_from), \
            ('lhm_nab_id.date_pks','<=',self.date_to), \
            ('block_id.owner_type','=','plasma'), \
            ('lhm_nab_id.plasma_invoice_id','=',False), \
            ('lhm_nab_id.state','in',['confirmed', 'done'])])
        line_grouped = {}
        for x in data_nab:
            price = self.with_context({'date_pks': x.lhm_nab_id.date_pks})._get_price(x.block_id)
            key = (x.block_id.year, price)
            if key not in line_grouped.keys():
                line_grouped.update({key: []})
            line_grouped[key].append(x)
        line_header = {}
        for tahun_tanam, price in line_grouped.keys():
            for line in line_grouped[(tahun_tanam, price)]:
                vals = {
                    'lhm_nab_line_id': line.id,
                    'date_pks': line.lhm_nab_id.date_pks,
                    'block_id': line.block_id.id,
                    'qty_nab': line.qty_nab,
                    'janjang_jml': line.lhm_nab_id.janjang_jml,
                    'nilai_bjr': line.block_id.with_context({'date': line.lhm_nab_id.date_pks})._get_rate_bjr(),
                    'netto': line.lhm_nab_id.netto,
                    'wizard_id': self.id,
                }
                self.env['wizard.lhm.bill.plasma.detail'].create(vals)
                key = (tahun_tanam, price, line.block_id.afdeling_id)
                if key not in line_header.keys():
                    account = self.product_id.property_account_expense_id or self.product_id.categ_id.property_account_expense_categ_id
                    if not account:
                        raise UserError(_('Please define Expense account for this product: "%s" (id:%d) - or for its category: "%s".') %
                            (self.product_id.name, self.product_id.id, self.product_id.categ_id.name))
                    line_header.update({key: {
                        'year': tahun_tanam,
                        'afdeling_id': line.block_id.afdeling_id.id,
                        'price_unit': price,
                        'account_id': account.id,
                        'qty': 0.0,
                        'line_ids': [],
                        'wizard_id': self.id,
                        }})
                line_header[key]['line_ids'].append(line)
                line_header[key]['qty'] += ((vals['qty_nab']*vals['nilai_bjr'])/sum([(x.qty_nab*x.block_id.with_context({'date': line.lhm_nab_id.date_pks})._get_rate_bjr()) for x in line.lhm_nab_id.line_ids]) * vals['netto'])
        total_value = 0.0
        for values in line_header.values():
            first_date = min([x.lhm_nab_id.date_pks for x in values['line_ids']])
            last_date = max([x.lhm_nab_id.date_pks for x in values['line_ids']])
            date_start = datetime.strptime(first_date, '%Y-%m-%d').strftime('%d %B %Y')
            date_end = datetime.strptime(last_date, '%Y-%m-%d').strftime('%d %B %Y')
            values.update({
                'name': 'Tahun Tanam %s Period %s s/d %s'%(values['year'], date_start, date_end),
                })
            total_value += values['qty']*values['price_unit']
            self.env['wizard.lhm.bill.plasma.header'].create(values)

        # Decrease value with Sharing Profit Formula
        if self.sharing_profit_id and total_value:
            for line in self.sharing_profit_id.line_ids.filtered(lambda x: not x.to_pay):
                new_line = {
                    'year': False,
                    'afdeling_id': False,
                    'account_id': line.account_id.id,
                    'name': '%s (%s %%)'%(line.name, str(line.percentage_value)),
                    'price_unit': -1*total_value * (line.percentage_value/100.0),
                    'qty': 1,
                    'line_ids': [],
                    'wizard_id': self.id,
                }
                self.env['wizard.lhm.bill.plasma.header'].create(new_line)

    @api.multi
    def create_bill(self):
        Invoice = self.env['account.invoice']
        InvoiceLine = self.env['account.invoice.line']

        journal_id = Invoice.with_context({'type': 'in_invoice'}).default_get(['journal_id'])['journal_id']
        type_lokasi_null   = self.env['lhm.location.type'].search([('name','=','-')], limit=1)
        if not journal_id:
            raise UserError(_('Please define an accounting sale journal for this company.'))
        invoice_vals = {
            'name': '',
            'type': 'in_invoice',
            'reference': 'NAB %s'%(datetime.strptime(self.date_invoice, '%Y-%m-%d').strftime('%d/%m/%Y')),
            'date_invoice': self.date_invoice,
            # 'force_period_id': self.period_id.id,
            'account_id': self.partner_id.property_account_payable_id.id,
            'partner_id': self.partner_id.id,
            'partner_shipping_id': self.partner_id.id,
            'journal_id': journal_id,
            'currency_id': self.partner_id.property_product_pricelist and \
                self.partner_id.property_product_pricelist.currency_id.id or self.company_id.currency_id.id,
            'company_id': self.company_id.id,
        }
        invoice = Invoice.create(invoice_vals)
        for line in self.header_nab_ids:
            invoice_line_vals = {
                'invoice_id': invoice.id,
                'plantation_location_type_id': type_lokasi_null and type_lokasi_null[0].id or False,
                'plantation_location_id': False,
                'plantation_activity_id': False,
                'product_id': self.product_id.id,
                'price_unit': line.price_unit,
                'uom_id': self.product_id.uom_id.id,
                'quantity': line.qty,
                'account_id': line.account_id.id,
            }
            if line.afdeling_id:
                invoice_line_vals.update({'name': 'Afdeling %s %s'%(line.afdeling_id.code, line.name)})
            else:
                invoice_line_vals.update({'name': '%s'%line.name})
            invoice_line_id = InvoiceLine.create(invoice_line_vals)

        if not invoice.invoice_line_ids:
            raise UserError(_('There is no invoicable line.'))
        # If invoice is negative, do a refund invoice instead
        if invoice.amount_untaxed < 0:
            invoice.type = 'in_refund'
            for line in invoice.invoice_line_ids:
                line.quantity = -line.quantity
        # Use additional field helper function (for account extensions)
        for line in invoice.invoice_line_ids:
            line._set_additional_fields(invoice)
        # Necessary to force computation of taxes. In account_invoice, they are triggered
        # by onchanges, which are not triggered when doing a create.
        invoice.compute_taxes()
        invoice.message_post('This invoice has been created from \
            Generate Bill TBS Plasma')

        # Update all related NAB
        for nab in list(set([x.lhm_nab_line_id.lhm_nab_id for x in self.line_nab_ids])):
            nab.write({'plasma_invoice_id': invoice.id})
        
        # Redirect to show Invoice
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        action['views'] = [(self.env.ref('account.invoice_supplier_form').id, 'form')]
        action['res_id'] = invoice.id
        return action

TAHUN = [(num, str(num)) for num in range((datetime.now().year) - 8, (datetime.now().year) + 1)]

class LhmGenNabHeaderWizard(models.TransientModel):
    _name           = "wizard.lhm.bill.plasma.header"
    _description    = "Total Keseluruhan NAB Plasma"

    @api.multi
    @api.depends('qty', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.price_unit*line.qty

    def _default_year(self):
        return int(time.strftime('%Y'))

    wizard_id       = fields.Many2one('wizard.lhm.bill.plasma', 'Wizard', required=True, ondelete='cascade')
    year            = fields.Selection(TAHUN, string='Tahun Tanam', default=_default_year)
    account_id      = fields.Many2one('account.account', 'Account', required=False)
    afdeling_id     = fields.Many2one('res.afdeling', 'Afdeling', required=False)
    qty             = fields.Float('Jumlah Barang', required=True)
    price_unit      = fields.Float('Harga Satuan', required=True)
    name            = fields.Char('Description', required=True)
    subtotal        = fields.Float('Subtotal', compute='_compute_subtotal')

class LhmGenNabLineWizard(models.TransientModel):
    _name            = "wizard.lhm.bill.plasma.detail"
    _description     = "Detail NAB Plasma"

    wizard_id       = fields.Many2one('wizard.lhm.bill.plasma', 'Wizard', required=True, ondelete='cascade')
    lhm_nab_line_id = fields.Many2one('lhm.nab.line', 'Reference')
    date_pks        = fields.Date('Tanggal PKS')
    block_id        = fields.Many2one('lhm.plant.block', 'Block Tanam')
    nilai_bjr       = fields.Float('BJR (kg)')
    qty_nab         = fields.Float('Total Nab')
    janjang_jml     = fields.Float('Total Janjang')
    netto           = fields.Float('Berat Bersih di PKS')