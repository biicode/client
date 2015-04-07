
import unittest
import urllib
from mock import Mock
from biicode.client.rest.rest_api import (RestApiClient, HttpMethodNotImplementedException,
                                          MethodNotFoundInApiException, InvalidURLException)
from biicode.common.settings.fixed_string import FixedStringWithValue


get_mock = Mock()
post_mock = Mock()
put_mock = Mock()
head_mock = Mock()
options_mock = Mock()
delete_mock = Mock()


class HttpMockLibMethod(FixedStringWithValue):
    """Available methods"""
    map_values = {'GET': get_mock,
                  'POST': post_mock,
                  'PUT': put_mock,
                  'HEAD': head_mock,
                  'OPTIONS': options_mock,
                  'DELETE': delete_mock}


class FakeRestApi(RestApiClient):

    def __init__(self):
        authorized_functions = {
         'invalid_method_one': {'pattern': '/:lang/latest/:user/quickstart/', 'method': 34},
         'get_one': {'pattern': '/:lang/latest/:user/quickstart/', 'method': "GET"},
         'post_one': {'pattern': '/:lang/latest/:user/quickstart/', 'method': "POST"},
         'head_one': {'pattern': '/:lang/latest/:user/quickstart/', 'method': "HEAD"},
         'put_one': {'pattern': '/:lang/latest/:user/quickstart/', 'method': "PUT"},
         'options_one': {'pattern': '/:lang/latest/:user/quickstart/', 'method': "OPTIONS"},
         'delete_one': {'pattern': '/:lang/latest/:user/quickstart/', 'method': "DELETE"}
        }
        super(FakeRestApi, self).__init__("http://www.testingfakeurl.com",
                                          authorized_functions, http_lib_methods=HttpMockLibMethod)


class RestApiTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.api = FakeRestApi()
        self.user = "user1"
        self.url_params = {"lang": "es", "user": self.user}

    def test_http_method_not_implemented(self):
        ''' should raise an exception for an wrong HTTP method (34) '''
        self.assertRaises(HttpMethodNotImplementedException,
                          self.api.call,
                          'invalid_method_one', self.url_params
                          )

    def test_api_method_not_implemented(self):
        # should raise an exception for calling a not defined method
        self.assertRaises(MethodNotFoundInApiException,
                          self.api.call,
                          'method_missing', {}
                          )

    def test_incomplete_url_definition(self):
        ''' should raise an exception for not send compete parameters for URL construction '''
        self.assertRaises(InvalidURLException, self.api.call, 'get_one', {"lang": "en"})

    def test_too_much_url_parameters(self):
        ''' It will be ok if we pass more than necessary parameters '''
        self.url_params["unnecesary_parameter"] = "value"
        self.api.call('get_one', self.url_params)
        self.assertTrue(get_mock.called)

        #We mock the POST method for avoid calling network
        self.api.call('post_one', self.url_params)
        self.assertTrue(post_mock.called)

    def test_get_parameters_passed_ok(self):
        #We mock the GET Method method for avoid calling network
        get_vars = {'var': 1, 'dos': 'tres', 'cuatro': 4}
        post_vars = {'var': 2, 'dos': 'gaticos', 'cuatro': 'monetes'}
        self.api.call('post_one', self.url_params, get_vars, post_vars)
        post_mock.assert_called_with("http://www.testingfakeurl.com/es/latest/user1/quickstart/",
                                       verify=False, headers=None, data=post_vars, params=get_vars,
                                       timeout=15, auth=None,
                                       proxies=urllib.getproxies())

    def test_correct_http_method_called(self):

        expected_methods = {'get_one': get_mock,
                             'post_one': post_mock,
                             'head_one': head_mock,
                             'put_one': put_mock,
                             'options_one': options_mock,
                             'delete_one': delete_mock}

        for method, http_method_mock in expected_methods.iteritems():
            self.assertFalse(http_method_mock.called)
            self.api.call(method, self.url_params)
            self.assertTrue(http_method_mock.called)
