#!/usr/bin/env python3

import argparse
import time
import requests
import paho.mqtt.client as paho
from Windhager import Windhager

parser = argparse.ArgumentParser()
parser.add_argument('--windhager', type=str, required=True, help='Windhager IP/Host')
parser.add_argument('--wuser', type=str, default='Service', help='Windhager Username')
parser.add_argument('--wpass', type=str, default='123', help='Windhager Password')
parser.add_argument('--mqtt', type=str, required=True, help='MQTT Broker')
parser.add_argument('--muser', type=str, required=True, help='MQTT Username')
parser.add_argument('--mpass', type=str, required=True, help='MQTT Password')
parser.add_argument('--mtopic', type=str, required=True, help='MQTT Topic')
parser.add_argument('--debug', action='store_true', help='Activate Debug')
args = parser.parse_args()

CONFIG = {
    'ww_on':        48,
    'ww_off':       54,
    'ww_max':       60,
    'kessel_min':   65,
    'kessel_max':   75,
    'leistung_min': 40,
    'leistung_max': 95
}

def get_current_state(w, last_state, leistung, kessel, ww, heizkreispumpe, now):
    #
    #  Pumpe ist AUS
    #
    if last_state == 'OFF':
        if leistung > 0 and kessel > ww and ww < CONFIG['ww_max']:
            if ww < CONFIG['ww_on']:
                w.log.info(f"WW < {CONFIG['ww_on']} -> turning ON")
                return 'ON'
            if kessel > CONFIG['kessel_max']:
                w.log.info(f"Kessel > {CONFIG['kessel_max']} -> turning ON")
                return 'ON'
            if leistung < CONFIG['leistung_min']:
                w.log.info(f"Leistung < {CONFIG['leistung_min']} -> turning ON")
                return 'ON'
        # Kessel aus und Heizkreispumpe aus -> Sommerbetrieb - Restwärme nutzen
        elif leistung == 0 and heizkreispumpe == 0 and kessel > ww + 5:
            w.log.info("Sommerbetrieb - Restwärme -> turning ON")
            return 'ON'
    #
    # WW Pumpe ist AN
    #
    elif last_state == 'ON':
        if leistung == 0 and (heizkreispumpe != 0 or kessel < ww + 3):
            w.log.info(f"Leistung == 0 -> turning OFF")
            return 'OFF'
        if ww > CONFIG['ww_max']:
            w.log.info(f"WW > {CONFIG['ww_max']} -> turning OFF")
            return 'OFF'
        if (ww > CONFIG['ww_off']) and (leistung > CONFIG['leistung_max']):
                w.log.info(f"Leistung > {CONFIG['leistung_max']} -> turning OFF")
                return 'OFF'
    return None

def set_mqtt_state(w, state):
    if state not in ['ON', 'OFF']:
        w.log.info(f"unknown state {state}")
        state = 'OFF'

    try:
        client = paho.Client()
        client.username_pw_set(username=args.muser, password=args.mpass)
        client.connect(args.mqtt, keepalive=10)
        client.publish(args.mtopic, state)
        client.disconnect()
    except Exception as e:
        w.log.error(f"setting status to {state} on {args.mtopic} failed!")
        w.log.error(f"{e}")

def loop(w):
    last_state = 'OFF'
    while True:
        leistung_ist = float(w.get_datapoint('1/60/0/0/9/0')['value'])
        kessel_ist = float(w.get_datapoint('1/60/0/0/7/0')['value'])
        ww_ist = float(w.get_datapoint('1/15/0/0/4/0')['value'])
        heizkreispumpe = float(w.get_datapoint('1/15/0/1/20/0')['value'])
        now = time.localtime()
        nowstr = time.strftime("%H:%M:%S", now)

        w.log.debug(f"last_state={last_state} leistung={leistung_ist} kessel={kessel_ist} ww={ww_ist} heizkreispumpe={heizkreispumpe}")

        new_state = get_current_state(w, last_state, leistung_ist, kessel_ist, ww_ist, heizkreispumpe, now)
        if new_state:
            w.log.info(f"set {args.mtopic} to {new_state}")
            if new_state != last_state:
                last_state = new_state
        # Just set it always to be sure not to get in unknown state for some time
        set_mqtt_state(w, last_state)
        time.sleep(20)

def main():
    level = 'INFO'
    if args.debug:
        level = 'DEBUG'
    w = Windhager(args.windhager, user=args.wuser, password=args.wpass, level=level)

    w.log.info("Initialization done")

    loop(w)

if __name__ == '__main__':
    main()

