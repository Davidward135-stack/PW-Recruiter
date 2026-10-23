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

MESSAGE = '<ms-copilot-line-break><ms-copilot-line-break>APPLY IN-GAME<ms-copilot-line-break><ms-copilot-line-break>DISCORD'

QUERY = "query($page:Int!){nations(first:100,page:$page){paginatorInfo{currentPage lastPage}data{id nation_name alliance_id vacation_mode_turns last_active}}}"


def load_contacted():
    try:
        with open(LOG, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return {int(item) for item in data}
