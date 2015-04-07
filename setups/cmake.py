from biicode.client.shell.biistream import Color
from biicode.common.settings.osinfo import OSInfo
from biicode.common.settings.version import Version
import os
from biicode.client.setups.setup_tools import download, decompress
from biicode.common.utils.file_utils import load, save
from biicode.client.setups.conf.downloads_url import S3_URL
from biicode.client.command.process_executor import simple_exe
import re


_CMAKE_VERSION = Version('3.0.2')
_CMAKE_MIN_VERSION = Version('3.0')


def _get_cmake_download_url():
    if OSInfo.is_win():
        url = S3_URL + "cmake-%s-win32-x86.zip" % _CMAKE_VERSION
    elif OSInfo.is_mac():
        url = S3_URL + 'cmake-%s-Darwin64-universal.dmg' % _CMAKE_VERSION
    elif OSInfo.is_linux():
        import platform
        if OSInfo.architecture() == "64bit":
            url = S3_URL + "cmake-%s-Linux-64.tar.gz" % _CMAKE_VERSION
        elif OSInfo.architecture() == "32bit":
            url = S3_URL + "cmake-%s-Linux-i386.tar.gz" % _CMAKE_VERSION
        if platform.machine() == "armv6l" or platform.machine() == "armv7l":
            url = S3_URL + "cmake-%s-Linux-armv6.tar.gz" % _CMAKE_VERSION
    return url


def _cmake_version(cmake_path):
    command = os.path.join(cmake_path, "cmake")
    try:
        simple_exe.output = ""
        simple_exe('%s --version' % command)
        version_match = re.search('cmake version ([0-9.]+)', simple_exe.output)
        del simple_exe.output
        if version_match:
            return Version(version_match.group(1))
    except OSError:  # WindowsError
        pass
    return None


def _valid_cmake(path, user_io):
    current_version = _cmake_version(path)
    path_msg = "your path" if not path else '"%s"' % path
    if current_version:
        if current_version >= _CMAKE_MIN_VERSION:
            user_io.out.success('Valid cmake version %s > %s in %s'
                                % (current_version, _CMAKE_MIN_VERSION, path_msg))
            return True
        else:
            user_io.out.writeln("Invalid cmake version %s < %s in %s"
                                % (current_version, _CMAKE_MIN_VERSION, path_msg),
                                Color.BRIGHT_GREEN)
            return False
    user_io.out.writeln("No cmake detected in %s" % path_msg, Color.BRIGHT_GREEN)
    return False


def install_cmake(user_io, bii_paths, interactive):
    # check if the one by biicode is valid
    cmake_path_file = bii_paths.cmake_path_file
    if os.path.exists(cmake_path_file) and _valid_cmake(load(cmake_path_file).strip(), user_io):
        return

    # Check if the one in path is valid
    if _valid_cmake("", user_io):
        return

    if interactive:
        # Do you have it installed elsewhere?
        while True:
            path = user_io.request_string("If you have cmake > %s installed, please enter path"
                                          % _CMAKE_MIN_VERSION, "None")
            if path == "None":
                break
            if _valid_cmake(path, user_io):
                save(cmake_path_file, path)
                return

        # Do you want me to install a copy for biicode it?
        user_io.out.writeln("CMake >= %s not found.\nIf you want, biicode can install a local copy"
                             " of cmake for its use.\nIt won't interfere with your current install"
                             " if any.\nIf you dont want it, just quit, install it yourself and "
                             "re-run this setup to enter its path" % _CMAKE_MIN_VERSION,
                             Color.BRIGHT_GREEN)
        install = user_io.request_boolean("Install local copy of cmake %s?" % _CMAKE_VERSION,
                                          default_option=True)
    else:
        user_io.out.warn("You are running in non-interactive mode.\n"
                         "A CMake local copy will be installed automatically.\n"
                         "Please run with '-i' or '--interactive' for more options")
        install = True

    if install:
        cmake_install_path = _install_cmake(user_io, bii_paths)
        save(cmake_path_file, cmake_install_path)
        if not _valid_cmake(cmake_install_path, user_io):
            user_io.out.error("Something failed in the installation of cmake")
        else:
            user_io.out.success("CMake %s installed ok" % _CMAKE_VERSION)


def _install_cmake(user_io, bii_paths):
    user_io.out.writeln('Downloading and installing CMake %s' % _CMAKE_VERSION, front=Color.GREEN)
    if OSInfo.is_win():
        return _install_cmake_win(user_io, bii_paths)
    elif OSInfo.is_mac():
        return _install_cmake_mac(user_io)
    elif OSInfo.is_linux():
        return _install_cmake_linux(user_io, bii_paths)


def _install_cmake_linux(user_io, bii_paths):
    url = _get_cmake_download_url()
    basename = os.path.basename(url)
    package_name = os.path.basename(url)
    uncompressed_name = basename.replace(".tar.gz", "")
    filename = download(url, package_name)
    user_io.out.info("Extracting cmake")
    install_path = bii_paths.user_bii_home
    if not os.path.exists(install_path):
        os.mkdir(install_path)
    decompress(filename, install_path)
    cmake_path = os.path.join(install_path, uncompressed_name)
    bin_path = os.path.join(cmake_path, "bin")
    return bin_path


def _install_cmake_mac(user_io):
    filename = download(_get_cmake_download_url(), 'cmake%s.dmg' % _CMAKE_VERSION)
    user_io.out.writeln('Click on Agree and drag CMake.app to your Applications folder')
    os.system('open %s' % filename)
    user_io.request_string('Please press ENTER when finished installing cmake')
    if not os.path.exists('/Applications/CMake.app/Contents/bin/'):
        user_io.out.error('CMake.app not found in Applications folder')
    return '/Applications/CMake.app/Contents/bin/'


def _install_cmake_win(user_io, bii_paths):
    filename = download(_get_cmake_download_url(), 'cmake%s.zip' % _CMAKE_VERSION)
    user_io.out.info("Unzipping cmake")
    install_path = bii_paths.user_bii_home
    decompress(filename, install_path)
    return_path = os.path.join(install_path, "cmake-%s-win32-x86/bin" % _CMAKE_VERSION)
    cmake_path = return_path.replace('\\', '/')
    return cmake_path
