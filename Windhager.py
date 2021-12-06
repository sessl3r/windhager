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
LOOKUP_API = 'api/1.0/lookup/1'
DATAPOINT_API = 'api/1.0/datapoint/1'

######### Functions

## INIT
def init(ip, user = 'Service', pw = '123'):
    this.url = 'http://' + ip + '/'
    this.xml = None
    this.init_xml()

def init_xml():
    resp = this.request_get('res/xml/VarIdentTexte_de.xml')
    this.xml = etree.fromstring(resp.text.encode('utf-8'))

def request_get(url, params = None):
    return requests.get(this.url + url, params = params, auth=HTTPDigestAuth(this.user, this.pw))

def request_put(url, data, headers):
    return requests.put(this.url + url,
            data=json.dumps(data),
            headers = headers,
            auth=HTTPDigestAuth(this.user, this.pw))

def request_delete(url):
    return requests.delete(this.url + url, auth=HTTPDigestAuth(this.user, this.pw))

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
def get_lookup(objs):
    ret = []
    for o in objs:
        ret.append(_jget(LOOKUP_API + o))
    return ret


def get_lookup_all():
    jtop = get_lookup([''])[0]
    nodes = []
    subnodes = []
    objects = []
    for t in jtop:
        n = '/' + str(t['nodeId']) + '/0'
        nodes.append(n)

    jnode = get_lookup(nodes)
    for n in nodes:
        for j in jnode:
            for jid in j:
                s = n + '/' + str(jid['id'])
                subnodes.append(s)

    oids = []
    i = 0
    for s in subnodes:
        res = get_lookup([s])[0]
        i = i + 1
        if (i > 10):
            break
        for r in res:
            if 'OID' not in r:
                print(r)
                continue
            else:
                oids.append(r['OID'])

    for o in oids:
        print(_get(DATAPOINT_API + o))


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
