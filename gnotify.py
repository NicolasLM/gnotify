#!/usr/bin/env python
from collections import namedtuple
from datetime import datetime, timedelta
from email.message import EmailMessage
import json
import logging
import os
import signal
import smtplib
import sys
import threading

import pytz

FILENAME = os.environ.get('FILENAME', '/var/gnotify/cities-dst.json')
DELAY = int(os.environ.get('DELAY', '7200'))
TO = os.environ.get('TO', 'Nicolas Le Manchet <nicolas@lemanchet.fr>')
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.mailgun.org')
SMTP_USER = os.environ['SMTP_USER']
SMTP_PASSWORD = os.environ['SMTP_PASSWORD']
FROM = f'DST Notifier <{SMTP_USER}>'

logger = logging.getLogger('gnotify')
must_stop = threading.Event()
City = namedtuple('City', ['code', 'name', 'country', 'zonename'])

CITIES = (
    City('PPG', 'Pago Pago', 'USA', 'Pacific/Pago_Pago'),
    City('HNL', 'Honolulu', 'USA', 'Pacific/Honolulu'),
    City('ANC', 'Anchorage', 'USA', 'America/Anchorage'),
    City('YVR', 'Vancouver', 'Canada', 'America/Vancouver'),
    City('LAX', 'Los Angeles', 'USA', 'America/Los_Angeles'),
    City('YEA', 'Edmonton', 'Canada', 'America/Edmonton'),
    City('DEN', 'Denver', 'USA', 'America/Denver'),
    City('MEX', 'Mexico City', 'Mexico', 'America/Mexico_City'),
    City('CHI', 'Chicago', 'USA', 'America/Chicago'),
    City('NYC', 'New York City', 'USA', 'America/New_York'),
    City('SCL', 'Santiago', 'Chile', 'America/Santiago'),
    City('YHZ', 'Halifax', 'Canada', 'America/Halifax'),
    City('YYT', "St. John's", 'Canada', 'America/St_Johns'),
    City('RIO', 'Rio de Janeiro', 'Brazil', 'America/Sao_Paulo'),
    City('FEN', 'Fernando de Noronha', 'Brazil', 'America/Noronha'),
    City('RAI', 'Praia', 'Cape Verde', 'Atlantic/Cape_Verde'),
    City('LIS', 'Lisbon', 'Portugal', 'Europe/Lisbon'),
    City('LON', 'London', 'United Kingdom', 'Europe/London'),
    City('MAD', 'Madrid', 'Spain', 'Europe/Madrid'),
    City('PAR', 'Paris', 'France', 'Europe/Paris'),
    City('ROM', 'Rome', 'Italy', 'Europe/Rome'),
    City('BER', 'Berlin', 'Germany', 'Europe/Berlin'),
    City('STO', 'Stockholm', 'Sweden', 'Europe/Stockholm'),
    City('ATH', 'Athens', 'Greece', 'Europe/Athens'),
    City('CAI', 'Cairo', 'Egypt', 'Africa/Cairo'),
    City('JRS', 'Jerusalem', 'Israel', 'Asia/Jerusalem'),
    City('MOW', 'Moscow', 'Russia', 'Europe/Moscow'),
    City('JED', 'Jeddah', 'Saudi Arabia', 'Asia/Riyadh'),
    City('THR', 'Tehran', 'Iran', 'Asia/Tehran'),
    City('DBX', 'Dubai', 'United Arab Emirates', 'Asia/Dubai'),
    City('KBL', 'Kabul', 'Afghanistan', 'Asia/Kabul'),
    City('KHI', 'Karachi', 'Pakistan', 'Asia/Karachi'),
    City('DEL', 'Delhi', 'India', 'Asia/Kolkata'),
    City('KTM', 'Kathmandu', 'Nepal', 'Asia/Kathmandu'),
    City('DAC', 'Dhaka', 'Bangladesh', 'Asia/Dhaka'),
    City('RGN', 'Yangon', 'Burma', 'Asia/Rangoon'),
    City('BKK', 'Bangkok', 'Thailand', 'Asia/Bangkok'),
    City('SIN', 'Singapore', 'Singapore', 'Asia/Singapore'),
    City('HKG', 'Hong Kong', 'Hong Kong', 'Asia/Hong_Kong'),
    City('BJS', 'Beijing', 'China', 'Asia/Shanghai'),
    City('TPE', 'Taipei', 'Taiwan', 'Asia/Taipei'),
    City('SEL', 'Seoul', 'South Korea', 'Asia/Seoul'),
    City('TYO', 'Tokyo', 'Japan', 'Asia/Tokyo'),
    City('ADL', 'Adelaide', 'Australia', 'Australia/Adelaide'),
    City('GUM', 'Guam', '', 'Pacific/Guam'),
    City('SYD', 'Sydney', 'Australia', 'Australia/Sydney'),
    City('NOU', 'Noumea', 'New Caledonia', 'Pacific/Noumea'),
    City('WLG', 'Wellington', 'New Zealand', 'Pacific/Auckland'),
)


def load_state() -> dict:
    try:
        with open(FILENAME, 'r') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning('Could not load state from file %s: %s', FILENAME, e)
        return dict()


def save_state(state: dict):
    with open(FILENAME, 'w') as f:
        json.dump(state, f)


def notify(changed_cities):
    msg = EmailMessage()
    msg['From'] = FROM
    msg['To'] = TO
    msg['Subject'] = 'DST change notification'

    content = 'Hello,\n\n'
    for city in changed_cities:
        if is_dst(city.zonename):
            content += f'- {city.name} ({city.code}) turned DST ON\n'
        else:
            content += f'- {city.name} ({city.code}) turned DST OFF\n'
    msg.set_content(content)

    with smtplib.SMTP_SSL(SMTP_HOST, timeout=60) as s:
        s.login(SMTP_USER, SMTP_PASSWORD)
        s.send_message(msg)
    logger.info('Sent email notification to %s', TO)


def is_dst(zonename: str) -> bool:
    """Tell whether a timezone currently has DST enabled."""
    tz = pytz.timezone(zonename)
    now = pytz.utc.localize(datetime.utcnow())
    return now.astimezone(tz).dst() != timedelta(0)


def current_time(zonename: str) -> str:
    return datetime.now(pytz.timezone(zonename)).strftime('%H:%M')


def check_dst_change():
    """Check if any city enabled/disable DST since last check."""
    changed_cities = list()
    state = load_state()

    for city in CITIES:

        is_city_dst = is_dst(city.zonename)
        if is_city_dst == state.get(city.code):
            continue

        state[city.code] = is_city_dst
        changed_cities.append(city)
        logger.info('%s switched DST', city.name)

    if changed_cities:
        notify(changed_cities)
        save_state(state)
    else:
        logger.info('No DST change')


def daemon():
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s %(levelname)-5.5s %(name)s] %(message)s',
    )

    def handle_sig(*args):
        logger.info('Received signal, quitting')
        must_stop.set()

    signal.signal(signal.SIGTERM, handle_sig)
    signal.signal(signal.SIGINT, handle_sig)

    while not must_stop.is_set():
        try:
            check_dst_change()
        except Exception:
            logger.exception('Error while checking DST changes')

        must_stop.wait(DELAY)


def print_cities_list():
    for city in CITIES:
        print('{} {} {}'.format(
            city.code,
            'DST' if is_dst(city.zonename) else '   ',
            current_time(city.zonename)
        ))


def main():
    if len(sys.argv) == 2 and sys.argv[1] == 'list':
        return print_cities_list()

    else:
        return daemon()


if __name__ == '__main__':
    main()
