#!/usr/bin/env python

from oauth2client.service_account import ServiceAccountCredentials
from httplib2 import Http
from apiclient.discovery import build
from pprint import pprint

import json
import gcalbridge
import time
import logging

logging.basicConfig(level=logging.INFO)

domains = {}
calendars = {}

def setup(config, domains, calendars):

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        config.keyfile,
        scopes=config.scopes)

    pprint(credentials)

    for domain in config.domains:
        domains[domain] = gcalbridge.Domain(domain,
                                            config.domains[domain],
                                            credentials)

    pprint(domains)

    for cal in config.calendars:
        calendars[cal] = gcalbridge.SyncedCalendar(cal,
                                                   config.calendars[cal],
                                                   domains=domains)
    pprint(calendars)


if __name__ == '__main__':
    config = gcalbridge.config.Config("config.json")
    setup(config, domains, calendars)

    while True:

        for cal in calendars:
            calendars[cal].sync()
            calendars[cal].update()

        time.sleep(config.poll_time)
