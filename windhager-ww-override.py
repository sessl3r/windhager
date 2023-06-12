#!/usr/bin/env python3.9

import argparse
import time
import logging
import json
import paho.mqtt.client as paho

parser = argparse.ArgumentParser()
parser.add_argument('--mqtt', type=str, default='localhost', help='MQTT Broker')
parser.add_argument('--muser', type=str, required=True, help='MQTT Username')
parser.add_argument('--mpass', type=str, required=True, help='MQTT Password')
parser.add_argument('--mwindhager', type=str, default='stat/windhager/state', help='MQTT Windhager')
parser.add_argument('--mswitch', type=str, required=True, help='MQTT Switch Topic')
parser.add_argument('--debug', action='store_true', help='Activate Debug')
args = parser.parse_args()

CONFIG = {
    'ww_on':        48,
    'ww_off':       52,
    'ww_max':       62,
    'kessel_min':   65,
    'kessel_max':   75,
    'leistung_min': 40,
    'leistung_max': 95
}

def get_current_state(last_state, leistung, kessel, kessel_soll, ww, heizkreispumpe):
    #
    #  Pumpe ist AUS
    #
    if last_state == 'OFF':
        if ( (leistung > 0) and (kessel > ww) and (ww < CONFIG['ww_max']) and  (kessel > (kessel_soll-2))):
            if ww < CONFIG['ww_on']:
                logging.info("WW < {} -> turning ON".format(CONFIG['ww_on']))
                return 'ON'
            if kessel > CONFIG['kessel_max']:
                logging.info("Kessel > {} -> turning ON".format(CONFIG['kessel_max']))
                return 'ON'
            if leistung < CONFIG['leistung_min']:
                logging.info("Leistung < {} -> turning ON".format(CONFIG['leistung_min']))
                return 'ON'
        # Kessel aus und Heizkreispumpe aus -> Sommerbetrieb - Restwärme nutzen
        elif leistung == 0 and heizkreispumpe == 0 and kessel > ww + 5 and ww < (CONFIG['ww_max'] - 4):
            logging.info("Sommerbetrieb - Restwärme -> turning ON (leistung: {} kessel: {} ww: {})".format(leistung, kessel, ww))
            return 'ON'
    #
    # WW Pumpe ist AN
    #
    elif last_state == 'ON':
        if leistung == 0 and (heizkreispumpe != 0 or kessel < ww + 3):
            logging.info("Leistung == 0 -> turning OFF (leistung: {} kessel: {} ww: {})".format(leistung, kessel, ww))
            return 'OFF'
        if ww > CONFIG['ww_max']:
            logging.info("WW > {} -> turning OFF".format(CONFIG['ww_max']))
            return 'OFF'
        if (ww > CONFIG['ww_off']) and (leistung > CONFIG['leistung_min']):
                logging.info("Leistung > {} -> turning OFF".format(CONFIG['leistung_min']))
                return 'OFF'
    return None

def mqtt_on_connect(client, userdata, flags, rc):
    """ on connect subscribe to updates from windhager-proxy """
    client.subscribe(args.mwindhager)
    logging.info("initialization done, subscribed to {}".format(args.mwindhager))

def mqtt_on_message(client, userdata, msg):
    if msg.topic == 'stat/windhager/state':
        try:
            data = json.loads(msg.payload.decode('utf-8'))
        except Exception as e:
            logging.error("Failed to parse data {} with {}".format(msg.payload, e))
            return
        try:
            leistung_ist = data['aktuelle_kesselleistung_0_9']
            kessel_ist = data['kesseltemperatur_istwert_0_7']
            kessel_soll = data['solltemperatur_1_7']
            ww_ist = data['aktueller_wert_0_4']
            heizkreispumpe = data['heizkreispumpe_1_20']
        except Exception as e:
            logging.error("KeyError while extracting data {}".format(e))
            return

        logging.debug("last_state={} leistung={} kessel_ist={} kessel_soll={} ww={} heizkreispumpe={}".format(client.ww_state, leistung_ist, kessel_ist, kessel_soll, ww_ist, heizkreispumpe))

        new_state = get_current_state(client.ww_state, leistung_ist, kessel_ist, kessel_soll, ww_ist, heizkreispumpe)
        if new_state:
            client.ww_state = new_state
#            logging.debug(f"new_state: {client.ww_state}")
        if client.ww_state not in ['ON', 'OFF']:
#            logging.info(f"unknown state {client.ww_state}, defaulting of 'OFF'")
            client.ww_state = 'OFF'
        try:
            client.publish(args.mswitch, client.ww_state)
        except Exception as e:
            pass
            logging.error("setting status to {} on {} failed! {}".format(client.ww_state, args.mswitch, e))

def main():
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Connect to MQTT broker
    client = paho.Client()
    client.on_connect = mqtt_on_connect
    client.on_message = mqtt_on_message
    client.username_pw_set(username=args.muser, password=args.mpass)
    client.connect(args.mqtt)
    # Set inital state for WW override to OFF
    client.ww_state = 'OFF'
    client.publish(args.mswitch, client.ww_state)
    logging.info("Init done...")
    client.loop_forever()

if __name__ == '__main__':
    main()
