# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class CurrencyRevaluation(models.TransientModel):
    _name = "currency.revaluation"
    _description = "Currency Revaluation"

    @api.model
    def _get_default_revaluation_date(self):
        """
        Get last date of previous fiscalyear
        """
        cp = self.env.user.company_id
        # find previous fiscalyear
        current_date = date.today().strftime('%Y-%m-01')
        prev_period_date = datetime.strptime(current_date,'%Y-%m-%d') - relativedelta(days=1)
        return prev_period_date.strftime('%Y-%m-%d')

    @api.model
    def _get_default_journal_id(self):
        """
        Get default journal if one is defined in company settings
        """
        cp = self.env.user.company_id

        journal = cp.default_currency_reval_journal_id
        return journal and journal.id or False

    revaluation_date = fields.Date('Revaluation Date', required=True, default=_get_default_revaluation_date)
    rate_date = fields.Date('Rate Date', required=True)
    journal_id = fields.Many2one('account.journal', required=True, domain=[('type', '=', 'general')], 
        help="You can set the default journal in company settings.", default=_get_default_journal_id)
    label = fields.Char('Entry Description', required=True, 
        help="This label will be inserted in entries description. You can use %(account)s, %(currency)s"
            " and %(rate)s keywords.", 
        default="%(currency)s (%(account)s) %(rate)s currency revaluation")

    @api.model
    def _compute_unrealized_currency_gl(self, currency_id, balances):
        """
        Update data dict with the unrealized currency gain and loss
        plus add 'currency_rate' which is the value used for rate in
        computation

        @param int currency_id: currency to revaluate
        @param dict balances: contains foreign balance and balance

        @return: updated data for foreign balance plus rate value used
        """
        context = self._context

        Currency = self.env['res.currency']
        # type_id = self.currency_type and self.currency_type.id or False

        # Compute unrealized gain loss
        ctx_rate = context.copy()
        ctx_rate['date'] = self.rate_date
        company_currency = self.journal_id.company_id.currency_id

        currency = Currency.with_context(ctx_rate).browse(currency_id)

        foreign_balance = adjusted_balance = balances.get(
            'foreign_balance', 0.0)
        balance = balances.get('balance', 0.0)
        unrealized_gain_loss = 0.0
        if foreign_balance:
            ctx_rate['revaluation'] = True
            # adjusted_balance = Currency.compute(
            #     cr, uid, currency_id, company_currency_id, foreign_balance,
            #     currency_rate_type_to=type_id,
            #     context=ctx_rate)
            adjusted_balance = currency.with_context(ctx_rate).compute(foreign_balance, company_currency)
            unrealized_gain_loss = adjusted_balance - balance
            # revaluated_balance =  balance + unrealized_gain_loss
        else:
            if balance:
                if currency_id != company_currency.id:
                    unrealized_gain_loss = 0.0 - balance
                else:
                    unrealized_gain_loss = 0.0
            else:
                unrealized_gain_loss = 0.0
        return {'unrealized_gain_loss': unrealized_gain_loss,
                'currency_rate': currency.rate,
                'revaluated_balance': adjusted_balance}

    @api.model
    def _format_label(self, account_id, currency_id, rate):
        """
        Return a text with replaced keywords by values

        @param str text: label template, can use
            %(account)s, %(currency)s, %(rate)s
        @param int account_id: id of the account to display in label
        @param int currency_id: id of the currency to display
        @param float rate: rate to display
        """
        Account = self.env['account.account']
        Currency = self.env['res.currency']
        account = Account.browse(account_id)
        currency = Currency.browse(currency_id)
        data = {'account': account.code or False,
                'currency': currency.name or False,
                'rate': rate or False}
        return self.label % data

    @api.model
    def _write_adjust_balance(self, account_id, currency_id, partner_id, amount, sums, label):
        """
        Generate entries to adjust balance in the revaluation accounts

        @param account_id: ID of account to be reevaluated
        @param amount: Amount to be written to adjust the balance
        @param label: Label to be written on each entry
        @param form: Wizard browse record containing data

        @return: ids of created move_lines
        """
        context = self._context

        def create_move():
            base_move = {'name': label,
                         'journal_id': self.journal_id.id,
                         # 'period_id': period.id,
                         'date': self.revaluation_date}
            return Move.create(base_move)

        def create_move_line(move_id, line_data, sums, label):
            base_line = {'name': label,
                         'partner_id': partner_id,
                         'currency_id': currency_id,
                         'amount_currency': 0.0,
                         'date': self.revaluation_date,
                         }
            base_line.update(line_data)
            # we can assume that keys should be equals columns name + gl_
            # but it was not decide when the code was designed. So commented
            # code may sucks:
            # for k, v in sums.items():
            #    line_data['gl_' + k] = v
            base_line['gl_foreign_balance'] = sums.get('foreign_balance', 0.0)
            base_line['gl_balance'] = sums.get('balance', 0.0)
            base_line['gl_revaluated_balance'] = sums.get(
                'revaluated_balance', 0.0)
            base_line['gl_currency_rate'] = sums.get('currency_rate', 0.0)
            return MoveLine.with_context(check_move_validity=False).create(base_line)
        if partner_id is None:
            partner_id = False
        Account = self.env['account.account']
        Move = self.env['account.move']
        MoveLine = self.env['account.move.line']
        # period_obj = self.env['account.period']
        company = self.journal_id.company_id or self.env.user.company_id
        # period_ids = period_obj.search(
        #     cr, uid,
        #     [('date_start', '<=', form.revaluation_date),
        #      ('date_stop', '>=', form.revaluation_date),
        #      ('company_id', '=', company.id),
        #      ('special', '=', False)],
        #     limit=1,
        #     context=context)
        # if not period_ids:
        #     raise osv.except_osv(_('Error!'),
        #                          _('There is no period for company %s on %s'
        #                            % (company.name, form.revaluation_date)))
        # period = period_obj.browse(cr, uid, period_ids[0], context=context)
        created_ids = []
        # over revaluation
        account = Account.browse(account_id)
        if amount >= 0.01:
            if company.revaluation_gain_account_id:
                move = create_move()
                # Create a move line to Debit account to be revaluated
                line_data = {'debit': amount,
                             'move_id': move.id,
                             'account_id': account_id,
                             }
                created_ids.append(create_move_line(move.id, line_data, sums, label))
                # Create a move line to Credit revaluation gain account
                line_data = {
                    'credit': amount,
                    'account_id': company.revaluation_gain_account_id.id,
                    'move_id': move.id,
                }
                # label = 'Gain Income from Revaluation Account (%s) %s'%(account.code, account.name)
                label = 'Gain Income from Revaluation Account %s'%label
                created_ids.append(create_move_line(move.id, line_data, sums, label))
        # under revaluation
        elif amount <= -0.01:
            amount = -amount
            if company.revaluation_loss_account_id:
                move = create_move()
                # Create a move line to Debit revaluation loss account
                line_data = {
                    'debit': amount,
                    'move_id': move.id,
                    'account_id': company.revaluation_loss_account_id.id,
                }
                # label = 'Gain Income from Revaluation Account (%s) %s'%(account.code, account.name)
                label = 'Loss Expense from Revaluation Account %s'%label
                created_ids.append(create_move_line(move.id, line_data, sums, label))
                # Create a move line to Credit account to be revaluated
                line_data = {
                    'credit': amount,
                    'move_id': move.id,
                    'account_id': account_id,
                }
                created_ids.append(create_move_line(move.id, line_data, sums, self.label))
        return created_ids

    @api.model
    def _write_adjust_balance_for_reconcile_account(self, dict_moves, dict_gain_loss, label):
        """
        Generate entries to adjust balance in the revaluation accounts

        @param account_id: ID of account to be reevaluated
        @param amount: Amount to be written to adjust the balance
        @param label: Label to be written on each entry
        @param form: Wizard browse record containing data

        @return: ids of created move_lines
        """
        Move = self.env['account.move']
        MoveLine = self.env['account.move.line']
        
        context = self._context
        company = self.journal_id.company_id or self.env.user.company_id
        created_ids = []

        move = Move.create({'name': label,
                         'journal_id': self.journal_id.id,
                         'date': self.revaluation_date})
        rec_list_ids = []
        for move_line, move_line_reval in dict_moves.items():
            move_line_reval.update({'move_id': move.id})
            new_move_line = MoveLine.with_context(check_move_validity=False).create(move_line_reval)
            created_ids.append(new_move_line)

        for key, move_gain_loss in dict_gain_loss.items():
            partner, currency = key
            gain_or_loss = move_gain_loss['debit'] - move_gain_loss['credit']
            if gain_or_loss>0.0:
                move_gain_loss['debit'] = gain_or_loss
                move_gain_loss['credit'] = 0.0
                move_gain_loss['account_id'] = company.revaluation_loss_account_id.id
                label = 'Loss Expense from %s %s %s'%(label, partner.name, currency.rate)
            else:
                move_gain_loss['debit'] = 0.0
                move_gain_loss['credit'] = abs(gain_or_loss)
                label = 'Gain Income from %s %s %s'%(label, partner.name, currency.rate)
                move_gain_loss['account_id'] = company.revaluation_gain_account_id.id
            
            move_gain_loss['name'] = label
            move_gain_loss.update({'move_id': move.id})
            new_move_line = MoveLine.with_context(check_move_validity=False).create(move_gain_loss)
            created_ids.append(new_move_line)
        return created_ids

    @api.multi
    def revaluate_currency(self, context=None):
        """
        Compute unrealized currency gain and loss and add entries to
        adjust balances

        @return: dict to open an Entries view filtered on generated move lines
        """

        def _remove_noise_in_o2m():
            """if the line is partially reconciled, then we must pay attention to display it only once and
                in the good o2m.
                This function returns True if the line is considered as noise and should not be displayed
            """
            if line.matched_debit_ids:
                if line.amount_residual_currency <= 0:
                    return True
            return False


        self.ensure_one()
        context = self._context
        Account = self.env['account.account']
        Currency = self.env['res.currency']
        Move = self.env['account.move']
        MoveLine = self.env['account.move.line']
        
        company = self.journal_id.company_id or self.env.user.company_id
        currency_id = company.currency_id.id
        if (not company.revaluation_loss_account_id and not company.revaluation_gain_account_id):
            raise UserError(
                _("No revaluation or provision account are defined"
                  " for your company.\n"
                  "You must specify at least one provision account or"
                  " a couple of provision account."))
        created_ids = []
        # Search for accounts Balance Sheet to be eevaluated
        # on those criterions
        # - deferral method of account type is not None
        account_ids = Account.search([('user_type_id.include_initial_balance', '=', True),
            ('currency_revaluation', '=', True)])
        if not account_ids:
            raise UserError(
                _("No account to be revaluated found. "
                  "Please check 'Allow Currency Revaluation' "
                  "for at least one account in account form."))
        bankandcash_account_ids = account_ids.filtered(lambda x: x.user_type_id.type=='liquidity')
        reconcile_account_ids = account_ids.filtered(lambda x: x.user_type_id.type in ['receivable','payable'] and x.reconcile==True)
        account_ids = account_ids.filtered(lambda x: x.id not in bankandcash_account_ids.ids+reconcile_account_ids.ids)
        
        ctx_account = context.copy()
        if bankandcash_account_ids:
            # Get balance sums
            # account_sums = Account.foreign_currency_balance_bankandcash(
            account_sums = bankandcash_account_ids.with_context(ctx_account).foreign_currency_balance(self.revaluation_date)
            for account_id, account_tree in account_sums.iteritems():
                for currency_id, sums in account_tree.iteritems():
                    if not sums['balance']:
                        continue
                    # Update sums with compute amount currency balance
                    diff_balances = self.with_context(ctx_account)._compute_unrealized_currency_gl(
                        currency_id, sums)
                    account_sums[account_id][currency_id].\
                        update(diff_balances)
            # Create entries only after all computation have been done
            for account_id, account_tree in account_sums.iteritems():
                for currency_id, sums in account_tree.iteritems():
                    adj_balance = sums.get('unrealized_gain_loss', 0.0)
                    if not adj_balance:
                        continue

                    rate = sums.get('currency_rate', 0.0)
                    label = self._format_label(account_id, currency_id, rate)

                    # Write an entry to adjust balance
                    new_ids = self._write_adjust_balance(account_id, currency_id, 
                        False, adj_balance, sums, label)
                    created_ids.extend(new_ids)

        if reconcile_account_ids:
            # Get balance sums
            for account in reconcile_account_ids:
                move_line_ids = MoveLine.search([('reconciled', '=', False),
                    ('account_id', '=', account.id),('currency_id','!=',False),
                    ('date','<=',self.revaluation_date)])
                dict_gain_loss, dict_moves = {}, {}
                label = "Revaluation Account (%s) %s" % (account.code, account.name)
                for line in move_line_ids:
                    if _remove_noise_in_o2m():
                        continue
                    move_line_reval, move_line_reval_ct = line.compute_revaluations(self.revaluation_date, self.rate_date)
                    if not move_line_reval:
                        continue
                    # unrealized_gain_loss = adjusted_balance - balance
                    # adj_balance = Currency.round(line_currency, unrealized_gain_loss)
                    # line_sums = {
                    #     'revaluated_balance' : adjusted_balance,
                    #     'unrealized_gain_loss' : unrealized_gain_loss,
                    #     'currency_rate' : line_currency.rate,
                    # }
                    key = line.partner_id, line.currency_id
                    if key not in dict_gain_loss.keys():
                        partner, line_currency = key
                        currency = Currency.with_context(date=self.rate_date).browse(line_currency.id)
                        key = partner, currency
                        dict_gain_loss.update({key: move_line_reval_ct})
                    else:
                        dict_gain_loss[key]['debit'] += move_line_reval_ct['debit']
                        dict_gain_loss[key]['credit'] += move_line_reval_ct['credit']
                        dict_gain_loss[key]['gl_balance'] += move_line_reval_ct['gl_balance']
                        dict_gain_loss[key]['gl_revaluated_balance'] += move_line_reval_ct['gl_revaluated_balance']
                        dict_gain_loss[key]['gl_foreign_balance'] += move_line_reval_ct['gl_foreign_balance']

                    dict_moves.update({line: move_line_reval})
                new_ids = self._write_adjust_balance_for_reconcile_account(dict_moves, dict_gain_loss, label)
                created_ids.extend(new_ids)

        if account_ids:
            # Get balance sums
            account_sums = account_ids.with_context(ctx_account).foreign_currency_balance(self.revaluation_date)
            for account_id, account_tree in account_sums.iteritems():
                for currency_id, currency_tree in account_tree.iteritems():
                    for partner_id, sums in currency_tree.iteritems():
                        if not sums['balance']:
                            continue
                        # Update sums with compute amount currency balance
                        diff_balances = self.with_context(ctx_account)._compute_unrealized_currency_gl(
                            currency_id, sums)
                        account_sums[account_id][currency_id][partner_id].\
                            update(diff_balances)
            # Create entries only after all computation have been done
            for account_id, account_tree in account_sums.iteritems():
                for currency_id, currency_tree in account_tree.iteritems():
                    for partner_id, sums in currency_tree.iteritems():
                        adj_balance = sums.get('unrealized_gain_loss', 0.0)
                        if not adj_balance:
                            continue

                        rate = sums.get('currency_rate', 0.0)
                        label = self._format_label(account_id, currency_id, rate)

                        # Write an entry to adjust balance
                        new_ids = self._write_adjust_balance(account_id, currency_id,
                            partner_id, adj_balance, sums, label)
                        created_ids.extend(new_ids)

        if created_ids:
            return {'domain': "[('id', 'in', %s)]" % [x.id for x in created_ids],
                    'name': _("Created Revaluation Lines"),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'auto_search': True,
                    'res_model': 'account.move.line',
                    'view_id': False,
                    'search_view_id': False,
                    'type': 'ir.actions.act_window'}
        else:
            raise UserError(_("Account to be revaluate is not found. No accounting entry have been posted."))
CurrencyRevaluation()