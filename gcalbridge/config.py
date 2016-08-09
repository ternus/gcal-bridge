#!/usr/bin/env python

"""Manage configuration.
"""

import json
import os.path
import logging
from pprint import pformat


from .domain import Domain
from .calbridge import SyncedCalendar
from .errors import BadConfigError


class Config:

    defaults = {
        "scopes": "https://www.googleapis.com/auth/calendar",
        "keyfile": "keyfile.json",
        "poll_time": 5,
        "max_exceptions": 5,
        "domains": {
        },
        "calendars": []
    }

    config_needed = {
        "scopes": "One or more scopes - see https://developers.google.com/identity/protocols/googlescopes",
        "keyfile": "Path to a keyfile for a service account - see https://developers.google.com/identity/protocols/OAuth2ServiceAccount",
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
