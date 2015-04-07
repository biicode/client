'''
role:
    URL's of where biicode downloads the Arduino SDK, MinGW, CMake, etc.
'''
from biicode.common.settings.osinfo import OSInfo


S3_URL = "https://s3.amazonaws.com/biibinaries/thirdparty/"

############################## Arduino ##############################


def get_arduino_download_url(version):
    if OSInfo.is_win():
        url = S3_URL + "arduino-%s-windows.zip" % version
    elif OSInfo.is_mac():
        url = S3_URL + "arduino-%s-macosx.zip" % version
    elif OSInfo.is_linux():
        if OSInfo.architecture() == "64bit":
            url = S3_URL + "arduino-%s-linux64.tgz" % version
        elif OSInfo.architecture() == "32bit":
            url = S3_URL + "arduino-%s-linux32.tgz" % version
    return url


############################## MinGW ##############################

def get_mingw_download_url():
    return S3_URL + "MinGW.zip"
