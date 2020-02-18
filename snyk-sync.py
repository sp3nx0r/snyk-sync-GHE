# This script pulls down GHE repositories and runs through Snyk projects to keep in sync
# Note: This depends on a config.ini in same directory as Python script which utilizes ConfigParser
# Note: This will also work with Github.com by modifying the DOMAIN value

# TODO: Need to add logging to syslog w/ rotation
# TODO: Need to add error checking in case GHE doesn't respond and seen repos is empty
# TODO: Need to add error handling for Snyk connection failure
# TODO: Add handling for "new" repos that don't have supported target files (no dependency files)

import datetime
import configparser
from github import Github
import snyk
from ast import literal_eval
from slack_webhook import Slack

# Use ConfigParser to build necessary secrets for integrations
config = configparser.ConfigParser()
config.read('config.ini')

# feature flag: DEBUG=True means no Snyk/Slack execution
DEBUG = config['Debug'].getboolean('debug')
# Github
DOMAIN = config['Github']['DOMAIN']
GHE_ACCESS_TOKEN = config['Github']['GHE_ACCESS_TOKEN']
ORGS = literal_eval(config['Github']['ORGS'])
excluded_repos = literal_eval(config['Github']['excluded_repos'])
# Snyk
SNYK_API_TOKEN = config['Snyk']['SNYK_API_TOKEN']
SNYK_ORG_ID = config['Snyk']['SNYK_ORG_ID']
SNYK_INTEGRATION_ID = config['Snyk']['SNYK_INTEGRATION_ID']
# Slack
slack = Slack(url=config['Slack']['webhook_alerts'])
# Days since run, linked to cron job duration. Basically, how do we determine a "new" repo is new to us
DAYS_SINCE_RUN = 10

# GHE API python wrapper
ghe = Github(base_url=f"https://{DOMAIN}/api/v3", login_or_token=GHE_ACCESS_TOKEN, per_page=1000)

# Snyk API python wrapper, get all existing project (aka onboarded GHE repos)
client = snyk.SnykClient(SNYK_API_TOKEN)
projects = client.organizations.get(SNYK_ORG_ID).projects.all()

archived_repos = []
new_repos = []
is_present = False
seen_repos = []

for watched_org in ORGS:
    org = ghe.get_organization(watched_org)
    for repo in org.get_repos(type="all"):
        seen_repos.append(repo.full_name)
        # check that a repo isn't on the excluded list
        if repo.full_name not in excluded_repos:
            # Build a list of archived repos
            if repo.archived:
                archived_repos.append(repo.full_name)
                print(f'Found archived repo: {repo.full_name}')

            else:
                # Build list of any new repos not in Snyk that probably should be added
                is_present = False
                for project in projects:
                    if repo.full_name == project.name.split(":")[0]:
                        is_present = True
                if not is_present:
                    # if it's newer than
                    if abs(datetime.datetime.today() - repo.pushed_at).days <= DAYS_SINCE_RUN:
                        new_repos.append(repo.full_name)
                        print(f'Found new repo: {repo.full_name} last pushed at {repo.pushed_at}')

# API call to delete archived projects
deleted_projects = []
for project in projects:
    project_name = project.name.split(":")[0]
    if project_name in archived_repos:
        # repo has been recently archived
        if not DEBUG:
            project.delete()
        if project_name not in deleted_projects:
            deleted_projects.append(project_name)
        print(f'Project {project.name}  deleted because it archived')
    if project_name not in seen_repos and project.origin == 'github-enterprise':
        # repo must be deleted or isn't in GHE anymore
        if not DEBUG:
            project.delete()
        if project_name not in deleted_projects:
            deleted_projects.append(project_name)
        print(f'Project {project.name} deleted because it gooooone')
    if project_name in excluded_repos:
        # cleanup any excluded repos, they shouldn't be in Snyk
        if not DEBUG:
            project.delete()
        if project_name not in deleted_projects:
            deleted_projects.append(project_name)
        print(f'Project {project.name} deleted because it excluded')

# API call to add new projects
org = client.organizations.get(SNYK_ORG_ID)
integration = org.integrations.get(SNYK_INTEGRATION_ID)
for new_repo in new_repos:
    new_repo_org = new_repo.split("/")[0]
    new_repo_name = new_repo.split("/")[1]
    if not DEBUG:
        job = integration.import_git(new_repo_org, new_repo_name)
    print(f'Repo {new_repo_org}/{new_repo_name} added because it new')

# communicate deltas
if new_repos or deleted_projects:
    slack_payload = 'Snyk-GHE Synchronization Script Completed:' + '\n' + f'>GHE repos: {len(seen_repos)} Snyk projects: {len(projects)}'
    if deleted_projects:
        slack_payload = slack_payload + '\n' + f'>Removed Snyk projects: {deleted_projects}'
    if new_repos:
        slack_payload = slack_payload + '\n' + f'>Newly added GHE repos: {new_repos}'
    if not DEBUG:
        slack.post(text=slack_payload)
    print(slack_payload)
