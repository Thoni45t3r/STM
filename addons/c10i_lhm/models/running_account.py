# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from res import _RUNNING_SELECTION
_logger = logging.getLogger(__name__)

class running_account(models.Model):
    _name           = 'running.account'
    _inherit        = ['mail.thread', 'ir.needaction_mixin']
    _description    = 'Running Account'
    _order          = 'account_period_id DESC'

    def _default_running_sequence_id(self):
        running_sequence_id = self.env['res.running'].search([])[-1]
        return running_sequence_id and running_sequence_id.id or False

    def _get_state(self):
        STATUS = list(_RUNNING_SELECTION)
        STATUS.append(('done','Completed'))
        return STATUS

    name                    = fields.Char(readonly=True, compute='_compute_running_name', string='Running Name', store=True)
    account_period_id       = fields.Many2one("account.period", string="Accounting Periode", ondelete="restrict", track_visibility='onchange')
    running_sequence_ids    = fields.One2many("running.account.sequence", inverse_name="running_account_id", string="Sequence", readonly=True)
    running_line_ids        = fields.One2many("running.account.line", inverse_name="running_account_id", string="Details")
    running_line_detail_ids = fields.One2many("running.account.line.detail", inverse_name="running_account_id", string="Details")
    running_move_line_ids   = fields.One2many("running.account.move.line", inverse_name="running_account_id", string="Details")
    running_sequence_id     = fields.Many2one('res.running', string='Running Sequence', default=_default_running_sequence_id)
    company_id              = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    state                   = fields.Selection(selection=_get_state, string='Status', default='running')
    move_ids                = fields.Many2many('account.move', 'account_move_running_rel', 'running_account_id', 'move_id', 'Journal Entries')

    @api.multi
    @api.depends('account_period_id')
    def _compute_running_name(self):
        for running in self:
            running.name = "Running " + str(running.account_period_id.name or "")
        # for lead in self.filtered(lambda l: l.date_closed):
        #     date_create = fields.Datetime.from_string(lead.create_date)
        #     date_close = fields.Datetime.from_string(lead.date_closed)
        #     lead.day_close = abs((date_close - date_create).days)

    @api.onchange('running_sequence_id')
    def onchange_running_sequence_id(self):
        sequence_ids        = []
        if self.running_sequence_id:
            for sequence in self.running_sequence_id.line_ids:
                vals = {
                    'sequence'  : sequence.sequence,
                    'doc_id'    : sequence.doc_id,
                    'run_state' : sequence.run_state,
                }
                sequence_ids.append((0, 0, vals))
        self.running_sequence_ids = sequence_ids

    @api.multi
    def running(self):
        running_sequence_ids = self.env['res.running.line'].search([('running_id', '=', self.running_sequence_id.id)], order="sequence ASC")
        # RUNNING FROM TRANSACTION LINE
        self.get_data()
        self.calculate()
        for run_seq in running_sequence_ids:
            if run_seq.doc_id and run_seq.doc_id.running_model:
                if 'vehicle' in run_seq.doc_id.running_model:
                    self.recalculate_vehicle()
                elif 'workshop' in run_seq.doc_id.running_model:
                    self.recalculate_workshop()
                elif 'machine' in run_seq.doc_id.running_model:
                    self.recalculate_machine()
        # CREATE JOURNAL FROM RUNNING LINE
        self.create_journal()
        self.write({'state': 'project'})
        return True

    @api.multi
    def get_data(self):
        line_obj    = self.env['running.account.line']
        if self.running_line_ids != []:
            for hapus in self.running_line_ids:
                hapus.unlink()
        running_sequence_ids    = self.env['res.running.line'].search([('running_id', '=', self.running_sequence_id.id)], order="sequence ASC")
        for run_seq in running_sequence_ids:
            if run_seq.doc_id and run_seq.doc_id.running_model:
                if 'vehicle' in run_seq.doc_id.running_model:
                    data_ids    = self.env[str(run_seq.doc_id.running_model)].search([('account_period_id', '=', self.account_period_id.id)], order="vehicle_code ASC")
                    for vehicle in data_ids:
                        for vehicle_line in vehicle.line_ids:
                            other_utility = self.env['lhm.utility'].search([('location_id', '=', vehicle_line.location_id and vehicle_line.location_id.id or False)])
                            if vehicle_line.activity_id and vehicle_line.activity_id.bypass:
                                calculate   = False
                            else:
                                calculate   = True
                            if vehicle_line.difference_value == 0:
                                vehicle_value   = vehicle_line.use_hours
                            else:
                                vehicle_value   = vehicle_line.difference_value
                            values  = {
                                'name'                  : vehicle.name,
                                'sequence'              : run_seq.sequence,
                                'utility_id'            : vehicle.vehicle_id and vehicle.vehicle_id.id or False,
                                'other_utility_id'      : other_utility and other_utility.id or False,
                                'date'                  : vehicle_line.date,
                                'type'                  : 'vh',
                                'doc_id'                : run_seq.doc_id.id,
                                'qty'                   : vehicle_value,
                                'location_type_id'      : vehicle_line.location_type_id and vehicle_line.location_type_id.id or False,
                                'location_id'           : vehicle_line.location_id and vehicle_line.location_id.id or False,
                                'activity_id'           : vehicle_line.activity_id and vehicle_line.activity_id.id or False,
                                'src_account_id'        : run_seq.doc_id.account_id.id,
                                'dest_account_id'       : vehicle_line.activity_id.account_id.id or False,
                                'calculate'             : calculate,
                                'recalculate'           : True if other_utility else False,
                                'running_account_id'    : self.id,
                            }
                            line_obj.create(values)
                elif 'workshop' in run_seq.doc_id.running_model:
                    data_ids    = self.env[str(run_seq.doc_id.running_model)].search([('account_period_id', '=', self.account_period_id.id)], order="workshop_code ASC")
                    for workshop in data_ids:
                        for workshop_line in workshop.line_ids:
                            other_utility   = self.env['lhm.utility'].search([('location_id', '=', workshop_line.location_id and workshop_line.location_id.id or False)])
                            if workshop_line.activity_id and workshop_line.activity_id.bypass:
                                calculate   = False
                            else:
                                calculate   = True
                            values  = {
                                'name'                  : workshop.name,
                                'sequence'              : run_seq.sequence,
                                'utility_id'            : workshop.workshop_id and workshop.workshop_id.id or False,
                                'other_utility_id'      : other_utility and other_utility.id or False,
                                'date'                  : workshop_line.date,
                                'type'                  : 'ws',
                                'doc_id'                : run_seq.doc_id.id,
                                'qty'                   : workshop_line.use_hours,
                                'location_type_id'      : workshop_line.location_type_id and workshop_line.location_type_id.id or False,
                                'location_id'           : workshop_line.location_id and workshop_line.location_id.id or False,
                                'activity_id'           : workshop_line.activity_id and workshop_line.activity_id.id or False,
                                'src_account_id'        : run_seq.doc_id.account_id.id,
                                'dest_account_id'       : workshop_line.activity_id.account_id.id or False,
                                'calculate'             : calculate,
                                'recalculate'           : True if other_utility else False,
                                'running_account_id'    : self.id,
                            }
                            line_obj.create(values)
                elif 'machine' in run_seq.doc_id.running_model:
                    data_ids    = self.env[str(run_seq.doc_id.running_model)].search([('account_period_id', '=', self.account_period_id.id)], order="machine_code ASC")
                    for machine in data_ids:
                        for machine_line in machine.line_ids:
                            other_utility = self.env['lhm.utility'].search([('location_id', '=', machine_line.location_id and machine_line.location_id.id or False)])
                            if machine_line.activity_id and machine_line.activity_id.bypass:
                                calculate   = False
                            else:
                                calculate   = True
                            values  = {
                                'name'                  : machine.name,
                                'sequence'              : run_seq.sequence,
                                'utility_id'            : machine.machine_id and machine.machine_id.id or False,
                                'date'                  : machine_line.date,
                                'type'                  : 'ma',
                                'other_utility_id'      : other_utility and other_utility.id or False,
                                'doc_id'                : run_seq.doc_id.id,
                                'qty'                   : machine_line.use_hours,
                                'location_type_id'      : machine_line.location_type_id and machine_line.location_type_id.id or False,
                                'location_id'           : machine_line.location_id and machine_line.location_id.id or False,
                                'activity_id'           : machine_line.activity_id and machine_line.activity_id.id or False,
                                'src_account_id'        : run_seq.doc_id.account_id.id,
                                'dest_account_id'       : machine_line.activity_id.account_id.id or False,
                                'calculate'             : calculate,
                                'recalculate'           : True if other_utility else False,
                                'running_account_id'    : self.id,
                            }
                            line_obj.create(values)

    @api.multi
    def calculate(self):
        for running in self.running_line_ids:
            total_qty       = 0
            total_journal   = 0
            total_value     = 0
            total_all       = 0
            if running.calculate:
                filters         = ""
                filters_journal = ""
                if running.utility_id:
                    filters = filters + " AND utility_id=" + str(running.utility_id.id) + " AND running_account_id=" + str(running.running_account_id.id)
                if running.utility_id.location_id:
                    filters_journal = filters_journal + " AND plantation_location_id=" + str(running.utility_id.location_id.id)
                if running.src_account_id:
                    filters_journal = filters_journal + " AND account_id=" + str(running.src_account_id.id)
                self.env.cr.execute("select sum(qty) as total from running_account_line WHERE calculate = TRUE" + filters + " GROUP BY type")
                for total in self.env.cr.fetchall():
                    total_qty       = total[0] or 0.0
                self.env.cr.execute("select sum(debit) - sum(credit) as total from account_move_line WHERE date::DATE BETWEEN %s::DATE AND %s::DATE" + filters_journal, (self.account_period_id.date_start,self.account_period_id.date_stop))
                for total in self.env.cr.fetchall():
                    total_journal   = total[0] or 0.0
                if total_qty != 0:
                    total_value = total_journal/total_qty
                if total_value != 0:
                    total_all   = total_value * running.qty
                running.sudo().write({
                    'total_qty'     : total_qty,
                    'total_journal' : total_journal,
                    'value'         : total_value,
                    'total'         : total_all,
                    'total_other'   : 0.0,
                    'var_plus'      : 0.0,
                    'var_minus'     : 0.0
                })
            else:
                running.sudo().write({
                    'total_qty'     : 0.0,
                    'total_journal' : 0.0,
                    'total_other'   : 0.0,
                    'var_plus'      : 0.0,
                    'var_minus'     : 0.0
                })

    @api.multi
    def recalculate_workshop(self):
        line_obj            = self.env['running.account.line']
        util_running_ids    = line_obj.search([('type', '=', 'ws'), ('running_account_id', '=', self.id), ('recalculate', '=', True), ('total', '<>', 0)], order="utility_code ASC, other_utility_code ASC")
        util_temp           = False
        other_util_temp     = False
        for utility in util_running_ids:
            if utility.utility_id.id == util_temp and utility.other_utility_id.id == other_util_temp:
                total_other_utils   = 0
                running_ids         = line_obj.search([('type', '=', 'ws'), ('running_account_id', '=', self.id), ('recalculate', '=', True), ('total', '<>', 0), ('other_utility_id', '=', int(utility.other_utility_id.id))], order="sequence ASC, utility_code ASC, location_code ASC, activity_code ASC")
                for running in running_ids:
                    total_other_utils += running.total
                for recal in running_ids:
                    recal.write({'total_other' : total_other_utils})
            else:
                utility.write({'total_other': utility.total})
                util_temp           = utility.utility_id.id
                other_util_temp     = utility.other_utility_id.id
        util_temp           = False
        other_util_temp     = False
        for utility in util_running_ids:
            if utility.utility_id.id == util_temp and utility.other_utility_id.id == other_util_temp:
                pass
            else:
                util_temp       = utility.utility_id.id
                other_util_temp = utility.other_utility_id.id
                total_beban     = 0
                other_ids       = line_obj.search([('type', '=', utility.other_utility_id.type), ('running_account_id', '=', self.id), ('calculate', '=', True), ('total', '<>', 0), ('utility_id', '=', int(utility.other_utility_id.id))], order="sequence ASC, utility_code ASC, location_code ASC, activity_code ASC")
                util_data       = line_obj.search([('type', '=', 'ws'), ('running_account_id', '=', self.id), ('total', '<>', 0), ('other_utility_id', '=', int(utility.other_utility_id.id)), ('utility_id', '=', int(utility.utility_id.id))], limit=1)
                if util_data:
                    total_beban = util_data[0].total_other
                if other_ids != [] and total_beban != 0:
                    for other in other_ids:
                        other.write({
                            'total_journal' : other.total_journal + total_beban,
                            'value'         : (other.total_journal + total_beban) / other.total_qty,
                            'total'         : other.qty * ((other.total_journal + total_beban) / other.total_qty),
                        })
        change_state_ids = self.env['lhm.workshop'].search([('account_period_id', '=', self.account_period_id.id)])
        for change_state in change_state_ids:
            change_state.write({'state' : 'done'})

    @api.multi
    def recalculate_vehicle(self):
        line_obj            = self.env['running.account.line']
        line_detail_obj     = self.env['running.account.line.detail']
        util_running_ids    = line_obj.search([('type', '=', 'vh'), ('running_account_id', '=', self.id), ('recalculate', '=', True), ('total', '<>', 0)], order="utility_code ASC, other_utility_code ASC")
        sequence_detail     = 0
        if self.running_line_detail_ids != []:
            for hapus in self.running_line_detail_ids:
                hapus.unlink()
        for utility in util_running_ids:
            utility_ids = line_obj.search([('type', '=', 'vh'), ('running_account_id', '=', self.id), ('calculate', '=', True), ('total', '<>', 0), ('utility_id', '=', int(utility.utility_id.id))], order="sequence ASC, utility_code ASC, location_code ASC, activity_code ASC")
            if utility.activity_id.vh2vh:
                sequence_detail += 1
                line_detail_obj.create({
                    'sequence'              : sequence_detail,
                    'activity_id'           : utility.activity_id.id,
                    'src_utility'           : utility.utility_id.id,
                    'dest_utility'          : utility.other_utility_id.id,
                    'var_plus'              : 0.0,
                    'var_minus'             : utility.total,
                    'qty_minus'             : utility.qty,
                    'running_account_id'    : self.id,
                    'running_line_id'       : utility.id,
                })
                sequence_detail += 1
                line_detail_obj.create({
                    'sequence'              : sequence_detail,
                    'activity_id'           : utility.activity_id.id,
                    'src_utility'           : utility.other_utility_id.id,
                    'dest_utility'          : utility.utility_id.id,
                    'var_plus'              : utility.total,
                    'var_minus'             : 0.0,
                    'qty_minus'             : 0.0,
                    'running_account_id'    : self.id,
                    'running_line_id'       : utility.id,
                })
            if utility_ids != []:
                for minus in utility_ids:
                    minus.write({
                        'var_minus' : minus.var_minus + utility.total,
                        'total_qty' : minus.total_qty - utility.qty,
                    })
            other_ids = line_obj.search([('type', '=', utility.other_utility_id.type), ('running_account_id', '=', self.id), ('calculate', '=', True), ('total', '<>', 0), ('utility_id', '=', int(utility.other_utility_id.id))], order="sequence ASC, utility_code ASC, location_code ASC, activity_code ASC")
            if other_ids != []:
                for other in other_ids:
                    other.write({
                        'var_plus'      : other.var_plus + utility.total,
                    })
        vh_running_ids = line_obj.search([('type', '=', 'vh'), ('running_account_id', '=', self.id), ('calculate', '=', True), ('total', '<>', 0)], order="sequence ASC, utility_code ASC, location_code ASC, activity_code ASC")
        for vh in vh_running_ids:
            total_journal   = vh.total_journal + (vh.var_plus - vh.var_minus)
            vh.write({
                'total_journal' : total_journal,
                'value'         : total_journal / vh.total_qty,
                'total'         : vh.qty * (total_journal / vh.total_qty),
            })
        for vh in vh_running_ids:
            total_after = 0
            for data in line_obj.search([('type', '=', 'vh'), ('running_account_id', '=', self.id), ('calculate', '=', True), ('total', '<>', 0), ('utility_id', '=', vh.utility_id.id)], order="sequence ASC, utility_code ASC, location_code ASC, activity_code ASC"):
                total_after += data.total
            vh.write({
                'total_journal'   : total_after,
            })

        vh_list         = []
        for util_run in util_running_ids:
            detail_ids      = line_detail_obj.search([('running_line_id', '=', util_run.id)], order="sequence ASC")
            total_after_run = 0
            for detail in detail_ids:
                if detail.src_utility.id == util_run.utility_id.id and detail.dest_utility.id == util_run.other_utility_id.id:
                    total_after_run         = util_run.total - detail.var_minus
                    zero_line_obj           = line_obj.search([('running_account_id', '=', self.id), ('qty', '>', 0), ('total', '=', 0), ('calculate', '=', True), ('utility_id', '=', util_run.other_utility_id.id)])
                    util_run.write({
                        'total_journal' : util_run.total_journal - total_after_run,
                        'total'         : util_run.total - total_after_run,
                        'value'         : util_run.value - total_after_run,
                    })

                if detail.src_utility.id == util_run.other_utility_id.id and detail.dest_utility.id == util_run.utility_id.id:
                    detail.write({
                        'var_plus_vh'  : total_after_run,
                    })
                    total_after_run = 0
                    vh_list.append(detail.id)
                zeroing_total_journal = 0
                for zeroing in zero_line_obj:
                    zeroing_total_journal = zeroing.total_journal + detail.var_minus
                if zero_line_obj and len(zero_line_obj) == 1 and zero_line_obj.total == 0:
                    zero_line_obj.write({
                        'total_journal' : zeroing_total_journal,
                        'total'         : detail.var_minus,
                        'value'         : detail.var_minus,
                    })
                    util_run.write({
                        'total_journal' : util_run.total_journal - detail.var_minus,
                        'total'         : util_run.total - detail.var_minus,
                        'value'         : util_run.value - detail.var_minus,
                    })
        # for detail_run in line_detail_obj.search([('id', 'in', vh_list), ('var_plus_vh', '<>', 0)]):
        #     other_ids       = line_obj.search([('type', '=', detail_run.src_utility.type), ('running_account_id', '=', self.id), ('calculate', '=', True), ('total', '<>', 0), ('utility_id', '=', int(detail_run.src_utility.id))], order="sequence ASC, utility_code ASC, location_code ASC, activity_code ASC")
        #     if other_ids != []:
        #         for other in other_ids:
        #             other.write({
        #                 'total_journal' : other.total_journal + detail_run.var_plus_vh,
        #                 'value'         : (other.total_journal + detail_run.var_plus_vh) / other.total_qty,
        #                 'total'         : other.qty * ((other.total_journal + detail_run.var_plus_vh) / other.total_qty)
        #             })

        change_state_ids = self.env['lhm.vehicle'].search([('account_period_id', '=', self.account_period_id.id)])
        for change_state in change_state_ids:
            change_state.write({'state' : 'done'})


    @api.multi
    def recalculate_machine(self):
        change_state_ids = self.env['lhm.machine'].search([('account_period_id', '=', self.account_period_id.id)])
        for change_state in change_state_ids:
            change_state.write({'state' : 'done'})

    @api.multi
    def create_journal(self):
        journal_obj             = self.env['account.move']
        line_obj                = self.env['running.account.line']
        running_sequence_ids    = self.env['res.running.line'].search([('running_id', '=', self.running_sequence_id.id)], order="sequence ASC")
        for sequence in running_sequence_ids:
            running_utility_ids     = line_obj.search([('doc_id', '=', sequence.doc_id.id)], order="utility_code ASC")
            utility_ids             = list(set([x.utility_id for x in running_utility_ids]))
            for utility in utility_ids:
                line_journal    = []
                total_journal   = 0
                total_qty       = 0
                running_ids     = line_obj.search([('running_account_id', '=', self.id), ('calculate', '=', True), ('total', '<>', 0), ('utility_id', '=', int(utility.id))], order ="sequence ASC, utility_code ASC, location_code ASC, activity_code ASC")
                if running_ids:
                    for running in running_ids:
                        total_journal   += running.total
                        total_qty       += running.qty
                        line_journal.append((0, 0, {
                            'name'                          : "["+ (utility.code or '-') +"] " + (utility.name or '-'),
                            'ref'                           : "Running - " + (utility.code or '-'),
                            'journal_id'                    : sequence.default_journal_id and sequence.default_journal_id.id or False,
                            'date'                          : self.account_period_id.date_stop,
                            'company_id'                    : self.company_id and self.company_id.id or False,
                            'date_maturity'                 : self.account_period_id.date_stop,
                            'account_id'                    : running.dest_account_id and running.dest_account_id.id or False,
                            'plantation_location_type_id'   : running.location_type_id and running.location_type_id.id or False,
                            'plantation_location_id'        : running.location_id and running.location_id.id or False,
                            'plantation_activity_id'        : running.activity_id and running.activity_id.id or False,
                            'debit'                         : running.total,
                            'credit'                        : 0.0,
                            'quantity'                      : running.qty,
                        }))
                    line_journal.append((0, 0, {
                        'name'          : "["+ (utility.code or '-') +"] " + (utility.name or '-'),
                        'ref'           : "Running - " + (utility.code or '-'),
                        'journal_id'    : sequence.default_journal_id and sequence.default_journal_id.id or False,
                        'date'          : self.account_period_id.date_stop,
                        'company_id'    : self.company_id and self.company_id.id or False,
                        'date_maturity' : self.account_period_id.date_stop,
                        'account_id'    : sequence.doc_id.contra_account_id and sequence.doc_id.contra_account_id.id or False,
                        'debit'         : 0.0,
                        'credit'        : total_journal,
                        'quantity'      : total_qty,
                    }))
                journal_value = {
                    'name'          : "/",
                    'ref'           : "Running - " + (utility.code or '-'),
                    'company_id'    : self.company_id.id,
                    'date'          : self.account_period_id.date_stop,
                    'journal_id'    : sequence.default_journal_id.id,
                    'line_ids'      : line_journal,
                }
                new_journal_id  = journal_obj.create(journal_value)
                new_journal_id.post()
                self.write({'move_ids': [(4, new_journal_id.id)]})

    @api.multi
    def project_allocation(self):
        for doc in self:
            doc.move_allocation(doc.state)
        self.write({'state': 'nursery'})
        return True

    @api.multi
    def nursery_allocation(self):
        for doc in self:
            doc.move_allocation(doc.state)
        self.write({'state': 'planting'})
        return True

    @api.multi
    def planting_allocation(self):
        for doc in self:
            doc.move_allocation(doc.state)
        self.write({'state': 'infrastructure'})
        return True

    @api.multi
    def infras_allocation(self):
        for doc in self:
            doc.move_allocation(doc.state)
        self.write({'state': 'other'})
        return True

    @api.multi
    def other_allocation(self):
        for doc in self:
            doc.move_allocation(doc.state)
        self.write({'state': 'closing'})
        return True

    @api.multi
    def closing(self):
        for doc in self:
            doc.move_allocation(doc.state)
        self.write({'state': 'done'})
        return True

    @api.multi
    def restart_running(self):
        for doc in self:
            for move in doc.move_ids:
                move.button_cancel()
                move.unlink()
            doc.write({'state': 'running'})
        return True

    @api.one
    @api.model
    def move_allocation(self, state):
        # running_sequence_ids = self.env['res.running.line'].search([('running_id', '=', self.running_sequence_id.id)], order="sequence ASC")
        running_sequence_ids = self.running_sequence_ids.filtered(lambda x: x.run_state==state)
        # RUNNING FROM JOURNAL ITEMS
        for hapus in self.running_move_line_ids.filtered(lambda l: l.doc_id.id in [x.doc_id.id for x in running_sequence_ids]):
            hapus.unlink()
        for run_seq in running_sequence_ids:
            if run_seq.doc_id and run_seq.doc_id.default_location_type_id:
                self.get_data_from_move_line(run_seq.doc_id, run_seq.doc_id.default_location_type_id)
            elif not run_seq.doc_id.default_location_type_id:
                raise UserError(_('Tipe Dokumen %s tidak memiliki Tipe Lokasi yg ingin di Proses. \nSilahkan diisi terlebih dahulu') %run_seq.doc_id.name)
        # CREATE JOURNAL FROM RUNNING MOVE LINE AFTER RUNNING OF TRANSAFTION LINE
        self.create_journal_from_move_line()

    @api.multi
    def get_data_from_move_line(self, document_type, location_type_id):
        RunningAccountMoveLine = self.env['running.account.move.line']
        if not document_type.account_id and not (location_type_id.general_charge or location_type_id.indirect):
            raise UserError(_('Tipe Dokumen %s tidak memiliki Alokasi Running Account. \nSilahkan diisi terlebih dahulu') %document_type.name)
        # SELECT ALL MOVE LINE
        if location_type_id.general_charge or location_type_id.indirect:
            if not location_type_id.beban_closing_account_id:
                raise UserError(_('Tipe Lokasi %s tidak memiliki Beban Alokasi Closing Account (Default). \
                    \nSilahkan diisi melalui menu Tipe Lokasi') %(location_type_id.code))
            # khusus untuk direct dan indirect cost, tarik smua ledger/account.move.line yg tipenya gc/idc
            # terlepas dari account apapun yg ada di ledger tersebut
            move_lines = self.env['account.move.line'].search([ \
                ('date','>=',self.account_period_id.date_start), \
                ('date','<=',self.account_period_id.date_stop),  \
                ('account_id.user_type_id.include_initial_balance','=',False),  \
                ('plantation_location_type_id', '=', location_type_id.id), \
                ('plantation_location_id', '!=', False)])
        else:
            # sedangkan untuk infras, bibit, planting, dan closing, wajib memiliki account asal
            move_lines = self.env['account.move.line'].search([ \
                ('date','>=',self.account_period_id.date_start), \
                ('date','<=',self.account_period_id.date_stop),  \
                ('account_id', '=', document_type.account_id.id), \
                ('plantation_location_type_id', '=', location_type_id.id), \
                ('plantation_location_id', '!=', False)])
        # KALO OIL PALM HARUS NGAMBIL FILTERNYA BUKAN ACCOUNT

        # IN CASE OF PROJECT
        project_datas = self.env['lhm.project'].search([('location_type_id','=',location_type_id.id), \
            ('location_id','in',[x.plantation_location_id.id for x in move_lines])])
        for project in project_datas:
            if not project.categ_id:
                raise UserError(_('Project %s tidak memiliki Alokasi Tipe Project. \nSilahkan diisi melalui menu Project') %project.code)
            if project.categ_id and not project.categ_id.account_id:
                raise UserError(_('Project %s tidak memiliki Akun didalam Tipe Projectnya (%s). \nSilahkan diisi melalui menu Project') %(project.code, project.categ_id.name))
            if not document_type.contra_account_id:
                raise UserError(_('Running Project akan membutuhkan Akun Alokasi hasil running,\n Sedangkan Tipe Dokumen %s tidak memiliki Alokasi Kontra Running Account. \nSilahkan diisi terlebih dahulu') %document_type.name)
            moves = move_lines.filtered(lambda l: l.plantation_location_id.id==project.location_id.id)
            if not moves:
                continue
            values = {
                'running_account_id': self.id,
                'doc_id': document_type.id,
                'project_id': project.id,
                'location_id': project.location_id.id,
                'location_type_id': project.location_type_id.id,
                'src_account_id': document_type.account_id.id, 
                'dest_account_id': project.categ_id.account_id.id,
                'counterpart_account_id': document_type.contra_account_id.id,
                'total': sum([(x.debit-x.credit) for x in moves]),
            }
            RunningAccountMoveLine.create(values)

        # IN CASE OF NURSERY
        nursery_datas = self.env['lhm.nursery'].search([('location_type_id','=',location_type_id.id), \
            ('location_id','in',[x.plantation_location_id.id for x in move_lines])])
        for ns in nursery_datas:
            if not ns.account_id:
                raise UserError(_('Blok Bibitan %s tidak memiliki Cost/Beban Akun. \nSilahkan diisi melalui menu Blok Bibitan') %(ns.code))
            if not document_type.contra_account_id:
                raise UserError(_('Running Nursery/Pembibitan akan membutuhkan Akun Alokasi hasil running,\n Sedangkan Tipe Dokumen %s tidak memiliki Alokasi Kontra Running Account. \nSilahkan diisi terlebih dahulu') %document_type.name)
            moves = move_lines.filtered(lambda l: l.plantation_location_id.id==ns.location_id.id)
            if not moves:
                continue
            values = {
                'running_account_id': self.id,
                'doc_id': document_type.id,
                'nursery_id': ns.id,
                'location_id': ns.location_id.id,
                'location_type_id': ns.location_type_id.id,
                'src_account_id': document_type.account_id.id, 
                'dest_account_id': ns.account_id.id,
                'counterpart_account_id': document_type.contra_account_id.id,
                'total': sum([(x.debit-x.credit) for x in moves]),
            }
            RunningAccountMoveLine.create(values)

        # IN CASE OF PLANTING
        # BELUM ADA COY

        # IN CASE OF INFRASTRUCTURE
        infrastruktur_datas = self.env['lhm.infrastruktur'].search([('location_type_id','=',location_type_id.id), \
            ('location_id','in',[x.plantation_location_id.id for x in move_lines])])
        for infras in infrastruktur_datas:
            if not infras.beban_infras_account_id:
                raise UserError(_('Infrastruktur %s tidak memiliki Akun Beban Infrastruktur (Default). \
                    \nSilahkan diisi melalui menu Infrastruktur') %(infras.code))
            if not infras.counterpart_expense_account_id:
                raise UserError(_('Infrastruktur %s tidak memiliki Kontra Beban Infrastruktur. \
                    \nSilahkan diisi melalui menu Infrastruktur') %(infras.code))
            moves = move_lines.filtered(lambda l: l.plantation_location_id.id==infras.location_id.id)
            values = {
                'running_account_id': self.id,
                'doc_id': document_type.id,
                'name': '/',
                'infrastruktur_id': infras.id,
                'location_type_id': infras.location_type_id.id,
                'location_id': infras.location_id.id,
                'src_account_id': document_type.account_id.id, 
                'dest_account_id': infras.beban_infras_account_id.id,
                'counterpart_account_id': infras.counterpart_expense_account_id.id,
                'total_journal': sum([(x.debit-x.credit) for x in moves]),
                'total': 0.0,
            }
            if infras.charge_type == 'op' and infras.charge_op_id:
                plant_blocks = self.env['lhm.plant.block'].search([('land_block_id','=',infras.charge_op_id.id)])
                if plant_blocks:
                    for block in plant_blocks:
                        vals = values.copy()
                        if block.status == 'tm':
                            # if block.owner_type=='plasma':
                                # vals['dest_account_id'] = infras.tm_plasma_infras_account_id and infras.tm_plasma_infras_account_id.id or vals['dest_account_id']
                            # else:
                                vals['dest_account_id'] = infras.tm_beban_infras_account_id and infras.tm_beban_infras_account_id.id or vals['dest_account_id']
                        vals['plant_block_id'] = block.id
                        vals['total'] = values['total_journal']*block.koefisien_luas
                        RunningAccountMoveLine.create(vals)
                else:
                    raise UserError(_('Lokasi Blok Tanah %s dari Infrastruktur %s tidak memiliki Blok Tanam') \
                            %(infras.location_id.code, infras.code))
            else:
                values['total'] = values['total_journal']
                RunningAccountMoveLine.create(values)
        
        # IN CASE OF IDC (INDIRECT COST)
        plasma_locatoin_datas = self.env['lhm.location'].search([('owner_type','=','plasma')])
        for location in plasma_locatoin_datas:
            moves = move_lines.filtered(lambda l: l.plantation_location_id.id==location.id)
            if not moves:
                continue
            values = {
                'running_account_id': self.id,
                'doc_id': document_type.id,
                'name': '/',
                'location_type_id': location_type_id.id,
                'location_id': location.id,
                'src_account_id': False, 
                'dest_account_id': location_type_id.beban_closing_account_id.id,
                'counterpart_account_id': document_type.contra_account_id.id,
                'total_journal': sum([(x.debit-x.credit) for x in moves]),
                'total': sum([(x.debit-x.credit) for x in moves]),
            }
            RunningAccountMoveLine.create(values)
        
        # IN CASE OF GC (GENERAL COST)
        plasma_cost_center_datas = self.env['account.cost.center'].search([('owner_type','=','plasma')])
        for cost_center in plasma_cost_center_datas:
            moves = move_lines.filtered(lambda l: l.plantation_location_id.id==cost_center.location_id.id)
            if not moves:
                continue
            values = {
                'running_account_id': self.id,
                'doc_id': document_type.id,
                'name': '/',
                'location_type_id': location_type_id.id,
                'location_id': cost_center.location_id.id,
                'src_account_id': False, 
                'dest_account_id': location_type_id.beban_closing_account_id.id,
                'counterpart_account_id': document_type.contra_account_id.id,
                'total_journal': sum([(x.debit-x.credit) for x in moves]),
                'total': sum([(x.debit-x.credit) for x in moves]),
            }
            RunningAccountMoveLine.create(values)

        # IN CASE OF CLOSING OIL PALM ACTIVITY
        for move_line in move_lines.filtered(lambda l: l.plantation_location_type_id.oil_palm):
            plant_blocks = self.env['lhm.plant.block'].search([('location_type_id','=',location_type_id.id),\
                ('location_id','=',move_line.plantation_location_id.id)])
            if not plant_blocks:
                raise UserError(_('Tidak dapat menemukan Blok Tanam dengan Lokasi %s') % \
                        l.plantation_location_id.id.code)
            if not move_line.plantation_activity_id.beban_closing_account_id or \
                    not move_line.plantation_activity_id.counterpart_closing_account_id or \
                    not move_line.plantation_activity_id.tm_plasma_closing_account_id or \
                    not move_line.plantation_activity_id.tm_plasma_counterpart_closing_account_id or \
                    not move_line.plantation_activity_id.tm_beban_closing_account_id or \
                    not move_line.plantation_activity_id.tm_counterpart_closing_account_id:
                raise UserError(_('Oil Palm Aktivitas %s tidak memiliki Alokasi Akun. \nSilahkan diisi semua Akunnya melalui menu Aktivitas') %(move_line.plantation_activity_id.code))
            values = {
                'running_account_id': self.id,
                'date': move_line.date,
                'doc_id': document_type.id,
                'plant_block_id': plant_blocks[-1].id,    
                'location_id': move_line.plantation_location_id.id,
                'location_type_id': move_line.plantation_location_type_id.id,
                'src_account_id': document_type.account_id.id, 
                'dest_account_id': move_line.plantation_activity_id.beban_closing_account_id.id,
                'counterpart_account_id': move_line.plantation_activity_id.counterpart_closing_account_id.id,
                'total': (move_line.debit-move_line.credit),
            }
            if plant_blocks[-1].status == 'tm':
                if plant_blocks[-1].afdeling_id and plant_blocks[-1].owner_type=='plasma':
                    values['dest_account_id'] = move_line.plantation_activity_id.tm_plasma_closing_account_id.id
                    values['counterpart_account_id'] = move_line.plantation_activity_id.tm_plasma_counterpart_closing_account_id.id
                else:
                    values['dest_account_id'] = move_line.plantation_activity_id.tm_beban_closing_account_id.id
                    values['counterpart_account_id'] = move_line.plantation_activity_id.tm_counterpart_closing_account_id.id
            RunningAccountMoveLine.create(values)

    @api.multi
    def create_journal_from_move_line(self):
        for seq in self.running_sequence_id.line_ids.filtered(lambda x: x.run_state==self.state):
            move_lines = []
            line_grouped = {}
            line_grouped_kontra = {}
            for line in self.running_move_line_ids.filtered(lambda x: x.doc_id and x.doc_id.id==seq.doc_id.id):
                if line.dest_account_id.id not in line_grouped.keys():
                    line_grouped.update({line.dest_account_id.id: 0.0})
                if line.counterpart_account_id.id not in line_grouped_kontra.keys():
                    line_grouped_kontra.update({line.counterpart_account_id.id: 0.0})
                line_grouped[line.dest_account_id.id]+=line.total
                line_grouped_kontra[line.counterpart_account_id.id]+=line.total
            for account_id, total in line_grouped.items():
                move_line_temp = {
                    'name': 'Alokasi: %s'%seq.doc_id.name,
                    'journal_id': seq.default_journal_id and seq.default_journal_id.id or False,
                    'date': self.account_period_id.date_stop,
                    'company_id': self.company_id and self.company_id.id or False,
                    'account_id': account_id,
                    'debit': total>0 and total or 0.0,
                    'credit': total<0 and abs(total) or 0.0,
                }
                move_lines.append((0,0,move_line_temp))
            for account_id, total in line_grouped_kontra.items():
                move_line_temp = {
                    'name': 'Kontra Alokasi: %s'%seq.doc_id.name,
                    'journal_id': seq.default_journal_id and seq.default_journal_id.id or False,
                    'date': self.account_period_id.date_stop,
                    'company_id': self.company_id and self.company_id.id or False,
                    'account_id': account_id,
                    'debit': total<0 and abs(total) or 0.0,
                    'credit': total>0 and total or 0.0,
                }
                move_lines.append((0,0,move_line_temp))
            if move_lines:
                move_values = {
                    'name'          : "/",
                    'ref'           : "Running %s"%seq.doc_id.name,
                    'company_id'    : self.company_id.id,
                    'date'          : self.account_period_id.date_stop,
                    'journal_id'    : seq.default_journal_id.id,
                    'line_ids'      : move_lines,
                }
                move_id  = self.env['account.move'].create(move_values)
                move_id.post()
                self.write({'move_ids': [(4, move_id.id)]})

