#!/usr/bin/env python
from __future__ import print_function

import logging
import json

from pprint import pformat
from collections import defaultdict
from apiclient.errors import HttpError
from errors import BadConfigError
from copy import deepcopy
import time

MAX_ACTIONS_PER_BATCH = 950
ITERATION_LIMIT = 100


class Event(dict):
    """
    A wrapper around events.
    """

    # These are properties that are true for two events that are considered
    # identical across domains.
    props = [
        "id",
        "status",
        "start",
        "end",
        "summary",
        "description",
        "location",
        "colorId",
        "reminders",
        "transparency",
        "visibility",
    ]

    special_props = [
        "attendees",
    ]

    def __init__(self, args, **kwargs):
        self.dirty = False
        super(Event, self).__init__(args, **kwargs)

    def active(self):
        return self['status'] != 'cancelled'

    def __cmp__(self, obj):
        """
        Compare two events. If there's no meaningful difference, they're
        'identical' (even if they were updated at different times). Otherwise,
        the most recently updated copy wins.
        """
        if not obj or not isinstance(obj, Event):
            return 1
        elif self.ehash() == obj.ehash():
            return 0
        else:
            for p in self.props:
                if p in self and p in obj:
                    if self[p] != obj[p]:
                        logging.debug("!!!!!==== %s %s %s", p, self[p], obj[p])
            return cmp(self['updated'], obj['updated'])

    def __setitem__(self, k, v):
        self.dirty = True
        dict.__setitem__(self, k, v)

    def ehash(self):
        d = {}
        for p in self.props:
            d[p] = self.get(p, None)
        for p in self.special_props:
            if p in self:
                d[p] = sorted([a['email'] for a in self[p]])
        return hash(json.dumps(d))


