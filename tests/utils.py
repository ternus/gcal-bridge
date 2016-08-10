#!/usr/bin/env python

""" Utilities for testing """
import os
from gcalbridge import config

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

import logging
logging.basicConfig()


def datafile(name):
    return os.path.join(DATA_DIR, name)


def dataread(name):
    return open(os.path.join(DATA_DIR, name)).read()


def get_default_config():
    return config.Config(os.path.join(DATA_DIR, "config-test.json"))
