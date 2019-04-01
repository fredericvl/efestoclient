"""EfestoClient provides controlling Efesto heat devices
"""
import warnings
import logging
import requests
from datetime import datetime, timedelta
from requests.packages.urllib3.exceptions import InsecureRequestWarning

try:
    import http.client as http_client
except ImportError:
    # Python 2
    import httplib as http_client

name = "efestoclient"

"""Disable SSL verify warning because Efesto has self signed certificates"""
warnings.simplefilter('ignore',InsecureRequestWarning)

logging.basicConfig()
_LOGGER = logging.getLogger(__name__)

HEADER_ACCEPT = (
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,"
    "image/apng,*/*;q=0.8,application/signed-exchange;v=b3"
)
HEADER_CONTENT_TYPE = (
    "application/x-www-form-urlencoded"
)
HEADER = {
    'Accept': HEADER_ACCEPT,
    'Content-Type': HEADER_CONTENT_TYPE
}

class EfestoClient(object):
    """Provides access to Efesto."""

    statusTranslated = {
        0: "OFF", 1: "START", 2: "LOAD PELLETS", 3: "FLAME LIGHT", 4: "ON",
        5: "CLEANING FIRE-POT", 6: "CLEANING FINAL", 7: "ECO-STOP", 8: "?",
        9: "NO FIRE?", 10: "?", 11: "?", 12: "?", 13: "?", 14: "?", 15: "?",
        16: "?", 17: "?", 18: "?", 19: "?"
    }

    def __init__(self, url, username, password, deviceid, debug=False):
        """EfestoClient object constructor"""
        if debug is True:
            _LOGGER.setLevel(logging.DEBUG)
            _LOGGER.debug("Debug mode is explicitly enabled.")

            requests_logger = logging.getLogger("requests.packages.urllib3")
            requests_logger.setLevel(logging.DEBUG)
            requests_logger.propagate = True

            http_client.HTTPConnection.debuglevel = 1
        else:
            _LOGGER.debug(
                "Debug mode is not explicitly enabled "
                "(but may be enabled elsewhere)."
            )

        self.url = url
        self.username = username
        self.password = password
        self.deviceid = deviceid

        self.phpsessid = None
        self.remember = None

        self._login()

    def _login(self):
        self.sessionid()
        self.login()

    def _headers(self):
        """Correctly set headers including cookies for requests to Efesto."""

        if not self.phpsessid:
            cookies = ''
        else:
            if not self.remember:
                cookies = "PHPSESSID=" + self.phpsessid
            else:
                cookies = "PHPSESSID=" + self.phpsessid + "; remember=" \
                          + self.remember

        return {'Accept': HEADER_ACCEPT,
                'Cookie': cookies,
                'Content-Type': HEADER_CONTENT_TYPE,
                'Origin': self.url,
                'Referer': self.url + '/en/heaters/action/manage/heater/'
                                    + self.deviceid + '/'}

    def sessionid(self):
        """Get PHP session information"""

        url = self.url + '/en/login/'

        response = requests.get(url, headers=self._headers(), verify=False)
        response.raise_for_status()

        self.phpsessid = response.cookies.get("PHPSESSID")

        return self.phpsessid

    def login(self):
        """Authenticate with username and password to Efesto"""

        url = self.url + '/en/login/'

        payload = {
            'login[username]': self.username,
            'login[password]': self.password
        }

        response = requests.post(url, data=payload, headers=self._headers(),
                                 verify=False, allow_redirects=False)
        response.raise_for_status()

        self.remember = response.cookies.get("remember")

        if self.remember is None:
            raise Exception('Failed to login, please check credentials')

        return self.remember

    def get_system_modes(self):
        """Get list of system modes"""
        statusList = []
        for key in self.statusTranslated:
            statusList.append(self.statusTranslated[key])
        return statusList

    def handle_webcall(self, url, payload):
        response = requests.post(url, data=payload, headers=self._headers(),
                                 verify=False, allow_redirects=False)
        response.raise_for_status()

        if response.status_code == 200:
            res = response.json()
            if res is None:
                returnpayload = {
                    'status': 1,
                    'message': 'Unkown error at Efesto end'
                }
            else:
                returnpayload = res
        elif response.status_code == 302:
            returnpayload = {
                'status': 1,
                'message': 'Efesto server is temporary unavailable ' +
                           '(got temporary redirect)'
            }
        else:
            returnpayload = {
                'status': 1,
                'message': 'Efesto server is unavailable'
            }
        return returnpayload

    def get_status(self):
        """Get stove status"""

        url = (self.url + "/en/ajax/action/frontend/response/ajax/")

        payload = {
            'method': 'get-state',
            'params': '1',
            'device': self.deviceid
        }

        res = self.handle_webcall(url, payload)
        if res['status'] == 0:
            returnpayload = {
                'status': res['status'],
                'deviceStatus': res['message']['deviceStatus'],
                'deviceStatusTranslated':
                    self.statusTranslated[res['message']['deviceStatus']],
                'airTemperature': res['message']['airTemperature'],
                'smokeTemperature': res['message']['smokeTemperature'],
                'realPower': res['message']['realPower'],
                'lastSetAirTemperature':
                    res['message']['lastSetAirTemperature'],
                'lastSetPower': res['message']['lastSetPower']
            }
            if res['idle'] is not None:
                extrapayload = {
                    'idle_info': res['idle']['idle_label']
                }
                returnpayload.update(extrapayload)
            return returnpayload
        else:
            return res

    def set_off(self):
        """Turn stove off"""

        url = (self.url + "/en/ajax/action/frontend/response/ajax/")

        payload = {
            'method': 'heater-off',
            'params': '1',
            'device': self.deviceid
        }

        res = self.handle_webcall(url, payload)
        if res['status'] == 0:
            if (res["status"] > 0):
                returnpayload = {
                    'status': 1,
                    'message': 'failed'
                }
            else:
                returnpayload = {
                    'status': 0,
                    'message': 'ok'
                }
            return returnpayload
        else:
            return res

    def set_on(self):
        """Turn stove off"""

        url = (self.url + "/en/ajax/action/frontend/response/ajax/")

        payload = {
            'method': "heater-on",
            'params': "1",
            'device': self.deviceid
        }

        response = requests.post(url, data=payload, headers=self._headers(),
                                 verify=False)
        response.raise_for_status()

        res = self.handle_webcall(url, payload)
        if res['status'] == 0:
            if (res["status"] > 0):
                returnpayload = {
                    'status': 1,
                    'message': 'failed'
                }
            else:
                returnpayload = {
                    'status': 0,
                    'message': 'ok'
                }
            return returnpayload
        else:
            return res

    def set_temperature(self, temperatureValue):
        """Set desired room temperature"""

        url = (self.url + "/en/ajax/action/frontend/response/ajax/")

        payload = {
            'method': "write-parameters-queue",
            'params': "set-air-temperature=" + str(temperatureValue),
            'device': self.deviceid
        }

        response = requests.post(url, data=payload, headers=self._headers(),
                                 verify=False)
        response.raise_for_status()

        res = self.handle_webcall(url, payload)
        if res['status'] == 0:
            if (res["status"] > 0):
                returnpayload = {
                    'status': 1,
                    'message': 'failed'
                }
            else:
                for key in res["message"]:
                    if (res["message"][key] > 0):
                        returnpayload = {
                            'status': 1,
                            'message': 'failed'
                        }
                    else:
                        returnpayload = {
                            'status': 0,
                            'message': 'ok'
                        }
            return returnpayload
        else:
            return res

    def set_power(self, powerValue):
        """Set desired power value"""

        url = (self.url + "/en/ajax/action/frontend/response/ajax/")

        payload = {
            'method': "write-parameters-queue",
            'params': "set-power=" + str(powerValue),
            'device': self.deviceid
        }

        response = requests.post(url, data=payload, headers=self._headers(),
                                 verify=False)
        response.raise_for_status()

        res = self.handle_webcall(url, payload)
        if res['status'] == 0:
            if (res["status"] > 0):
                returnpayload = {
                    'status': 1,
                    'message': 'failed'
                }
            else:
                for key in res["message"]:
                    if (res["message"][key] > 0):
                        returnpayload = {
                            'status': 1,
                            'message': 'failed'
                        }
                    else:
                        returnpayload = {
                            'status': 0,
                            'message': 'ok'
                        }
            return returnpayload
        else:
            return res
