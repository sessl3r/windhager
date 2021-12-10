#!/usr/bin/env python3

import time
import math
import os
import sys
import argparse
import syslog
import Windhager

from influxdb import InfluxDBClient

OIDS = []

parser = argparse.ArgumentParser()
parser.add_argument('--windhager', type=str, required=True, help='Windhager IP/Host')
parser.add_argument('--db', type=str, required=True, help='Influx Database')
parser.add_argument('--dbuser', type=str, required=True, help='Influx Database User')
parser.add_argument('--dbpass', type=str, required=True, help='Influx Database Password')
parser.add_argument('--oids', type=str, default='oids.txt', help='File with list of OIDs')
args = parser.parse_args()

client = InfluxDBClient('localhost', 8086, database=args.db, username=args.dbuser, password=args.dbpass)
syslog.openlog(facility=syslog.LOG_DAEMON)

def push_influx(points):
    bodys = []
    for p in points:
        bodys.append({
            "measurement": f"windhager-{p[0]}",
            "fields": { 'value': p[1] }
        })
    client.write_points(bodys)

def init():
    global OIDS
    with open(args.oids, 'r') as fd:
        lines = fd.readlines()
    OIDS = [line.split(',')[0].rstrip() for line in lines]

    Windhager.init(args.windhager)
    Windhager.init_xml()

def loop():
    while True:
        points = []
        for oid in OIDS:
            dp = Windhager.get_lookup(oid)
            if 'name' not in dp:
                continue
            if 'value' not in dp:
                continue
            key = f"{dp['groupNr']}-{dp['memberNr']}"
            try:
                value = float(dp['value'])
            except:
                continue
            name = Windhager.get_name(dp['groupNr'], dp['memberNr'])
            if name:
                name = name.replace(' ','-')
                points.append((f"{key}-{name}", value))

        syslog.syslog(syslog.LOG_INFO, f"pushing {len(points)} values to influxdb")
        push_influx(points)
        while (int(time.time()) % 60):
            time.sleep(1)

def main():
    mq = init()
    syslog.syslog(syslog.LOG_INFO, "service started")
    loop()

main()
