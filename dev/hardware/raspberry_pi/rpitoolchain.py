import argparse
from biicode.common.utils.decorators import os_constraint
from biicode.client.dev.hardware.raspberry_pi.rpi_settings_wizard import rpi_settings_wizard,\
    rpi_settings_args
from biicode.client.dev.hardware.raspberry_pi.raspberrypi import RaspberryPi
from biicode.common.output_stream import Color
import os
from biicode.common.model.blob import Blob
from biicode.common.utils.file_utils import save_blob_if_modified
from biicode.common.settings.osinfo import OSInfo
from biicode.client.setups.rpi_cross_compiler import find_gnu_arm


class RPiToolChain(object):
    '''EXPERIMENTAL Raspberry Pi general tools commands'''
    group = 'rpi'

    def __init__(self, bii):
        self.bii = bii
        self.user_io = bii.user_io
        self.paths = self.bii.bii_paths
        self.hive_disk_image = self.bii.hive_disk_image
        self.rpi = RaspberryPi(self.user_io, self.paths, self.hive_disk_image)

    @os_constraint("Linux")
    def send(self, *parameters):
        '''Send by scp the bin folder into the specified directory'''
        parser = argparse.ArgumentParser(description=self.send.__doc__,
                                         prog="bii %s:send" % self.group)
        parser.parse_args(*parameters)
        self.rpi.send_sync()

    @os_constraint("Linux")
    def ssh(self, *parameters):
        '''Connect by ssh with the Raspberry Pi'''
        parser = argparse.ArgumentParser(description=self.ssh.__doc__,
                                         prog="bii %s:ssh" % self.group)
        parser.parse_args(*parameters)
        self.rpi.ssh()

    def settings(self, *parameters):
        '''Configure Raspberry Pi project settings'''
        parser = argparse.ArgumentParser(description=self.settings.__doc__,
                                         prog="bii %s:settings" % self.group)
        parser.add_argument('--user', help='Your RPi user session, e.g.: pi')
        parser.add_argument("--ip", help="Your RPi IP, e.g.: 50.1.2.3")
        parser.add_argument("--directory", help="Directory where you'll send the binary files, e.g.: bin")
        args = parser.parse_args(*parameters)  # for -h

        settings = self.hive_disk_image.settings
        if any([args.user, args.ip, args.directory]):
            rpi_settings_args(args, settings)
        else:
            rpi_settings_wizard(self.user_io, settings)

        #Write to disk
        self.hive_disk_image.settings = settings
        self.user_io.out.info('Settings saved in:  %s' % self.paths.settings)

        toolchain_rpi_path = os.path.join(self.paths.bii, "rpi_toolchain.cmake")
        if not os.path.exists(toolchain_rpi_path):
            if OSInfo.is_linux():
                self.user_io.out.write('Creating toolchain for Raspberry PI\n', Color.BLUE)
                c_path, cpp_path = find_gnu_arm()
                if not c_path or not cpp_path:
                    self.user_io.out.error("Unable to find RPI cross-compilers.\n"
                                           "Try executing bii setup:rpi")

                content = []
                content.append("INCLUDE(CMakeForceCompiler)")
                content.append("SET(CMAKE_SYSTEM_NAME Linux)")
                content.append("SET(CMAKE_SYSTEM_VERSION 1)")
                content.append("SET(CMAKE_C_COMPILER %s)" % c_path)
                content.append("SET(CMAKE_CXX_COMPILER %s)" % cpp_path)
                content = os.linesep.join(content)
                save_blob_if_modified(toolchain_rpi_path, Blob(content))

                self.user_io.out.success('Run "bii configure -t rpi" to activate it')
                self.user_io.out.success('Run "bii configure -t" to disable it')
            else:
                self.user_io.out.error("Toolchain for R-Pi only available in Linux now")
                self.user_io.out.error("You can try to define your own bii/rpi_toolchain.cmake")
