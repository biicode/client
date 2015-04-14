from biicode.client.rest.rest_api import RestApiClient
from biicode.common.utils.serializer import Serializer, ListDeserializer
from biicode.common.exception import BiiServiceException
from biicode.common.model.symbolic.block_version_table import BlockVersionTable
from biicode.common.find.finder_result import FinderResult
from biicode.common.utils.bii_logging import logger
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.model.renames import Renames
from biicode.common.model.symbolic.reference import ReferencedResources
from biicode.common.rest.rest_return_mapping import getExceptionFromHttpError
from biicode.common.api.biiapi import BiiAPI
from biicode.common.settings.osinfo import OSInfo
from biicode.common.model.server_info import ServerInfo
from biicode.common.model.cells import CellDeserializer
from biicode.common.model.content import ContentDeserializer
from biicode.common.model.brl.block_cell_name import BlockCellName
from biicode.common.diffmerge.changes import ChangesDeserializer
from biicode.common.model.brl.cell_name import CellName
from biicode.common.model.resource import ResourceDeserializer
from biicode.common.model.block_delta import BlockDelta
from biicode.common.model.block_info import BlockInfo
from biicode.client.rest.rest_api import JWTAuth
from requests.auth import HTTPBasicAuth
from biicode.common.utils.bson_encoding import decode_bson, encode_bson
from biicode.common.api.ui import BiiResponse


