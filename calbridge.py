#!/usr/bin/env python

from .config import BadConfigError

class Calendar:

    def __init__(self, config, domains=None, service=None):
        self.domain_id = config['domain']
        self.url = config['url']

        if domains:
            if not domain_id in self.domains:
                raise BadConfigError("Domain %s referenced in calendar config not defined." % domain_id)
            self.domain = domains[domain_id]
            self.service = self.domain.cal_svc

        if service:
            self.service = service

class SyncedCalendar:
    """
    A collection of Calendar objects that should all have the same set of events.
    """
    def __init__(self, name, config, domains=None):
        self.name = name
        self.calendars = []
        for cal in config['calendars']:
            self.calendars.append(Calendar(cal, domains=domains))
