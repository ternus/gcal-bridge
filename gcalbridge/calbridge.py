#!/usr/bin/env python

from .config import BadConfigError
from logging import info
from pprint import pprint, pformat
from collections import defaultdict

class Calendar:

    def __init__(self, config, domains=None, service=None):

        self.domain_id = config['domain']
        self.url = config['url']
        self.sync_token = ""
        self.events = {}

        info("Creating new calendar at %s with url %s" % (self.domain_id, self.url))

        if domains:
            if not self.domain_id in domains:
                raise BadConfigError("Domain %s referenced in calendar config not defined." % domain_id)
            self.domain = domains[self.domain_id]
            self.service = self.domain.cal_svc

        if service:
            self.service = service

    def update_events_from_result(self, result):
        updated = 0
        for event in result.get("items", []):
            id = event['id']
            if (not id in self.events) or self.events[id] != event:
                updated += 1
                self.events[event['id']] = event
        info("Updated %d events" % updated)
        return updated

    def update_events(self):
        request = self.service.events().list(calendarId=self.url,
                                          syncToken=self.sync_token,
                                          showDeleted=True)
        updated = 0
        while request is not None:
            result = request.execute()
            info(pformat(result))
            updated += self.update_events_from_result(result)
            request = self.service.events().list_next(request, result)
        self.sync_token = result.get("nextSyncToken", "")
        info("Got %d events. syncToken is now %s" % (len(self.events), self.sync_token))
        return updated

    def sync_event(self, event):
        eid = event['id']
        if eid in self.events:
            if self.events[eid]['updated'] < event['updated']:
                self.patch_event(eid, event)
        else:
            self.add_event(event)

    def add_event(self, event):
        result = self.service.events().insert(calendarId=self.url, body=event).execute()
        self.update_events_from_result(result)

    def patch_event(self, event_id, new_event):
        result = self.service.events().patch(calendarId=self.url,
                                             eventId=event_id,
                                             body=new_event).execute()
        pprint(result)

        self.update_events_from_result(result)

class SyncedCalendar:
    """
    A collection of Calendar objects that should all have the same set of events.
    """
    def __init__(self, name, config, domains=None):
        self.name = name
        self.calendars = []
        for cal_config in config['calendars']:
            cal = Calendar(cal_config, domains=domains)
            self.calendars.append(cal)
        self.event_set = {}

    def get_event(self, id):
        """
        Returns the most up-to-date version of a given event.
        """
        updated = None
        result = None
        for c in self.calendars:
            if id in c.events and c.events[id]['updated'] > updated:
                result = c.events[id]
                updated = result['updated']
        return result

    def sync(self):
        for cal in self.calendars:
            cal.update_events()
            pprint(cal.events)
            for eid, event in cal.events.iteritems():
                if not eid in self.event_set:
                    self.event_set[eid] = defaultdict(lambda: 0)
                self.event_set[eid][cal.url] = event['updated']

    def update(self):
        for eid in self.event_set:
            event = self.get_event(eid)
            for cal in self.calendars:
                cal.sync_event(event)
