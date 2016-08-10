#!/usr/bin/env python

"""
Manage configuration.
"""

import json
import os.path
import logging
from pprint import pformat

from .domain import Domain
from .calendar import SyncedCalendar
from .errors import BadConfigError


class Config:

    defaults = {
        "scopes": "https://www.googleapis.com/auth/calendar",
        "client_id_file": "client_id.json",
        "poll_time": 5,
        "max_exceptions": 5,
        "domains": {
        },
        "calendars": []
    }

    config_needed = {
        "scopes": "One or more scopes - see https://developers.google.com/identity/protocols/googlescopes",
        "client_id_file": "Path to a client ID json file",
        "poll_time": "Time to wait while polling",
        "max_exceptions": "Number of exceptions to encounter before exiting"
    }

    def __init__(self, filename="config.json"):

        if not os.path.isfile(filename):
            raise RuntimeError("Config file %s not found." % filename)
        with open(filename, 'r') as f:
            self.__dict__.update(json.loads(f.read()))

        # Do some sanity checking.

        for k in self.config_needed.keys():
            if not hasattr(self, k):
                raise BadConfigError(
                    "Config file %s missing needed config entry: %s [%s]" % \
                    (filename, k, self.config_needed[k]))

        # Ensure our Client ID file exists, is readable, is valid JSON

        if not os.path.isfile(self.client_id_file):
            raise RuntimeError("Client ID file %s not found." % self.client_id_file)

        try:
            with open(self.client_id_file) as f:
                json.loads(f.read())
        except ValueError as e:
            raise RuntimeError("Client ID file %s is not valid JSON! %s" % repr(e))

    def setup(self):
        """
        Given a config, perform setup of sync system.
        """

        domains = {}
        calendars = {}

        for domain in self.domains:
            domains[domain] = Domain(domain,
                                     self.domains[domain])

        logging.debug(pformat(domains))

        for cal in self.calendars:
            calendars[cal] = SyncedCalendar(cal,
                                            self.calendars[cal],
                                            domains=domains)
        logging.debug(pformat(calendars))
        return calendars
