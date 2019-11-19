"""EfestoClient provides controlling Efesto heat devices
"""
import warnings
import logging
import requests
import socket
from datetime import datetime, timedelta
from requests.packages.urllib3.exceptions import InsecureRequestWarning

try:
    import http.client as http_client
except ImportError:
    # Python 2
    import httplib as http_client

name = "efestoclient"

"""Disable SSL verify warning because Efesto has self signed certificates"""
warnings.simplefilter('ignore', InsecureRequestWarning)

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
        9: "NO PELLETS", 10: "?", 11: "?", 12: "?", 13: "?", 14: "?", 15: "?",
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

        try:
            response = requests.get(url, headers=self._headers(), verify=False)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            raise ConnectionError(str.format("Connection to {0} not possible", url))

        self.phpsessid = response.cookies.get("PHPSESSID")

        return self.phpsessid

    def login(self):
        """Authenticate with username and password to Efesto"""

        url = self.url + '/en/login/'

        payload = {
            'login[username]': self.username,
            'login[password]': self.password
        }

        try:
            response = requests.post(url, data=payload, headers=self._headers(),
                                    verify=False, allow_redirects=False)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            raise ConnectionError(str.format("Connection to {0} not possible", url))

        self.remember = response.cookies.get("remember")

        if self.remember is None:
            raise UnauthorizedError('Failed to login, please check credentials')

        return self.remember

    def get_system_modes(self):
        """Get list of system modes"""
        statusList = []
        for key in self.statusTranslated:
            statusList.append(self.statusTranslated[key])
        return statusList

    def handle_webcall(self, url, payload):
        try:
            response = requests.post(url, data=payload, headers=self._headers(),
                                    verify=False, allow_redirects=False)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            raise ConnectionError(str.format("Connection to {0} not possible", url))

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
        if res['status'] > 0:
            raise Error(str.format("{0}", res['message']))

        idle_info = res['idle']['idle_label'] if res['idle'] is not None else None

        return Device(self.deviceid,
                      res['message']['deviceStatus'],
                      self.statusTranslated[res['message']['deviceStatus']],
                      res['message']['airTemperature'],
                      res['message']['smokeTemperature'],
                      res['message']['realPower'],
                      res['message']['lastSetAirTemperature'],
                      res['message']['lastSetPower'],
                      idle_info)

    def set_off(self):
        """Turn stove off"""

        url = (self.url + "/en/ajax/action/frontend/response/ajax/")

        payload = {
            'method': 'heater-off',
            'params': '1',
            'device': self.deviceid
        }

        res = self.handle_webcall(url, payload)
        if res['status'] > 0:
            raise Error(str.format("{0}", res['message']))

        return True

    def set_on(self):
        """Turn stove off"""

        url = (self.url + "/en/ajax/action/frontend/response/ajax/")

        payload = {
            'method': "heater-on",
            'params': "1",
            'device': self.deviceid
        }

        res = self.handle_webcall(url, payload)
        if res['status'] > 0:
            raise Error(str.format("{0}", res['message']))

        return True

    def set_temperature(self, temperatureValue):
        """Set desired room temperature"""

        url = (self.url + "/en/ajax/action/frontend/response/ajax/")

        payload = {
            'method': "write-parameters-queue",
            'params': "set-air-temperature=" + str(temperatureValue),
            'device': self.deviceid
        }

        res = self.handle_webcall(url, payload)
        if res['status'] > 0:
            raise Error(str.format("{0}", res['message']))

        for key in res["message"]:
            if (res["message"][key] > 0):
                raise Error(str.format("{0}-failed", key))

    def set_power(self, powerValue):
        """Set desired power value"""

        url = (self.url + "/en/ajax/action/frontend/response/ajax/")

        payload = {
            'method': "write-parameters-queue",
            'params': "set-power=" + str(powerValue),
            'device': self.deviceid
        }

        res = self.handle_webcall(url, payload)
        if res['status'] > 0:
            raise Error(str.format("{0}", res['message']))

        for key in res["message"]:
            if (res["message"][key] > 0):
                raise Error(str.format("{0}-failed", key))


class Device(object):
    """Efesto heating device representation"""
    def __init__(self, device_id, device_status, device_status_human,
                 air_temperature, smoke_temperature, real_power,
                 last_set_air_temperature, last_set_power, idle_info=None):
        self.__device_id = device_id
        self.__device_status = device_status
        self.__device_status_human = device_status_human
        self.__air_temperature = air_temperature
        self.__smoke_temperature = smoke_temperature
        self.__real_power = real_power
        self.__last_set_air_temperature = last_set_air_temperature
        self.__last_set_power = last_set_power
        self.__idle_info = idle_info

    @property
    def device_id(self):
        return self.__device_id

    @property
    def device_status(self):
        return self.__device_status

    @property
    def device_status_human(self):
        return self.__device_status_human

    @property
    def air_temperature(self):
        return self.__air_temperature

    @property
    def smoke_temperature(self):
        return self.__smoke_temperature

    @property
    def real_power(self):
        return self.__real_power

    @property
    def last_set_air_temperature(self):
        return self.__last_set_air_temperature

    @property
    def last_set_power(self):
        return self.__last_set_power

    @property
    def idle_info(self):
        return self.__idle_info


class Error(Exception):
    """Exception type for Efesto"""
    def __init__(self, message):
        Exception.__init__(self, message)


class UnauthorizedError(Error):
    """Unauthorized"""
    def __init__(self, message):
        super().__init__(message)


class ConnectionError(Error):
    """Unauthorized"""
    def __init__(self, message):
        super().__init__(message)
