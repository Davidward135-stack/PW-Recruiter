import json
import os
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
MAX_QUERY_RETRIES = 3

SUBJECT = "Your Nation. Your Decisions."

MESSAGE = "BANKING NOTICE: Before depositing into the alliance bank, register with our Discord banking bot and generate your personal deposit code. Always include the code provided by the bot when making your in-game bank deposit. DO NOT USE THE SAME CODE TWICE. A NEW CODE GENERATES EACH TIME. Deposits made without the correct code may not be credited to your personal bank balance.\n\nAPPLY IN-GAME\n\nDISCORD"


def load_contacted():
    if not os.path.exists(CONTACT_LOG):
        return set()

    try:
        with open(CONTACT_LOG, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return {int(item) for item in data}

    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    return set()


def save_contacted(contacted):
    with open(CONTACT_LOG, "w", encoding="utf-8") as file:
        json.dump(sorted(contacted), file, indent=2)


def load_cutoff():
    if not os.path.exists(CUTOFF_FILE):
        return None

    try:
        with open(CUTOFF_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return int(data["minimum_nation_id"])

    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def save_cutoff(nation_id):
    data = {
        "minimum_nation_id": int(nation_id),
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    with open(CUTOFF_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def parse_date(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    except ValueError:
        return None


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

    for attempt in range(1, MAX_QUERY_RETRIES + 1):
        try:
            response = requests.post(
                GRAPHQL_URL,
                params={"api_key": V3_API_KEY},
                json={
                    "query": query,
                    "variables": {"page": page}
                },
                timeout=30
            )

            response.raise_for_status()
            payload = response.json()

            if "errors" in payload:
                raise RuntimeError(
                    f"GraphQL error: {payload['errors']}"
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
                f"Query attempt {attempt} failed: {error}"
            )

    raise RuntimeError(
        f"Unable to fetch nations: {last_error}"
    )


def is_eligible(nation, contacted, cutoff):
    try:
        nation_id = int(nation["id"])
        alliance_id = int(
            nation.get("alliance_id") or 0
        )
        vacation_turns = int(
            nation.get("vacation_mode_turns") or 0
        )

    except (KeyError, TypeError, ValueError):
        return False

    if nation_id in contacted:
        return False

    if alliance_id != 0:
        return False

    if vacation_turns > 0:
        return False

    if cutoff is not None and nation_id < cutoff:
        return False

    last_active = parse_date(
        nation.get("last_active")
    )
