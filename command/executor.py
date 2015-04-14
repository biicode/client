import sys
from biicode.common.exception import BiiException
from biicode.client.command.biicommand import BiiCommand
from biicode.common.utils.bii_logging import logger
from biicode.client.exception import NotInAHiveException, ClientException
from biicode.client.migrations.migration_launcher import launch as migration_launch
import traceback
from biicode.common.output_stream import WARN, DEBUG


class ToolExecutor(object):
    def __init__(self, bii, catalog):
        self.bii = bii
        self.catalog = catalog

    def execute(self, argv):
        '''Executes given command
        @param argv: array containing command and its parameters
        '''

        #Obtain method, group and class
        try:
            if '--quiet' in argv:
                argv.remove('--quiet')
                self.bii.user_io.out.level = WARN
            elif '--verbose' in argv:
                argv.remove('--verbose')
                self.bii.user_io.out.level = DEBUG

            command = argv[0]
            if command == '--help' or command == '-h':
                self.catalog.print_help(self.bii.user_io.out, argv[1:])
                return
            elif command == '-v' or command == '--version':
                from biicode.common import __version__
                self.bii.user_io.out.write(str(__version__) + '\n')
                return

            method, _, class_ = self._get_method(command)
        except Exception as e:
            tb = traceback.format_exc()
            logger.debug(argv)
            raise ClientException('None or bad command. Type "bii --help" for available commands')

        #Obtain delegate object
        try:
            instance = class_(self.bii)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(e)
            logger.error(tb)
            raise BiiException('Internal error: %s tool cannot be created ' % class_.__name__)

        #run bii:work if necessary to process local changes, except for the xxx:exe method
        #if '-h' not in argv and '--help' not in argv:
        #    self._migrate_hive(group)
        #Effective call
        self._migrate_hive()
        self._call_method(argv, method, instance)

    def _get_method(self, command):
        '''Obtains reference to target method'''
        tokens = command.split(":")
        if len(tokens) == 1:
            group = 'bii'
            method_name = tokens[0]
            class_ = BiiCommand
        else:
            group = tokens[0]
            method_name = tokens[1]
            class_ = self.catalog[group]
        method = getattr(class_, method_name)
        return method, group, class_

    def _migrate_hive(self):
        try:
            migration_launch(self.bii)
        except NotInAHiveException:
            pass  # If not in a hive, nothing to migrate

    def _call_method(self, argv, method, instance):
        '''Calls method on instance with params in argv'''
        params = argv[1:]  # Don't pass command name as a parameter
        sys.argv = []  # We don't want to pass argv to ArgumentParser
        if len(params) == 0:
            method(instance)
        else:
            method(instance, params)
