#!/usr/bin/env python

# List emoji information from Slack.
# https://github.com/smashwilson/slack-emojinator

from __future__ import print_function

import argparse
import os
import re
from time import sleep
import json

from bs4 import BeautifulSoup

import requests

try:
    raw_input
except NameError:
    raw_input = input

URL_CUSTOMIZE = "https://{team_name}.slack.com/customize/emoji"
URL_LIST = "https://{team_name}.slack.com/api/emoji.adminList"

API_TOKEN_REGEX = r'.*(?:\"?api_token\"?):\s*\"([^"]+)\".*'
API_TOKEN_PATTERN = re.compile(API_TOKEN_REGEX)


class ParseError(Exception):
    pass


def _session(args):
    assert args.cookie, "Cookie required"
    assert args.team_name, "Team name required"
    session = requests.session()
    session.headers = {'Cookie': args.cookie}
    session.url_customize = URL_CUSTOMIZE.format(team_name=args.team_name)
    session.url_list = URL_LIST.format(team_name=args.team_name)
    session.api_token = args.api_token or _fetch_api_token(session)
    return session


def _argparse():
    parser = argparse.ArgumentParser(
        description='Bulk upload emoji to slack'
    )
    parser.add_argument(
        '--team-name', '-t',
        default=os.getenv('SLACK_TEAM'),
        help='Defaults to the $SLACK_TEAM environment variable.'
    )
    parser.add_argument(
        '--cookie', '-c',
        default=os.getenv('SLACK_COOKIE'),
        help='Defaults to the $SLACK_COOKIE environment variable.'
    )
    parser.add_argument(
        '--api-token', '-a',
        default=os.getenv('SLACK_API_TOKEN', ""),
        help='Set the API token from input'
             'Defaults to the value pulled from the cookie'
    )
    parser.add_argument(
        'outputPath',
        nargs='+',
        help=('Paths to output your info file'),
    )
    args = parser.parse_args()
    if not args.team_name:
        args.team_name = raw_input('Please enter the team name: ').strip()
    if not args.cookie:
        args.cookie = raw_input('Please enter the "emoji" cookie: ').strip()
    return args


def _fetch_api_token(session):
    # Fetch the form first, to get an api_token.
    r = session.get(session.url_customize)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    all_script = soup.findAll("script")
    for script in all_script:
        for line in script.text.splitlines():
            if 'api_token' in line:
                # api_token: "xoxs-12345-abcdefg....",
                # "api_token":"xoxs-12345-abcdefg....",
                match_group = API_TOKEN_PATTERN.match(line.strip())
                if not match_group:
                    raise ParseError(
                        "Could not parse API token from remote data! "
                        "Regex requires updating."
                    )

                return match_group.group(1)

    print("No api_token found in page. Search your https://<teamname>.slack.com/customize/emoji "
          "page source for \"api_token\" and enter its value manually.")
    return raw_input(
        'Please enter the api_token ("xoxs-12345-abcdefg....") from the page: ').strip()


def main():
    args = _argparse()
    session = _session(args)
    existing_emojis = get_current_emoji_list(session)
    write_emoji_details(args, existing_emojis)


def get_current_emoji_list(session):
    page = 1
    result = []
    while True:
        data = {
            'query': '',
            'page': page,
            'count': 1000,
            'token': session.api_token
        }
        resp = session.post(session.url_list, data=data)
        resp.raise_for_status()
        response_json = resp.json()

        result.extend(response_json["emoji"]) #map(lambda e: e["name"], response_json["emoji"]))
        if page >= response_json["paging"]["pages"]:
            break

        page = page + 1
    return result


def write_emoji_details(args, emoji_list):
    with open(args.outputPath[0], 'w') as emoji_info_file:
        json.dump(emoji_list, emoji_info_file)


if __name__ == '__main__':
    main()
