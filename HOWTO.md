# How to set up calendar syncing

## Do this once

Go to https://console.developers.google.com/iam-admin/projects

Click Create Project. Pick a name. Wait for the project to be created.

It'll redirect you to the Library tab. Click the Calendar API and click Enable.

Click Go to Credentials.

On the resulting screen, select the "service account" link next to "If you wish you can skip this step".

Create a new service account. Pick a name and select 'Project -> Service Account Actor' as the role. Check both "Furnish a new private key" and "Enable Google Apps Domain-wide Delegation". Pick a "product" name. Click "Create".

A JSON key will download. Save it somewhere safe.

In the list of service accounts, find your service account and click the "View Client ID" link. Copy the "Client ID" number (e.g. 1092585022291133333444).

## For each domain:

### Enable access for that account

Log into `admin.google.com` as a domain admin user.

Go to More Controls (gray bar at the bottom) -> Security -> Show more -> Advanced settings -> Manage API Client Access.

Under Client Name, enter the "Client ID" you saved from before. Enter 'https://www.googleapis.com/auth/calendar' as the API Scope.
