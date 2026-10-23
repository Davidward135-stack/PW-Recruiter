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

MAX_ATTEMPTS = 200
MAX_INACTIVE_DAYS = 3
SECONDS_BETWEEN_MESSAGES = 5
MAX_QUERY_RETRIES = 3

SUBJECT = "Your Nation. Your Decisions."

MESSAGE = (
    '<p style="text-align:center;">'
    '<img src="https://i.postimg.cc/N02h8y9w/IMG-8522.png">'
    '</p>'
    '<p><b>BANKING NOTICE:</b> Before depositing into the alliance bank, '
    'register with our Discord banking bot and generate your personal '
    'deposit code. Always include the code provided by the bot when making '
    'your in-game bank deposit. '
    '<b>DO NOT USE THE SAME CODE TWICE. A NEW CODE GENERATES EACH TIME.</b> '
    'Deposits made without the correct code may not be credited to your '
    'personal bank balance.</p>'
    '<p>'
    '<a href="https://politicsandwar.com/alliance/join/id=15689" '
    'style="background:#22c55e;border:14px solid #22c55e;'
    'color:#ffffff;text-decoration:none;font-weight:bold;">'
    'APPLY IN-GAME'
    '</a>'
    '</p>'
    '<p>'
    '<a href="https://discord.gg/zCxaUKfXza" '
    'style="background:#22c55e;border:14px solid #22c55e;'
    'color:#ffffff;text-decoration:none;font-weight:bold;">'
    'DISCORD'
    '</a>'
    '</p>'
)


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
            params={"api_key": V3_API_KEY},
            json={
                "query": query,
                "variables": {"page": page}
            },
            timeout=30
        )

        if response.status_code == 429:
            wait_time = get_wait_time(response)

            print(
                "GraphQL rate limit reached. "
                "Waiting {} seconds.".format(wait_time)
            )

            time.sleep(wait_time)
            continue

        if response.status_code >= 500:
            wait_time = 15 * attempt

            print(
                "GraphQL server error {}. "
                "Waiting {} seconds.".format(
                    response.status_code,
                    wait_time
                )
            )

            time.sleep(wait_time)
            continue

        response.raise_for_status()
        payload = response.json()

        if payload.get("errors"):
            raise RuntimeError(
                "GraphQL error: "
                + json.dumps(payload["errors"], indent=2)
            )

        remaining = response.headers.get(
            "X-RateLimit-Remaining"
        )

        print(
            "Fetched nation page {}. "
            "API requests remaining: {}".format(
                page,
                remaining
            )
        )

        return payload["data"]["nations"]

    raise RuntimeError(
        "Unable to retrieve nations after retries."
    )


def send_message_once(nation_id):
    try:
        response = requests.post(
            MESSAGE_URL,
            data={
                "key": LEGACY_API_KEY,
                "to": nation_id,
                "subject": SUBJECT,
                "message": MESSAGE
            },
            timeout=30
        )

    except requests.RequestException as error:
        return {
            "success": False,
            "uncertain": True,
            "general_message": (
                "Message request produced an uncertain result: {}"
            ).format(error)
        }

    if response.status_code == 429:
        wait_time = get_wait_time(response)

        return {
            "success": False,
            "rate_limited": True,
            "wait_time": wait_time,
            "general_message": (
                "Message endpoint rate limited the request."
            )
        }

    if response.status_code >= 500:
        return {
            "success": False,
            "uncertain": True,
            "general_message": (
                "Message endpoint returned HTTP {}. "
                "The request will not be retried because delivery "
                "may already have occurred."
            ).format(response.status_code)
        }

    try:
        response.raise_for_status()
    except requests.RequestException as error:
        return {
            "success": False,
            "uncertain": False,
            "general_message": str(error)
        }

    try:
        return response.json()
    except ValueError:
        return {
            "success": False,
            "uncertain": True,
            "general_message": (
                "Message endpoint returned an unreadable response. "
                "The request will not be retried."
            )
        }


def eligible(nation, contacted):
    nation_id = int(nation["id"])

    if nation_id in contacted:
        return False

    alliance_id = nation.get("alliance_id")

    if alliance_id not in (None, 0, "0"):
        return False

    vacation_turns = int(
        nation.get("vacation_mode_turns") or 0
    )

    if vacation_turns > 0:
        return False

    last_active = parse_date(
        nation.get("last_active")
    )

    if last_active is None:
        return False

    cutoff = datetime.now(timezone.utc) - timedelta(
        days=MAX_INACTIVE_DAYS
    )

    return last_active >= cutoff


def main():
    contacted = load_contacted()

    attempts = 0
    successful = 0
    uncertain = 0
    failed = 0
    page = 1

    while attempts < MAX_ATTEMPTS:
        result = fetch_nations(page)
        nations = result["data"]

        for nation in nations:
            if attempts >= MAX_ATTEMPTS:
                break

            if not eligible(nation, contacted):
                continue

            nation_id = int(nation["id"])
            nation_name = nation["nation_name"]

            attempts += 1

            print(
                "Attempt {}/{}: {} "
                "(Nation ID {})".format(
                    attempts,
                    MAX_ATTEMPTS,
                    nation_name,
                    nation_id
                )
            )

            # Record before sending.
            # This prevents duplicate messages if P&W delivers the
            # message but returns an error or times out afterwards.
            contacted.add(nation_id)
            save_contacted(contacted)

            response = send_message_once(nation_id)

            if response.get("rate_limited"):
                wait_time = response.get(
                    "wait_time",
                    120
                )

                print(
                    "Message rate limit reached. "
                    "Waiting {} seconds.".format(wait_time)
                )

                time.sleep(wait_time)

                # Do not retry this nation because delivery status
                # must remain at-most-once.
                uncertain += 1

                print(
                    "SKIPPED AFTER RATE LIMIT {}: {}".format(
                        uncertain,
                        nation_name
                    )
                )

            elif response.get("success"):
                successful += 1

                print(
                    "SUCCESS {}: {}".format(
                        successful,
                        nation_name
                    )
                )

            elif response.get("uncertain"):
                uncertain += 1

                print(
                    "UNCERTAIN {}: {}".format(
                        uncertain,
                        nation_name
                    )
                )

                print(
                    response.get(
                        "general_message",
                        "Unknown uncertain result."
                    )
                )

            else:
                failed += 1

                print(
                    "FAILED {}: {}".format(
                        failed,
                        nation_name
                    )
                )

                print(
                    json.dumps(
                        response,
                        indent=2
                    )
                )

            time.sleep(SECONDS_BETWEEN_MESSAGES)

        last_page = result["paginatorInfo"]["lastPage"]

        if attempts >= MAX_ATTEMPTS:
            break

        if page >= last_page:
            break

        page += 1

    save_contacted(contacted)

    print("")
    print("NOVA recruitment batch complete.")
    print("Attempts: {}".format(attempts))
    print("Successful: {}".format(successful))
    print("Uncertain but not retried: {}".format(uncertain))
    print("Confirmed failures: {}".format(failed))
    print(
        "Recorded recipients: {}".format(
            len(contacted)
        )
    )


if __name__ == "__main__":
    main()
