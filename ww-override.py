#!/usr/bin/env python3

import time
import math
import os
import sys
import argparse
import requests
import Windhager

parser = argparse.ArgumentParser()
parser.add_argument('--windhager', type=str, required=True, help='Windhager IP/Host')
parser.add_argument('--tasmota', type=str, required=True, help='Tasmota IP/Host')
parser.add_argument('--wwmin', type=int, default=42, help='Minimum WW-Temperature')
parser.add_argument('--wwmax', type=int, default=70, help='Maximum WW-Temperature')
parser.add_argument('--kesselmax', type=int, default=75, help='Maximum Kessel-Temperature')
parser.add_argument('--kesselmin', type=int, default=65, help='Minimum Kessel-Temperature')
parser.add_argument('--leistungmin', type=int, default=45, help='Minimal Kessel-Leistung')
parser.add_argument('--leistungmax', type=int, default=95, help='Maximale Kessel-Leistung')
args = parser.parse_args()


def get_current_state(leistung, kessel, ww, now):
    # Kessel ist AN
    if leistung > 0 and kessel > 45:
        # Einschalten WW
        if ww < args.wwmin:
            return 'ON'
        if kessel > args.kesselmax and ww < args.wwmax:
            return 'ON'
        if leistung < args.leistungmin and ww < args.wwmax:
            return 'ON'

        # Ausschalten WW
        if kessel < args.kesselmin:
            return 'OFF'
        if leistung > args.leistungmax:
            return 'OFF'

    return 'OFF'

def set_tasmota_state(state):
    r = requests.get(f"http://{args.tasmota}/cm", params={'cmnd': f'Power1 {state}'})
    if r.status_code != 200:
        print(f"ERROR setting status to {state} on {args.tasmota}")

def init():
    Windhager.init(args.windhager)

def loop():
    print(f"\t\tOverride\tLeistung\tKessel\tWW")
    last_state = 'OFF'
    while True:
        leistung_ist = float(Windhager.get_datapoint('1/60/0/0/9/0')['value'])
        kessel_ist = float(Windhager.get_datapoint('1/60/0/0/7/0')['value'])
        ww_ist = float(Windhager.get_datapoint('1/15/0/0/4/0')['value'])
        now = time.localtime()
        nowstr = time.strftime("%H:%M:%S", now)

        new_state = get_current_state(leistung_ist, kessel_ist, ww_ist, now)
        set_tasmota_state(new_state)
        if new_state != last_state:
            last_state = new_state

        print(f"{nowstr}\t{new_state}\t\t{leistung_ist}\t\t{kessel_ist}\t{ww_ist}")

        time.sleep(15)
def main():
    mq = init()
    loop()

main()
