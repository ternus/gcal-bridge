#!/usr/bin/env python

import unittest
import os
import datetime
import time

from random import randint, choice
from apiclient.errors import HttpError

import gcalbridge
from utils import *
import logging
from pprint import pformat

# FORMAT = "[%(levelname)-8s:%(filename)-15s:%(lineno)4s: %(funcName)20.20s ] %(message)s"
# logging.basicConfig(format=FORMAT, level=logging.DEBUG)

@unittest.skipUnless(os.path.isfile(datafile("client_id.json")),
                     "Only run on a machine with valid secrets.")
class EndToEndTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = gcalbridge.Config(datafile('config_e2e.json'))

    @classmethod
    def tearDownClass(cls):
        cals = cls.config.setup()
        for cal in cals.values():
            for cc in cal.calendars:
                cc._show_deleted = True
            cal.sync()
            for c in cal.calendars:
                for id in c.active_events():
                    c.events[id]['status'] = 'cancelled'
                c.push_events(batch=True)


    def setUp(self):
        self.calendars = gcalbridge.Config(datafile('config_e2e.json')).setup()
        for c in self.calendars.values():
            for cc in c.calendars:
                cc._show_deleted = True
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

    def assertHasSameEvents(self, cals=None):
        if cals is None: cals = self._cals
        s = set(cals[0].active_events())
        for c in cals[1:]:
            self.assertEqual(s, set(c.active_events()))

    def sync_and_check(self, mn=0, mx=0, cal=None):
        if cal is None: cal = self.cal
        r = cal.sync()
        if mn:
            self.assertGreaterEqual(r, mn)
        if mx:
            self.assertLessEqual(r, mx)
        self.assertHasSameEvents(cals=cal.calendars)

    def test_e2e_working(self):
        for c in self._cals:
            self.assertIsInstance(c, gcalbridge.calendar.Calendar)
            self.assertIsInstance(c.domain, gcalbridge.domain.Domain)
            # self.assertEqual(len(c.events), 0)
        self.sync_and_check()
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

        self.sync_and_check(1)

        for field in ["summary", "description", "location"]:
            k = self.tag()
            c.service.events().patch(calendarId=c.url, eventId=new_event['id'],
                                     body={field: k}).execute()
            self.sync_and_check(1)
            for c in self._cals:
                self.assertEqual(len(c.events), ec[c.url] + 1)
                e = c.events[new_event['id']]
                self.assertIsInstance(e, gcalbridge.calendar.Event)
                self.assertEqual(e[field], k)

        c.service.events().patch(calendarId=c.url, eventId=new_event['id'],
                                 body={"status": "cancelled"}).execute()
        self.sync_and_check(1)
        for c in self._cals:
            self.assertEqual(len(c.events), ec[c.url] + 1)
            e = c.events[new_event['id']]
            self.assertIsInstance(e, gcalbridge.calendar.Event)
            self.assertEqual(e['status'], "cancelled")
            self.assertFalse(e.active())

    def test_double_sync(self):
        """
        Make sure syncing with no intermediate changes is idempotent.
        """
        self.sync_and_check()
        self.sync_and_check(mx=0)

    def test_create_lots_of_events(self):
        """
        Create 100 random events distributed between calendars, sync, and
        cancel them.
        """
        for c in self._cals:
            c._batch = c.service.new_batch_http_request()
        for i in range(100):
            c = choice(self._cals)
            c._batch.add(c.service.events().insert(calendarId=c.url,
                                                 body=self.random_event()
                                                 ))
        for c in self._cals:
            c._batch.execute()

        self.sync_and_check(99)

        eids = self._cals[0].active_events()

        for id in eids:
            self.assertEvent(id, tests={
                'status': 'confirmed'
            })
            choice(self._cals).events[id]['status'] = 'cancelled'


        for c in self._cals:
            c.push_events(batch=True)

        self.sync_and_check(99)

        for id in eids:
            # logging.debug("%s %s", id, self._cals[0].events[id]['status'])
            self.assertEvent(id, tests={
                'status': 'cancelled'
            })


    def test_propagate_invite(self):
        """
        Create an event on the primary calendar, invite a resource
        to it, then ensure the invite propagates properly across domains.
        """
        cal = self._cals[0]
        svc = cal.service.events()
        tag = self.tag()

        # Create a new event on the **primary** calendar,
        # which isn't synced.

        new_event = svc.insert(calendarId="primary",
                   body=self.random_event(tag=tag)).execute()

        self.assertIn('summary', new_event)
        self.assertIn(tag, new_event['summary'])
        self.created_events.append((cal.service, "primary",
                                    new_event))

        self.sync_and_check()

        # Check that the event didn't appear in any of our calendars.

        for c in self._cals:
            e = c.events.get(new_event['id'], None)
            self.assertIsNone(e)

        # Invite the resource to the event.

        new_event = svc.patch(calendarId="primary", eventId=new_event['id'],
                            body={'attendees': [
                 {
                     'email': cal.url,
                     'resource': True
                 }]}).execute()
        self.wait_for_backend(cal)

        # Make sure we got at least one update and the event is on all
        # calendars.

        self.sync_and_check(1)
        self.assertEvent(new_event['id'])

        # Change the time.

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

        # Sync and check the event time changed.

        self.sync_and_check(1)
        self.assertEqual(patched['id'], new_event['id'])
        self.assertEvent(patched['id'])

        # Cancel the event on the primary calendar.

        svc.patch(calendarId="primary", eventId=new_event['id'],
                             body={"status": "cancelled"}).execute()
        self.wait_for_backend(cal)

        # Sync and check that all events got cancelled.

        self.sync_and_check(1)
        self.assertEvent(new_event['id'], tests={
                    'status': 'cancelled'
        })

    def test_read_only(self):
        ro_cal = self._cals[0]
        ro_cal.read_only = True
        rw_cal = self._cals[1]
        self.sync_and_check()

        rw_cal.service.events().insert(calendarId=rw_cal.url,
                                       body=self.random_event()).execute()

        self.sync_and_check()
