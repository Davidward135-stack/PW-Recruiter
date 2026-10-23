import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests


V3_API_KEY = os.environ["PNW_API_KEY"]
LEGACY_API_KEY = os.environ["PNW_LEGACY_KEY"]

GRAPHQL_URL = "https://api.politicsandwar.com/graphql"
MESSAGE_URL = "https://politicsandwar.com/api/send-message/"

CONTACT_LOG = "contacted.json"

TARGET_SENDS = 50
MAX_INACTIVE_DAYS = 7
MAX_QUERY_RETRIES = 4
MAX_MESSAGE_RETRIES = 4
MAX_SCAN_PAGES = 500
SECONDS_BETWEEN_MESSAGES = 5

SUBJECT = "Your Nation. Your Decisions."

MESSAGE = "BANKING NOTICE: Before depositing into the alliance bank, register with our Discord banking bot and generate your personal deposit code. Always include the code provided by the bot when making your in-game bank deposit. DO NOT USE THE SAME CODE TWICE. A NEW CODE GENERATES EACH TIME. Deposits made without the correct code may not be credited to your personal bank balance.\n\nAPPLY IN-GAME\n\nDISCORD"


def load_contacted():
    if not os.path.exists(CONTACT_LOG):
        return set()

    try:
        with open(
            CONTACT_LOG,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        if isinstance(data, list):
            return {
                int(item)
                for item in data
            }

    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
        ValueError
    ):
        pass

    return set()


def save_contacted(contacted):
    with open(
        CONTACT_LOG,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            sorted(contacted),
            file,
            indent=2
        )


def parse_date(value):
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed

    except (
        TypeError,
        ValueError
    ):
        return None


def get_wait_time(
    response,
    fallback
):
    header_names = (
        "X-RateLimit-Reset-After",
        "Retry-After",
        "RateLimit-Reset"
    )

    for header_name in header_names:
        value = response.headers.get(
            header_name
        )

        if value:
            try:
                return max(
                    1,
                    int(float(value))
                ) + 2

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

    last_error = None

    for attempt in range(
        1,
        MAX_QUERY_RETRIES + 1
    ):
        try:
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
                },
                timeout=30
            )

            if response.status_code == 429:
                delay = get_wait_time(
                    response,
                    60
                )

                print(
                    "Nation search rate-limited. "
                    f"Waiting {delay} seconds."
                )

                time.sleep(delay)
                continue

            if (
                response.status_code >= 500
                and response.status_code < 600
            ):
                delay = 10 * attempt

                print(
                    f"Nation server error "
                    f"{response.status_code}. "
                    f"Retrying in {delay} seconds."
                )

                time.sleep(delay)
                continue

            response.raise_for_status()
            payload = response.json()

            if payload.get("errors"):
                raise RuntimeError(
                    str(payload["errors"])
                )

            return payload["data"]["nations"]

        except (
            requests.RequestException,
            ValueError,
            KeyError,
            RuntimeError
        ) as error:
            last_error = error

            print(
                f"Nation query attempt "
                f"{attempt} failed: {error}"
            )

            if attempt < MAX_QUERY_RETRIES:
                time.sleep(
                    5 * attempt
                )

    raise RuntimeError(
        f"Unable to fetch nation page "
        f"{page}: {last_error}"
    )


def is_eligible(
    nation,
    contacted,
    attempted
):
    try:
        nation_id = int(
            nation["id"]
        )

        alliance_id = int(
            nation.get(
                "alliance_id"
            ) or 0
        )

        vacation_turns = int(
            nation.get(
                "vacation_mode_turns"
            ) or 0
        )

    except (
        KeyError,
        TypeError,
        ValueError
    ):
        return False

    if nation_id in contacted:
        return False

    if nation_id in attempted:
        return False

    if alliance_id != 0:
        return False

    if vacation_turns > 0:
        return False

    last_active = parse_date(
        nation.get("last_active")
    )

    if last_active is None:
        return False

    active_after = (
        datetime.now(timezone.utc)
        - timedelta(
            days=MAX_INACTIVE_D
