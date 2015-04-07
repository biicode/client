from biicode.common.settings.osinfo import OSInfo
import os


def install_tk_support(user_io):
    if OSInfo.is_debian_based_linux():
        user_io.out.warn('Installing "python-tk" and "libtk8.5" as "sudo", enter "sudo" password if requested')
        ret = os.system('sudo apt-get install python-tk libtk8.5')
        if ret == 0:
            user_io.out.success("Tk support already installed")
