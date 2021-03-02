import sqlite3
from utils import send
import requests
from parameters import recruitment_message as message, login_payload, exclude_inactive, inactivity_threshold


def recruit(key):
    """ Finds new players from the nations API, then sends and logs recruitment messages to them. """

    conn = sqlite3.connect('logs.db')
    with conn:
        unaligned = get_unaligned_nations(key)
        contacts = filter_unaligned(unaligned, conn)

        with requests.Session() as s:
            s.post('https://politicsandwar.com/login/', data=login_payload, headers={'User-Agent': 'Mozilla/5.0'})
            print("Sending recruitment messages.")
            c = conn.cursor()
            for contact in contacts:
                send(contact, message, s)
                # log the message
                c.execute('''INSERT INTO recruitment(nation_id) VALUES(?)''', (contact['nationid'],))
            c.close()
        print('Finished messaging unaligned nations.')


def get_unaligned_nations(key):
    req = requests.get(f"https://politicsandwar.com/api/nations/?key={key}&alliance_id=0", headers={'User-Agent': 'Mozilla/5.0'})
    print('Calling the API...')
    data = req.json()
    if not data['success']:
        raise SystemExit("PW API Error : " + data['general_message'])
    nations = data['nations']
    print('API Loaded')
    return nations


def filter_unaligned(nations, conn):
    print('Filtering previously messaged nations...')
    filtered = []
    c = conn.cursor()
    # Filter out vacation mode and previously messaged nations
    for nation in nations:
        if nation['vacmode']:
            continue
        if exclude_inactive:
            if nation['minutesinactive'] > inactivity_threshold:
                continue
        nation_id = nation['nationid']
        c.execute('''SELECT nation_id FROM recruitment WHERE nation_id=?''', (nation_id,))
        result = c.fetchone()
        if result:
            continue
        filtered.append(nation)
    c.close()
    print(f"Found {len(filtered)} unmessaged nations.")
    return filtered