class running_account_sequence(models.Model):
    _name           = 'running.account.sequence'
    _description    = 'Running Account Sequence'

    name                = fields.Char("Name", related="doc_id.name", readonly=True)
    sequence            = fields.Integer("Sequence")
    doc_id              = fields.Many2one(comodel_name="res.doc.type", string="Document Type")
    running_account_id  = fields.Many2one(comodel_name="running.account", string="Running Account", ondelete="cascade")
    run_state           = fields.Selection(selection=_RUNNING_SELECTION, string='Run State', default='running')

class running_account_line(models.Model):
    _name           = 'running.account.line'
    _description    = 'Running Account Line'
    _order          = 'sequence ASC, utility_code ASC, location_code ASC, activity_code ASC'

    name                = fields.Char("Name", readonly=True)
    sequence            = fields.Integer("Sequence")
    doc_id              = fields.Many2one(comodel_name="res.doc.type", string="Document Type")
    type                = fields.Selection([('vh', 'VH'), ('ws', 'WS'), ('ma', 'MA'),], string='Type')
    uom_performance     = fields.Selection([('km', 'KM'), ('hm', 'HM')], string='Satuan', readonly=True, related="utility_id.uom_performance", store=True)
    date                = fields.Date("Tanggal")
    value               = fields.Float("Value")
    qty                 = fields.Float("Qty")
    total_qty           = fields.Float("Total Qty")
    total_journal       = fields.Float("Total Journal")
    total               = fields.Float("Total")
    total_other         = fields.Float("Total Other")
    var_plus            = fields.Float("Var+")
    var_minus           = fields.Float("Var-")
    calculate           = fields.Boolean("Calc")
    recalculate         = fields.Boolean("ReCalc")
    src_account_id      = fields.Many2one(comodel_name="account.account", string="Source", ondelete="restrict")
    dest_account_id     = fields.Many2one(comodel_name="account.account", string="Destination", ondelete="restrict")
    utility_id          = fields.Many2one(comodel_name="lhm.utility", string="Utility", ondelete="restrict")
    other_utility_id    = fields.Many2one(comodel_name="lhm.utility", string="Other Utility", ondelete="restrict")
    location_type_id    = fields.Many2one(comodel_name="lhm.location.type", string="Tipe", ondelete="restrict")
    location_id         = fields.Many2one(comodel_name="lhm.location", string="Lokasi", ondelete="restrict")
    activity_id         = fields.Many2one(comodel_name="lhm.activity", string="Aktivitas", ondelete="restrict")
    running_account_id  = fields.Many2one(comodel_name="running.account", string="Running Account", ondelete="cascade")
    location_code       = fields.Char(related="location_id.code", store=True)
    activity_code       = fields.Char(related="activity_id.code", store=True)
    utility_code        = fields.Char(related="utility_id.code", store=True)
    other_utility_code  = fields.Char(related="other_utility_id.code", store=True)
    other_utility_type  = fields.Selection([('vh', 'VH'), ('ws', 'WS'), ('ma', 'MA'),], related="other_utility_id.type", store=True, string="X")

