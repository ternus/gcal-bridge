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
from pprint import pformat

FORMAT = "[%(levelname)-8s:%(filename)-15s:%(lineno)4s: %(funcName)20.20s ] %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)

@unittest.skipUnless(os.path.isfile(datafile("client_id.json")),
                     "Only run on a machine with valid secrets.")
class EndToEndTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = gcalbridge.Config(datafile('config_e2e.json'))
        cals = cls.config.setup()
        for cal in cals.values():
            cal.sync()
            for c in cal.calendars:
                for e in c.events.values():
                    if e.active():
                        e['status'] = 'cancelled'
                c.push_events()

    def setUp(self):
        self.calendars = EndToEndTest.config.setup()
        self.config = EndToEndTest.config
        self.cal = list(self.calendars.values())[0]
        self.created_events = []

    def tearDown(self):
        for (svc, cid, evt) in self.created_events:
            try:
                svc.events().patch(calendarId=cid, eventId=evt['id'], body={
                    'status': 'cancelled'
                }).execute()
                # svc.events().delete(calendarId=cid,
                # eventId=evt['id']).execute()
            except HttpError:
                pass
        self.cal.sync()

    @property
    def _cals(self):
        return self.cal.calendars

    def tag(self):
        return str(randint(100000000, 1000000000))

    def wait_for_backend(self, cal=None):
        if cal is None:
            time.sleep(3)
        else:
            start = time.time()
            e = cal.service.events().list(calendarId=cal.url).execute().get('etag')
            while ((e == cal.service.events().list(calendarId=cal.url).execute().get('etag')) and
                   (time.time() - start) < 3):
                time.sleep(.2)

    def random_event(self, tag=None, attendees=None, additional=None):
        start = randint(1,24)
        e =  gcalbridge.calendar.Event({
             'summary': "test random %s %s" %(tag, datetime.datetime.now().isoformat()),
             'start': {
                 'dateTime': (datetime.datetime.now() +
                              datetime.timedelta(hours=start)).isoformat(),
                 'timeZone': 'America/New_York'
             },
             'end': {
                 'dateTime': (datetime.datetime.now() +
                              datetime.timedelta(hours=start+1)).isoformat(),
                 'timeZone': 'America/New_York'
             }
        })
        if attendees:
            e['attendees'] = attendees
        if additional:
            e.update(additional)
        return e

    def assertEvent(self, id, cals=None, tests={}):
        if cals is None: cals=self._cals
        for c in cals:
            e = c.events.get(id, None)
            self.assertIsNotNone(e)
            self.assertIsInstance(e, gcalbridge.calendar.Event)
            for t in tests.keys():
                self.assertEqual(e[t], tests[t])

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
        key = randint(100000, 1000000)
        new_event = (c.service.events().quickAdd(calendarId=c.url,
            text="Testing %d at AutoTestLoc tomorrow from 10am-10:30am" % key)
            .execute())
        self.created_events.append((c.service, c.url, new_event))
        self.assertEqual(new_event['status'], "confirmed")
        self.cal.sync()
        for c in self._cals:
            self.assertEqual(len(c.events), ec[c.url] + 1)
            for other_c in self._cals:
                for (eid, e) in c.events.iteritems():
                    self.assertIsInstance(e, gcalbridge.calendar.Event)
                    if not e.active():
                        continue
                    self.assertEqual(cmp(e, other_c.events[eid]), 0)

        for field in ["summary", "description", "location"]:
            k = str(randint(1, 10000000000))
            c.service.events().patch(calendarId=c.url, eventId=new_event['id'],
                                     body={field: k}).execute()
            self.cal.sync()
            for c in self._cals:
                self.assertEqual(len(c.events), ec[c.url] + 1)
                e = c.events[new_event['id']]
                self.assertIsInstance(e, gcalbridge.calendar.Event)
                self.assertEqual(e[field], k)

        c.service.events().patch(calendarId=c.url, eventId=new_event['id'],
                                 body={"status": "cancelled"}).execute()
        self.cal.sync()
        for c in self._cals:
            self.assertEqual(len(c.events), ec[c.url] + 1)
            e = c.events[new_event['id']]
            self.assertIsInstance(e, gcalbridge.calendar.Event)
            self.assertEqual(e['status'], "cancelled")
            self.assertFalse(e.active())

    def test_double_sync(self):
        before = self.cal.sync()
        after = self.cal.sync()
        self.assertEqual(after, 0)

    def test_propagate_invite(self):
        cal = self._cals[0]
        svc = cal.service.events()
        tag = self.tag()
        new_event = svc.insert(calendarId="primary",
                   body=self.random_event(tag=tag)).execute()

        self.assertIn('summary', new_event)
        self.assertIn(tag, new_event['summary'])
        self.created_events.append((cal.service, "primary",
                                    new_event))

        self.cal.sync()

        for c in self._cals:
            e = c.events.get(new_event['id'], None)
            self.assertIsNone(e)

        patched = svc.patch(calendarId="primary", eventId=new_event['id'],
                            body={'attendees': [
                 {
                     'email': cal.url,
                     'resource': True
                 }]}).execute()

        self.wait_for_backend(cal)

        self.assertGreater(self.cal.sync(), 0)

        self.assertEvent(new_event['id'])

        patched = svc.patch(calendarId="primary", eventId=new_event['id'],
                body={
                    'start': {
                        'dateTime': (datetime.datetime.now() +
                                     datetime.timedelta(hours=2)).isoformat(),
                        'timeZone': 'America/New_York'
                    },
                    'end': {
                        'dateTime': (datetime.datetime.now() +
                                     datetime.timedelta(hours=3)).isoformat(),
                        'timeZone': 'America/New_York'
                    },

                }).execute()
        self.wait_for_backend(cal)

        self.assertGreater(self.cal.sync(), 0)

        self.assertEqual(patched['id'], new_event['id'])

        self.assertEvent(patched['id'])

        svc.patch(calendarId="primary", eventId=new_event['id'],
                             body={"status": "cancelled"}).execute()
        self.wait_for_backend(cal)  #  give the backend a second to catch up
        self.cal.sync()

        for c in self._cals:
            e = c.events.get(new_event['id'], None)
            # logging.debug(pformat(e))
            self.assertIsNotNone(e)
            self.assertEqual(e['status'], 'cancelled')
