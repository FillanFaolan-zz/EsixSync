import requests
import time

_lastRequestTime = 0.0


class ApiBase:
    _session = requests.session()
    # the max value of how many page you can query in 1 operation, which aim to do less stress to the server
    picPerPage = 100
    e621 = "https://e621.net"
    # in this field, fill with the UA which will provide to the site
    headers = {
        "User-Agent": "EsixSync/1.0"
    }
    # a dict which store login and api_key
    loginParams = None

    # http get method implement
    def Get(self, subUrl: str, paramDict: dict = None):
        global _lastRequestTime
        # in case you want to login
        if self.loginParams is not None:
            paramDict["login"] = self.loginParams["login"]
            paramDict["api_key"] = self.loginParams["api_key"]
        now = time.time()
        # the operation that wait for 1.0 seconds between two requests follows the instruction on e621.net.
        # plz do not modify this by yourself if you haven't got any permission from e621.net
        if now - _lastRequestTime < 1.0:
            time.sleep(now - _lastRequestTime)
        _lastRequestTime = now
        # two request cannot be send too quick cuz it will stress the server
        response = None
        if paramDict is not None:
            response = self._session.get(self.e621 + subUrl, headers=self.headers, params=paramDict)
        else:
            response = self._session.get(self.e621 + subUrl, headers=self.headers)
        if response.status_code == 200:
            return response
        else:
            raise Exception(
                "Send Get Request Fail on %s, code=%s, response=%s" % (
                    self.e621 + subUrl,
                    response.status_code,
                    response.text
                )
            )
