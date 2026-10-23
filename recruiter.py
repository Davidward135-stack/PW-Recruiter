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
MESSAGE = "BANKING NOTICE: Before depositing into the alliance bank, register with our Discord banking bot and generate your personal deposit code. Always include the code provided by the bot when making your in-game bank deposit. DO NOT USE THE SAME CODE TWICE. A NEW CODE GENERATES EACH TIME. Deposits made without the correct code may not be credited to your personal bank balance.\n\nAPPLY IN-GAME\n\nDISCORD"
QUERY = "query($page:Int!){nations(first:100,page:$page){paginatorInfo{currentPage lastPage}data{id nation_name alliance_id vacation_mode_turns last_active}}}"


def load_contacted():
    try:
        with open(LOG, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return {int(item) for item in data}

    except (OSError, ValueError, TypeError):
        pass

    return set()


def save_contacted(items):
    with open(LOG, "w", encoding="utf-8") as file:
        json.dump(sorted(items), file, indent=2)


def parse_date(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))

        if result.tzinfo is None:
            result = result.replace(tzinfo=timezone.utc)

        return result

    except (AttributeError, ValueError):
        return None


def wait_seconds(response, fallback):
    headers = [
        "X-RateLimit-Reset-After",
        "Retry-After",
        "RateLimit-Reset"
    ]

    for header in headers:
        try:
            value = response.headers[header]
            return max(1, int(float(value))) + 2

        except (KeyError, ValueError):
            pass

    return fallback


def fetch_page(page):
    error = None

    for attempt in range(1, 5):
        try:
            response = requests.post(
                GRAPHQL,
                params={"api_key": V3_KEY},
                json={
                    "query": QUERY,
                    "variables": {"page": page}
                },
                timeout=30
            )

            if response.status_code == 429:
                delay = wait_seconds(response, 60)
                print(
                    f"Search rate limited. Waiting {delay} seconds.",
                    flush=True
                )
                time.sleep(delay)
                continue

            if 500 <= response.status_code < 600:
                delay = 10 * attempt
                print(
                    f"Search server error {response.status_code}. "
                    f"Retrying in {delay} seconds.",
                    flush=True
                )
                time.sleep(delay)
                continue

            response.raise_for_status()
            payload = response.json()

            if payload.get("errors"):
                raise RuntimeError(str(payload["errors"]))

            return payload["data"]["nations"]

        except (
            requests.RequestException,
            ValueError,
            KeyError,
            RuntimeError
        ) as exception:
            error = exception

            print(
                f"Search attempt {attempt} failed: {exception}",
                flush=True
            )

            if attempt < 4:
                time.sleep(5 * attempt)

    raise RuntimeError(f"Nation search failed: {error}")


def send_message(nation_id):
    form = {
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
                data=form,
                timeout=30
            )

            if response.status_code == 429:
                delay = wait_seconds(response, 120)

                print(
                    f"Message rate limited. "
                    f"Waiting {delay} seconds.",
                    flush=True
                )

                time.sleep(delay)
                continue

            if 500 <= response.status_code < 600:
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

            print(
                f"Message attempt {attempt} failed: "
                f"{exception}",
                flush=True
            )

            if attempt < 4:
                time.sleep(15 * attempt)

    raise RuntimeError(f"Send failed: {error}")


def main():
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")

    if event_name != "workflow_dispatch":
        sys.exit("Use the GitHub Run workflow button.")

    contacted = load_contacted()
    attempted = set()

    counts = {
        "pages": 0,
        "checked": 0,
        "eligible": 0,
        "contacted": 0,
        "allied": 0,
        "vacation": 0,
        "inactive": 0,
        "bad": 0
    }

    sent = 0
    failed = 0
    page = 1
    last_page = 1

    cutoff = datetime.now(timezone.utc) - timedelta(
        days=ACTIVE_DAYS
    )

    print(
        f"Target: {TARGET} successful messages.",
        flush=True
    )

    while sent < TARGET and page <= last_page:
        result = fetch_page(page)

        counts["pages"] += 1

        paginator = result.get("paginatorInfo", {})

        last_page = int(
            paginator.get("lastPage", page)
        )

        print(
            f"Scanning page {page}/{last_page}.",
            flush=True
        )

        nations = result.get("data", [])

        for nation in nations:
            if sent >= TARGET:
                break

            counts["checked"] += 1

            try:
                nation_id = int(nation["id"])
                alliance_id = int(
                    nation.get("alliance_id") or 0
                )
                vacation_turns = int(
                    nation.get("vacation_mode_turns") or 0
                )

            except (KeyError, TypeError, ValueError):
                counts["bad"] += 1
                continue

            if nation_id in contacted:
                counts["contacted"] += 1
                continue

            if nation_id in attempted:
                counts["contacted"] += 1
                continue

            if alliance_id != 0:
                counts["allied"] += 1
                continue

            if vacation_turns > 0:
                counts["vacation"] += 1
                continue

            active = parse_date(
                nation.get("last_active")
            )

            if active is None:
                counts["inactive"] += 1
                continue

            if active < cutoff:
                counts["inactive"] += 1
                continue

            counts["eligible"] += 1
            attempted.add(nation_id)

            nation_name = nation.get(
                "nation_name",
                "Unknown"
            )

            print(
                f"Trying {nation_name} ({nation_id}).",
                flush=True
            )

            try:
                reply = send_message(nation_id)

            except RuntimeError as exception:
                failed += 1

                print(
                    f"FAILED {nation_id}: {exception}",
                    flush=True
                )

            else:
                if reply.get("success") is True:
                    contacted.add(nation_id)
                    save_contacted(contacted)
                    sent += 1

                    print(
                        f"SENT {nation_id}. "
                        f"Progress {sent}/{TARGET}.",
                        flush=True
                    )

                else:
                    failed += 1

                    print(
                        f"FAILED {nation_id}: {reply}",
                        flush=True
                    )

            if sent < TARGET:
                time.sleep(PAUSE)

        page += 1

    print(
        "=== NOVA RESULT ===",
        flush=True
    )

    print(
        f"PAGES SCANNED: {counts['pages']}",
        flush=True
    )

    print(
        f"NATIONS CHECKED: {counts['checked']}",
        flush=True
    )

    print(
        f"ELIGIBLE FOUND: {counts['eligible']}",
        flush=True
    )

    print(
        f"SENT: {sent}",
        flush=True
    )

    print(
        f"FAILED: {failed}",
        flush=True
    )

    print(
        f"ALREADY CONTACTED: "
        f"{counts['contacted']}",
        flush=True
    )

    print(
        f"IN ALLIANCES: {counts['allied']}",
        flush=True
    )

    print(
        f"VACATION MODE: {counts['vacation']}",
        flush=True
    )

    print(
        f"INACTIVE OVER {ACTIVE_DAYS} DAYS: "
        f"{counts['inactive']}",
        flush=True
    )

    print(
        f"BAD DATA: {counts['bad']}",
        flush=True
    )

    print(
        "===================",
        flush=True
    )


if __name__ == "__main__":
    main()
