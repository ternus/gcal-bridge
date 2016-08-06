# A Google Apps domain

from httplib2 import Http
import logging
from .config import BadConfigError
import apiclient.discovery

class Domain:
    """
    Represents a single Google Apps domain, including the delegated
    credentials necessary to perform operations on it.
    """

    def __init__(self, domain, domain_config, credentials):
        self.domain = domain
        self.domain_config = domain_config

        if not "account" in domain_config:
            raise BadConfigError("Domain %s doesn't have 'account' value set!")

        try:
            self.credentials = credentials.create_delegated(self.domain_config['account'])
        except Exception as e:
            logging.critical("Failed to create delegated credentials for account %s.\n" + \
                            "Did you enable domain-wide delegation and authorize\n" + \
                             "your key properly? See HOWTO.md.")

        self.cal_svc = apiclient.discovery.build('calendar', 'v3', credentials=delegated_credentials)

    def get_calendars(self):

        return self.cal_svc.calendarList().list().execute()
        
