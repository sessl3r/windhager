#!/usr/bin/env python3.9

import time
import json
import argparse
import logging
from Windhager import Windhager
from influxdb import InfluxDBClient
import paho.mqtt.client as paho

MQTT_BASE_TOPIC = "stat/windhager"
MQTT_STATE = "state"
MQTT_LWT = "lwt"

parser = argparse.ArgumentParser()
parser.add_argument('--windhager', type=str, required=True, help='Windhager IP/Host')
parser.add_argument('--wuser', type=str, default='Service', help='Windhager Username')
parser.add_argument('--wpass', type=str, default='123', help='Windhager Password')
parser.add_argument('--influx', type=str, default='localhost', help='Influx Database Server')
parser.add_argument('--influxport', type=int, default=8086, help='Influx Database Server Port')
parser.add_argument('--db', type=str, required=True, help='Influx Database')
parser.add_argument('--dbuser', type=str, required=True, help='Influx Database User')
parser.add_argument('--dbpass', type=str, required=True, help='Influx Database Password')
parser.add_argument('--mqtt', type=str, default='localhost', help='MQTT Broker URL')
parser.add_argument('--muser', type=str, required=True, help='MQTT User')
parser.add_argument('--mpass', type=str, required=True, help='MQTT Password')
parser.add_argument('--oids', type=str, default='oids.txt', help='File with list of OIDs')
parser.add_argument('--debug', action='store_true', help='Activate Debug')
args = parser.parse_args()

def poll_windhager_values(w, oids):
    points = []
    for oid,entry in oids.items():
        if 'name' not in entry:
            w.log.warning(f"Invalid config for {oid} : {entry}")
            continue
        key = entry['name']

        d = w.get_datapoint(oid)
        if 'value' not in d:
            w.log.warning(f"Invalid data for {oid}: {dp}")
            continue

        #name = w.id_to_string(key.split('-')[0], key.split('-')[1])
        if 'text' in entry:
            name = entry['text'].replace(".", "").replace(" ", "_")
        else:
            name = "unknown"

        #TODO: float vs int vs string vs date?
        #  can not change as most value already as float in influxdb
        try:
            if 'minValue' in d and 'maxValue' in d:
                if (d['minValue'] == 0 and d['maxValue'] == 1):
                    value = int(d['value'])
                else:
                    value = float(d['value'])
            else:
                value = float(d['value'])
        except Exception as exc:
            w.log.warning(f"can not convert datapoint {oid}:{name} value {d['value']} {type(d['value'])}")
            w.log.warning(f"entry: {d}")
            w.log.warning(f"exception: {exc}")
            continue
        w.log.debug(f"got datapoint {name} {key} with {value}")
        points.append((key, name, value))

    return points

def influx_push(db, points):
    bodys = []
    for p in points:
        bodys.append({
            "measurement": f"windhager-{p[0]}-{p[1]}",
            "fields": { 'value': p[2] }
        })
    db.write_points(bodys)

def mqtt_push_values(mqtt, points):
    values = {}
    for p in points:
        text = p[1].lower().replace(".", "").replace("-", "_").replace("ö", "oe").replace("ä", "ae").replace("ü", "ue").replace("ß", "s")
        oid = p[0].lower().replace("-", "_")
        name =  f"{text}_{oid}"
        values[name] = p[2]

    mqtt.publish(f"{MQTT_BASE_TOPIC}/{MQTT_STATE}" , json.dumps(values))

