# snyk-sync-GHE

## About

`snyk-sync-GHE` is a script that enables syncing of Github Enterprise (or
github.com) repos into Snyk for periodic testing. It leverages the existing
Snyk python wrapper [pysnyk](https://github.com/snyk-labs/pysnyk) and runs through a config
file that contains the information about your SCM (orgs, things to ignore).

### New repos
This script will look for any newly touched repos within the last `DAYS_SINCE_RUN` 
(default 10 days) to catch any potentially new repos that come up and aren't 
onboarded into Snyk. 

### Archived repos
Any repos that are archived will have their projects purged from Snyk to de-clutter
the projects that are currently tracked. 

### Snyk project cleanup
And finally the script reviews any projects for their corresponding repo to
still exist. This would catch any repos deleted or set to ignore via `config.ini`

## Installation
Copy config.ini.example to config.ini and modify with your appropriate values before 
doing the following:

```bash
$ git clone https://github.com/sp3nx0r/snyk-sync-GHE
$ virtualenv -p /usr/bin/python3.7 .
$ source ./bin/activate
$ pip install -r requirements.txt
$ python snyk-sync.py
```

### Configuration

This wrapper requires a `config.ini` file which contains the secrets, ids, other data required for script to run. Check
out `config.ini.examples` for a template to populate.  

```
[Github]
DOMAIN = github.com
GHE_ACCESS_TOKEN = <token>
ORGS = ["some-org"]
excluded_repos = ['org/ignored_repo']
[Snyk]
SNYK_API_TOKEN = <token>
SNYK_ORG_ID = <uuid>
SNYK_INTEGRATION_ID = <uuid>
[Slack]
webhook_alerts = https://hooks.slack.com/services/HOOK
[Debug]
debug = True
```

## Usage
Recommended usage is to run this as a cronjob on periodic basis (like weekly) via `crontab -e`:

`0 9 * * mon echo 'cd /path/to/snyk-sync; source /path/to/snyk-sync/bin/activate; python3.7 /path/to/snyk-sync/snyk-sync.py' | /bin/bash`

### Debug flag
There's a debug flag within the `config.ini` file which can be set to True/False which 
controls the Slack notification and more importantly the actual modification of 
Snyk data. Set this to `True` to test your integrations prior to executing in Snyk. 

### Excluded repos
Sometimes there's repos that don't have manifest files that Snyk doesn't care about. To
get them off the list of continuously trying to sync, you can add it to a Python list
within the `config.ini` file. This will ignore those repos for onboarding into Snyk.

## Dependencies
https://github.com/snyk-labs/pysnyk
https://github.com/PyGithub/PyGithub