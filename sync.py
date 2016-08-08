#!/usr/bin/env python

""" Synchronize Google Calendars as defined in config.json. """

from apiclient.discovery import build
from apiclient.errors import HttpError

from pprint import pformat

import json
import gcalbridge
import time
import logging

FORMAT = "[%(levelname)-8s:%(filename)-15s:%(lineno)4s: %(funcName)20.20s ] %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)


def setup(config):

    domains = {}
    calendars = {}

    for domain in config.domains:
        domains[domain] = gcalbridge.Domain(domain,
                                            config.domains[domain])

    logging.debug(pformat(domains))

    for cal in config.calendars:
        calendars[cal] = gcalbridge.SyncedCalendar(cal,
                                                   config.calendars[cal],
                                                   domains=domains)
    logging.debug(pformat(calendars))
    return calendars


def main():

    config = gcalbridge.config.Config("config.json")
    calendars = setup(config)

    sleep_time = config.poll_time
    exception_count = 0

    while True:
        try:
            for cal in calendars:
                calendars[cal].sync()
        except HttpError as e:
            if e.resp.reason in ['userRateLimitExceeded', 'quotaExceeded',
                                'internalServerError', 'backendError']:
                exception_count += 1
                logging.error(repr(e))
                if exception_count >= config.max_exceptions:
                    break
        time.sleep(config.poll_time * 2 ** exception_count)

if __name__ == '__main__':
    main()
