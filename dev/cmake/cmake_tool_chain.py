import argparse
from abc import ABCMeta, abstractproperty
from biicode.client.command.process_executor import simple_exe
from biicode.common.exception import BiiException
from biicode.client.dev.cmake.cmaketool import KEEP_CURRENT_TOOLCHAIN, ctest_command, cmake_command
from biicode.client.client_hive_manager import ClientHiveManager
import platform
from biicode.client.command.context_manager import CustomEnvPath
import re
from biicode.client.wizards.eclipse import Eclipse


class CMakeToolChain(object):
    """ ABC for cmake dev commands, as build and configure
    Derived class can extend for cpp:build or arduino:configure
    """
    __metaclass__ = ABCMeta

    def __init__(self, bii):
        self.bii = bii

    @abstractproperty
    def target_processor(self):
        """ Must return the processor class that computes the targets to be built
        """
        raise NotImplementedError()

    @abstractproperty
    def cmake(self):
        """ return: a CMakeTool (or derived CPPMakeTool, etc) class, not object
        """
        raise NotImplementedError()

    def build(self, *parameters):
        '''Build the project with cmake --build. You can pass the same parameters as cmake.
        It will call "configure" without any parameter
        '''
        parser = argparse.ArgumentParser(description=self.build.__doc__,
                                         prog="bii %s:build" % self.group)
        parser.parse_known_args(*parameters)

        self._configure(force=False, generator=None,
                        toolchain=KEEP_CURRENT_TOOLCHAIN, parameters=[])
        self._build(*parameters)

    def _build(self, *parameters):
        paths_to_add = self.prepare_build_path()
        with CustomEnvPath(paths_to_add=paths_to_add):
            paths = self.bii.bii_paths
            if len(parameters) == 1:  # It's tuple, first element is list with actual parameters
                parameters = parameters[0]
            self._handle_parallel_build(parameters)
            build_options = ' '.join(parameters)

            # Necessary for building in windows (cygwin in path)
            cmd = '"%s" --build . %s' % (cmake_command(paths), build_options)
            self.bii.user_io.out.write('Building: %s\n' % cmd)
            retcode = simple_exe(cmd, cwd=paths.build)
            if 'Eclipse' in self.bii.hive_disk_image.settings.cmake.generator:
                ide = Eclipse(paths)
                try:
                    ide.configure_project()
                except IOError:
                    pass
            if retcode != 0:
                raise BiiException('Build failed')

    def prepare_build_path(self):
        hive_disk_image = self.bii.hive_disk_image
        settings = hive_disk_image.settings
        if settings.arduino and settings.arduino.sdk:
            return [settings.arduino.sdk]
        return None

    def prepare_configure_cmds(self, generator):
        hive_disk_image = self.bii.hive_disk_image
        settings = hive_disk_image.settings.cmake.generator
        # if (new generator) or (previous settings) or (default value)
        mingw_in_new_generator = (generator and "MinGW Makefiles" in generator)
        mingw_in_settings = (settings and "MinGW Makefiles" in settings and generator is None)
        default_value = ((settings and generator) is None and platform.system() == 'Windows')
        if (mingw_in_new_generator) or (mingw_in_settings) or (default_value):
            return ['sh']

    def _configure(self, force, generator, toolchain, parameters):
        paths_to_add = self.prepare_build_path()
        cmds_to_remove = self.prepare_configure_cmds(generator)
        with CustomEnvPath(paths_to_add=paths_to_add, cmds_to_remove=cmds_to_remove):
            client_hive_manager = ClientHiveManager(self.bii)
            client_hive_manager.work()
            base = self.target_processor(client_hive_manager)
            block_targets = base.targets()
            cmake = self.cmake(self.bii)
            cmake.configure(block_targets, force, generator, toolchain, parameters)

    def configure(self, *parameters):
        '''Configure project with cmake'''
        parser = argparse.ArgumentParser(description=self.configure.__doc__,
                                         prog="bii %s:configure" % self.group)
        parser.add_argument('-G', metavar='"CMake generator"',
                            help='Define cmake generator. Type cmake --help to see'
                            ' available generators')
        parser.add_argument('-t', "--toolchain", nargs='?', default=argparse.SUPPRESS,
                            help='Define cmake toolchain')
        args, unknown_args = parser.parse_known_args(*parameters)

        toolchain = getattr(args, "toolchain", KEEP_CURRENT_TOOLCHAIN)
        if toolchain == "None" or toolchain == "":
            toolchain = None

        self._configure(True, args.G, toolchain, unknown_args)

    def test(self, *parameters):
        '''Build only the tests declared into your biicode.conf '[tests]' section.
        It's a wrapper of 'cmake --build . --target biitest' command.
        '''
        parser = argparse.ArgumentParser(description=self.test.__doc__,
                                         prog="bii %s:tests" % self.group)
        parser.add_argument('-j',
                            help=('Build and run your tests with parallel build flag. '
                                  'Specify an int number.'))
        args, unknown_args = parser.parse_known_args(*parameters)
        build_params = ["--target", "biitest"]
        ctest_params = unknown_args
        if args.j:
            parallel_build = '-j%s' % args.j
            build_params = ["--target", "biitest", parallel_build]
            ctest_params = unknown_args + [parallel_build]
        self.build(build_params)
        self._test(ctest_params)

    def _test(self, parameters):
        ''' Method to execute tests with CTest

            Attributes:
                parameters: list of entered flags
        '''
        paths = self.bii.bii_paths
        _ctest_command = ctest_command(paths)
        # If generator is Visual Stdio, biicode'll pass a default build config
        hive_disk_image = self.bii.hive_disk_image
        generator = hive_disk_image.settings.cmake.generator
        needs_config = "Visual Studio" in generator or "Xcode" in generator
        build_config = '-C Debug' if needs_config and '-C' not in parameters else ''
        # By default, if user don't pass any argument, biicode'll pass --extra-verbose
        if not parameters:
            cmd = '"%s" -VV %s' % (_ctest_command, build_config)
        else:
            cmd = '"%s" %s %s' % (_ctest_command, ' '.join(parameters), build_config)
        self.bii.user_io.out.write('Running tests: %s\n' % cmd)
        retcode = simple_exe(cmd, cwd=paths.build)
        if retcode != 0:
            raise BiiException('CTest failed')

    def _handle_parallel_build(self, parameters):
        ''' Check if user enters flags to use native building options.
            If -j4 is detected, biicode changes it for the suitable command

            Attributes:
                parameters: list of parameters
            Return:
                A valid core pattern (string) or None
        '''
        if '--' in parameters:  # If user enters "bii build -- -j4" biicode respects it
            return

        pattern = re.compile('-j(\s+)?[0-9]{1,2}')  # detect "-j    2", "-j10", ...
        for index, param in enumerate(parameters):
            if pattern.match(param):
                # Getting a valid core pattern (Visual Studio or Unix pattern)
                hive_disk_image = self.bii.hive_disk_image
                is_visual = "Visual Studio" in hive_disk_image.settings.cmake.generator
                valid_core_pattern = '/m:' if is_visual else '-j'
                parameters[index] = '-- %s' % param.replace('-j', valid_core_pattern)
                return '-- %s' % param.replace('-j', valid_core_pattern)
