#!/usr/bin/env python

from httplib2 import Http
import apiclient.discovery
import oauth2client
import json
import os

import logging

from errors import BadConfigError


class Domain:
    """
    Represents a single Google Apps domain, including the delegated
    credentials necessary to perform operations on it.
    """

    def __init__(self, domain, domain_config, authorize=True, code=None, http=None):
        self.domain = domain
        self.domain_config = domain_config
        self.http = http

        if not "account" in domain_config:
            raise BadConfigError("Domain %s doesn't have 'account' value set!")

        self.account = self.domain_config['account']

        if authorize:
            try:
                self.credentials = self.obtain_credentials(code=code)
            except Exception as e:
                logging.critical("Failed to obtain credentials for account %s [%s]",
                                 self.account, repr(e))
                raise e

    def get_file_path(self):
        if 'credfile' in self.domain_config:
            return self.domain_config['credfile']
        else:
            return "creds_" + self.account + ".json"

    def check_credentials(self, credentials=None):
        if not credentials:
            if self.credentials:
                credentials = self.credentials
            else:
                return None
        try:
            service = self.get_service(credentials=credentials)
            service.calendarList().list().execute()
            return credentials
        except Exception as e:
            logging.error(repr(e))
            return None

    def obtain_credentials(self, code=None):
        logging.info("Getting credentials for %s" % self.domain)
        credentials = None
        if os.path.isfile(self.get_file_path()):
            logging.info("%s exists, attempting to retrieve credentials", self.get_file_path())
            try:
                credentials = oauth2client.file.Storage(self.get_file_path()).get()
                return self.check_credentials(credentials)
            except Exception as e:
                logging.error(repr(e))
                raise e
        else:
            flow = oauth2client.client.flow_from_clientsecrets(
                    'client_id.json',
                    scope='https://www.googleapis.com/auth/calendar',
                    redirect_uri='urn:ietf:wg:oauth:2.0:oob',
                    login_hint=self.account
                )
            flow.params['access_type'] = "offline"
            print("Go to this URL:")
            print(flow.step1_get_authorize_url())
            print("authorize the app, and enter the code here:")
            if code is None:
                code = raw_input("Code: ")
            try:
                credentials = flow.step2_exchange(code)
                if self.check_credentials(credentials):
                    oauth2client.file.Storage(self.get_file_path()).put(credentials)
                    return credentials
            except Exception as e:
                logging.error(repr(e))
                raise e
            return None

    def get_service(self, credentials=None):
        if self.http:
            # For testing purposes.
            return apiclient.discovery.build('calendar', 'v3', http=self.http)
        else:
            if not credentials:
                credentials = self.credentials
            return apiclient.discovery.build('calendar', 'v3', credentials=credentials)

    def get_calendars(self):
        return self.get_service().calendarList().list().execute()
