from biicode.client.exception import ClientException
from biicode.client.setups.conf.downloads_url import S3_URL
import os
from biicode.common.settings.osinfo import OSInfo
from biicode.client.setups.setup_tools import download, decompress
from biicode.client.shell.biistream import Color, BiiOutputStream
from biicode.client.command.process_executor import execute
from biicode.common.settings.tools import Architecture
from biicode.client.shell.userio import UserIO
from cStringIO import StringIO
from biicode.client.workspace.bii_paths import get_biicode_env_folder_path


def install_linux_x32_compatibility(user_io):
    if OSInfo.is_linux() and OSInfo.architecture() == Architecture("64bit"):
        cmd = "dpkg-query -S lib32z1"
        exit_code, _ = execute(cmd, UserIO(out=BiiOutputStream(StringIO())))
        if exit_code == 0:
            user_io.out.writeln('x86 compatibility for 64bits already installed',
                                front=Color.GREEN)
        else:
            user_io.out.writeln('Installing x86 compatibility for 64bits architecture...',
                                front=Color.GREEN)
            user_io.out.warn('Installing lib32z1 as "sudo", enter "sudo" password if requested')
            os.system('sudo apt-get install lib32z1')


def find_gnu_arm():
    path_gnu_arm = os.path.join(get_biicode_env_folder_path(), 'raspberry_cross_compilers')
    bin_path = os.path.join(path_gnu_arm, 'arm-bcm2708/arm-bcm2708hardfp-linux-gnueabi/bin')
    c_path = os.path.join(bin_path, 'arm-bcm2708hardfp-linux-gnueabi-gcc')
    cpp_path = os.path.join(bin_path, 'arm-bcm2708hardfp-linux-gnueabi-g++')
    if not os.path.exists(c_path) or not os.path.exists(c_path):
        return None, None
    return c_path, cpp_path


def install_gnu_arm(user_io):
    if not OSInfo.is_linux():
        raise ClientException("ARM Cross compile only works on Linux")

    install_linux_x32_compatibility(user_io)
    c_path, cpp_path = find_gnu_arm()
    if c_path is None or cpp_path is None:
        url = S3_URL + "raspberry_cross_compilers.tgz"
        filename = download(url, url.split("/")[-1])
        user_io.out.info("Unzipping arm gnu SDK")
        install_path = get_biicode_env_folder_path()
        if not os.path.exists(install_path):
            os.mkdir(install_path)
        decompress(filename, install_path)
        user_io.out.success('Installed GNU ARM compilers for RPI')
        # Try to find again
        c_path, cpp_path = find_gnu_arm()
    else:
        user_io.out.writeln('The arm gnu is already downloaded', front=Color.GREEN)
    return c_path, cpp_path