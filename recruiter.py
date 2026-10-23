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
            data = json.load(file)

        if isinstance(data, list):
            return {
                int(item)
                for item in data
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
