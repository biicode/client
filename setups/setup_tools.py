from __future__ import division
from biicode.common.settings.version import Version
import os
from biicode.client.shell.biistream import Color
import sys
from biicode.client.command.process_executor import execute
from biicode.common.settings.osinfo import OSInfo
import urllib
import tempfile


def decompress(filename, destination):
    if filename.endswith(".zip"):
        unzip(filename, destination)
    elif filename.endswith(".tgz") or filename.endswith("tar.gz"):
        untargz(filename, destination)


def unzip(filename, destination):
    import zipfile
    with zipfile.ZipFile(filename, "r") as z:
        if OSInfo.is_linux() or OSInfo.is_mac():
            for zinfo in z.filelist:
                zinfo.create_system = 3  # UNIX
        if OSInfo.is_mac():
            for thefile in z.filelist:
                name = thefile.filename
                perm = ((thefile.external_attr >> 16L) & 0777)
                if name.endswith('/'):
                    os.mkdir(os.path.join(destination, name), perm)
                else:
                    outfile = os.path.join(destination, name)
                    fh = os.open(outfile, os.O_CREAT | os.O_WRONLY, perm)
                    os.write(fh, z.read(name))
                    os.close(fh)
            z.close()
        else:
            z.extractall(destination)


def untargz(filename, destination):
    import tarfile
    with tarfile.TarFile.open(filename, 'r:gz') as tarredgzippedFile:
        tarredgzippedFile.extractall(destination)


def execute_as(command, root=False):
    try:
        if root and sys.platform == "win32":
            os.startfile(command, "runas")
        else:
            ret_code, output = execute(command)
            return ret_code, output
    except Exception as e:
        print e
        return -1, ''


def install_or_upgrade(installed_version, version, user_io):
    if not installed_version:
        user_io.out.writeln('Not found. Do you want to download it?', front=Color.CYAN)
        return user_io.request_boolean(default_option=True)
    elif Version(installed_version) < Version(version):
        user_io.out.writeln('%s older than %s. Do you want to upgrade?'
                                  % (Version(installed_version), version), front=Color.CYAN)
        return user_io.request_boolean(default_option=True)
    elif Version(installed_version) >= Version(version):
        user_io.out.writeln('%s newer or equal %s. Already installed'
                                  % (Version(installed_version), version), front=Color.GREEN)


def notify_win_reg_changes():
    ''' Checking there is any change in the registry '''
    import ctypes
    from ctypes.wintypes import HWND, UINT, WPARAM, LPARAM, LPVOID
    LRESULT = LPARAM
    SendMessage = ctypes.windll.user32.SendMessageW
    SendMessage.argtypes = HWND, UINT, WPARAM, LPVOID
    SendMessage.restype = LRESULT
    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x1A
    SendMessage(HWND_BROADCAST, WM_SETTINGCHANGE, 0, u'Environment')


def add2path(folder):
    if not folder:
        return
    import _winreg
    HKCU = _winreg.HKEY_CURRENT_USER
    ENV = "Environment"
    PATH = "PATH"
    DEFAULT = u"%PATH%"

    with _winreg.CreateKey(HKCU, ENV) as key:
        try:
            envpath = _winreg.QueryValueEx(key, PATH)[0]
        except WindowsError:
            envpath = DEFAULT

        paths = [envpath]

        if folder not in envpath:
            if os.path.isdir(folder):
                paths.insert(0, folder)

        envpath = os.pathsep.join(paths)
        _winreg.SetValueEx(key, PATH, 0, _winreg.REG_EXPAND_SZ, envpath)
        _winreg.CloseKey(key)
        notify_win_reg_changes()
        return str(envpath).split(';')


def update_progress(progress, total_size):
    '''prints a progress bar, with percentages, and auto-cr so always printed in same line
    @param progress: percentage, float
    @param total_size: file total size in Mb
    '''
    bar_length = 40
    status = ""
    if progress < 0:
        progress = 0
        status = "Halt...\r\n"
    if progress >= 1:
        progress = 1
        status = "Done...\r\n"
    block = int(round(bar_length * progress))
    text = "\rPercent: [{0}] {1:.1f}% of {2:.1f}Mb {3}".format("#" * block +
                                                               "-" * (bar_length - block),
                                                               progress * 100, total_size, status)
    sys.stdout.write(text)
    sys.stdout.flush()


def download(url, filename, dl_progress=None, download_dir=None):
    '''download from url, saved with filename.
    if dl_progress, use it as callback for progress, otherwise use console printing
    if download_dir, use that dir, otherwise create temp one
    return: the complete filename, including path
    '''
    if not download_dir:
        download_dir = tempfile.mkdtemp()
    if not dl_progress:
        def dl_progress_callback_cmd(count, block_size, total_size):
            update_progress(min(count * block_size, total_size) / total_size,
                            total_size / (1024 ** 2))
        dl_progress_callback = dl_progress_callback_cmd
    else:
        dl_progress_callback = dl_progress
    print 'Download ', filename
    print 'from ', url
    filename = os.path.join(download_dir, filename)
    print 'download to ', filename
    urllib.urlretrieve(url, filename, reporthook=dl_progress_callback)

    return filename


# Testing download method
if __name__ == '__main__':
    file_ = download('http://www.cmake.org/files/v2.8/cmake-2.8.11-win32-x86.exe', 'localfile.exe')
    print file_
