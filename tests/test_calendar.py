#!/usr/bin/env python

import unittest
import gcalbridge
from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import HttpMock, HttpMockSequence
from httplib2 import Http
from .utils import datafile, dataread, get_default_config
from testfixtures import LogCapture


class CalendarTest(unittest.TestCase):
    def setUp(self):
        build('calendar', 'v3')
        self.conf = get_default_config()
        self.domain = gcalbridge.domain.Domain(
            "foo.com",
            {
                "account": "foo@foo.com"
            },
            authorize=False
        )
        self.domains = {
            "foo.com": self.domain
        }
        self.calendar_conf = {
            "url": "foo.com_1@resource.calendar.google.com",
            "domain": "foo.com"
        }

    def tearDown(self):
        pass

    def test_basic_calendar(self):
        self.domain.http = HttpMock(datafile("calendarList.json"))
        c = gcalbridge.calendar.Calendar(self.calendar_conf, self.domains)

    def test_calendar_missing_domain(self):
        with self.assertRaises(gcalbridge.errors.BadConfigError):
            c = gcalbridge.calendar.Calendar(self.calendar_conf, domains={})

    def test_calendar_missing_url(self):
        self.domain.http = HttpMock(datafile("calendarList-empty.json"))
        with self.assertRaises(gcalbridge.errors.BadConfigError):
            c = gcalbridge.calendar.Calendar(self.calendar_conf, self.domains)

    def test_calendar_http_error(self):
        with LogCapture() as l:
            self.domain.http = HttpMock(datafile("calendarList.json"), {
                "status": '404'})
            with self.assertRaises(HttpError):
                c = gcalbridge.calendar.Calendar(self.calendar_conf, self.
                    domains)

    def test_calendar_update_events(self):
        self.domain.http = HttpMockSequence([
            ({'status': '200'}, dataread("calendarList.json")),
            ({'status': '200'}, dataread("calendar-events.json")),
            ({'status': '200'}, dataread("calendar-events-empty.json")),
            ({'status': '200'}, dataread("calendar-events.json")),
            ({'status': '200'}, dataread("calendar-events-empty.json"))
              ])
        c = gcalbridge.calendar.Calendar(self.calendar_conf, self.domains)
        self.assertEqual(c.update_events(), 5)
        # A second call should be idempotent
        self.assertEqual(c.update_events(), 0)
