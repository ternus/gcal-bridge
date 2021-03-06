#!/usr/bin/env python

""" Domain tests

Unit tests for domain module"""

import gcalbridge
from gcalbridge import domain, config
from oauth2client.client import FlowExchangeError
import unittest
import sys
from StringIO import StringIO
from testfixtures import LogCapture
from .utils import get_default_config


class DomainTest(unittest.TestCase):
    def setUp(self):
        self.conf = get_default_config()
        self.old_stdout = sys.stdout
        self.old_stdin = sys.stdin
        sys.stdin = StringIO()
        sys.stdout = StringIO()

    def tearDown(self):
        sys.stdin = self.old_stdin
        sys.stdout = self.old_stdout

    def test_basic_domain(self):
        d = domain.Domain("foo.com", self.conf.domains['foo.com'],
            authorize=False)
        self.assertEqual(d.domain, "foo.com")
        self.assertEqual(d.domain_config['account'], "foo@foo.com")

    # These tests were a bad idea.

    # def test_creds_no_code(self):
    #     with LogCapture() as l:
    #         with self.assertRaises(FlowExchangeError):
    #             d = domain.Domain("foo.com", self.conf.domains['foo.com'],
    #                         authorize=True, code="")
    #
    # def test_creds_bad_code(self):
    #     with LogCapture() as l:
    #         with self.assertRaises(FlowExchangeError):
    #             d = domain.Domain("foo.com", self.conf.domains['foo.com'],
    #                         authorize=True, code="bad code")
