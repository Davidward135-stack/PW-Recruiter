import json, os, sys, time
from datetime import datetime, timedelta, timezone
import requests

V3 = os.environ["PNW_API_KEY"]
LEGACY = os.environ["PNW_LEGACY_KEY"]

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

APPLY_STYLE = "display:inline-block;padding:14px 24px;background-color:#2563eb;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:bold;"

DISCORD_STYLE = "display:inline-block;padding:14px 24px;background-color:#5865f2;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:bold;"

MESSAGE = f'<div style="text-align:center"><img src="{IMAGE}" style="max-width:100%;height:auto"><br><br><a href="{APPLY}" style="{APPLY_STYLE}">APPLY IN-GAME</a><br><br><a href="{DISCORD}" style="{DISCORD_STYLE}">DISCORD</a></div>'

QUERY = "query($page:Int!){nations(first:100,page:$page){paginatorInfo{currentPage lastPage}data{id nation_name alliance_id vacation_mode_turns last_active}}}"


def load_log():
    try:
        with open(
            LOG,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

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
    temporary = LOG + ".tmp"

    with open(
        temporary,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            sorted(items),
            file,
            indent=2
        )

    os.replace(
        temporary,
        LOG
    )


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


def fetch_page(number):
    last_error = None

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
                print(
                    "Nation search rate limited. "
                    "Waiting 60 seconds.",
                    flush=True
                )

                time.sleep(60)
                continue

            if response.status_code >= 500:
                delay = 10 * attempt

                print(
                    f"Nation search server error "
                    f"{response.status_code}. "
                    f"Waiting {delay} seconds.",
                    flush=True
                )

                time.sleep(delay)
                continue

            response.raise_for_status()

            payload = response.json()

            errors = payload.get(
                "errors"
            )

            if errors:
                raise RuntimeError(
                    str(errors)
                )

            return payload[
                "data"
            ][
                "nations"
            ]

        except (
            requests.RequestException,
            ValueError,
            KeyError,
            RuntimeError
        ) as error:
            last_error = error

            if attempt < 4:
                time.sleep(
                    5 * attempt
                )

    raise RuntimeError(
        f"Nation search failed: "
        f"{last_error}"
    )


def send_once(nation_id):
    form = {
        "key": LEGACY,
        "to": str(nation_id),
        "subject": SUBJECT,
        "message": MESSAGE
    }

    try:
        response = requests.post(
            SEND_URL,
            data=form,
            timeout=30
        )

    except requests.RequestException as error:
        return (
            False,
            "Uncertain delivery, "
            f"not retried: {error}"
        )

    if response.status_code >= 400:
        return (
            False,
            "Uncertain delivery, "
            "not retried: "
            f"HTTP {response.status_code}"
        )

    try:
        reply = response.json()

    except ValueError:
        return (
            False,
            "Uncertain delivery, "
            "not retried: "
            "invalid API response"
        )

    if reply.get("success") is True:
        return (
            True,
            str(reply)
        )

    return (
        False,
        str(reply)
    )


def main():
    event_name = os.environ.get(
        "GITHUB_EVENT_NAME",
        ""
    )

    if event_name != "workflow_dispatch":
        sys.exit(
            "Use the GitHub "
            "Run workflow button."
        )

    blocked = load_log()

    sent = 0
    uncertain = 0
    current = 1
    last = 1

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(
            days=ACTIVE_DAYS
        )
    )

    print(
        f"Target: {TARGET} "
        f"unique recipients",
        flush=True
    )

    while (
        sent < TARGET
        and current <= last
    ):
        result = fetch_page(
            current
        )

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
                continue

            if nation_id in blocked:
                continue

            if alliance_id != 0:
                continue

            if vacation_turns > 0:
                continue

            active = parse_date(
                nation.get(
                    "last_active"
                )
            )

            if active is None:
                continue

            if active < cutoff:
                continue

            blocked.add(
                nation_id
            )

            save_log(
                blocked
            )

            print(
                f"LOCKED {nation_id} "
                f"before send",
                flush=True
            )

            success, detail = send_once(
                nation_id
            )

            if success:
                sent += 1

                print(
                    f"SENT {nation_id}. "
                    f"Progress "
                    f"{sent}/{TARGET}",
                    flush=True
                )

            else:
                uncertain += 1

                print(
                    f"SKIPPED {nation_id}. "
                    f"{detail}",
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
        f"SENT: {sent}",
        flush=True
    )

    print(
        f"UNCERTAIN OR FAILED: "
        f"{uncertain}",
        flush=True
    )

    print(
        f"TOTAL BLOCKED IDS: "
        f"{len(blocked)}",
        flush=True
    )

    print(
        "NO MESSAGE POST WAS RETRIED",
        flush=True
    )

    print(
        "===================",
        flush=True
    )


if __name__ == "__main__":
    main()
