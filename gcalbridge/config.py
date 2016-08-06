# Manage configuration.

import json
import os.path

class BadConfigError(RuntimeError): pass

class Config:

    defaults = {
        "scopes": "https://www.googleapis.com/auth/calendar",
        "keyfile": "keyfile.json",
        "sites": {
        },
        "calendars": []
    }

    config_needed = {
        "scopes": "One or more scopes - see https://developers.google.com/identity/protocols/googlescopes",
        "keyfile": "Path to a keyfile for a service account - see https://developers.google.com/identity/protocols/OAuth2ServiceAccount",
        "poll_time": "Time to wait while polling",
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
