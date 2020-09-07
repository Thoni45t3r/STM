from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import timedelta
import calendar


class LhmContractorBill(models.TransientModel):
    _name           = "lhm.contractor.bill.wizard"
    _description    = "Contractor Bill Wizard"

    contractor_id   = fields.Many2one("res.partner", "Kontraktor", ondelete="restrict", required=True)
    date_invoice    = fields.Date('Invoice Date', required=True)
    start_period_id = fields.Many2one('account.period', 'Account Period', required=True, ondelete="restrict", copy=True)
    contractor_vehicle  = fields.Boolean(string="Vehicle")
    company_id      = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)

    lhm_contractor_ids = fields.Many2many('lhm.contractor', string='LHM Contractor')
    
    invoice_lines   = fields.One2many('lhm.contractor.summary', 'wizard_id', string='Summary', copy=False)
    line_ids        = fields.Many2many('lhm.contractor.line', string='Detail Kontraktor', readonly=True)
    line_vehicle_ids = fields.Many2many('lhm.contractor.vehicle.line', string='Detail Kontraktor Alat', readonly=True)
    has_npwp        = fields.Boolean(compute='_get_npwp', string='Ada NPWP?')
    taxes_id        = fields.Many2many('account.tax', string='Tax')
    
    @api.multi
    @api.depends('contractor_id')
    def _get_npwp(self):
        result = []
        for wizard in self:
            self.has_npwp = wizard.contractor_id.has_npwp

    @api.multi
    def generate_line(self):
        if self.contractor_vehicle:
            if self.line_vehicle_ids:
                self.line_vehicle_ids = [(5, None, None)]
        else:
            if self.line_ids:
                self.line_ids = [(5, None, None)]
        if self.invoice_lines:
            for line in self.invoice_lines:
                line.unlink()

        date_from   = self.start_period_id.date_start
        # date_to     = self.end_period_id.date_stop
        date_to     = self.start_period_id.date_stop

        # draft_buku_kontraktor = self.env['lhm.contractor'].search([('date_start', '>=', date_from),
        #                                           ('date_end', '<=', date_to),
        #                                           ('state', '=', 'draft')],  order='name', )
        # if draft_buku_kontraktor:
        #     raise UserError(_('Ada beberapa Buku Kontraktor yang berstatus DRAFT diperiode tersebut. \nSilahkan di periksa terlebih dahulu.'))

        if self.lhm_contractor_ids:
            buku_kontraktor_datas = self.lhm_contractor_ids
        else:
            buku_kontraktor_datas = self.env['lhm.contractor'].search([('date_start', '>=', date_from),
                                                  ('date_end', '<=', date_to), ('invoice_id','=',False),
                                                  ('supplier_id', '=', self.contractor_id.id), 
                                                  ('state', '=', 'confirmed')],  order='name', )

        to_write = {}
        if buku_kontraktor_datas:
            grouped_lines = {}
            bk_line_ids = []
            bk_line_vehicle_ids = []
            for buku_kontraktor in buku_kontraktor_datas:
                if self.contractor_vehicle:
                    for y in buku_kontraktor.line_vehicle_ids:
                        bk_line_vehicle_ids.append(y.id)

                    for line in buku_kontraktor.line_vehicle_ids:
                        if line.tidak_ditagihkan:
                            continue
                        key = (line.location_type_id, line.location_id, line.activity_id)
                        if key not in grouped_lines.keys():
                            grouped_lines.update({key: {
                                'location_type_id': line.location_type_id and line.location_type_id.id or False,
                                'location_id': line.location_id and line.location_id.id or False,
                                'activity_id': line.activity_id and line.activity_id.id or False,
                                'amount': 0.0,
                                'wizard_id': self.id,
                            }})
                        grouped_lines[key]['amount'] += line.total
                        to_write.update({'line_vehicle_ids': list(map(lambda x: (4, x), bk_line_vehicle_ids))})
                else:
                    for x in buku_kontraktor.line_ids:
                        bk_line_ids.append(x.id)

                    for line in buku_kontraktor.line_ids:
                        if line.tidak_ditagihkan:
                            continue
                        key = (line.location_type_id, line.location_id, line.activity_id)
                        if key not in grouped_lines.keys():
                            grouped_lines.update({key: {
                                'location_type_id': line.location_type_id and line.location_type_id.id or False,
                                'location_id': line.location_id and line.location_id.id or False,
                                'activity_id': line.activity_id and line.activity_id.id or False,
                                'amount': 0.0,
                                'wizard_id': self.id,
                                }})
                        grouped_lines[key]['amount'] += line.total
                        to_write.update({'line_ids': list(map(lambda x: (4,x), bk_line_ids))})

            for vals in grouped_lines.values():
                self.env['lhm.contractor.summary'].create(vals)
            self.write(to_write)
        return True

    @api.multi
    def process(self):
        Invoice = self.env['account.invoice']
        InvoiceLine = self.env['account.invoice.line']
        if self.line_vehicle_ids:
            contractor_datas = list(set([x.contractor_id for x in self.line_vehicle_ids]))
            # reference = 'Buku Kontraktor Alat %s'%(datetime.strptime(self.date_invoice, '%Y-%m-%d').strftime('%d/%m/%Y'))
        else:
            contractor_datas = list(set([x.contractor_id for x in self.line_ids]))
            # reference = 'Buku Kontraktor %s'%(datetime.strptime(self.date_invoice, '%Y-%m-%d').strftime('%d/%m/%Y'))

        for contractor in contractor_datas:
            if contractor.invoice_id:
                raise UserError(_('Buku Kontraktor ini sudah memiliki Vendor Bill'))

        journal_id = Invoice.with_context({'type': 'in_invoice'}).default_get(['journal_id'])['journal_id']
        if not journal_id:
            raise UserError(_('Please define an accounting purchase journal for this company.'))
        invoice_vals = {
            'name': '',
            'type': 'in_invoice',
            'date_invoice': self.date_invoice,
            # 'force_period_id': self.period_id.id,
            'account_id': self.contractor_id.property_account_payable_id.id,
            # 'reference': reference,
            'partner_id': self.contractor_id.id,
            'partner_shipping_id': self.contractor_id.id,
            'journal_id': journal_id,
            'currency_id': self.company_id.currency_id.id,
            'company_id': self.company_id.id,
            'operating_unit_id': contractor_datas and contractor_datas[0].operating_unit_id and contractor_datas[0].operating_unit_id.id or False,
        }
        invoice = Invoice.create(invoice_vals)

        for line in self.invoice_lines:
            # date_start = datetime.strptime(line.date_from, '%Y-%m-%d').strftime('%d %B %Y')
            # date_end = datetime.strptime(line.date_to, '%Y-%m-%d').strftime('%d %B %Y')
            invoice_line_vals = {
                'invoice_id': invoice.id,
                'name': "Jasa Kontraktor: %s"%(line.activity_id.name),
                'plantation_location_type_id': line.location_type_id.id,
                'plantation_location_id': line.location_id.id,
                'plantation_activity_id': line.activity_id.id,
                # 'account_id': line.activity_id.account_id.id,
                'account_id': self.contractor_id.account_payable_contractor_id.id,
                'product_id': False,
                'uom_id': False,
                'quantity': 1,
                'price_unit': line.amount,
                'invoice_line_tax_ids': [(6,0,[x.id for x in self.taxes_id])],
            }
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
        invoice.message_post('This invoice has been created from Buku Kontraktor')

        # Update all related Buku Kontraktor
        for contractor in contractor_datas:
            contractor.write({'invoice_id': invoice.id})

        # Redirect to show Invoice
        # action = self.env.ref('account.invoice_supplier_tree').read()[0]
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        action['views'] = [(self.env.ref('account.invoice_supplier_form').id, 'form')]
        action['res_id'] = invoice.id
        return action


class LhmContractorSummary(models.TransientModel):
    _name           = "lhm.contractor.summary"
    _description    = "Rangkuman Buku Kontraktor"

    wizard_id           = fields.Many2one('lhm.contractor.bill.wizard', 'Wizard', required=True, ondelete="cascade", copy=False)
    location_type_id    = fields.Many2one("lhm.location.type", "Tipe", ondelete="restrict")
    location_id         = fields.Many2one("lhm.location", "Lokasi", ondelete="restrict")
    activity_id         = fields.Many2one("lhm.activity", "Aktivitas", ondelete="restrict")
    amount              = fields.Float('Nilai')