#!/usr/bin/env python3

import time
import math
import os
import sys
import syslog
import argparse
import requests
import Windhager

parser = argparse.ArgumentParser()
parser.add_argument('--windhager', type=str, required=True, help='Windhager IP/Host')
parser.add_argument('--tasmota', type=str, required=True, help='Tasmota IP/Host')
parser.add_argument('--wwmin', type=int, default=52, help='Minimum WW-Temperature')
parser.add_argument('--wwmax', type=int, default=55, help='Maximum WW-Temperature')
parser.add_argument('--kesselmax', type=int, default=75, help='Maximum Kessel-Temperature')
parser.add_argument('--kesselmin', type=int, default=65, help='Minimum Kessel-Temperature')
parser.add_argument('--leistungmin', type=int, default=45, help='Minimal Kessel-Leistung')
parser.add_argument('--leistungmax', type=int, default=90, help='Maximale Kessel-Leistung')
args = parser.parse_args()
syslog.openlog(facility=syslog.LOG_DAEMON)

syslog.syslog(f"started for {args.windhager} with tasmota {args.tasmota}")
syslog.syslog(f"WW-min {args.wwmin} WW-max: {args.wwmax}")
syslog.syslog(f"Kessel-min {args.kesselmin} Kessel-max: {args.kesselmax}")
syslog.syslog(f"Leistung-min {args.leistungmin} Leistung-max: {args.leistungmax}")

def get_current_state(last_state, leistung, kessel, ww, now):
    # Kessel ist AN
    if leistung > 0 and kessel > ww:
        if  last_state == 'OFF':
        # Einschalten WW
            if ww < args.wwmin:
                syslog.syslog(syslog.LOG_INFO, f"WW < {args.wwmin} -> turning ON")
                return 'ON'
            if kessel > args.kesselmax and ww < args.wwmax:
                syslog.syslog(syslog.LOG_INFO, f"Kessel > {args.kesselmax} -> turning ON")
                return 'ON'
            if leistung < args.leistungmin and ww < args.wwmax:
                syslog.syslog(syslog.LOG_INFO, f"Leistung < {args.leistungmin} -> turning ON")
                return 'ON'

        else:
            # Ausschalten WW
            if ww > args.wwmax:
                if kessel < args.kesselmin:
                    syslog.syslog(syslog.LOG_INFO, f"Kessel < {args.kesselmin} -> turning OFF")
                    return 'OFF'
                if leistung > args.leistungmax:
                    syslog.syslog(syslog.LOG_INFO, f"Leistung > {args.leistungmax} -> turning OFF")
                    return 'OFF'
            if ww > 72:
                syslog.syslog(syslog.LOG_INFO, f"WW > 72 -> turning OFF")
                return 'OFF'
    if leistung == 0 and last_state == 'ON':
        return 'OFF'
    return None

def set_tasmota_state(state):
    for i in range(8):
        r = requests.get(f"http://{args.tasmota}/cm", params={'cmnd': f'Power1 {state}'})
        if r.status_code == 200:
            return
        else:
            syslog.syslog(syslog.LOG_ERROR, f"setting status to {state} on {args.tasmota} failed! retry")
        sys.exit(1)

def init():
    Windhager.init(args.windhager)

def loop():
    last_state = 'OFF'
    while True:
        leistung_ist = float(Windhager.get_datapoint('/1/60/0/0/9/0')['value'])
        kessel_ist = float(Windhager.get_datapoint('/1/60/0/0/7/0')['value'])
        ww_ist = float(Windhager.get_datapoint('/1/15/0/0/4/0')['value'])
        now = time.localtime()
        nowstr = time.strftime("%H:%M:%S", now)

        new_state = get_current_state(last_state, leistung_ist, kessel_ist, ww_ist, now)
        if new_state:
            syslog.syslog(syslog.LOG_INFO, f"set {args.tasmota} to {new_state}")
            if new_state != last_state:
                last_state = new_state
        # Just set it always to be sure not to get in unknown state for some time
        set_tasmota_state(last_state)
        time.sleep(20)

def main():
    mq = init()
    loop()

main()
