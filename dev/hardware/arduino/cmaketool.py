import os
from biicode.common.model.blob import Blob
from biicode.common.utils.file_utils import save_blob_if_modified, load_resource
from jinja2 import Template
from biicode.client.dev.hardware.arduino.arduino_converter import cmake_board_settings
from biicode.common.settings.version import Version
from biicode.client.workspace.hive_disk_image import HiveDiskImage
from biicode.client.dev.hardware.arduino import DEV_ARDUINO_DIR
from biicode.common.output_stream import Color
from biicode.client.dev.hardware.arduino.arduino_settings_wizard import board_mapping


def install_arduino_toolchain(bii):
    '''Arduino Toolchain uses AVR-GCC & AVR-G++ compilers
    '''
    hive_disk_image = bii.hive_disk_image
    user_io = bii.user_io
    paths = hive_disk_image.paths
    arduino_cmake = load_resource(DEV_ARDUINO_DIR, "cmake/Arduino.cmake")
    bii_ard_path = os.path.join(paths.bii, "Platform/Arduino.cmake")
    save_blob_if_modified(bii_ard_path, Blob(arduino_cmake))

    toolchain = load_resource(DEV_ARDUINO_DIR, "cmake/arduino_toolchain.cmake")
    bii_ard_path = os.path.join(paths.bii, "arduino_toolchain.cmake")

    arduino_sdk_path = hive_disk_image.settings.arduino.sdk
    toolchain += 'SET(ARDUINO_SDK_PATH "%s")\n' % arduino_sdk_path

    SDK_PATH_LIBRARIES = '''SET(SDK_PATH_LIBS "{{libs_dir}}")
        SET(ALL_LIBS_DIR    {% for name in libs_names %}
                            ${SDK_PATH_LIBS}/{{name}}/src
                            ${SDK_PATH_LIBS}/{{name}}
                            {% endfor %})
        INCLUDE_DIRECTORIES(${ALL_LIBS_DIR})
        '''

    SDK_PATH_AVR_LIBS = '''
    SET(SDK_AVR_PATH_LIBS "{{libs_dir}}")
    SET(ALL_LIBS_DIR    {% for name in libs_names %}
                        ${SDK_AVR_PATH_LIBS}/{{name}}/src
                        ${SDK_AVR_PATH_LIBS}/{{name}}
                        {% endfor %})
    INCLUDE_DIRECTORIES(${ALL_LIBS_DIR})
        '''

    libraries_info, libs_recurse_names = _get_libraries_folders(user_io, hive_disk_image)
    libraries_path, list_libraries = libraries_info['common']
    include_libraries_path = Template(SDK_PATH_LIBRARIES).render(libs_dir=libraries_path,
                                                                 libs_names=list_libraries)
    avr_libs_info = libraries_info.get('avr')
    if avr_libs_info:
        libs_path, list_libraries = avr_libs_info
        include_libraries_path += Template(SDK_PATH_AVR_LIBS).render(libs_dir=libs_path,
                                                                     libs_names=list_libraries)

    toolchain += include_libraries_path
    settings = hive_disk_image.settings.arduino
    boards_settings = cmake_board_settings(settings.sdk, settings.version)
    # Problems with encoding of 1.5.8, yun with accent
    boards_settings = boards_settings.decode("utf-8").encode("ascii", "ignore")
    toolchain += boards_settings

    set_lib_recurses = ["set(%s_RECURSE True)" % lib for lib in libs_recurse_names]
    toolchain += "\n".join(set_lib_recurses)
    modified = save_blob_if_modified(bii_ard_path, Blob(toolchain))
    if modified:
        user_io.out.warn("Arduino toolchain defined, regenerating project")
        hive_disk_image.delete_build_folder()

    user_io.out.write('Creating toolchain for Arduino\n', Color.BRIGHT_BLUE)
    user_io.out.success('Run "bii configure -t arduino" to activate it')
    user_io.out.success('Run "bii configure -t" to disable it')


def regenerate_arduino_settings_cmake(bii):
    '''
    Regenerate arduino_settings.cmake from current settings
    '''
    hive_disk_image = bii.hive_disk_image
    current_settings = hive_disk_image.settings

    # Now process settings
    arduino_settings_cmake = load_resource(DEV_ARDUINO_DIR, "cmake/arduino_settings.cmake")

    ard_settings = current_settings.arduino
    board = board_mapping.get(ard_settings.board, ard_settings.board)
    arduino_settings_cmake = arduino_settings_cmake.format(board=board,
                                                           port=ard_settings.port,
                                                           programmer=ard_settings.programmer
                                                           or "usbtinyisp",
                                                           serial="")
    settings_path = os.path.join(hive_disk_image.paths.bii,
                                 "arduino_settings.cmake")
    save_blob_if_modified(settings_path, Blob(arduino_settings_cmake))


def _get_libraries_folders(user_io, hive_disk_image):
    '''get all folders about libraries in Arduino, and the libraries which
    have sub-folders different to examples folder'''

    def add_libraries(lib_path, lib_name, recurse_libs, libraries_info):
        try:
            libs = os.listdir(lib_path)
            for lib in libs:
                lib_folder = os.path.join(lib_path, lib)
                if os.path.isdir(lib_folder):
                    for name in os.listdir(lib_folder):
                        if name != "examples" and os.path.isdir(os.path.join(lib_folder, name)):
                            recurse_libs.append(lib)
                            break

            libraries_info[lib_name] = (lib_path.replace("\\", "/"), libs)
        except OSError:
            user_io.out.warn("You don't have %s libraries in SDK Path %s" % (lib_name, lib_path))
            libraries_info[lib_name] = (None, [])

    libraries_info = {}
    arduino_sdk_path = hive_disk_image.settings.arduino.sdk
    lib_path = os.path.join(arduino_sdk_path, 'libraries')
    recurse_libs = []
    add_libraries(lib_path, "common", recurse_libs, libraries_info)

    if Version(hive_disk_image.settings.arduino.version) > Version('1.5'):
        lib_path = os.path.join(arduino_sdk_path, 'hardware', 'arduino', 'avr', 'libraries')
        add_libraries(lib_path, "avr", recurse_libs, libraries_info)

    return libraries_info, recurse_libs
