import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests


V3_KEY = os.environ["PNW_API_KEY"]
LEGACY_KEY = os.environ["PNW_LEGACY_KEY"]

GRAPHQL = "https://api.politicsandwar.com/graphql"
SEND_URL = "https://politicsandwar.com/api/send-message/"

LOG = "contacted.json"

TARGET = 50
ACTIVE_DAYS = 7
PAUSE = 5

SUBJECT = "Your Nation. Your Decisions."

IMAGE = "https://i.postimg.cc/x8KCgfC6/IMG-8716.png"

APPLY = "https://politicsandwar.com/alliance/join/id=15689"

DISCORD = "https://discord.gg/zCxaUKfXza"

BUTTON = "display:inline-block;padding:12px 22px;background:#5865F2;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:bold;margin:6px;"

MESSAGE = f'<ms-copilot-line-break><ms-copilot-line-break>APPLY IN-GAME<ms-copilot-line-break>DISCORD'

QUERY = "query($page:Int!){nations(first:100,page:$page){paginatorInfo{currentPage lastPage}data{id nation_name alliance_id vacation_mode_turns last_active}}}"


def load_contacted():
    try:
        file = open(
            LOG,
            "r",
            encoding="utf-8"
        )

        data = json.load(file)

        file.close()

        if isinstance(data, list):
            return set(
                int(item)
                for item in data
            )

    except (
        OSError,
        ValueError,
        TypeError
    ):
        pass

    return set()


def save_contacted(items):
    file = open(
        LOG,
        "w",
        encoding="utf-8"
    )

    json.dump(
        sorted(items),
        file,
        indent=2
    )

    file.close()


def parse_date(value):
    try:
        result = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )

        if result.tzinfo is None:
            result = result.replace(
                tzinfo=timezone.utc
            )

        return result

    except (
        AttributeError,
        ValueError
    ):
        return None


def wait_seconds(
    response,
    fallback
):
    headers = [
        "X-RateLimit-Reset-After",
        "Retry-After",
        "RateLimit-Reset"
    ]

    for header in headers:
        try:
            value = response.headers[
                header
            ]

            return max(
                1,
                int(float(value))
            ) + 2

        except (
            KeyError,
            ValueError
        ):
            pass

    return fallback


def fetch_page(page):
    error = None

    for attempt in range(1, 5):
        try:
            params = {
                "api_key": V3_KEY
            }

            variables = {
                "page": page
            }

            body = {
                "query": QUERY,
                "variables": variables
            }

            response = requests.post(
                GRAPHQL,
                params=params,
                json=body,
                timeout=30
            )

            if response.status_code == 429:
                delay = wait_seconds(
                    response,
                    60
                )

                print(
                    f"Search rate limited. "
                    f"Waiting {delay} seconds.",
                    flush=True
                )

                time.sleep(delay)
                continue

            if response.status_code >= 500:
                delay = 10 * attempt

                print(
                    f"Search server error "
                    f"{response.status_code}. "
                    f"Retrying in "
                    f"{delay} seconds.",
                    flush=True
                )

                time.sleep(delay)
                continue

            response.raise_for_status
