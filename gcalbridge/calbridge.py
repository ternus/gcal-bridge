#!/usr/bin/env python

import logging
from pprint import pformat
from collections import defaultdict

from .config import BadConfigError


class Calendar:
    """
    Represents a single Google Calendar and the credentials required to
    edit it.
    """

    def __init__(self, config, domains=None, service=None):

        self.domain_id = config['domain']
        self.url = config['url']
        self.sync_token = ""
        self.events = {}

        logging.info("Creating new calendar at %s with url %s" % (self.domain_id, self.url))

        if domains:
            if not self.domain_id in domains:
                raise BadConfigError("Domain %s referenced in calendar config not defined." % domain_id)
            self.domain = domains[self.domain_id]
            self.service = self.domain.cal_svc

        if service:
            self.service = service

    def update_events_from_result(self, result):
        """
        Given an Events resource result, update our local events.
        """
        updated = 0
        for event in result.get("items", []):
            id = event['id']
            if (not id in self.events) or self.events[id] != event:
                updated += 1
                self.events[event['id']] = event
        logging.info("Updated %d events" % updated)
        return updated

    def update_events(self):
        """
        Get events from Google and update our local events using
        update_events_from_result.

        Uses syncToken to optimize result retrieval.
        """
        request = self.service.events().list(calendarId=self.url,
                                          syncToken=self.sync_token,
                                          showDeleted=True)
        updated = 0
        while request is not None:
            result = request.execute()
            logging.debug(pformat(result))
            updated += self.update_events_from_result(result)
            request = self.service.events().list_next(request, result)
        self.sync_token = result.get("nextSyncToken", "")
        logging.info("Got %d events. syncToken is now %s" % (len(self.events), self.sync_token))
        return updated

    def sync_event(self, event):
        """
        If `event` doesn't exist, create it with `add_event`; otherwise,
        if `event` is newer than our version, patch it with our version.

        Idempotent if `event` is already the latest version.
        """
        eid = event['id']
        if eid in self.events:
            if self.events[eid]['updated'] < event['updated']:
                self.patch_event(eid, event)
        else:
            self.add_event(event)

    def add_event(self, event):
        """
        Add an event, then update our events with the result.
        """
        result = self.service.events().insert(calendarId=self.url, body=event).execute()
        logging.debug(pformat(result))
        self.update_events_from_result(result)

    def patch_event(self, event_id, new_event):
        """
        Unconditionally patch the event referenced by `event_id` with the
        data in `event`.
        """
        result = self.service.events().patch(calendarId=self.url,
                                             eventId=event_id,
                                             body=new_event).execute()
        logging.debug(pformat(result))
        self.update_events_from_result(result)


class SyncedCalendar:
    """
    A collection of Calendars to be synced.
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
        """
        Update calendar info, getting the latest events. Then, for each event,
        add or update that event as needed.
        """
        for cal in self.calendars:
            logging.info("Updating calendar: %s" % cal.url)
            cal.update_events()
            logging.debug(pformat(cal.events))
            for eid, event in cal.events.iteritems():
                if not eid in self.event_set:
                    self.event_set[eid] = defaultdict(lambda: 0)
                self.event_set[eid][cal.url] = event['updated']

        for eid in self.event_set:
            event = self.get_event(eid)
            for cal in self.calendars:
                cal.sync_event(event)
