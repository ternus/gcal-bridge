#!/usr/bin/env python

from oauth2client.service_account import ServiceAccountCredentials
from httplib2 import Http
from apiclient.discovery import build
from pprint import pprint

SCOPES=["https://www.googleapis.com/auth/calendar"]

credentials = ServiceAccountCredentials.from_json_keyfile_name('keyfile.json', scopes=SCOPES)

delegated_credentials = credentials.create_delegated('')

calendar = build('calendar', 'v3', credentials=delegated_credentials)


pprint(calendar.calendarList().list().execute().get('items', []))

pprint(calendar.events().list(calendarId=CALENDAR).execute())
