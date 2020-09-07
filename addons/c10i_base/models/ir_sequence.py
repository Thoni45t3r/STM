# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from datetime import datetime, timedelta
import logging
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class IrSequence(models.Model):
    _inherit    = 'ir.sequence'

    def get_next_char(self, number_next):
        def _interpolate(s, d):
            return (s % d) if s else ''

        def _interpolation_dict():
            now = range_date = effective_date = datetime.now(pytz.timezone(self._context.get('tz') or 'UTC'))
            if self._context.get('ir_sequence_date'):
                effective_date = datetime.strptime(self._context.get('ir_sequence_date'), '%Y-%m-%d')
            if self._context.get('ir_sequence_date_range'):
                range_date = datetime.strptime(self._context.get('ir_sequence_date_range'), '%Y-%m-%d')

            sequences = {
                'year': '%Y', 'month': '%m', 'day': '%d', 'y': '%y', 'doy': '%j', 'woy': '%W',
                'weekday': '%w', 'h24': '%H', 'h12': '%I', 'min': '%M', 'sec': '%S', 'month_roman': '%m',
            }
            res = {}
            for key, format in sequences.iteritems():
                res[key] = effective_date.strftime(format)
                res['range_' + key] = range_date.strftime(format)
                res['current_' + key] = now.strftime(format)

            return res

        d = _interpolation_dict()
        if d.get('month_roman', False):
            if d.get('month_roman', False) == '01':
                roman_month = str('I')
            elif d.get('month_roman', False) == '02':
                roman_month = str('II')
            elif d.get('month_roman', False) == '03':
                roman_month = str('III')
            elif d.get('month_roman', False) == '04':
                roman_month = str('IV')
            elif d.get('month_roman', False) == '05':
                roman_month = str('V')
            elif d.get('month_roman', False) == '06':
                roman_month = str('VI')
            elif d.get('month_roman', False) == '07':
                roman_month = str('VII')
            elif d.get('month_roman', False) == '08':
                roman_month = str('VIII')
            elif d.get('month_roman', False) == '09':
                roman_month = str('IX')
            elif d.get('month_roman', False) == '10':
                roman_month = str('X')
            elif d.get('month_roman', False) == '11':
                roman_month = str('XI')
            elif d.get('month_roman', False) == '12':
                roman_month = str('XII')
            else:
                roman_month = d.get('month', '')
            d['month_roman'] = roman_month
        try:
            interpolated_prefix = _interpolate(self.prefix, d)
            interpolated_suffix = _interpolate(self.suffix, d)
        except ValueError:
            raise UserError(_('Invalid prefix or suffix for sequence \'%s\'') % (self.get('name')))
        return interpolated_prefix + '%%0%sd' % self.padding % number_next + interpolated_suffix
