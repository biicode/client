'''
Collaborate with BiiRestApiClient to make remote anonymous and authenticated calls.
Uses user_io to request user's login and password and obtain a token for calling authenticated
methods if receives AuthenticationException from BiiRestApiClient.


Flow:

    Directly invoke a REST method in BiiRestApiClient, example: get_dep_table.
    if receives AuthenticationException (not open method) will ask user for login and password
    and will invoke BiiRestApiClient.get_token() (with LOGIN_RETRIES retries) and retry to call
    get_dep_table with the new token.
'''


from biicode.common.exception import AuthenticationException, ForbiddenException
from biicode.common.api.biiapi import BiiAPI
from biicode.common.utils.bii_logging import logger
from uuid import getnode as get_mac
import hashlib


def input_credentials_if_unauthorized(func):
    """Decorator. Handles AuthenticationException and request user
    to input a user and a password"""
    LOGIN_RETRIES = 3

    def wrapper(self, *args, **kwargs):
        try:
            # Set custom headers of mac_digest and username
            self.set_custom_headers(self.user)
            return func(self, *args, **kwargs)
        except ForbiddenException as e:
            # User valid but not enough permissions
            logger.debug("Forbidden: %s" % str(e))
            if self.user is None or self.rest_client.token is None:
                # token is None when you change user with user command
                # Anonymous is not enough, ask for a user
                self.user_io.out.info('Please log in to perform this action. If you don\'t have'
                                      ' an account sign up here: http://www.biicode.com')
                if self.user is None:
                    logger.debug("User None, ask for it, anonymous not enough!")
                return retry_with_new_token(self, *args, **kwargs)
            else:
                # If our user receives a ForbiddenException propagate it, not log with other user
                raise e
        except AuthenticationException:
            # Token expired or not valid, so clean the token and repeat the call
            # (will be anonymous call but registering who is calling)
            self._store_login((self.user, None))
            self.rest_client.token = None
            # Set custom headers of mac_digest and username
            self.set_custom_headers(self.user)
            return wrapper(self, *args, **kwargs)

    def retry_with_new_token(self, *args, **kwargs):
        """Try LOGIN_RETRIES to obtain a password from user input for which
        we can get a valid token from api_client. If a token is returned,
        credentials are stored in localdb and rest method is called"""
        for _ in range(LOGIN_RETRIES):
            user, password = self.user_io.request_login(self.user)
            token = None
            try:
                token = self.authenticate(user, password)
            except AuthenticationException:
                if self.user is None:
                    self.user_io.out.error('Wrong user or password')
                else:
                    self.user_io.out.error('Wrong password for user "%s"' % self.user)
                    self.user_io.out.info('You can change username with "bii user <username>"')
            if token:
                self.rest_client.token = token
                self.user = user
                self._store_login((user, token))
                # Set custom headers of mac_digest and username
                self.set_custom_headers(user)
                return func(self, *args, **kwargs)

        raise AuthenticationException("Too many failed login attempts, bye!")
    return wrapper


class BiiApiAuthManager(BiiAPI):
    """ BiiAPI implementation in charge of executing authenticated calls
    """
    def __init__(self, rest_client, user_io, localdb):
        self.user_io = user_io
        self.rest_client = rest_client
        self.localdb = localdb
        self.user, self.rest_client.token = localdb.get_login()

    def _store_login(self, login):
        try:
            self.localdb.set_login(login)
        except Exception as e:
            self.user_io.out.error('Your credentials could not be stored in local cache\n')
            self.user_io.out.debug(str(e) + '\n')

    @staticmethod
    def get_mac_digest():
        sha1 = hashlib.sha1()
        sha1.update(str(get_mac()))
        return str(sha1.hexdigest())

    def set_custom_headers(self, username):
        #First identifies our machine, second the username even if it was not authenticated
        self.rest_client.custom_headers['X-Client-Anonymous-Id'] = self.get_mac_digest()
        self.rest_client.custom_headers['X-Client-Id'] = username

    ########## BII API METHODS ##########

    @input_credentials_if_unauthorized
    def get_dep_table(self, block_version):
        return self.rest_client.get_dep_table(block_version)

    @input_credentials_if_unauthorized
    def get_published_resources(self, references):
        return self.rest_client.get_published_resources(references)

    @input_credentials_if_unauthorized
    def get_cells_snapshot(self, block_version):
        return self.rest_client.get_cells_snapshot(block_version)

    @input_credentials_if_unauthorized
    def get_renames(self, brl_block, t1, t2):
        return self.rest_client.get_renames(brl_block, t1, t2)

    @input_credentials_if_unauthorized
    def publish(self, publish_request):
        return self.rest_client.publish(publish_request)

    @input_credentials_if_unauthorized
    def get_version_delta_info(self, block_version):
        return self.rest_client.get_version_delta_info(block_version)

    @input_credentials_if_unauthorized
    def get_version_by_tag(self, brl_block, version_tag):
        return self.rest_client.get_version_by_tag(brl_block, version_tag)

    @input_credentials_if_unauthorized
    def get_block_info(self, brl_block):
        return self.rest_client.get_block_info(brl_block)

    @input_credentials_if_unauthorized
    def find(self, finder_request, response):
        return self.rest_client.find(finder_request, response)

    @input_credentials_if_unauthorized
    def read_hive(self, brl_hive):
        return self.rest_client.read_hive(brl_hive)

    @input_credentials_if_unauthorized
    def upload(self, brl_hive, upload_pack):
        return self.rest_client.upload(brl_hive, upload_pack)

    @input_credentials_if_unauthorized
    def get_server_info(self):
        return self.rest_client.get_server_info()

    @input_credentials_if_unauthorized
    def require_auth(self):
        """Only for validating token (Used in publish manager to ensure
        logged user before publishing)"""
        return self.rest_client.require_auth()

    def authenticate(self, user, password):
        """Get token"""
        return self.rest_client.authenticate(user, password)