class Calendar:
    """
    Represents a single Google Calendar and the domain service required to
    edit it.
    """

    def __init__(self, config, domains=None, service=None):

        self.domain_id = config['domain']
        self.url = config['url']
        self.name = self.url
        self.sync_token = ""
        self.events = {}
        self.batch = None
        self.batch_count = 0
        self.read_only = False
        self.calendar_metadata = None
        self.ratelimit = 0

        if 'read_only' in config:
            self.read_only = config['read_only']

        logging.info("Creating new calendar at %s with url %s" % (self.
            domain_id, self.url))

        if domains is not None:
            if not self.domain_id in domains:
                raise BadConfigError(
                    "Domain %s referenced in calendar config not defined." %
                    self.domain_id)
            self.domain = domains[self.domain_id]
            self.service = self.domain.get_service()

        if service:
            self.service = service

        # Perform self-checking

        try:
            calendars = self.domain.get_calendars()
        except HttpError as e:
            logging.critical("Error while trying to load calendar %s: %s",
                self.url, repr(e))
            raise e

        for c in calendars.get('items', []):
            if c['id'] == self.url:
                self.calendar_metadata = c
                break

        if not self.calendar_metadata:
            raise BadConfigError("Couldn't find calendar %s in domain %s!" % (
                self.url, self.domain_id))
        # Now that we have metadata, we can use a name instead of a URL

        self.name = "%s [%s]" % (self.calendar_metadata['summary'], self.
            domain_id)

        if (self.calendar_metadata['accessRole'] not in self.valid_access_roles()):
            logging.critical(
                "Permission '%s' on calendar %s is too restrictive! Needed %s",
                self.calendar_metadata['accessRole'], self.url, self.
                valid_access_roles())
            raise RuntimeError

    def valid_access_roles(self):
        """
        The set of access roles required.
        """
        if self.read_only:
            return ["owner", "writer", "reader"]
        return ["owner", "writer"]

    def active_events(self):
        return {k:v for k,v in self.events.iteritems() if v.active()}

    def update_events_from_result(self, result, exception=None):
        """
        Given an Events resource result, update our local events.
        """
        if exception is not None:
            logging.warn("Callback indicated failure -- exception: %s",
                exception)
            logging.debug(pformat(result))
            logging.debug(pformat(exception))
            raise exception
            # return 0
        updated = 0
        for event in result.get("items", []):
            id = event['id']
            new_event = Event(event)
            old_event = self.events.get(id, None)
            if new_event != old_event:  # see Event.__cmp__; not that simple!
                if not (old_event and not old_event.active()):
                    updated += 1
                self.events[id] = Event(event)
        if updated:
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
            updated += self.update_events_from_result(result)
            request = self.service.events().list_next(request, result)
        self.sync_token = result.get("nextSyncToken", "")
        # logging.info("Got %d events. syncToken is now %s" % (updated,
        # self.sync_token))
        return updated

    def begin_batch(self):
        """
        Start a new batch of actions.
        """
        logging.debug("Calendar %s starting new batch" % self.url)
        if self.batch:
            logging.warn(
                "begin_batch called with active batch! Trying to commit")
            self.commit_batch()
        self.batch = self.service.new_batch_http_request()

    def commit_batch(self):
        """
        Execute the currently active batch.
        """
        if not self.batch:
            logging.warn("commit_batch called but no batch was started!")
            return
        if self.batch_count:
            # Only commit a batch when necessary, to save on HTTP requests.
            logging.debug("Calendar %s committing batch of %d" % (self.url,
                self.batch_count))
            if self.ratelimit:
                time.sleep(self.ratelimit / 1000.0)
                self.ratelimit = 0
            result = self.batch.execute()
            #self.update_events_from_result(result)
            # logging.debug(pformat(result))
        self.batch = None
        self.batch_count = 0

    def _action_to_batch(self, action):
        """
        Add an action to the currently active batch. If the batch contains more
        than MAX_ACTIONS_PER_BATCH actions, commit it and start a new one.
        """
        if self.batch:
            self.batch.add(action, callback=lambda request_id, response,
                exception: self.update_events_from_result(response,
                exception=exception))
            self.batch_count += 1
            self.ratelimit += 2
            if self.batch_count > MAX_ACTIONS_PER_BATCH:
                self.commit_batch()
                self.begin_batch()
        else:
            logging.critical(
                "Tried to add a batch action but no batch was active!")
            raise RuntimeError

    def sync_event(self, event):
        """
        If `event` doesn't exist, create it with `add_event`; otherwise,
        if `event` is newer than our version, patch it with our version.

        Idempotent if `event` is already the latest version.
        """
        eid = event['id']
        if eid in self.events:
            my_event = self.events[eid]
            if (my_event['status'] == 'cancelled' and event['status'] ==
                'cancelled'):
                my_event = event
                return None
            if my_event < event:
                # logging.debug(pformat(self.events[eid]))
                # logging.debug(pformat(event))
                return self.update_event(eid, event)
        else:
            self.events[eid] = event
            if event['status'] == 'cancelled':
                # If the event is both new to us and cancelled, there's no need
                # to add it (and Google doesn't let us do so for resources
                # anyway) so just add it to our event set and return.
                return None
            return self.add_event(event)
            # return self.import_event(event)

    def _process_action(self, action):
        """
        If we're running in batch mode, add the action to a batch.
        Otherwise, execute the action immediately and update.
        """
        if self.batch:
            return self._action_to_batch(action)
        else:
            result = action.execute()
            # logging.debug(pformat(result))
            self.update_events_from_result(result)
            return result

    def add_event(self, event):
        """
        Add an event, then update our events with the result.
        """
        if self.read_only:
            logging.debug("RO: %s +> %s" % (event['id'], self.name))
            return None
        action = self.service.events().insert(calendarId=self.url, body=event)
        return self._process_action(action)

    def patch_event(self, event_id, new_event):
        """
        Unconditionally patch the event referenced by `event_id` with the
        data in `event`.
        """
        if self.read_only:
            logging.debug("RO: %s => %s" % (event['id'], self.name))
            return None
        action = self.service.events().patch(calendarId=self.url,
                                             eventId=event_id,
                                             body=new_event)
        return self._process_action(action)

    def update_event(self, event_id, new_event):
        """
        Unconditionally update the event referenced by `event_id` with the
        data in `event`.
        """
        if self.read_only:
            logging.debug("RO: %s ~> %s" % (event['id'], self.name))
            return None
        # new_event['sequence'] += 1
        action = self.service.events().update(calendarId=self.url,
                                             eventId=event_id,
                                             body=new_event)
        return self._process_action(action)

    def push_events(self, batch=False):
        """
        If we have local modifications to events, push them
        to the server.
        """
        if batch: self.begin_batch()
        updates = 0
        for eid, e in self.events.iteritems():
            if e.dirty:
                # logging.debug("Pushing dirty event %s", eid)
                self.update_event(eid, e)
                e.dirty = False
                updates += 1
            # if updates > MAX_ACTIONS_PER_BATCH:
            #     if batch:
            #         self.commit_batch()
            #         self.begin_batch()
        if batch: self.commit_batch()
        return updates


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
        self.event_set = set()

    def sync_event(self, id):
        """
        Find the most up-to-date version of a given event, and sync changes
        that need to be made.
        """
        events = [c.events[id] for c in self.calendars if id in c.events]
        if not [e for e in events if e.active()]:
            # All events cancelled. We don't care.
            return 0
        elif [e for e in events if not e.active()]:
            # One or more events cancelled. All events should be cancelled.
            for e in events:
                e['status'] = 'cancelled'
        event = max(events)  # See __cmp__ in Event for how this is determined.
        sequence = max([e['sequence'] for e in events])
        if sequence > event['sequence']:
            # you get an update! you get an update! everyone gets an update!
            event['sequence'] = sequence + 1
            logging.debug("increasing SN of %.5s to %d", id, event['sequence'])
        return sum([c.sync_event(event) is not None for c in self.calendars])

    def print_debug_events(self):
        for e in self.event_set:
            print(("%.5s" % e), end=' ')
            for c in self.calendars:
                if e in c.events:
                    print(" %-4d %20.20s %25.25s" % (c.events[e]['sequence'],
                        c.events[e]['summary'], c.events[e]['updated']),
                        end=' ')
                else:
                    print(" " * 32, end=' ')
            print()

    def sync(self):
        """
        Update calendar info, getting the latest events. Then, for each event,
        add or update that event as needed.
        """

        changes = 0
        total_changes = 0
        iterations = 0

        while changes or (iterations == 0):
            try:
                total_changes += changes
                changes = 0
                for cal in self.calendars:
                    logging.info("Updating calendar: %s" % cal.url)
                    # First, get the latest set of events from Google.
                    changes += cal.update_events()
                    # Start a batch on this calendar.
                    cal.begin_batch()
                    # Update our set of event IDs.
                    self.event_set.update(cal.events.keys())

                changes += sum([self.sync_event(eid) for eid in self.event_set])

                for cal in self.calendars:
                    changes += cal.push_events()
                    cal.commit_batch()
                iterations += 1
                if iterations > ITERATION_LIMIT:
                    raise RuntimeError("Bug: exceeded iteration limit.")
                logging.debug("sync() iteration %d: %d changes, %d total", iterations, changes, total_changes)
            except HttpError as e:
                iterations += 1
                time.sleep(2 ** (iterations))
                for cal in self.calendars:
                    cal.ratelimit += 1000 * (2 ** iterations)
        for cal in self.calendars:
            cal.ratelimit = False

        return total_changes
