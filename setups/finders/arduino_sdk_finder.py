from biicode.common.settings.osinfo import OSInfo
import os
from biicode.client.shell.userio import UserIO
from biicode.client.shell.biistream import BiiOutputStream
from StringIO import StringIO
from biicode.client.command.process_executor import execute
from biicode.common.output_stream import Color
from biicode.client.workspace.bii_paths import get_biicode_env_folder_path


ARDUINO_SDK_COMPATIBLE_VERSIONS = ["1.0.6", "1.0.5", "1.5.8", "1.6.0"]
ARDUINO_AVR_COMPATIBLE_VERSIONS = ['4.3.2']


def find_arduino_sdks():
    """Finds the SDK and return the path.
    settings_versions is a version as string we want to find. EX: '1.0.5'"""
    paths_to_look = _get_all_arduino_sdk_paths()

    valid_versions = []
    # Check all compatible found versions
    for sdk_path in paths_to_look:
        version = valid_arduino_sdk_version(sdk_path)
        if version:
            valid_versions.append((sdk_path, version))

    return valid_versions


def print_sdks(out, sdks):
    out.writeln("Installed SDKs:", front=Color.GREEN)
    for number, (path, version) in enumerate(sdks):
        out.writeln("\t[%d.]\t version=%s\t path=%s" % (number, version, path), front=Color.GREEN)


#Standard arduino installation path
def _get_standard_path():
    if OSInfo.is_win():
        return 'C:/Program Files (x86)/Arduino'
    elif OSInfo.is_linux():
        return '/usr/share/arduino'
    elif OSInfo.is_mac():
        return '/Applications/Arduino.app/Contents/Resources/Java'


def _get_all_arduino_sdk_paths():
    """Get all the paths we need to look at an SDK"""
    paths_to_look = [_get_standard_path()]
    for compatible in ARDUINO_SDK_COMPATIBLE_VERSIONS:
        version_path = os.path.join(get_biicode_env_folder_path(), "arduino-%s" % compatible)
        if OSInfo.is_mac():
            version_path = os.path.join(version_path, "Arduino.app/Contents/Resources/Java")
        paths_to_look.append(version_path.replace('\\', '/'))
    return paths_to_look


def valid_arduino_sdk_version(sdk_path, biiout=None):
    """Returns None or version supported as string
    Parameters:
        sdk_path: BASE_FOLDER[/Arduino.app/Contents/Resources/Java]
    """
    path_version = os.path.join(sdk_path, "lib", "version.txt")
    if not os.path.exists(path_version):
        return None

    with open(path_version) as versiontxt:
        data = versiontxt.read()

    if OSInfo.is_linux():
        if _incompatible_avr_gcc_version_in_path():
            if biiout:
                biiout.warn("There isn't a fully compatible version of gcc-avr"
                          " so it can fail compiling some modules like WiFi.h\n"
                          "It's not a biicode issue, official arduino SDK will fail too. "
                          "More information is available here: http://goo.gl/AldCzv\n"
                          "You can solve this issue by uninstalling apt-get version of gcc-avr:\n"
                          " $ sudo apt-get remove gcc-avr\n"
                          " $ bii setup:arduino\n"
                          " $ bii clean\n"
                          " $ bii arduino:configure\n")

    for version in ARDUINO_SDK_COMPATIBLE_VERSIONS:
        if version in data:
            return version

    return None


def _incompatible_avr_gcc_version_in_path():
    # Check avr-gcc in path and check version
    exit_code, output = execute("avr-gcc --version", UserIO(out=BiiOutputStream(StringIO())))
    if exit_code == 0:
        for compatible_version in ARDUINO_AVR_COMPATIBLE_VERSIONS:
            if compatible_version in output:
                return False
        return True
    else:  # Not found, so its ok
        return False