class BiiRestApiClient(RestApiClient, BiiAPI):
    '''
        Communication with server remote REST API
     Satisfaction of BiiAPI Interface it's not necessary. Its
     fully implemented in BiiApiAuthManager

    '''

    version = "v1"

    authorized_functions = {
        'get_published_resources': {'pattern': '/get_published_resources', 'method': "POST"},
        'publish': {'pattern': '/publish', 'method': "POST"},
        'upload': {'pattern': '/upload', 'method': "POST"},
        'require_auth': {'pattern': '/require_auth', 'method': "GET"},
        'get_dep_table': {'pattern': '/users/:user_name/blocks/:block_name/branches/:branch_name/versions/:version/block_version_table/',
                          'method': "GET"},
        'get_cells_snapshot': {'pattern': '/cells_snapshot', 'method': "POST"},
        'find': {'pattern': '/finder_result', 'method': "POST"},
        'diff': {'pattern': '/diff', 'method': "POST"},
        'get_renames': {'pattern': '/renames', 'method': "POST"},
        'get_block_info': {'pattern': '/users/:user_name/blocks/:block_name/branches/:branch_name/info', 'method': "GET"},
        'get_server_info': {'pattern': '/get_server_info', 'method': "POST"},
        'authenticate': {'pattern': '/authenticate', 'method': "GET"},  # Sends user and password by basic http, other methods sends user + token
        'get_version_delta_info': {'pattern': '/users/:user_name/blocks/:block_name/branches/:branch_name/version/:version/delta_info', 'method': "GET"},
        'get_version_by_tag': {'pattern': '/users/:user_name/blocks/:block_name/branches/:branch_name/tag/:tag', 'method': "GET"},
      }

    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None  # Anonymous until setted
        self.custom_headers = {}  # Can set custom headers to each request
        logger.debug("Init rest api client pointing to: %s" % self.base_url)
        super(BiiRestApiClient, self).__init__(
                                   self.base_url + "/" + BiiRestApiClient.version,
                                   self.authorized_functions)

    ################### REST METHODS ########################
    def get_published_resources(self, references):
        serialized_data = Serializer().build(("data", references))
        return self.bson_jwt_call('get_published_resources', data=serialized_data,
                                   deserializer=ReferencedResources)

    def publish(self, publish_request):
        data = Serializer().build(("data", publish_request))
        return self.bson_jwt_call('publish', data=data, deserializer=BlockVersion)

    def get_dep_table(self, block_version):
        block, time, _ = block_version
        owner_name = block.owner
        block_name = block.block_name
        branch_name = block.branch

        params = {"user_name": owner_name, "block_name": block_name,
                      "branch_name":  branch_name, "version": time}
        deserializer = BlockVersionTable
        return self.bson_jwt_call('get_dep_table', url_params=params, deserializer=deserializer)

    def get_cells_snapshot(self, block_version):
        data = Serializer().build(("data", block_version))
        return self.bson_jwt_call('get_cells_snapshot', data=data,
                                  deserializer=ListDeserializer(CellName))

    def find(self, finder_request, response):
        data = Serializer().build(("data", finder_request))
        return self.bson_jwt_call('find', data=data, deserializer=FinderResult, response=response)

    def diff(self, base, other):
        data = Serializer().build(("base", base),
                                  ("other", other))
        values_deserializer = ResourceDeserializer(CellDeserializer(BlockCellName),
                                                  ContentDeserializer(BlockCellName))
        deserializer = ChangesDeserializer(CellName, values_deserializer)
        return self.bson_jwt_call('diff', data=data, deserializer=deserializer)

    def get_renames(self, brl_block, t1, t2):
        data = Serializer().build(("block", brl_block),
                                  ("t1", t1),
                                  ("t2", t2))
        return self.bson_jwt_call('get_renames', data=data, deserializer=Renames)

    def get_block_info(self, brl_block):
        owner_name = brl_block.owner
        block_name = brl_block.block_name
        branch_name = brl_block.branch

        url_params = {"user_name": owner_name,
                      "block_name": block_name,
                      "branch_name": branch_name}

        return self.bson_jwt_call('get_block_info', url_params=url_params, deserializer=BlockInfo)

    def get_version_delta_info(self, block_version):
        """Returns the last blockversion"""
        brl, time, _ = block_version
        url_params = {"user_name": brl.owner,
                      "block_name": brl.block_name,
                      "branch_name": brl.branch,
                      "version": time
                      }
        return self.bson_jwt_call('get_version_delta_info',
                                     url_params=url_params, deserializer=BlockDelta)

    def get_version_by_tag(self, brl_block, version_tag):
        """Given a BlockVersion that has a tag but not a time returns a complete BlockVersion"""
        assert version_tag is not None
        url_params = {"user_name": brl_block.owner,
                      "block_name": brl_block.block_name,
                      "branch_name": brl_block.branch,
                      "tag": version_tag
                      }
        return self.bson_jwt_call('get_version_by_tag',
                                  url_params=url_params, deserializer=BlockVersion)

    def get_server_info(self):
        """Gets a ServerInfo and sends os_info + client version to server"""
        os_info = OSInfo.capture()
        from biicode.common import __version__
        data = (os_info, str(__version__))
        serialized_data = Serializer().build(("data", data))
        info = self.bson_jwt_call('get_server_info', data=serialized_data,
                                  deserializer=ServerInfo, timeout=1)
        return info

    def require_auth(self):
        info = self.bson_jwt_call('require_auth')
        return info

    def authenticate(self, user, password):
        '''Sends user + password to get a token'''
        token = self.basic_auth_call(user, password, "authenticate")
        return token

    ################### END REST METHODS ########################
    def bson_jwt_call(self, function_name, deserializer=None, url_params={}, data=None,
                      headers=None, response=None, timeout=None):
        # If we dont have token, send without jwtauth (anonymous)
        logger.debug("JWT Call %s" % str(function_name))
        auth = JWTAuth(self.token) if self.token else None
        headers = headers or {}
        headers.update(self.custom_headers)
        headers['Content-Type'] = 'application/bson'

        if data is not None:
            data = str(encode_bson(data))
        return self.call(function_name, url_params=url_params, data=data, headers=headers,
                         auth=auth, deserializer=deserializer, response=response, timeout=timeout)

    def basic_auth_call(self, user, password, function_name, url_params={},
                        data=None, headers=None, deserializer=None):
        auth = HTTPBasicAuth(user, password)
        return self.call(function_name, url_params=url_params,
                         data=data, headers=headers, auth=auth,
                         deserializer=deserializer)

    def call(self, *args, **kwargs):
        deserializer = kwargs.pop("deserializer", None)
        response = kwargs.pop("response", None)
        ret = super(BiiRestApiClient, self).call(*args, **kwargs)
        return BiiRestApiClient.deserialize_return(ret, deserializer, response)

    @staticmethod
    def decode_return_content(res, response=None):
        if 'content-type' in res.headers and res.headers['content-type'] == "application/bson":
            tmp = decode_bson(res.content)
            if response is not None:
                response_server = BiiResponse.deserialize(tmp["info"])
                response_server.biiout(response)
            return tmp["return"]
        else:
            return res.content

    @staticmethod
    def deserialize_return(res, deserializer=None, response=None):
        '''Returns data deserialized and biiresponse object or
            raises an exception with biiresponse info'''
        exc_kls = getExceptionFromHttpError(res.status_code)
        logger.debug("Exception to throw for this return: %s" % str(exc_kls))
        logger.debug("Content Type: %s" % str(res.headers.get('content-type', "")))
        #logger.debug("Response: %s" % str(res.content))
        data = BiiRestApiClient.decode_return_content(res, response)
        if exc_kls is None:
            if deserializer is not None:
                try:
                    return deserializer.deserialize(data)
                except KeyError:  # TODO: Check if better capture any exception
                    raise BiiServiceException("Error handling server response")
            else:
                return data
        else:
            if 'content-type' in res.headers and "text/html" in res.headers['content-type']:
                logger.debug("Can't process html as output")
            raise exc_kls(data)
