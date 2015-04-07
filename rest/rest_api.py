import requests
from biicode.common.settings.fixed_string import FixedStringWithValue
from biicode.client.exception import BiiException, ConnectionErrorException
from requests.auth import AuthBase
from requests.exceptions import ConnectionError, Timeout
import urllib
from biicode.common.utils.bii_logging import logger


class RestApiException(BiiException):
    """Base class exception of this module"""
    pass


class MethodNotFoundInApiException(RestApiException):
    """API method not found"""
    def __init__(self, expr):
        RestApiException.__init__(self)
        self.expr = expr

    def __str__(self):
        return repr("Method: " + self.expr)


class HttpMethodNotImplementedException(RestApiException):
    """Http method not found"""
    pass


class InvalidURLException(RestApiException):
    def __init__(self, expr):
        RestApiException.__init__(self)
        self.expr = expr

    def __str__(self):
        return repr("URL: " + self.expr)


class HttpRequestsLibMethod(FixedStringWithValue):
    """Available methods"""
    map_values = {'GET': requests.get, 'POST': requests.post,
              'PUT': requests.put, 'HEAD': requests.head,
              'OPTIONS': requests.options, 'DELETE': requests.delete}


class JWTAuth(AuthBase):
    """Attaches JWT Authentication to the given Request object."""
    def __init__(self, token):
        self.token = token

    def __call__(self, request):
        request.headers['Authorization'] = "Bearer %s" % self.token
        return request


class RestApiClient(object):

    DEFAULT_TIMEOUT = 15

    def __init__(self, base_url, authorized_methods,
                 http_lib_methods=HttpRequestsLibMethod, timeout=None, proxies=None, verify=False):

        self.base_url = base_url
        self.authorized_methods = authorized_methods
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.proxies = proxies or urllib.getproxies()
        self.verify = verify
        self.http_lib_methods = http_lib_methods
        assert(isinstance(self.http_lib_methods, FixedStringWithValue.__class__))

    def call(self, function_name, url_params=None, params=None, data=None, auth=None,
             headers=None, timeout=None):

        url_params = url_params or {}
        method = self._get_method(function_name)
        pattern = self._get_pattern(function_name)
        url = self._get_url(pattern, url_params)
        try:
            return method(url, params=params, data=data, auth=auth, headers=headers,
                          verify=self.verify, timeout=timeout or self.timeout,
                          proxies=self.proxies)
        except (ConnectionError, Timeout) as e:
            logger.debug(str(e))
            raise ConnectionErrorException("Can't connect to biicode, check internet connection!")

    def _get_method(self, function_name):
        try:
            return self.http_lib_methods(self.authorized_methods[function_name]['method']).value
        except KeyError:
            raise MethodNotFoundInApiException(function_name)  # From dict method
        except ValueError:
            # From FixedStringWithValue
            raise HttpMethodNotImplementedException("Http method specified for %s" % function_name)

    def _get_pattern(self, function_name):
        try:
            return self.authorized_methods[function_name]['pattern']
        except KeyError:
            raise MethodNotFoundInApiException(function_name)  # From dict method

    def _get_url(self, pattern, url_params):
        url = (self.base_url + self._build_path(pattern, url_params))
        if not self.valid_url(url):
            raise InvalidURLException(url)
        return url

    def _build_path(self, pattern, url_params):
        for var_name in url_params.keys():
            varValue = url_params[var_name]
            pattern = pattern.replace(":" + var_name, str(varValue))
        return pattern

    def valid_url(self, url):
        return url.find("/:") == -1  # There is some parameter not filled
