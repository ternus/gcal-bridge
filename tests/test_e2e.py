#!/usr/bin/env python

import unittest
import os

import gcalbridge
from utils import *

@unittest.skipUnless(os.path.isfile(datafile("client_id.json")),
                     "Only run on a machine with valid secrets.")
class EndToEndTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = gcalbridge.Config(datafile('config_e2e.json'))
        cls.calendars = cls.config.setup()

    def setUp(self):
        self.calendars = EndToEndTest.calendars
        self.config = EndToEndTest.config
        self.cal = list(self.calendars.values())[0]

    @property
    def _cals(self):
        return self.cal.calendars

    def test_e2e_working(self):
        for c in self._cals:
            self.assertEqual(len(c.events), 0)
        self.cal.sync()
        for c in self._cals:
            self.assertGreater(len(c.events), 0)
            self.assertIsNone(c.batch)
            self.assertEqual(c.batch_count, 0)
            self.assertIsNotNone(c.calendar_metadata)
