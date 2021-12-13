#!/usr/bin/env python3

import time
import argparse
from Windhager import Windhager
from influxdb import InfluxDBClient

parser = argparse.ArgumentParser()
parser.add_argument('--windhager', type=str, required=True, help='Windhager IP/Host')
parser.add_argument('--wuser', type=str, default='Service', help='Windhager Username')
parser.add_argument('--wpass', type=str, default='123', help='Windhager Password')
parser.add_argument('--influx', type=str, default='localhost', help='Influx Database Server')
parser.add_argument('--influxport', type=int, default=8086, help='Influx Database Server Port')
parser.add_argument('--db', type=str, required=True, help='Influx Database')
parser.add_argument('--dbuser', type=str, required=True, help='Influx Database User')
parser.add_argument('--dbpass', type=str, required=True, help='Influx Database Password')
parser.add_argument('--oids', type=str, default='oids.txt', help='File with list of OIDs')
parser.add_argument('--debug', action='store_true', help='Activate Debug')
args = parser.parse_args()

def push_influx(db, points):
    bodys = []
    for p in points:
        bodys.append({
            "measurement": f"windhager-{p[0]}",
            "fields": { 'value': p[1] }
        })
    db.write_points(bodys)

def loop(w, db, oids):
    while True:
        points = []
        dps = w.get_datapoints()
        w.log.debug(f"Got {len(dps)} Datapoints from API")
        for oid,key in oids.items():
            d = None
            for dp in dps:
                if dp['OID'] == '/' + oid:
                    d = dp
            if not d:
                w.log.warning("OID {oid} not found in datapoints, executing lookup")
                d = w.get_lookup(oid)
            if 'value' not in d:
                w.log.warning(f"Invalid data for {oid}: {dp}")
                continue

            name = w.id_to_string(key.split('-')[0], key.split('-')[1])
            try:
                value = float(d['value'])
            except:
                continue
            w.log.debug(f"got datapoint {name} {key} with {value}")
            if name:
                name = name.replace(' ','-')
                points.append((f"{key}-{name}", value))

        push_influx(db, points)
        w.log.info(f"pushed {len(points)} values to influxdb")

        # Wait for next minute to begin
        time.sleep(5)
        while (int(time.time()) % 60):
            time.sleep(1)

def main():
    level = 'INFO'
    if args.debug:
        level = 'DEBUG'
    w = Windhager(args.windhager, user=args.wuser, password=args.wpass, level=level)
    db = InfluxDBClient(args.influx, args.influxport, database=args.db, username=args.dbuser, password=args.dbpass)
    oids = {}
    with open(args.oids, 'r') as fd:
        lines = fd.readlines()
        for line in lines:
            split = line.split(',')
            oids[split[0]] = split[1]

    w.log.info("Initialization done")

    loop(w, db, oids)

if __name__ == '__main__':
    main()

