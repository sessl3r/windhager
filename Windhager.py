import sys
import logging
import json
import xml.etree.ElementTree as etree
import requests
from requests.auth import HTTPDigestAuth

class Windhager:
    """ Helper functions to interact with the Windhager InfoWin API
    as documented in self.ip/api-docs

    The default User/Password are given in the user manual.
    If using the myComfort App the password will be changed by Windhager!

    :param hostname: Host or IP of InfoWin device
    :param user: Username to Authenticate (from Usermanual)
    :param password: Password to Authenticate (from Usermanual)

    """

    LOOKUP_API = 'api/1.0/lookup'
    DATAPOINT_API = 'api/1.0/datapoint'
    DATAPOINTS_API = 'api/1.0/datapoints'
    OBJECT_API = 'api/1.0/object'

    def __init__(self, hostname, user = 'Service', password = '123', level='INFO'):
        self._host = hostname
        self._user = user
        self._password = password
        self._xml = None
        self.auth = HTTPDigestAuth(user, password)

        # configure logging
        logging.basicConfig()
        self.log = logging.getLogger(__name__)
        self.log.setLevel(level)

        # check connectivity to device
        self.get('api-docs/')

    def set(self, api, data, params = None, timeout=2):
        """ Issue a put request to InfoWin

        :param api: The API string to use
        :param data: The Data to set
        :param params: Parameters to add to the GET request
        :param timeout: Timeout in seconds

        """

        r = requests.put(f"http://{self._host}/{api}", data = json.dumps(data), params = params, auth = self.auth)
        self.log.debug(f"PUT http://{self._host}/{api} data={json.dumps(data)} params={params} returned {r.status_code}")
        if r.status_code != 200:
            raise Exception(r)
        return r

    def set_datapoint(self, oid, value):
        data = {
            'OID': oid,
            'value': str(value)
        }
        self.set(self.DATAPOINT_API, data)

    def get(self, api, params = None, timeout=2):
        """ Issue a get request to InfoWin

        :param api: The API string to use
        :param params: Parameters to add to the GET request
        :param timeout: Timeout in seconds

        """

        r = requests.get(f"http://{self._host}/{api}", params = params, auth = self.auth)
        self.log.debug(f"GET http://{self._host}/{api} params={params} returned {r.status_code}")
        if r.status_code != 200:
            raise Exception
        try:
            return json.loads(r.text)
        except:
            return r.text

    def get_lookup(self, obj = None):
        """ Issue a request to lookup API

        From api-docs for GET:
            lookup/{subnetId}/{nodeId}/{fctNV}/0/{nvIndex}
        """

        if obj:
            return self.get(f"{self.LOOKUP_API}/{obj}")
        else:
            return self.get(self.LOOKUP_API)

    def get_lookup_all(self):
        """ Recursive lookup scan """
        ret = []

        # Get root node - should always be /1
        subnetIds = self.get_lookup()
        if not subnetIds:
            self.log.error("get_lookup_all: No subnetIds found!")
            return None

        # Iterate over all subnets
        for subnet in subnetIds:
            nodeIds = []
            nodeResp = self.get_lookup(subnet)
            for resp in nodeResp:
                if 'nodeId' in resp:
                    nodeIds.append(resp['nodeId'])

            # Iterate over all nodes
            for node in nodeIds:
                fctIds = []
                fctResp = self.get_lookup(f"{subnet}/{node}")
                if not 'functions' in fctResp:
                    self.log.error(f"Malformed fctResp, no functions found: {fctResp}")
                    return None
                for resp in fctResp['functions']:
                    if 'fctId' in resp:
                        fctIds.append(resp['fctId'])

                # Iterate over all functions
                for fct in fctIds:
                    subfctIds = []
                    try:
                        subfctResp = self.get_lookup(f"{subnet}/{node}/{fct}")
                    except:
                        continue
                    for resp in subfctResp:
                        if 'id' in resp:
                            subfctIds.append(resp['id'])

                    # Iterate over all subfunctions
                    for subfct in subfctIds:
                        try:
                            nvResp = self.get_lookup(f"{subnet}/{node}/{fct}/{subfct}")
                        except:
                            continue
                        for nv in nvResp:
                            ret.append(nv)

        return ret

    def get_object(self, obj, cache):
        """ Issue a request to object API

        From api-docs for GET:
            /object?OID=xx&cacheCtl={0,1}

        """

        return self.get(self.OBJECT_API, { 'OID': obj, 'cacheCtl': cache })

    def get_datapoint(self, obj):
        """ Issue a request to datapoint API

        From api-docs for GET:
            /datapoint/{subnetId}/{nodeId}/{fctId}/{groupId}/{memberId}/{varInst}
            /datapoint/{subnetId}/{nodeId}/{fctNV}/0/{nvIndex}/0

        """

        return self.get(f"{self.DATAPOINT_API}/{obj.lstrip('/')}")

    def get_datapoints(self):
        """ Issue a request to datapoints API

        TODO: per api-docs a param OID giving one or multiple OIDs should be supported.
            I did not get this working but always got Bad Gateway Errors. Need to revisit!

        """

        return self.get(f"{self.DATAPOINTS_API}")

    def get_datapoints_with_name(self):
        """ Get all (cached) datapoints and lookup the name -> text in the XML file """
        dps = get_datapoints()
        res = []
        for dp in dps:
            name = ""
            value = ""
            oid = ""
            if 'name' not in dp:
                res.append(dp)
                continue
            name = p['name']
            try:
                gN = int(p['name'].split('-')[0])
                mN = int(p['name'].split('-')[1])
            except:
                self.log.error(f"Malformed name: '{p['name']}' in datapoint {dp}")

            text = self.id_to_string(gN, mN)
            if text:
                p['text'] = text
            res.append(dp)
        return res

    @property
    def xml(self):
        """ Retrieve VarIdentTexte as parsed XML """
        if not self._xml:
            resp = self.get('res/xml/VarIdentTexte_de.xml')
            if not resp:
                self.log.error("Failed to get VarIdentTexte_de.xml")
            else:
                self._xml = etree.fromstring(resp.encode('utf-8'))
        return self._xml

    def id_to_string(self, gn, mn):
        """ Convert groupNr + memberNr to Text found in XML file if any """
        gn = int(gn)
        mn = int(mn)
        e = self.xml.find('gn[@id="' + str(gn) + '"]/mn[@id="' + str(mn) + '"]')
        if e is not None:
            if e.text is not None:
                return e.text.strip()
        return None

    def name_to_string(self, name):
        (gn, mn) = name.split('-')
        return self.id_to_string(gn, mn)
