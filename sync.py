#!/usr/bin/env python

from oauth2client.service_account import ServiceAccountCredentials
from httplib2 import Http
from apiclient.discovery import build
from pprint import pprint
import json

from .config import Config
from .domain import Domain


def setup():

    config = Config("config.json")

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        config.keyfile,
        scopes=config.scopes)

    domains = {}
    
    for domain in config.domains:
        domains[domain] = Domain(domain, config.domains[domain], credentials)
        
        calendars = {}
    for cal in config.calendars: 
        calendars[cal] = SyncedCalendar(cal, config.calendars[cal], domains=domains)


calendar = build('calendar', 'v3', credentials=delegated_credentials)

pprint(calendar.calendarList().list().execute().get('items', []))

pprint(calendar.events().list(calendarId=CALENDAR).execute())
