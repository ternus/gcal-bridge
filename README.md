# Google Calendar Bridge

[![Build Status](https://travis-ci.org/ternus/gcal-bridge.svg?branch=master)](https://travis-ci.org/ternus/gcal-bridge)

Synchronizes Google Calendars, including those belonging to different domains.
Useful for synchronizing resources (like shared meeting rooms).

_Use at your own risk._ Seriously. See [LICENSE](LICENSE).

## Installation

### Install the requirements

Download the source. Run `pip install -r requirements.txt` . You may need to
use `sudo` depending on the specifics of your python installation.

## Create your API key

Go to https://console.developers.google.com/

Click Create Project. Pick a name. Wait for the project to be created.

It'll redirect you to the Library tab. Click the Calendar API and click Enable.

Click Go to Credentials (or click Credentials on the left-hand tab)

Click the blue Create Credentials button. In the dropdown, select OAuth Client ID.

In the "Application type" menu, select Other. Pick a name (it doesn't matter what you use).

It will display your client ID and client secret. Close out of this. It'll show
a list of your active credentials. Next to the credential you created (on the right),
click the download arrow. It'll download a JSON file. Save this in your project
directory or somewhere else and make a note of the file path.

### Find the calendar IDs you want to sync, or create them

Calendars you want to sync must exist already (this service will not create them).
You'll need the calendar ID for each. Find the calendar under My Calendars on
the left side of Google Calendar's web UI, hover over it, click the dropdown arrow,
and select "Calendar settings". Next to Calendar Address you'll see a line that includes
`(Calendar ID: foo@bar.com)` or similar. Copy each calendar ID, and make a note
of the domain it came from. Calendar resources (like meeting rooms) have IDs like
`foo.com_2213232373144913933307@resource.calendar.google.com`.

Here's an example config syncing between two calendars
```
{
  "client_id_file": "client_id.json",
  "scopes": "https://www.googleapis.com/auth/calendar",
  "poll_time": 60,
  "max_exceptions": 5,
  "domains": {
    "bar.com": {
      "account": "user@bar.com"
    },
    "foo.com": {
      "account": "user@foo.com"
    }
  },
  "calendars": {
    "bob-office": {
      "calendars": [
        {
          "url": "foo.com_12345678900987654321@resource.calendar.google.com",
          "domain": "foo.com"
        },
        {
          "url": "bar.com_11111111111111111111@resource.calendar.google.com",
          "domain": "bar.com"
        }
      ]
    },
    "bob-conference-room": {
      "calendars": [
        {
          "url": "foo.com_22222222222222222222@resource.calendar.google.com",
          "domain": "foo.com"
        },
        {
          "url": "bar.com_33333333333333333333@resource.calendar.google.com",
          "domain": "bar.com"
        }
      ]
    }

  }
}
```

|Parameter     | Meaning        |
|--------------|----------------|
|`client_id_file`| Path to a client ID file, as described above. |
|`scopes`|Scopes to authorize. Should stay at the default unless you know otherwise.|
|`poll_time` | Time to wait between syncs. Automatically increases if ratelimit is hit.|
|`max_exceptions` | Maximum number of times to retry when an error occurs. |


### Run sync.py

The first time you run sync.py, it will prompt you to authorize the app and
download credentials for each domain.

```
$ ./sync.py
Go to this URL:
https://accounts.google.com/long/link/goes/here
authorize the app, and enter the code here:
Code:
```

Going to this URL will prompt you to sign in (as the user specified in the "account"
parameter for each domain) and grant read/write permission on calendars. The system
will save your credentials. If you want them saved in a particular location,
you can specify the `credfile` parameter:

```
"domains": {
  "bar.com": {
    "account": "user@bar.com",
    "credfile": "/path/to/creds_user@bar.com.json"
  }
```

The system will then begin syncing your accounts.
