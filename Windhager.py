import sys
import time
import json
import xml.etree.ElementTree as etree
import requests
from requests.auth import HTTPDigestAuth

this = sys.modules[__name__]
this.ip = None

this.user = 'Service'
this.pw = '123'

######### Constants

##  Allgemein
LOOKUP = 'api/1.0/lookup/'

## Fehlerlog
FEHLERLOG_API = 'InfoWinFehlerlog/api/1.0'
WINDYNDATA_API = 'WsFUP7030/api/1.0'
LOOKUP_API = 'api/1.0/lookup'
DATAPOINT_API = 'api/1.0/datapoint'

######### Functions

## INIT
def init(ip, user = 'Service', pw = '123'):
    this.url = 'http://' + ip
    this.session = requests.session()
    this.session.auth = HTTPDigestAuth(this.user, this.pw)
    this.xml = None
    this.init_xml()

def init_xml():
    resp = this.request_get('res/xml/VarIdentTexte_de.xml')
    this.xml = etree.fromstring(resp.text.encode('utf-8'))

def request_get(url, params = None):
    return this.session.get(f"{this.url}/{url}", params = params)

def request_put(url, data, headers):
    return this.session.put(f"{this.url}/{url}",
            data=json.dumps(data),
            headers = headers)

def request_delete(url):
    return this.session.delete(f"{this.url}/{url}")

def get_xml():
    return this.xml

def get_name(gn, mn):
    gn = int(gn)
    mn = int(mn)
    if (this.xml is None):
        return "unknown"
    e = this.xml.find('gn[@id="' + str(gn) + '"]/mn[@id="' + str(mn) + '"]')
    if e is not None:
        if e.text is not None:
            return e.text
    return None

## Basic requests wrapper
def _get (api, params = None):
    resp = this.request_get(api, params = params)
    return resp.text

def _jget (api, params = None):
    res = _get(api, params)
    return json.loads(res)

def _put (api, data, headers = None):
    if not headers:
        headers = {'Content-Type': "text/plain; charset=UTF-8"}
    resp = this.request_put(api, data, headers)
    return resp

def _del (api, data):
    resp = this.request_delete(api)
    return resp

## Fehlerlog API Wrappers
def get_fehlerlog ():
    return _jget(FEHLERLOG_API + 'fehlerlog')

def del_fehlerlog (id):
    fl = get_fehlerlog()
    if (id not in fl):
        return None

    data = {'id': id}
    return _del(FEHLERLOG_API + 'fehlerlog', data)

def lvl_fehlerlog ():
    pass

## WsFUP7030 API Wrappers
def getWindyndataReadDapDapId (subnet, node, dap):
    return _jget(WINDYNDATA_API + '/windyndata/' + subnet + '/' + node + '/2/' + dap)

## Lookup API Wrappers
def get_lookup(obj):
    return _jget(f"{LOOKUP_API}{obj}")

def get_lookup_all():
    ret = []
    for api in ['1/15/0', '1/60/0', '1/90/0']:
        nodes = get_lookup(api)
        for node in nodes:
            tmp = f"{api}/{node['id']}"
            fcts = get_lookup(tmp)
            for fct in fcts:
                ret.append(fct)
    return ret

def get_datapoint(p):
    return _jget(DATAPOINT_API + p)

def get_datapoints():
    jget = _jget('api/1.0/datapoints')
    res = []
    for p in jget:
        name = ""
        value = ""
        oid = ""
        if 'name' not in p:
            res.append(p)
            continue
        name = p['name']
        aname = name.split('-')

        text = get_name(int(aname[0]), int(aname[1]))
        if (text is not None):
            p['text'] = text.lower().replace(' ', '-').replace('ä', "ae").replace('ö', "oe").replace('ü', "ue").replace('ß', 's')

        res.append(p)
    return res
