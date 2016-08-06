# How to set up calendar syncing

## Install the requirements

Download the source. Run `pip install -r requirements.txt` . You may need to
use `sudo` depending on the specifics of your python installation.

## Do this once

Go to https://console.developers.google.com/iam-admin/projects

Click Create Project. Pick a name. Wait for the project to be created.

It'll redirect you to the Library tab. Click the Calendar API and click Enable.

Click Go to Credentials.

On the resulting screen, select the "service account" link next to "If you wish you can skip this step".

Create a new service account. Pick a name and select 'Project -> Service Account Actor' as the role. Check both "Furnish a new private key" and "Enable Google Apps Domain-wide Delegation". Pick a "product" name. Click "Create".

A JSON key will download.

In the list of service accounts, find your service account and click the "View Client ID" link. Copy the "Client ID" number (e.g. 1092585022291133333444).

## For each domain:

### Enable access for that account

Log into https://admin.google.com as a domain admin user.

Go to More Controls (gray bar at the bottom) -> Security -> Show more -> Advanced settings -> Manage API Client Access.

Under Client Name, enter the "Client ID" you saved from before. Enter 'https://www.googleapis.com/auth/calendar' as the API Scope.

### Find the calendar IDs you want to sync, or create them

Calendars you want to sync must exist already (this service will not create them).
You'll need the calendar ID for each. Find the calendar under My Calendars on
the left side of Google Calendar's web UI, hover over it, click the dropdown arrow,
and select "Calendar settings". Next to Calendar Address you'll see a line that includes
`(Calendar ID: foo@bar.com)` or similar. Copy each calendar ID, and make a note
of the domain it came from. Calendar resources (like meeting rooms) have IDs like
`foo.com_2213232373144913933307@resource.calendar.google.com`.

## Create a config file

Create a file, `config.json`, using `config.json.example`, to match the config you want. For example, a config
for syncing a single calendar, `bob-office`, across two domains, `foo.com` and `bar.com`:

```
{
  "keyfile": "/path/to/keyfile.json",
  "scopes": "https://www.googleapis.com/auth/calendar",
  "poll_time": 60,
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
          "url": "bob-office@foo.com",
          "domain": "foo.com"
        },
        {
          "url": "bob-office@bar.com",
          "domain": "bar.com"
        }
      ]
    }
  }
}
```
