#!/usr/bin/env python3

import time
import math
import os
import sys
import syslog
import Windhager

from influxdb import InfluxDBClient

BLACKLIST = [
    "20-108"
]

windhager_ip = os.getenv('WINDHAGER_IP')
db = os.getenv('INFLUX_DB')
user = os.getenv('INFLUX_USER')
password = os.getenv('INFLUX_PASS')

client = InfluxDBClient('localhost', 8086, db, user, password)

syslog.openlog(facility=syslog.LOG_DAEMON)

def push_influx(points):
    body = {
        "measurement": "windhager",
        "fields": { }
    }
    for p in points:
        try:
            value = float(p[1])
        except:
            continue
        body['fields'][p[0]] = value

    client.write_points([body])

def init():
    Windhager.init(windhager_ip)
    Windhager.init_xml()
    # Force all values into cache to be present in datapoints
    Windhager.get_lookup_all()

def loop():
    while True:
        points = []
        dps = Windhager._jget("api/1.0/datapoints")
        for dp in dps:
            if not 'OID' in dp:
                continue
            xdp = Windhager._jget("api/1.0/datapoint" + dp['OID'])
            if (not 'groupNr' in xdp or not 'memberNr' in xdp):
                continue
            name = Windhager.get_name(xdp['groupNr'], xdp['memberNr'])
            key = f"{xdp['groupNr']}-{xdp['memberNr']}"
            if name:
                key = f"{key}-{name}"
            if 'value' in xdp:
                value = xdp['value']
            else:
                value = None
            if value:
                if key not in BLACKLIST:
                    points.append((key.replace(' ','-'),value))

        syslog.syslog(syslog.LOG_INFO, f"pushing {len(points)} values to influxdb")
        push_influx(points)
        while (int(time.time()) % 60):
            time.sleep(1)

def main():
    mq = init()
    syslog.syslog(syslog.LOG_INFO, "service started")
    loop()

main()
