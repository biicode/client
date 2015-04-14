import argparse
from biicode.common.settings.osinfo import OSInfo
from biicode.common.exception import BiiException
from biicode.client.setups.installers.tk_support_installer import install_tk_support
from biicode.client.setups.installers.gnu_compiler_installer import install_gnu
from biicode.client.setups.installers.arduino_sdk_installer import install_arduino_sdk
from biicode.client.setups.cmake import install_cmake
from biicode.client.setups.rpi_cross_compiler import install_gnu_arm
from biicode.client.workspace.bii_paths import BiiPaths


class SetupCommands(object):
    '''External tools setup utilities'''
    group = 'setup'

    def __init__(self, bii):
        self.bii = bii

    def rpi(self, *parameters):
        '''Setup cross compiler tools for Raspberry Pi (must be linux)'''
        parser = argparse.ArgumentParser(description=self.rpi.__doc__,
                                         prog="bii %s:rpi" % self.group)
        parser.add_argument("-i", "--interactive", default=False,
                            action='store_true',
                            help='Runs in interactive mode, can require user input')
        args = parser.parse_args(*parameters)

        if not OSInfo.is_linux():
            raise BiiException('You need to use a linux OS')

        # If we are installing c++ cross compiler... we need the other c++ tools
        install_gnu_arm(self.bii.user_io)
        self._setup_cpp(args.interactive)

    def cpp(self, *parameters):
        '''Setup for installing cpp third party tools'''
        parser = argparse.ArgumentParser(description=self.cpp.__doc__,
                                         prog="bii %s:cpp" % self.group)
        parser.add_argument("-i", "--interactive", default=False,
                            action='store_true',
                            help='Runs in interactive mode, can require user input')
        args = parser.parse_args(*parameters)
        self.bii.user_io.out.warn('This setup is EXPERIMENTAL.\nPlease refer to the docs '
                                  'for manual installation if something fails')

        self._setup_cpp(args.interactive)

    def _setup_cpp(self, interactive):
        restart_console = False
        try:
            paths = self.bii.bii_paths
            install_cmake(self.bii.user_io, paths, interactive)
            gnu_optional = OSInfo.is_win()
            # GNU in windows is optional, you could use Visual
            restart_console2 = install_gnu(self.bii.user_io, gnu_optional)
            restart_console = restart_console or restart_console2
        except BiiException as e:
            self.bii.user_io.out.error(str(e))
            raise BiiException("The cpp setup has failed. Please fix problems and launch bii "
                                "setup:cpp again")
        finally:
            if restart_console:
                self.bii.user_io.out.warn('The PATH has changed, it is necessary '
                                          'to CLOSE this window')
                self.bii.user_io.out.warn('Please close this window')

    def arduino(self, *parameters):
        '''Setup for installing cpp third party tools'''
        parser = argparse.ArgumentParser(description=self.cpp.__doc__,
                                         prog="bii %s:arduino" % self.group)
        parser.add_argument("-i", "--interactive", default=False,
                            action='store_true',
                            help='Runs in interactive mode, can require user input')
        args = parser.parse_args(*parameters)
        self.bii.user_io.out.warn('This setup is EXPERIMENTAL.\nPlease refer to the docs '
                                  'for manual installation if something fails')

        restart_console = False
        try:
            paths = self.bii.bii_paths
            install_cmake(self.bii.user_io, paths, args.interactive)
            restart_console2 = install_gnu(self.bii.user_io, optional=False)  # we need make!
            restart_console = restart_console or restart_console2

            install_arduino_sdk(self.bii.user_io)
            install_tk_support(self.bii.user_io)
        except BiiException as e:
            self.bii.user_io.out.error(str(e))
            raise BiiException("The arduino setup has failed. Please fix problems and launch bii "
                                "setup:arduino again")
        finally:
            if restart_console:
                self.bii.user_io.out.warn('The PATH has changed, it is necessary '
                                          'to CLOSE this window')
                self.bii.user_io.out.warn('Please close this window')
