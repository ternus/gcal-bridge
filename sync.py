#!/usr/bin/env python

""" Synchronize Google Calendars as defined in config.json. """

from apiclient.discovery import build
from apiclient.errors import HttpError

from pprint import pformat

import json
import time
import logging
import os

import gcalbridge

FORMAT = "[%(levelname)-8s:%(filename)-15s:%(lineno)4s: %(funcName)20.20s ] %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)

def main():

    config = gcalbridge.config.Config("config.json")
    calendars = config.setup()

    sleep_time = config.poll_time
    exception_count = 0

    while True:
        try:
            for cal in calendars:
                calendars[cal].sync()
                exception_count = 0
        except HttpError as e:
            if e.resp.reason in ['userRateLimitExceeded', 'quotaExceeded',
                                'internalServerError', 'backendError']:
                exception_count += 1
                logging.error(repr(e))
                if exception_count >= config.max_exceptions:
                    break
        logging.debug("---------- %d %d", config.poll_time, exception_count)
        time.sleep(config.poll_time * 2 ** exception_count)

if __name__ == '__main__':
    main()
