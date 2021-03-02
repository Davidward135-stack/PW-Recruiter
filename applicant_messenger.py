from parameters import applicant_message as message, login_payload, alliance_id
import requests
import sqlite3
from utils import send


def get_applicants(key):
    req = requests.get(f'https://politicsandwar.com/api/nations/?key={key}&alliance_id={alliance_id}')
    data = req.json()
    nations = data['nations']
    applicants = []
    for nation in nations:
        if nation['allianceposition'] == 1:
            applicants.append(nation)
    return applicants


def message_applicants(key):
    applicants = get_applicants(key)
    conn = sqlite3.connect('logs.db')
    with conn:
        with requests.Session() as s:
            s.post('https://politicsandwar.com/login/', data=login_payload, headers={'User-Agent': 'Mozilla/5.0'})
            print("Sending applicant messages.")
            c = conn.cursor()
            for applicant in applicants:
                # Skip if message log exists
                log = c.execute('''SELECT nation_id FROM applicants WHERE nation_id=?''', (applicant['nationid'],)).fetchone()
                if log:
                    continue
                send(applicant, message, s)
                # log the nation ID
                c.execute('''INSERT INTO applicants(nation_id) VALUES(?)''', (applicant['nationid'],))
            c.close()
            print("Finished messaging applicants.")
