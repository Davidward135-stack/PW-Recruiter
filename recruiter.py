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
