#!/usr/bin/env python3

import argparse
import time
import requests
from Windhager import Windhager

parser = argparse.ArgumentParser()
parser.add_argument('--windhager', type=str, required=True, help='Windhager IP/Host')
parser.add_argument('--wuser', type=str, default='Service', help='Windhager Username')
parser.add_argument('--wpass', type=str, default='123', help='Windhager Password')
parser.add_argument('--tasmota', type=str, required=True, help='Tasmota IP/Host')
parser.add_argument('--debug', action='store_true', help='Activate Debug')
args = parser.parse_args()

CONFIG = {
    'ww_on':        49,
    'ww_off':       53,
    'ww_max':       65,
    'kessel_min':   65,
    'kessel_max':   75,
    'leistung_min': 35,
    'leistung_max': 95
}

def get_current_state(w, last_state, leistung, kessel, ww, now):
    # Highest prio: if WW is too hot
    if ww > CONFIG['ww_max']:
        w.log.info(f"WW > {CONFIG['ww_max']} -> turning OFF")
        return 'OFF'

    # Kessel ist AN
    if leistung > 0 and kessel > ww and last_state == 'OFF':
        # Einschalten WW
        if ww < CONFIG['ww_on']:
            w.log.info(f"WW < {CONFIG['ww_on']} -> turning ON")
            return 'ON'
        if kessel > CONFIG['kessel_max']:
            w.log.info(f"Kessel > {CONFIG['kessel_max']} -> turning ON")
            return 'ON'
        if leistung < CONFIG['leistung_min']:
            w.log.info(f"Leistung < {CONFIG['leistung_min']} -> turning ON")
            return 'ON'
    elif last_state == 'ON':
        # Ausschalten WW
        if leistung == 0:
            return 'OFF'
        if ww > CONFIG['ww_off']:
            if kessel < CONFIG['kessel_min']:
                w.log.info(f"Kessel < {CONFIG['kessel_min']} -> turning OFF")
                return 'OFF'
            if leistung > CONFIG['leistung_max']:
                w.log.info(f"Leistung > {CONFIG['leistung_max']} -> turning OFF")
                return 'OFF'
    return None

def set_tasmota_state(w, state):
    if state not in ['ON', 'OFF']:
        w.log.info(f"unknown state {state}")
        state = 'OFF'
    for i in range(8):
        r = requests.get(f"http://{args.tasmota}/cm", params={'cmnd': f'Power1 {state}'})
        if r.status_code == 200:
            return

        w.log.error(f"setting status to {state} on {args.tasmota} failed!")
        sys.exit(1)

def loop(w):
    last_state = 'OFF'
    while True:
        leistung_ist = float(w.get_datapoint('1/60/0/0/9/0')['value'])
        kessel_ist = float(w.get_datapoint('1/60/0/0/7/0')['value'])
        ww_ist = float(w.get_datapoint('1/15/0/0/4/0')['value'])
        now = time.localtime()
        nowstr = time.strftime("%H:%M:%S", now)

        w.log.debug(f"last_state={last_state} leistung={leistung_ist} kessel={kessel_ist} ww={ww_ist}")

        new_state = get_current_state(w, last_state, leistung_ist, kessel_ist, ww_ist, now)
        if new_state:
            w.log.info(f"set {args.tasmota} to {new_state}")
            if new_state != last_state:
                last_state = new_state
        # Just set it always to be sure not to get in unknown state for some time
        set_tasmota_state(w, last_state)
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

