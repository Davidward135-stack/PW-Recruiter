import json, os, sys, time
from datetime import datetime, timedelta, timezone
import requests

V3 = os.environ["PNW_API_KEY"]
LEGACY = os.environ["PNW_LEGACY_KEY"]

GRAPHQL = "https://api.politicsandwar.com/graphql"
SEND = "https://politicsandwar.com/api/send-message/"
LOG = "contacted.json"

TARGET = 50
DAYS = 7
PAUSE = 5

SUBJECT = "Your Nation. Your Decisions."

IMAGE = "https://i.postimg.cc/x8KCgfC6/IMG-8716.png"
APPLY = "https://politicsandwar.com/alliance/join/id=15689"
DISCORD = "https://discord.gg/zCxaUKfXza"

BLUE = "display:inline-block;padding:14px 24px;background-color:#2563eb;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:bold;margin:6px;"

PURPLE = "display:inline-block;padding:14px 24px;background-color:#5865f2;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:bold;margin:6px;"

MESSAGE = f'<div style="text-align:center"><img src="{IMAGE}" style="max-width:100%;height:auto"><br><br><a href="{APPLY}" style="{BLUE}">APPLY IN-GAME</a><br><br><a href="{DISCORD}" style="{PURPLE}">DISCORD</a></div>'

QUERY = "query($page:Int!){nations(first:100,page:$page){paginatorInfo{currentPage lastPage}data{id nation_name alliance_id vacation_mode_turns last_active}}}"


def load_log():
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


def save_log(items):
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


def wait_for(
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


def get_page(number):
    error = None

    for attempt in range(1, 5):
        try:
            params = {
                "api_key": V3
            }

            variables = {
                "page": number
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
                delay = wait_for(
                    response,
                    60
                )

                time.sleep(delay)

                continue

            if response.status_code >= 500:
                delay = 10 * attempt

                time.sleep(delay)

                continue

            response.raise_for_status()

            data = response.json()

            errors = data.get(
                "errors"
            )

            if errors:
                raise RuntimeError(
                    str(errors)
                )

            return data[
                "data"
            ][
                "nations"
            ]

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
        f"Search failed: {error}"
    )


def send_message(nation_id):
    form = {
        "key": LEGACY,
        "to": str(nation_id),
        "subject": SUBJECT,
        "message": MESSAGE
    }

    error = None

    for attempt in range(1, 5):
        try:
            response = requests.post(
                SEND,
                data=form,
                timeout=30
            )

            if response.status_code == 429:
                delay = wait_for(
                    response,
                    120
                )

                print(
                    f"Rate limited. "
                    f"Waiting {delay} seconds.",
                    flush=True
                )

                time.sleep(delay)

                continue

            if response.status_code >= 500:
                delay = 15 * attempt

                print(
                    f"Server error "
                    f"{response.status_code}. "
                    f"Retrying in "
                    f"{delay} seconds.",
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
                time.sleep(
                    15 * attempt
                )

    raise RuntimeError(
        f"Send failed: {error}"
    )


def main():
    event_name = os.environ.get(
        "GITHUB_EVENT_NAME",
        ""
    )

    if event_name != "workflow_dispatch":
        sys.exit(
            "Use Run workflow."
        )

    contacted = load_log()

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

    current = 1

    last = 1

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(
            days=DAYS
        )
    )

    print(
        f"Target: {TARGET}",
        flush=True
    )

    while (
        sent < TARGET
        and current <= last
    ):
        result = get_page(
            current
        )

        counts["pages"] += 1

        paginator = result.get(
            "paginatorInfo",
            {}
        )

        last = int(
            paginator.get(
                "lastPage",
                current
            )
        )

        print(
            f"Scanning "
            f"{current}/{last}",
            flush=True
        )

        nations = result.get(
            "data",
            []
        )

        for nation in nations:
            if sent >= TARGET:
                break

            counts["checked"] += 1

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
                nation.get(
                    "last_active"
                )
            )

            if active is None:
                counts["inactive"] += 1

                continue

            if active < cutoff:
                counts["inactive"] += 1

                continue

            counts["eligible"] += 1

            attempted.add(
                nation_id
            )

            name = nation.get(
                "nation_name",
                "Unknown"
            )

            print(
                f"Trying {name} "
                f"({nation_id})",
                flush=True
            )

            try:
                reply = send_message(
                    nation_id
                )

            except RuntimeError as exception:
                failed += 1

                print(
                    f"FAILED "
                    f"{nation_id}: "
                    f"{exception}",
                    flush=True
                )

            else:
                success = reply.get(
                    "success"
                )

                if success is True:
                    contacted.add(
                        nation_id
                    )

                    save_log(
                        contacted
                    )

                    sent += 1

                    print(
                        f"SENT "
                        f"{nation_id}. "
                        f"{sent}/{TARGET}",
                        flush=True
                    )

                else:
                    failed += 1

                    print(
                        f"FAILED "
                        f"{nation_id}: "
                        f"{reply}",
                        flush=True
                    )

            if sent < TARGET:
                time.sleep(PAUSE)

        current += 1

    print(
        "=== NOVA RESULT ===",
        flush=True
    )

    print(
        f"PAGES SCANNED: "
        f"{counts['pages']}",
        flush=True
    )

    print(
        f"NATIONS CHECKED: "
        f"{counts['checked']}",
        flush=True
    )

    print(
        f"ELIGIBLE FOUND: "
        f"{counts['eligible']}",
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
        f"IN ALLIANCES: "
        f"{counts['allied']}",
        flush=True
    )

    print(
        f"VACATION MODE: "
        f"{counts['vacation']}",
        flush=True
    )

    print(
        f"INACTIVE: "
        f"{counts['inactive']}",
        flush=True
    )

    print(
        f"BAD DATA: "
        f"{counts['bad']}",
        flush=True
    )

    print(
        "===================",
        flush=True
    )


if __name__ == "__main__":
    main()
