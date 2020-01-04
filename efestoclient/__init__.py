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

    # Available languages en, de, fr, it, es
    statusTranslated = {}

    statusTranslated['de'] = {
        0: "AUSGESCHALTET",
        1: "PELLET LAST",
        2: "WARTET FLAMME",
        3: "ZUNDUNG",
        4: "ARBEITEN",
        5: "ASCHKASTEN REINIGUNG",
        6: "ENDREINIGUNG",
        7: "BEREITHALTEN",
        8: "ALARM",
        9: "ALARMSPEICHER"
    }
    statusTranslated['en'] = {
        0: "OFF",
        1: "PELLET LOAD",
        2: "AWAITING FLAME",
        3: "LIGHTING",
        4: "WORKING",
        5: "ASHPAN CLEANING",
        6: "FINAL CLEANING",
        7: "STANDBY",
        8: "ALARM",
        9: "ALARM MEMORY"
    }
    statusTranslated['fr'] = {
        0: "ETEINT",
        1: "CHARGE GRANULE DE BOIS",
        2: "FLAMME DANS L'ATTENTE",
        3: "ALLUMAGE",
        4: "TRAVAIL",
        5: "NETTOYAGE BRASERO",
        6: "NETTOYAGE FINAL",
        7: "ETRE PRET",
        8: "ALARME",
        9: "MEMOIRE D'ALARME"
    }
    statusTranslated['it'] = {
        0: "SPENTA",
        1: "CARICO PELLET",
        2: "ATTESA FIAMMA",
        3: "ACCENSIONE",
        4: "LAVORO",
        5: "PULIZIA BRACIERE",
        6: "PULIZIA FINALE",
        7: "STAND-BY",
        8: "ALLARME",
        9: "MEMORIA ALLARME"
    }
    statusTranslated['es'] = {
        0: "APAGADA",
        1: "PELLETS DE CARGA",
        2: "LLAMA A LA ESPERA",
        3: "IGNICION",
        4: "TRABAJANDO",
        5: "LA LIMPIEZA DEL CENICERO",
        6: "LIMPIEZA FINAL",
        7: "EN ENSPERA",
        8: "ALARMA",
        9: "MEMORIA DE ALARMA"
    }

    errorTranslated = {}

    errorTranslated['de'] = {
        0: "None",
        1: "E8",
        2: "E4",
        4: "E9 - Fehlendes Pellet",
        8: "E7",
        16: "E3",
        32: "E1",
        48: "E6",
        64: "E2",
        72: "E14",
        129: "E12",
        132: "E19",
        136: "E13"
    }
    errorTranslated['en'] = {
        0: "None",
        1: "E8",
        2: "E4",
        4: "E9 - Missing pellet",
        8: "E7",
        16: "E3",
        32: "E1",
        48: "E6",
        64: "E2",
        72: "E14",
        129: "E12",
        132: "E19",
        136: "E13"
    }
    errorTranslated['fr'] = {
        0: "None",
        1: "E8",
        2: "E4",
        4: "E9 - Granule manquant",
        8: "E7",
        16: "E3",
        32: "E1",
        48: "E6",
        64: "E2",
        72: "E14",
        129: "E12",
        132: "E19",
        136: "E13"
    }
    errorTranslated['it'] = {
        0: "None",
        1: "E8",
        2: "E4",
        4: "E9 - Mancanza pellet",
        8: "E7",
        16: "E3",
        32: "E1",
        48: "E6",
        64: "E2",
        72: "E14",
        129: "E12",
        132: "E19",
        136: "E13"
    }
    errorTranslated['es'] = {
        0: "None",
        1: "E8",
        2: "E4",
        4: "E9 - Perdida de pellet",
        8: "E7",
        16: "E3",
        32: "E1",
        48: "E6",
        64: "E2",
        72: "E14",
        129: "E12",
        132: "E19",
        136: "E13"
    }

    def __init__(self, url, username, password, deviceid, language="en",debug=False):
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

        self.language = language

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
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise ConnectionError(str.format("Connection to {0} not possible", url))
        except requests.exceptions.RequestException:
            raise InvalidURLError(str.format("Invalid Efesto url: {0}", url))

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
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise ConnectionError(str.format("Connection to {0} not possible", url))
        except requests.exceptions.RequestException:
            raise InvalidURLError(str.format("Invalid Efesto url: {0}", url))

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
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise ConnectionError(str.format("Connection to {0} not possible", url))
        except requests.exceptions.RequestException:
            raise InvalidURLError(str.format("Invalid Efesto url: {0}", url))

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
                      self.statusTranslated[self.language][res['message']['deviceStatus']],
                      res['message']['isDeviceInAlarm'],
                      self.errorTranslated[self.language][res['message']['isDeviceInAlarm']],
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
                 device_error, device_error_human,
                 air_temperature, smoke_temperature, real_power,
                 last_set_air_temperature, last_set_power, idle_info=None):
        self.__device_id = device_id
        self.__device_status = device_status
        self.__device_status_human = device_status_human
        self.__device_error = device_error
        self.__device_error_human = device_error_human
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
    def device_error(self):
        return self.__device_error

    @property
    def device_error_human(self):
        return self.__device_error_human

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

class InvalidURLError(Error):
    """Invalid URL"""
    def __init__(self, message):
        super().__init__(message)

