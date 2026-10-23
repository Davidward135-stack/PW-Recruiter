import json, os, sys, time
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

MESSAGE = "BANKING NOTICE: Before depositing into the alliance bank, register with our Discord banking bot and generate your personal deposit code. Always include the code provided by the bot when making your in-game bank deposit. DO NOT USE THE SAME CODE TWICE. A NEW CODE GENERATES EACH TIME. Deposits made without the correct code may not be credited to your personal bank balance.\n\nAPPLY IN-GAME\n\nDISCORD"


def load_contacted():
    try:
        with open(
            LOG,
            "r",
            encoding="utf-8"
        ) as file:
            value = json.load(file)

        if isinstance(value, list):
            return {
                int(item)
                for item in value
            }

    except (
        OSError,
        ValueError,
        TypeError
    ):
        pass

    return set()


def save_contacted(items):
    with open(
        LOG,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            sorted(items),
            file,
            indent=2
        )


def parse_date(value):
    try:
        result = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )

        if result.tzinfo:
            return result

        return result.replace(
            tzinfo=timezone.utc
        )

    except (
        AttributeError,
        ValueError
    ):
        return None


def wait_seconds(
    response,
    fallback
):
    headers = (
        "X-RateLimit-Reset-After",
        "Retry-After",
        "RateLimit-Reset"
    )

    for header in headers:
        try:
            return max(
                1,
                int(
                    float(
                        response.headers[header]
                    )
                )
            ) + 2

        except (
            KeyError,
            ValueError
        ):
            pass

    return fallback


def fetch_page(page):
    query = """
    query($page: Int!) {
      nations(first: 100, page: $page) {
        paginatorInfo {
          currentPage
          lastPage
        }
        data {
          id
          nation_name
          alliance_id
          vacation_mode_turns
          last_active
        }
      }
    }
    """

    error = None

    for attempt in range(1, 5):
        try:
            response = requests.post(
                GRAPHQL,
                params={
                    "api_key": V3_KEY
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
                delay = wait_seconds(
                    response,
                    60
                )

                print(
                    f"Nation search rate-limited. "
                    f"Waiting {delay} seconds.",
                    flush=True
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
                    f"Retrying in {delay} seconds.",
                    flush=True
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
        ) as exception:
            error = exception

            if attempt < 4:
                time.sleep(
                    5 * attempt
                )

    raise RuntimeError(
        f"Nation search failed: {error}"
    )


def eligible(
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

    active = parse_date(
        nation.get("last_active")
    )

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(
            days=ACTIVE_DAYS
        )
    )

    return (
        nation_id not in contacted
        and nation_id not in attempted
        and alliance_id == 0
        and vacation_turns == 0
        and active is not None
        and active >= cutoff
    )


def send_message(nation_id):
    message_data = {
        "key": LEGACY_KEY,
        "to": str(nation_id),
        "subject": SUBJECT,
        "message": MESSAGE
    }

    error = None

    for attempt in range(1, 5):
        try:
            response = requests.post(
                SEND_URL,
                data=message_data,
                timeout=30
            )

            if response.status_code == 429:
                delay = wait_seconds(
                    response,
                    120
                )

                print(
                    f"Message rate-limited. "
                    f"Waiting {delay} seconds.",
                    flush=True
                )

                time.sleep(delay)
                continue

            if (
                response.status_code >= 500
                and response.status_code < 600
            ):
                delay = 15 * attempt

                print(
                    f"Message server error "
                    f"{response.status_code}. "
                    f"Retrying in {delay} seconds.",
                    flush=True
                )

                time.sleep(delay)
                continue

            response.raise_for_status()

            try:
                return response.json()

            except ValueError:
                return {
                    "success": False,
                    "general_message": response.text
                }

        except requests.RequestException as exception:
            error = exception

            if attempt < 4:
                delay = 15 * attempt
