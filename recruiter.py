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

# Maximum recruitment attempts per manually started run
MAX_ATTEMPTS = 200

# Only recruit nations active within the last three days
MAX_INACTIVE_DAYS = 3

# Slow down message sending to reduce temporary server errors
SECONDS_BETWEEN_MESSAGES = 5

# Retry temporary API/server failures
MAX_RETRIES = 3


SUBJECT = "Your Nation. Your Decisions."

MESSAGE = """


BANKING NOTICE: Before depositing into the alliance bank, register with our Discord banking bot and generate your personal deposit code. Always include the code provided by the bot when making your in-game bank deposit. DO NOT USE THE SAME CODE TWICE. A NEW CODE GENERATES EACH TIME. Deposits made without the correct code may not be credited to your personal bank balance.

APPLY IN-GAME

DISCORD
"""


def load_contacted():
    if not os.path.exists(CONTACT_LOG):
        return set()

    try:
        with open(CONTACT_LOG, "r", encoding="utf-8") as file:
            return set(json.load(file))
    except (json.JSONDecodeError, TypeError):
        return set()


def save_contacted(contacted):
    with open(CONTACT_LOG, "w", encoding="utf-8") as file:
        json.dump(sorted(contacted), file, indent=2)


def parse_date(value):
    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def get_wait_time(response, fallback=60):
    possible_headers = [
        "X-RateLimit-Reset-After",
        "Retry-After",
        "RateLimit-Reset"
    ]

    for header_name in possible_headers:
        value = response.headers.get(header_name)

        if not value:
            continue

        try:
            wait_time = int(float(value))

            if wait_time > 0:
                return wait_time + 2
        except ValueError:
            continue

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

    for attempt in range(1, MAX_RETRIES + 1):
        response = requests.post(
            GRAPHQL_URL,
            params={"api_key": V3_API_KEY},
            json={
                "query": query,
                "variables": {"page": page}
            },
            timeout=30
        )

        if response.status_code == 429:
            wait_time = get_wait_time(
                response,
                fallback=120
            )

            print(
                f"Graph
