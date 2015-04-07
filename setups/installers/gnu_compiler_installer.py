from biicode.client.shell.biistream import Color
from biicode.common.settings.osinfo import OSInfo
from biicode.client.setups.finders import finders
import os
from biicode.client.setups.conf.downloads_url import get_mingw_download_url
from biicode.client.setups.setup_tools import download, decompress, add2path


def install_gnu(user_io, optional):
    if _valid_gnu_version(user_io):
        return

    if OSInfo.is_mac():
        user_io.out.warn('A new window will open, please click on "Obtain Xcode" and install'
                         'Xcode from AppStore')
        os.system('xcode-select --install')
        user_io.request_string('Please press ENTER when finished installing cmake')
    elif OSInfo.is_linux():
        user_io.out.warn('Installing as "sudo", enter "sudo" password if requested')
        if OSInfo.is_debian_based_linux():
            os.system('sudo apt-get install build-essential')
        elif OSInfo.is_redhat_based_linux():
            os.system('sudo yum -y install wget make automake gcc gcc-c++ kernel-devel')
    else:
        return install_mingw(user_io, optional)


def _valid_gnu_version(user_io):
    version_gcc = finders.gnu_version('gcc')
    if version_gcc:
        user_io.out.writeln('gcc %s already installed' % version_gcc, front=Color.GREEN)
    version_gpp = finders.gnu_version('g++')
    if version_gpp:
        user_io.out.writeln('g++ %s already installed' % version_gpp, front=Color.GREEN)
    if version_gcc and version_gpp:
        return True
    return False


def install_mingw(user_io, optional):
    install = True
    if optional:
        user_io.out.writeln('MinGW is a free GNU C/C++ compiler and tools for windows\n'
                            'You need it to build C/C++ applications if you are not using\n'
                            'another compiler as e.g. Visual Studio', front=Color.CYAN)
        install = user_io.request_boolean('Do you want to install MinGW?', True)
    if install:
        user_io.out.writeln('Downloading mingw tools', front=Color.GREEN)
        filename = download(get_mingw_download_url(), 'MinGW.zip')
        user_io.out.info("Unzipping mingw. Please wait, this can take a while...")
        decompress(filename, 'C:\\')
        mingwpath = 'C:/MinGW/bin'
        mingwpath = mingwpath.replace('/', '\\')
        add2path(mingwpath)
        user_io.out.success("MinGW installed in %s!" % mingwpath)
        return True
