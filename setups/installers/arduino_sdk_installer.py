from biicode.common.settings.osinfo import OSInfo
from biicode.client.setups.finders.arduino_sdk_finder import find_arduino_sdks, print_sdks
import os
from biicode.client.setups.conf.downloads_url import get_arduino_download_url
from biicode.client.setups.setup_tools import decompress, download
from biicode.client.workspace.bii_paths import get_biicode_env_folder_path


CURRENT_VERSION = "1.0.6"


def install_arduino_sdk(user_io):
    ''' Install Arduino SDK in user biicode_env folder '''
    sdks = find_arduino_sdks()
    if sdks:
        print_sdks(user_io.out, sdks)

    versions = [version for _, version in sdks]
    if CURRENT_VERSION not in versions:
        request_message = 'Arduino SDK %s not detected. Install it?' % CURRENT_VERSION
        if user_io.request_boolean(request_message, True):
            _install_arduino_sdk(user_io)
            sdks = find_arduino_sdks()
            if sdks:
                print_sdks(user_io.out, sdks)


def _install_arduino_sdk(user_io):
    url = get_arduino_download_url(CURRENT_VERSION)
    decompress_to_folder = _get_install_arduino_sdk_path(CURRENT_VERSION)
    if url:
        filename = download(url, url.split("/")[-1])
        user_io.out.info("Unzipping arduino SDK. Please wait, this can take a while...")
        if not os.path.exists(decompress_to_folder):
            os.makedirs(decompress_to_folder)
        decompress(filename, decompress_to_folder)

        osinfo = OSInfo.capture()
        if osinfo.family == 'Windows' and osinfo.subfamily == '8':
            drivers = '%s/drivers' % decompress_to_folder
            user_io.out.warn('Windows 8 does not automatically detect Arduino drivers.\n'
                             'When installing the drivers, please use this folder: %s' % drivers)


def _get_install_arduino_sdk_path(version):
    if OSInfo.is_mac():
        decompress_to_folder = os.path.join(get_biicode_env_folder_path(), "arduino-%s" % version)
    else:
        decompress_to_folder = get_biicode_env_folder_path()
    return decompress_to_folder
