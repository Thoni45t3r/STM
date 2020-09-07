# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

import googleapiclient.discovery as discovery
import googleapiclient.errors as google_error
import time
import datetime
import os
import logging
from httplib2 import Http
from dateutil.relativedelta import relativedelta
from odoo import models, fields, tools, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class HrPublicHolidays(models.Model):
    _inherit        = 'hr.holidays.public'
    _description    = 'Public Holidays Inherit'

    @api.multi
    @api.depends('year')
    def _compute_dates(self):
        for holiday in self:
            if holiday.year:
                holiday.date_from = time.strftime(str(holiday.year) + '-01-01')
                holiday.date_to = time.strftime(str(holiday.year) + '-12-31')
            else:
                holiday.date_from = False
                holiday.date_to = False

    country_id      = fields.Many2one(comodel_name='res.country', string='Country', default=lambda self: self.env.user.company_id.country_id.id or False)
    company_id      = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    use_saturday    = fields.Boolean("Sabtu Libur")
    use_sunday      = fields.Boolean("Minggu Libur")
    use_google_cal  = fields.Boolean("Google Calendar")
    date_from       = fields.Date("Date Start", compute=_compute_dates, store=True)
    date_to         = fields.Date("Date End", compute=_compute_dates, store=True)
    google_error    = fields.Text("Pesan Error")

    @api.multi
    def generate_holiday(self):
        self.google_error = ""
        for line in self.line_ids:
            line.unlink()

        days_of_week    = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu', ]
        if self.year:
            date_from       = fields.Date.from_string(self.date_from)
            date_to         = fields.Date.from_string(self.date_to)
            list_dates      = []
            list_liburan    = []
            seq_sunday      = 1
            seq_saturday    = 1
            dates           = date_from
            if self.use_google_cal:
                service     = discovery.build('calendar', 'v3', developerKey=(self.company_id.cal_api_key or 'X'), cache_discovery=False)
                try:
                    eventsResult        = service.events().list(timeMin=self.date_from + 'T00:00:00-00:00', timeMax=self.date_to + 'T00:00:00-00:00', calendarId=(self.company_id.cal_id_google or ''), singleEvents=True, orderBy='startTime').execute()
                    events              = eventsResult.get('items', [])
                except google_error.HttpError, error:
                    if error.resp['status'] in ('400', '401', '410'):
                        self.google_error = "Error : " +error.resp['status'] + """\nGoogle API Keys are not properly configured or something wrong with server.\nIf you want to get a national holiday automatically.\nPlease contact the Administrator to configuration Google API Keys"""
                        events = []
                    elif error.resp['status'] in ('404'):
                        self.google_error = "Error : " +error.resp['status'] + """\nCalendarId are not properly configured or something wrong with server.\nIf you want to get a national holiday automatically.\nPlease contact the Administrator to configuration CalendarId"""
                        events = []
                    else:
                        self.google_error = "Error : " +error.resp['status']
                        events = []

                for event in events:
                    date_national   = event['start'].get('dateTime', event['start'].get('date'))
                    values          = (0, 0, {'name': event['summary'], 'date': str(date_national), 'is_national': True})
                    if date_national not in list_liburan:
                        list_dates.append(values)
                    list_liburan.append(str(date_national))

            while dates < date_to:
                if self.use_sunday:
                    if dates.weekday() == 6:
                        if str(dates) not in list_liburan:
                            values = (0, 0, {'name': days_of_week[dates.weekday()] +" ke " +str(seq_sunday), 'date': str(dates), 'is_weekend' : True})
                            list_dates.append(values)
                        seq_sunday += 1
                if self.use_saturday:
                    if dates.weekday() == 5:
                        if str(dates) not in list_liburan:
                            values = (0, 0, {'name': days_of_week[dates.weekday()] +" ke " +str(seq_saturday), 'date': str(dates), 'is_weekend' : True})
                            list_dates.append(values)
                        seq_saturday += 1
                dates = dates + relativedelta(days=1)
            self.line_ids = list_dates



class HrPublicHolidaysLine(models.Model):
    _inherit        = 'hr.holidays.public.line'
    _description    = 'Public Holidays Lines Inherit'

    is_weekend  = fields.Boolean("Libur Weekend")
    is_national = fields.Boolean("Libur Nasional")


