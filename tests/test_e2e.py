#!/usr/bin/env python

import unittest
import os
import datetime
import time

from random import randint
from apiclient.errors import HttpError

import gcalbridge
from utils import *
import logging

logging.basicConfig(level=logging.DEBUG)

@unittest.skipUnless(os.path.isfile(datafile("client_id.json")),
                     "Only run on a machine with valid secrets.")
class EndToEndTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = gcalbridge.Config(datafile('config_e2e.json'))

    def setUp(self):
        self.calendars = EndToEndTest.config.setup()
        self.config = EndToEndTest.config
        self.cal = list(self.calendars.values())[0]
        self.created_events = []

    def tearDown(self):
        for (svc, cid, evt) in self.created_events:
            try:
                svc.events().delete(calendarId=cid, eventId=evt['id']).execute()
            except HttpError:
                pass
    @property
    def _cals(self):
        return self.cal.calendars

    def test_e2e_working(self):
        for c in self._cals:
            self.assertIsInstance(c, gcalbridge.calendar.Calendar)
            self.assertIsInstance(c.domain, gcalbridge.domain.Domain)
            # self.assertEqual(len(c.events), 0)
        self.cal.sync()
        for c in self._cals:
            self.assertGreater(len(c.events), 0)
            for e in c.events.itervalues():
                self.assertIsInstance(e, gcalbridge.calendar.Event)
            self.assertIsNone(c.batch)
            self.assertEqual(c.batch_count, 0)
            self.assertIsNotNone(c.calendar_metadata)

    def test_create_new_event(self):
        self.cal.sync()
        ec = {}
        for c in self._cals:
            ec[c.url] = len(c.events)
        c = self._cals[0]
        key = randint(100000,1000000)
        new_event = c.service.events().quickAdd(calendarId=c.url,
                text="Testing %d at AutoTestLoc tomorrow from 10am-10:30am" % key
                                                ).execute()
        self.created_events.append((c.service, c.url, new_event))
        self.assertEqual(new_event['status'], "confirmed")
        self.cal.sync()
        for c in self._cals:
            self.assertEqual(len(c.events), ec[c.url] + 1)
            for other_c in self._cals:
                for (eid, e) in c.events.iteritems():
                    self.assertIsInstance(e, gcalbridge.calendar.Event)
                    if not e.active(): continue
                    self.assertEqual(cmp(e, other_c.events[eid]), 0)

        c.service.events().patch(calendarId=c.url,eventId=new_event['id'],
                                 body={"location": "NewAutoTestLoc"}).execute()
        self.cal.sync()
        for c in self._cals:
            self.assertEqual(len(c.events), ec[c.url] + 1)
            e = c.events[new_event['id']]
            self.assertIsInstance(e, gcalbridge.calendar.Event)
            self.assertEqual(e['location'], "NewAutoTestLoc")

        c.service.events().patch(calendarId=c.url,eventId=new_event['id'],
                                 body={"status": "cancelled"}).execute()
        self.cal.sync()
        for c in self._cals:
            self.assertEqual(len(c.events), ec[c.url] + 1)
            e = c.events[new_event['id']]
            self.assertIsInstance(e, gcalbridge.calendar.Event)
            self.assertEqual(e['status'], "cancelled")
            self.assertFalse(e.active())
