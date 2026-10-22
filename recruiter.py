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

# Maximum recruitment messages attempted per manual run
MAX_ATTEMPTS = 200

# Only recruit nations active within the last three days
MAX_INACTIVE_DAYS = 3

# Brief pause between messages
SECONDS_BETWEEN_MESSAGES = 1


SUBJECT = "Your Nation. Your Decisions."

MESSAGE = """
<p style="text-align:center;"><img src="https://i.postimg.cc/N02h8y9w/IMG-8522.png">\</p>

<p><b>BANKING NOTICE:</b> Before depositing into the alliance bank, register with our Discord banking bot and generate your personal deposit code. Always include the code provided by the bot when making your in-game bank deposit. <b>DO NOT USE THE SAME CODE TWICE. A NEW CODE GENERATES EACH TIME.</b> Deposits made without the correct code may not be credited to your personal bank balance.</p>

<p><a href="https://politicsandwar.com/alliance/join/id=15689">APPLY IN-GAME</a></p>

<p><a href="https://discord.gg/zCxaUKfXza">DISCORD\</a></p>
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

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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

    if payload.get("errors"):
        raise RuntimeError(
            "GraphQL error: "
            + json.dumps(payload["errors"], indent=2)
        )

    return payload["data"]["nations"]


def send_message(nation_id):
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

    response.raise_for_status()
    return response.json()


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

            try:
                response = send_message(nation_id)

                if response.get("success"):
                    contacted.add(nation_id)
                    save_contacted(contacted)

                    successful += 1

                    print(
                        f"SUCCESS {successful}: "
                        f"{nation_name} "
                        f"(Nation ID {nation_id})"
                    )
                else:
                    failed += 1

                    print(
                        f"FAILED {failed}: "
                        f"{nation_name} "
                        f"(Nation ID {nation_id})"
                    )

                    print(
                        json.dumps(
                            response,
                            indent=2
                        )
                    )

            except requests.RequestException as error:
                failed += 1

                print(
                    f"HTTP FAILURE {failed}: "
                    f"{nation_name} "
                    f"(Nation ID {nation_id})"
                )

                print(str(error))

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
    print(f"Attempts: {attempts}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Recorded recipients: {len(contacted)}")


if __name__ == "__main__":
    main()
