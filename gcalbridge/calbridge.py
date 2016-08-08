#!/usr/bin/env python

import logging
from pprint import pformat
from collections import defaultdict

from .config import BadConfigError

MAX_ACTIONS_PER_BATCH = 900

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
        self.batch = None
        self.batch_count = 0

        logging.info("Creating new calendar at %s with url %s" % (self.domain_id, self.url))

        if domains:
            if not self.domain_id in domains:
                raise BadConfigError("Domain %s referenced in calendar config not defined." % domain_id)
            self.domain = domains[self.domain_id]
            self.service = self.domain.cal_svc

        if service:
            self.service = service

    def update_events_from_result(self, result, exception=None):
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

    def begin_batch(self):
        """
        Start a new batch of actions.
        """
        logging.debug("Calendar %s starting new batch" % self.url)
        if self.batch:
            logging.warn("begin_batch called with active batch! Trying to commit")
            self.commit_batch()
        self.batch = self.service.new_batch_http_request()

    def commit_batch(self):
        """
        Execute the currently active batch.
        """
        logging.debug("Calendar %s committing batch of %d" % (self.url, self.batch_count) )
        if not self.batch:
            logging.warn("commit_batch called but no batch was started!")
            return
        result = self.batch.execute()
        logging.debug(pformat(result))
        self.batch = None
        self.batch_count = 0

    def _action_to_batch(self, action):
        """
        Add an action to the currently active batch. If the batch contains more
        than MAX_ACTIONS_PER_BATCH actions, commit it and start a new one.
        """
        if self.batch:
            self.batch.add(action, callback=lambda request_id, response, exception:
                           self.update_events_from_result(response, exception=exception))
            self.batch_count += 1
            if self.batch_count > MAX_ACTIONS_PER_BATCH:
                self.commit_batch()
                self.begin_batch()
        else:
            logging.critical("Tried to add a batch action but no batch was active!")
            raise RuntimeError

    def sync_event(self, event):
        """
        If `event` doesn't exist, create it with `add_event`; otherwise,
        if `event` is newer than our version, patch it with our version.

        Idempotent if `event` is already the latest version.
        """
        eid = event['id']
        if eid in self.events:
            if self.events[eid]['sequence'] < event['sequence']:
                logging.info(pformat(self.events[eid]))
                logging.info(pformat(event))
                self.update_event(eid, event)
        else:
            self.add_event(event)

    def _process_action(self, action):
        """
        If we're running in batch mode, add the action to a batch.
        Otherwise, execute the action immediately and update.
        """
        if self.batch:
            return self._action_to_batch(action)
        else:
            result = action.execute()
            logging.debug(pformat(result))
            self.update_events_from_result(result)
            return result

    def add_event(self, event):
        """
        Add an event, then update our events with the result.
        """
        action = self.service.events().insert(calendarId=self.url, body=event)
        return self._process_action(action)

    def patch_event(self, event_id, new_event):
        """
        Unconditionally patch the event referenced by `event_id` with the
        data in `event`.
        """
        action = self.service.events().patch(calendarId=self.url,
                                             eventId=event_id,
                                             body=new_event)
        return self._process_action(action)

    def update_event(self, event_id, new_event):
        """
        Unconditionally update the event referenced by `event_id` with the
        data in `event`.
        """
        action = self.service.events().update(calendarId=self.url,
                                             eventId=event_id,
                                             body=new_event)
        return self._process_action(action)


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
            cal.begin_batch()
            for eid, event in cal.events.iteritems():
                if not eid in self.event_set:
                    self.event_set[eid] = defaultdict(lambda: 0)
                self.event_set[eid][cal.url] = event['updated']

        for eid in self.event_set:
            event = self.get_event(eid)
            for cal in self.calendars:
                cal.sync_event(event)

        for cal in self.calendars:
            cal.commit_batch()
