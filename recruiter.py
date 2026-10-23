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

MESSAGE = (
    "BANKING NOTICE: Before depositing into the alliance bank, "
    "register with our Discord banking bot and generate your personal "
    "deposit code. Always include the code provided by the bot when making "
    "your in-game bank deposit. "
    "DO NOT USE THE SAME CODE TWICE. A NEW CODE GENERATES EACH TIME. "
    "Deposits made without the correct code may not be credited to your "
    "personal bank balance.\n\n"
    "APPLY IN-GAME\n\n"
    "DISCORD"
)


def load_contacted():
    if not os.path.exists(CONTACT_LOG):
        return set()

    try:
        with open(CONTACT_LOG, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return set(int(item) for item in data)

        return set()

    except (
        json.JSONDecodeError,
        TypeError,
        ValueError
    ):
        return set()


def save_contacted(contacted):
    with open(CONTACT_LOG, "w", encoding="utf-8") as file:
        json.dump(
            sorted(contacted),
            file,
            indent=2
        )


def load_cutoff():
    if not os.path.exists(CUTOFF_FILE):
        return None

    try:
        with open(CUTOFF_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return int(data["minimum_nation_id"])

    except (
        json
