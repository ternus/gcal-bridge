#!/usr/bin/env python

""" Synchronize Google Calendars as defined in config.json. """

from oauth2client.service_account import ServiceAccountCredentials
from httplib2 import Http
from apiclient.discovery import build
from pprint import pformat

import json
import gcalbridge
import time
import logging

#logging.basicConfig(level=logging.INFO)

def setup(config):

    domains = {}
    calendars = {}

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        config.keyfile,
        scopes=config.scopes)

    logging.debug(pformat(credentials))

    for domain in config.domains:
        domains[domain] = gcalbridge.Domain(domain,
                                            config.domains[domain],
                                            credentials)

    logging.debug(pformat(domains))

    for cal in config.calendars:
        calendars[cal] = gcalbridge.SyncedCalendar(cal,
                                                   config.calendars[cal],
                                                   domains=domains)
    logging.debug(pformat(calendars))
    return calendars


if __name__ == '__main__':
    config = gcalbridge.config.Config("config.json")
    calendars = setup(config)

    while True:
        for cal in calendars:
            calendars[cal].sync()
        time.sleep(config.poll_time)
