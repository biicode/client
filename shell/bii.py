import sys
import os
import shlex
import traceback
from biicode.client.command.executor import ToolExecutor
from biicode.client.command.tool_catalog import ToolCatalog
from biicode.common.exception import BiiException
from biicode.client.shell.userio import UserIO
from biicode.common.utils.bii_logging import logger
from biicode.client.command.biicommand import BiiCommand
from biicode.client.dev.cpp.cpptoolchain import CPPToolChain
from biicode.client.shell.biistream import BiiOutputStream
from biicode.common.output_stream import OutputStream, INFO
from biicode.client.setups.setup_commands import SetupCommands
from biicode.client.dev.hardware.raspberry_pi.rpitoolchain import RPiToolChain
from biicode.client.dev.hardware.arduino.arduinotoolchain import ArduinoToolChain
from biicode.client.shell.updates_manager import UpdatesStore, UpdatesManager
from biicode.common.model.server_info import ClientVersion
from biicode.client.exception import ObsoleteClient
from biicode.client.conf import BII_RESTURL
from biicode.client.rest.bii_rest_api_client import BiiRestApiClient
from biicode.client.dev.node.nodetoolchain import NodeToolChain
from biicode.client.workspace.bii_paths import BiiPaths
from biicode.client.workspace.hive_disk_image import HiveDiskImage
from biicode.client.workspace.user_cache import UserCache


class Bii(object):
    '''Entry point class for bii executable'''

    def __init__(self, user_io, current_folder, user_biicode_folder):
        self.user_io = user_io
        self.bii_paths = BiiPaths(current_folder, user_biicode_folder)
        self.user_cache = UserCache(self.bii_paths.user_bii_home)
        toolcatalog = ToolCatalog(BiiCommand, tools=[CPPToolChain,
                                                     RPiToolChain,
                                                     SetupCommands,
                                                     ArduinoToolChain,
                                                     NodeToolChain])
        self.executor = ToolExecutor(self, toolcatalog)
        self._biiapi = None

    @property
    def hive_disk_image(self):
        # not able to keep it persistent, as tests make a database locked operational error
        return HiveDiskImage(self.bii_paths, self.user_cache, self.user_io.out)

    @property
    def biiapi(self):
        if self._biiapi is None:
            from biicode.client.api.biiapi_proxy import BiiAPIProxy
            from biicode.client.api.biiapi_auth_manager import BiiApiAuthManager
            auth_manager = BiiApiAuthManager(self._restapi, self.user_io, self.user_cache.localdb)
            self._biiapi = BiiAPIProxy(self.user_cache.localdb, auth_manager, self.user_io)
        return self._biiapi

    @property
    def _restapi(self):
        return BiiRestApiClient(BII_RESTURL)

    def execute(self, argv):
        '''Executes user provided command. Eg. bii run:cpp'''
        errors = False
        try:
            if isinstance(argv, basestring):  # To make tests easier to write
                argv = shlex.split(argv)
            self.executor.execute(argv)  # Executor only raises not expected Exceptions
        except (KeyboardInterrupt, SystemExit) as e:
            logger.debug('Execution terminated: %s', e)
            errors = True
        except BiiException as e:
            errors = True
            self.user_io.out.error(str(e))
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(tb)
            errors = True
            self.user_io.out.error('Unexpected Exception\n %s' % e)
            self.user_io.out.error('Error executing command.\n'
                                   '\tCheck the documentation in http://docs.biicode.com\n'
                                   '\tor ask in the forum http://forum.biicode.com\n')
        return errors


def run_main(args, user_io=None, current_folder=None, user_folder=None, biiapi_client=None):
    try:
        user_folder = user_folder or os.path.expanduser("~")
        biicode_folder = os.path.join(user_folder, '.biicode')
        current_folder = current_folder or os.getcwd()
        user_io = user_io or create_user_io(biicode_folder)

        bii = Bii(user_io, current_folder, biicode_folder)

        # Update manager doesn't need proxy nor authentication to call get_server_info
        biiapi_client = biiapi_client or bii.biiapi
        updates_manager = get_updates_manager(biiapi_client, biicode_folder)

        try:  # Check for updates
            updates_manager.check_for_updates(bii.user_io.out)
        except ObsoleteClient as e:
            bii.user_io.out.error(e.message)
            return int(True)

        errors = bii.execute(args)
        return int(errors)
    except OSError as e:
        print str(e)
        return 1


def create_user_io(biicode_folder):
    """Creates the bii folder and init user_io with outputstream and logfile"""
    try:
        os.makedirs(biicode_folder)
    except:
        pass

    log_file = os.path.join(biicode_folder, 'bii.log')
    if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
        from colorama import init
        init()
        OutputStream.color = True
    user_io = UserIO(sys.stdin, BiiOutputStream(sys.stdout, log_file, level=INFO))
    return user_io


def get_updates_manager(biiapi, biicode_folder):
    file_store = os.path.join(biicode_folder, ".remote_version_info")
    updates_store = UpdatesStore(file_store)
    current_client = ClientVersion(get_current_client_version())
    manager = UpdatesManager(updates_store, biiapi, current_client)
    return manager


def get_current_client_version():
    from biicode.common import __version__ as current_version
    return current_version


def main(args):
    error = run_main(args)
    sys.exit(error)


if __name__ == '__main__':
    main(sys.argv[1:])
