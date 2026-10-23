import json
import os
import time
from datetime import datetime, timezone, timedelta

import requests


V3_API_KEY = os.environ["PNW_API_KEY"]
LEGACY_API_KEY = os.environ["PNW_LEGACY_KEY"]

GRAPHQL_URL = "https://api.politicsandwar.com/graphql"
MESSAGE_URL = "https://politicsandwar.com/api/send-message/"

CONTACT_LOG = "contacted.json"
CUTOFF_FILE = "new_nation_cutoff.json"

MAX_ATTEMPTS = 200
MAX_INACTIVE_DAYS = 3
SECONDS_BETWEEN_MESSAGES = 5
MAX_QUERY_RETRIES = 3

SUBJECT = "Your Nation. Your Decisions."

MESSAGE = (
    ''
    ''
    ''
    'BANKING NOTICE: Before depositing into the alliance bank, '
    'register with our Discord banking bot and generate your personal '
    'deposit code. Always include the code provided by the bot when making '
    'your in-game bank deposit. '
    'DO NOT USE THE SAME CODE TWICE. A NEW CODE GENERATES EACH TIME. '
    'Deposits made without the correct code may not be credited to your '
    'personal bank balance.'
    ''
    ''
    'APPLY IN-GAME'
    ''
    ''
    ''
    ''
    'DISCORD'
    ''
    ''
)


def load_contacted():
    if not os.path.exists(CONTACT_LOG):
        return set()

    try:
        with open(CONTACT_LOG, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return set(int(item) for item in data)

        return set()

    except (
        json.JSONDecodeError,
        TypeError,
        ValueError
    ):
        return set()


def save_contacted(contacted):
    with open(CONTACT_LOG, "w", encoding="utf-8") as file:
        json.dump(
            sorted(contacted),
            file,
            indent=2
        )


def load_cutoff():
    if not os.path.exists(CUTOFF_FILE):
        return None

    try:
        with open(CUTOFF_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return int(data["minimum_nation_id"])

    except (
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError
    ):
        return None


def save_cutoff(nation_id):
    data = {
        "minimum_nation_id": int(nation_id),
        "created_at": datetime.now(
            timezone.utc
        ).isoformat()
    }

    with open(CUTOFF_FILE, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=2
        )


def parse_date(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

    except ValueError:
        return None


def get_wait_time(response, fallback=120):
    header_names = [
        "X-RateLimit-Reset-After",
        "Retry-After",
        "RateLimit-Reset"
    ]

    for header_name in header_names:
        value = response.headers.get(header_name)

        if not value:
            continue

        try:
            seconds = int(float(value))

            if seconds > 0:
                return seconds + 2

        except ValueError:
            pass

    return fallback


def fetch_nations(page):
    query = """
    query GetNations($page: Int!) {
      nations(first: 100, page: $page) {
        paginatorInfo {
          currentPage
          lastPage
        }
        data {
          id
          nation_name
          leader_name
          alliance_id
          vacation_mode_turns
          last_active
        }
      }
    }
    """

    for attempt in range(1, MAX_QUERY_RETRIES + 1):
        response = requests.post(
            GRAPHQL_URL,
            params={
                "api_key": V3_API_KEY
            },
            json={
                "query": query,
                "variables": {
                    "page": page
                }
