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
CUTOFF_FILE = "new_nation_cutoff.json"

BATCH_SIZE = 50
MAX_INACTIVE_DAYS = 3
MAX_QUERY_RETRIES = 3
MAX_SCAN_PAGES = 100
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


def load_cutoff():
    if not os.path.exists(CUTOFF_FILE):
        return None

    try:
        with open(
            CUTOFF_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        return int(
            data["minimum_nation_id"]
        )

    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError
    ):
        return None


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
    fallback=120
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
                    response
                )

                print(
                    "Nation search rate-limited. "
                    f"Waiting {delay} seconds."
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
                time.sleep(5)

    raise RuntimeError(
        f"Unable to fetch nation page "
        f"{page}: {last_error}"
    )


def is_eligible(
    nation,
    contacted,
    cutoff
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

    if (
        cutoff is not None
        and nation_id < cutoff
    ):
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
            days=MAX_INACTIVE_DAYS
        )
    )

    return last_active >= active_after


def find_batch(
    contacted,
    cutoff
):
    batch = []
    page = 1

    while (
        len(batch) < BATCH_SIZE
        and page <= MAX_SCAN_PAGES
    ):
        result = fetch_nations(page)

        for nation in result.get(
            "data",
            []
        ):
            if is_eligible(
                nation,
                contacted,
                cutoff
            ):
                batch.append(nation)

                if len(batch) >= BATCH_SIZE:
                    break

        paginator = result.get(
            "paginatorInfo",
            {}
        )

        current_page = int(
            paginator.get(
                "currentPage",
                page
            )
        )

        last_page = int(
            paginator.get(
                "lastPage",
                current_page
            )
        )

        if current_page >= last_page:
            break

        page += 1

    return batch


def send_message(nation_id):
    message_data = {
        "key": LEGACY_API_KEY,
        "to": str(nation_id),
        "subject": SUBJECT,
        "message": MESSAGE
    }

    response = requests.post(
        MESSAGE_URL,
        data=message_data,
        timeout=30
    )

    if response.status_code == 429:
        delay = get_wait_time(
            response
        )

        print(
            "Message rate-limited. "
            f"Waiting {delay} seconds."
        )

        time.sleep(delay)

        response = requests.post(
            MESSAGE_URL,
            data=message_data,
            timeout=30
        )

    response.raise_for_status()

    try:
        return response.json()

    except ValueError:
        return {
            "success": False,
            "general_message": response.text
        }


def main():
    event_name = os.environ.get(
        "GITHUB_EVENT_NAME",
        ""
    )

    if event_name != "workflow_dispatch":
        print(
            "Stopped: start this using "
            "the GitHub Run workflow button."
        )

        sys.exit(1)

    contacted = load_contacted()
    cutoff = load_cutoff()

    batch = find_batch(
        contacted,
        cutoff
    )

    if not batch:
        print(
            "No eligible unallied "
            "nations were found."
        )
        return

    print(
        f"Found {len(batch)} eligible "
        f"nation(s). Starting this "
        f"manually initiated batch."
    )

    sent = 0
    failed = 0

    for position, nation in enumerate(
        batch,
        start=1
    ):
        nation_id = int(
            nation["id"]
        )

        nation_name = nation.get(
            "nation_name",
            "Unknown"
        )

        print(
            f"Sending {position}/"
            f"{len(batch)} to "
            f"{nation_name} "
            f"({nation_id})..."
        )

        try:
            result = send_message(
                nation_id
            )

        except requests.RequestException as error:
            failed += 1

            print(
                f"FAILED {nation_id}: "
                f"HTTP error: {error}"
            )

        else:
            print(
                f"API response for "
                f"{nation_id}: "
                f"{json.dumps(result, ensure_ascii=False)}"
            )

            if result.get("success") is True:
                contacted.add(
                    nation_id
                )

                save_contacted(
                    contacted
                )

                sent += 1

                print(
                    f"SENT {nation_id}"
                )

            else:
                failed += 1

                error_message = result.get(
                    "general_message",
                    result
                )

                print(
                    f"FAILED {nation_id}: "
                    f"{error_message}"
                )

        if position < len(batch):
            time.sleep(
                SECONDS_BETWEEN_MESSAGES
            )

    print(
        f"Batch complete. "
        f"Sent: {sent}. "
        f"Failed: {failed}."
    )

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
