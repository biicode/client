import os
from biicode.common.utils.bii_logging import logger
from abc import ABCMeta, abstractmethod
from biicode.client.wizards.eclipse import Eclipse
from biicode.common.exception import BiiException
from biicode.client.command.process_executor import execute
from biicode.client.setups.finders.msvc_finder import command_with_vcvars
from biicode.common.settings.osinfo import OSInfo
from biicode.client.dev.hardware.arduino.cmaketool import regenerate_arduino_settings_cmake
from biicode.common.utils.file_utils import load

KEEP_CURRENT_TOOLCHAIN = "keep"


def cmake_command(bii_paths):
    if not hasattr(cmake_command, "path"):
        cmake_command.path = _get_cmake_command_path(bii_paths, "cmake")
    return cmake_command.path


def ctest_command(bii_paths):
    if not hasattr(ctest_command, "path"):
        ctest_command.path = _get_cmake_command_path(bii_paths, "ctest")
    return ctest_command.path


def _get_cmake_command_path(bii_paths, command):
    if os.path.exists(bii_paths.cmake_path_file):
        return os.path.join(load(bii_paths.cmake_path_file).strip(), command)
    return command


class CMakeTool(object):
    '''Class to  handle CMake based projects to build binaries, both C++ and Fortran'''
    __metaclass__ = ABCMeta

    def __init__(self, bii):
        self.user_io = bii.user_io
        self.bii = bii
        self.hive_disk_image = self.bii.hive_disk_image
        self.bii_paths = self.bii.bii_paths
        if not os.path.exists(self.bii_paths.bin):
            os.makedirs(self.bii_paths.bin)
        if not os.path.exists(self.bii_paths.build):
            os.makedirs(self.bii_paths.build)
        if not os.path.exists(self.bii_paths.cmake):
            os.makedirs(self.bii_paths.cmake)
        if not os.path.exists(self.bii_paths.lib):
            os.makedirs(self.bii_paths.lib)

    def configure(self, block_targets, force, generator, toolchain, parameters):
        '''creates a CMakeLists for the given lang and invokes CMake in order to create project
        param block_targets: BiiBlockTargets, the structure of the program to be built
        param force: configure will be skipeed if cmake files have not changed at all, if !force
        param generator: CMake generator
        param toolchain: the name of the file containing toolchain. eg. bii/toolchain_xxx.cmake
        '''

        # If we have re-written CMake files or the CMakeCache does not exist (probably deleted
        # because of a change of settings), the call cmake generator
        self._handle_generator(generator)
        force = force or not os.path.exists(os.path.join(self.bii_paths.build, 'CMakeCache.txt'))
        toolchain_file = self._handle_toolchain(toolchain)
        force = force or not os.path.exists(os.path.join(self.bii_paths.build, 'CMakeCache.txt'))
        if self._create_cmakelists(block_targets) or force:
            self._generate_project(toolchain_file, parameters)

    @abstractmethod
    def _create_cmakelists(self, targets):
        '''Must return TRUE if the file is actually created or modified'''
        raise NotImplementedError()

    def _handle_toolchain(self, name):
        """ name KEEP_CURRENT_TOOLCHAIN string means keep current.
            name = None means invalidate current
        and use default
        """
        settings = self.hive_disk_image.settings
        current_toolchain = settings.cmake.toolchain
        if (name == KEEP_CURRENT_TOOLCHAIN):
            name = current_toolchain
            if name is None:  # There was no previous toolchain
                return None

        if name and name != current_toolchain:  # Toolchain change
            toolchain_path = os.path.join(self.bii_paths.bii, '%s_toolchain.cmake' % name)
            if not os.path.exists(toolchain_path):
                if name == "arduino":
                    raise BiiException("Arduino toolchain not found, please execute"
                                       " 'bii arduino:settings' first")
                elif name == "rpi":
                    raise BiiException("Raspberry Pi toolchain not found, please execute"
                                       " 'bii rpi:settings' first")
                else:
                    raise BiiException("CMake %s toolchain not found" % toolchain_path)
            self.user_io.out.warn('Toolchain changed to %s, regenerating project' % toolchain_path)
            self.hive_disk_image.delete_build_folder()
        elif name is None:  # Remove toolchain
            toolchain_path = None
            self.user_io.out.warn('Removing toolchain, regenerating project')
            self.hive_disk_image.delete_build_folder()
        else:  # Keep old toolchain
            toolchain_path = os.path.join(self.bii_paths.bii, '%s_toolchain.cmake' % name)

        # If arduino, regenerate arduino_settings.cmake from settings
        # (needed if manual change without arduino:settings)
        if name == "arduino":
            regenerate_arduino_settings_cmake(self.bii)

        settings.cmake.toolchain = name
        self.hive_disk_image.settings = settings
        return toolchain_path

    def _handle_generator(self, generator):
        """ update current settings with the arg passed generator, or define a
        default generator. If settings for the toolchain do not exist, they
        might be created, as defaults or requested to user by wizard (e.g. arduino board)
        param generator: possible None. Text string with the Cmake generator
        """
        hive_disk_image = self.hive_disk_image
        settings = hive_disk_image.settings
        if generator:
            if generator != settings.cmake.generator:
                if settings.cmake.generator:
                    self.bii.user_io.out.warn("Changed CMake generator, regenerating project")
                    hive_disk_image.delete_build_folder()
                settings.cmake.generator = generator
                hive_disk_image.settings = settings
        else:
            if not settings.cmake.generator:
                if OSInfo.is_win():
                    settings.cmake.generator = "MinGW Makefiles"
                else:
                    settings.cmake.generator = "Unix Makefiles"
                hive_disk_image.settings = settings

    def _generate_project(self, toolchain_file, parameters):
        '''runs CMake to generate Makefiles or Project'''
        # Obtain generator
        settings = self.hive_disk_image.settings
        generator = settings.cmake.generator

        # Define toolchain if necessary, for arduino or cross building
        toolchain = '' if not toolchain_file else '-DCMAKE_TOOLCHAIN_FILE=%s' % toolchain_file

        # Define command to run
        parameters = ' '.join(parameters)
        cmake_rel_path = os.path.relpath(self.bii_paths.cmake, self.bii_paths.build)
        command = ('"%s" %s -G "%s" -Wno-dev %s %s'
                   % (cmake_command(self.bii_paths), toolchain, generator, parameters,
                      cmake_rel_path))
        self.user_io.out.write('Running: %s\n' % command)

        if 'NMake' in generator:
            # VS specific: it is neccesary to call vcvarall
            self.user_io.out.warn('NMake generator must run in a shell with compiler defined.\n'
                                  'It might not work if not')
            command = command_with_vcvars(generator, self.bii_paths.build, command)

        retcode, cmake_output = execute(command, self.user_io, cwd=self.bii_paths.build)
        if 'Does not match the generator used previously' in cmake_output:
            try:
                self.user_io.out.warn('Previous generator does not match. Deleting build folder '
                                      'and trying again')
                self.hive_disk_image.delete_build_folder()
            except Exception as e:
                self.user_io.out.warn('Could not complete deletion %s' % str(e))
            self.user_io.out.warn('Running cmake again')
            retcode, cmake_output = execute(command, self.user_io, cwd=self.bii_paths.build)
        if retcode != 0:
            logger.error(cmake_output)
            raise BiiException('CMake failed')

        if 'Eclipse' in self.hive_disk_image.settings.cmake.generator:
            ide = Eclipse(self.bii_paths)
            ide.configure_project()
            self.user_io.out.success('Eclipse project in %s\n'
                                     'Open eclipse, select "File > Import > General > '
                                     'Existing project into Workspace" '
                                     'and select folder\n' % self.bii_paths.project_root)
