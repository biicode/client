import unittest
from biicode.common.exception import AuthenticationException, ForbiddenException
from biicode.client.test.shell.user_io_mock import mocked_user_io, mock_user_io
from biicode.client.api.biiapi_auth_manager import BiiApiAuthManager


class MockRestClient():

    token = None

    def __init__(self):
        self.dep_table_call_counter = 0
        self.renames_call_counter = 0
        self.authentication_failed = 0
        self.custom_headers = {}

    def get_dep_table(self, _):
        self.dep_table_call_counter += 1
        if self.token == "goodtoken":
            return "dep_table"
        elif self.token is None or self.token == "validtokenbutforbidden":
            raise ForbiddenException()  # <= Simulates a CantDoIt through REST API
        else:
            self.authentication_failed += 1
            raise AuthenticationException()

    def get_cells_snapshot(self, _):
        # No auth needed, token can be None
        return "snapshot"

    def get_renames(self, _1, _2, _3):
        # This method works only with anonymous call
        self.renames_call_counter += 1
        if self.token == None:
            return "renames_anonymous"
        else:
            self.authentication_failed += 1
            raise AuthenticationException()

    def authenticate(self, user, password):
        if user and password == "goodpass":
            return "goodtoken"
        else:
            self.authentication_failed += 1
            raise AuthenticationException()


class MockLocalDB():

    def __init__(self):
        self.user = None
        self.token = None
        self.set_login_call_counter = 0

    def get_login(self):
        return (self.user, self.token)

    def set_login(self, login):
        self.set_login_call_counter += 1
        self.user = login[0]
        self.token = login[1]


class BiiApiAuthManagerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.rest_client = MockRestClient()
        self.user_io = mocked_user_io()
        self.localdb = MockLocalDB()
        self.restmanager = BiiApiAuthManager(self.rest_client, self.user_io, self.localdb)

    def test_expire_and_anonymous_service_ok(self):
        self.assertEqual(self.restmanager.get_renames("blockversion", 1, 2), "renames_anonymous")
        self.localdb.token = "invalidtoken"
        self.restmanager = BiiApiAuthManager(self.rest_client, self.user_io, self.localdb)
        self.assertEqual(self.restmanager.get_renames("blockversion", 1, 2), "renames_anonymous")
        self.assertEqual(self.rest_client.authentication_failed, 1)
        # There calls, the first ok, the second failing because of bad token and third anonymous ok
        self.assertEqual(self.rest_client.renames_call_counter, 3)

    def test_anonymous_call_with_necessary_login(self):
        # In localdb there are not credentials.
        # There will be two calls to get_dep_table:
        #   1. With an anonymous user: Will fail in server with a ForbiddenException
        #   2. Before request login and password to user, will call again with token
        mock_user_io(self.user_io, login=("pepe", "goodpass"))

        # Result is OK
        self.assertEqual(self.restmanager.get_dep_table("blockversion"), "dep_table")
        # Two calls to real api
        self.assertEqual(self.rest_client.dep_table_call_counter, 2)
        # Stored in localdb right credentials
        self.assertEquals(self.localdb.set_login_call_counter, 1)
        self.assertEquals(self.localdb.token, "goodtoken")

        # In user io must be the message Please log in to perform this action. If you don\'t have'
        # an account sign up here: http://www.biicode.com

        self.assertIn('Please log in to perform this action. If you don\'t have '
                      'an account sign up here: http://www.biicode.com', str(self.user_io))

    def test_authenticated_call_but_forbidden_action(self):
        # In localdb there are credentials. If we receive a Forbidden, don't retry
        self.localdb.user = "pepe"
        self.localdb.token = "validtokenbutforbidden"
        self.restmanager = BiiApiAuthManager(self.rest_client, self.user_io, self.localdb)

        # Result is an ForbiddenException
        self.assertRaises(ForbiddenException, self.restmanager.get_dep_table, "blockversion")
        # One call to real api
        self.assertEqual(self.rest_client.dep_table_call_counter, 1)
        # Not called to store credentials
        self.assertEquals(self.localdb.set_login_call_counter, 0)
        self.assertEquals(self.localdb.token, "validtokenbutforbidden")

    # Otro test, si ya tengo usuario y hay forbidden, forbidden me llevo

    def test_all_retries(self):
        # user_io.request_login has to be called 3 times
        mock_user_io(self.user_io,
                     login=[("pepe", "badpass"),
                            ("pepe", "badpass2"),
                            ("pepe", "badpass3")])
        self.assertRaises(AuthenticationException, self.restmanager.get_dep_table, "blockversion")
        # Only one attemp to call get_dep_table, it raises all the rest in get_token
        self.assertEqual(self.rest_client.dep_table_call_counter, 1)

        # Login not stored
        self.assertEquals(self.localdb.set_login_call_counter, 0)

    def test_one_retry(self):
        mock_user_io(self.user_io,
                     login=[("pepe", "badpass"),
                            ("pepe", "goodpass")])

        self.assertEqual(self.restmanager.get_dep_table("blockversion"), "dep_table")

        # Two attemps, first fails because None is returned as user, second with a real token
        self.assertEqual(self.rest_client.dep_table_call_counter, 2)

        # Login stored
        self.assertEquals(self.localdb.set_login_call_counter, 1)

    def test_anonymous_service(self):
        # Not token needed, not user provided
        mock_user_io(self.user_io)
        ret = self.rest_client.get_cells_snapshot("blockversion")
        self.assertEqual(ret, "snapshot")

        # Login not stored
        self.assertEquals(self.localdb.set_login_call_counter, 0)