class running_account_line_detail(models.Model):
    _name           = 'running.account.line.detail'
    _description    = 'Running Account Line Detail'
    _order          = 'sequence ASC'

    name                = fields.Char("Name", readonly=True, related="activity_id.name", store=True)
    sequence            = fields.Integer("Sequence")
    activity_id         = fields.Many2one(comodel_name="lhm.activity", string="Aktivitas", ondelete="restrict")
    var_plus            = fields.Float("Var+")
    var_plus_vh         = fields.Float("VarVH")
    var_minus           = fields.Float("Var-")
    qty_minus           = fields.Float("Qty-")
    src_utility         = fields.Many2one(comodel_name="lhm.utility", string="Utility Source", ondelete="restrict")
    dest_utility        = fields.Many2one(comodel_name="lhm.utility", string="Utility Destination", ondelete="restrict")
    running_line_id     = fields.Many2one(comodel_name="running.account.line", string="Running Account Line", ondelete="cascade")
    running_account_id  = fields.Many2one(comodel_name="running.account", string="Running Account", ondelete="cascade")

class running_account_move_line(models.Model):
    _inherit        = 'running.account.line'
    _name           = 'running.account.move.line'
    _description    = 'Running Account from Journal Items'

    running_account_id = fields.Many2one(comodel_name="running.account", string="Running Account", ondelete="cascade")
    infrastruktur_id = fields.Many2one('lhm.infrastruktur', 'Infras')
    project_id = fields.Many2one('lhm.project', 'Project')
    # tipe lokasi : sdh ada di parent
    # src account : sdh ada di parent
    # total jurnal : sdh ada di parent
    charge_type = fields.Selection(selection=[('op', 'Oil Palm'), ('gc', 'General Charge'), ('idc', 'Indirect Cost')], related='infrastruktur_id.charge_type', string='Tipe Pembebanan')
    # Untuk Penghitungan Beban Oil Palm
    charge_op_id = fields.Many2one('lhm.land.block', related='infrastruktur_id.charge_op_id', string='Pembebanan OP')
    plant_block_id = fields.Many2one('lhm.plant.block', string='Blok Tanam')
    status = fields.Selection(selection=[('tm','Tanaman Menghasilkan'),('tbm','Tanaman Belum Menghasilkan')], related='plant_block_id.status', string='Status Blok')
    planted = fields.Float(related='plant_block_id.planted', string='Area ditanam')
    koefisien_luas = fields.Float(related='plant_block_id.koefisien_luas', string='Koefisien Luasan')

    # Untuk Penghitungan Beban Direct Cost
    charge_gc_id = fields.Many2one('account.cost.center', related='infrastruktur_id.charge_gc_id', string='Pembebanan GC')
    # Untuk Penghitungan Beban Indirect Cost
    charge_idc_id = fields.Many2one('res.afdeling', related='infrastruktur_id.charge_idc_id', string='Pembebanan IDC')
    # dest_account_id : sdh ada di parent
    # value : sdh ada di parent
    counterpart_account_id = fields.Many2one('account.account', string='Kontra Akun')