def mqtt_push_discovery(w, mqtt, oids):
    for k, oidarr in oids.items():
        text = oidarr["text"].lower().replace(".", "").replace("-", "_").replace("ö", "oe").replace("ä", "ae").replace("ü", "ue").replace("ß", "s")
        oid = oidarr["name"].lower().replace("-", "_")
        name = f"windhager_{text}_{oid}"
        if "einheit" in oidarr:
            einheit = oidarr["einheit"]
        else:
            einheit = ""
        config = {
            "~": MQTT_BASE_TOPIC,
            "name": name,
            "device": {
                "model": "BioWin2",
                "identifiers": MQTT_BASE_TOPIC,
                "name": "Windhager"
            },
            "unique_id": f"{MQTT_BASE_TOPIC}" + text,
            "state_topic": f"~/{MQTT_STATE}",
            "value_template": "{{ value_json['" + f"{text}_{oid}" + "'] }}"
        }

        if einheit == "Binary":
            config["device_class"] = "power"
            config["payload_on"] = "1.0"
            config["payload_off"] = "0.0"
            mqtt.publish(f'homeassistant/binary_sensor/{name}/config', json.dumps(config))
        elif einheit == "State":
            if text == "betriebsphasen":
                config["value_template"] = "\
                    {% set mapper = {'0': 'Brenner gesperrt', '1': 'Selbsttest', '2': 'WE ausschalten', '3': 'Standby', '4': 'Brenner AUS', '5': 'Vorspülen', '6': 'Zündphase', '7': 'Flammenstabilisierung', '8': 'Modulationsbetrieb', '9': 'Kessel gesperrt', '10': 'Standby Sperrzeit', '11': 'Gebläse AUS', '12': 'Verkleidungstür offen', '13': 'Zündung bereit', '14': 'Abbruch Zündphase', '15': 'Anheizvorgang', '16': 'Schichtladung', '17': 'Ausbrand'} %} \
                    {% set state = int(value_json['" + f"{text}_{oid}" + "']) %} \
                    {{ mapper[state] if state in mapper else 'Unknown' }}"
            elif text == "betriebswahl":
                config["value_template"] = "\
                    {% set mapper = {'0': 'Standby', '1': 'Heizprogramm 1', '2': 'Heizprogramm 2', '3': 'Heizprogramm 3', '4': 'Heizbetrieb', '5': 'Absenkbetrieb', '6': 'Warmwasserbetrieb'} %} \
                    {% set state = int(value_json['" + f"{text}_{oid}" + "']) %} \
                    {{ mapper[state] if state in mapper else 'Unknown' }}"                
            else:
                logging.warning(f"Unknwon state variable: {oidarr}")
                continue
            mqtt.publish(f'homeassistant/sensor/{name}/config', json.dumps(config))
        else:
            config["unit_of_measurement"] = einheit
            mqtt.publish(f'homeassistant/sensor/{name}/config', json.dumps(config))

        logging.debug(config)

def mqtt_on_publish(client, userdata, result):
    pass

def mqtt_on_message(client, userdata, message):
    w = client.windhager
    try:
        data = json.loads(message.payload)
    except Excetion as e:
        logging.error(f"Malformed JSON data {message.payload}")
        return
    if message.topic == "windhager/put/datapoint":
        if not 'OID' in data:
            logging.error(f"No OID in data {data}")
            return
        if not 'value' in data:
            logging.error(f"No value in data {data}")
            return
        oid = data['OID']
        value = data['value']
        if len(oid.split('/')) < 5:
            logging.error(f"Malformed OID '{oid}'")
            return
        try:
            logging.info(f"old value {oid} = {w.get_datapoint(oid)['value']}")
        except:
            logging.error(f"Failed to get datapoint for OID {oid}")
            return

        try:
            w.set_datapoint(oid, value)
        except:
            logging.error(f"Failed to set datapoint for OID {oid} to {value}")
            return

        logging.info(f"new value {oid} = {value}")

def mqtt_on_connect(client, userdata, flags, rc):
    logging.info("Connected to MQTT broker")
    client.publish(f"{MQTT_BASE_TOPIC}/{MQTT_LWT}", payload="Online", qos=0, retain=True)

def loop(w, db, mqtt, oids):
    last_discovery = 0
    while True:
        points = poll_windhager_values(w, oids)
        influx_push(db, points)

        if (time.time() - last_discovery > 900):
            logging.info("Pushing discovery data")
            mqtt_push_discovery(w, mqtt, oids)
            last_discovery = time.time()

        mqtt_push_values(mqtt, points)

        # Wait for next 1/4 minute
        time.sleep(1)
        while (int(time.time()) % 15):
            time.sleep(1)

def main():
    level = 'INFO'
    if args.debug:
        level = 'DEBUG'
    logging.basicConfig(level=level)
    w = Windhager(args.windhager, user=args.wuser, password=args.wpass, level=level)
    db = InfluxDBClient(args.influx, args.influxport, database=args.db, username=args.dbuser, password=args.dbpass)
    mqtt = paho.Client("windhager")
    mqtt.windhager = w
    mqtt.on_publish = mqtt_on_publish
    mqtt.on_message = mqtt_on_message
    mqtt.on_connect = mqtt_on_connect
    mqtt.username_pw_set(args.muser, args.mpass)
    mqtt.will_set(f"{MQTT_BASE_TOPIC}/{MQTT_LWT}", payload="offline", retain=True, qos=0)
    mqtt.connect(args.mqtt, keepalive=60)
    mqtt.subscribe('windhager/put/datapoint')

    oids = {}
    with open(args.oids, 'r') as fd:
        lines = fd.readlines()
        for line in lines:
            line = line.split('#', 1)[0].rstrip()
            split = line.split(',')
            if len(split) < 2:
                continue
            oids[split[0]] = {}
            if len(split) > 1:
                oids[split[0]]['name'] = split[1].rstrip()
            if len(split) > 2:
                oids[split[0]]['text'] = split[2].rstrip()
            if len(split) > 4:
                oids[split[0]]['einheit'] = split[4].rstrip()

    logging.info("Initialization done")

    mqtt.loop_start()
    loop(w, db, mqtt, oids)

if __name__ == '__main__':
    main()
