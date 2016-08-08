#!/usr/bin/env python

""" Config tests

Unit tests for config module"""


import unittest
from gcalbridge import config
import tempfile
import os
from copy import deepcopy
import json

class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.config_file = "config.json.example"
        self.fake_config_file, self.fake_config_name = tempfile.mkstemp()
        self.fake_config_file = os.fdopen(self.fake_config_file, 'w')

    def tearDown(self):
        self.fake_config_file.close()
        os.unlink(self.fake_config_name)

    def test_basic_config(self):
        conf = config.Config(self.config_file)

    def test_config_missing_file(self):
        with self.assertRaises(RuntimeError):
            config.Config("filethatdoesnotexist")

    def test_bad_config(self):
        self.fake_config_file.write("{{{")
        with self.assertRaises(ValueError):
            config.Config(self.fake_config_name)

    def test_config_missing_entry(self):
        for k in config.Config.config_needed.keys():
            d = deepcopy(config.Config.defaults)
            d.pop(k)
            json.dump(d, self.fake_config_file)
            self.fake_config_file.close()
            with self.assertRaises(config.BadConfigError):
                config.Config(self.fake_config_name)
            self.setUp()
