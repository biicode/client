import argparse
from biicode.client.dev.hardware.serial_monitor import monitor
from biicode.common.exception import BiiException
from biicode.client.dev.hardware.arduino.arduino_settings_wizard import arduino_settings_wizard,\
arduino_settings_args
from biicode.client.client_hive_manager import ClientHiveManager
from biicode.client.dev.hardware.arduino.arduino import Arduino
from biicode.client.dev.cpp.cpptoolchain import CPPToolChain
from biicode.client.dev.hardware.arduino.cmaketool import install_arduino_toolchain,\
    regenerate_arduino_settings_cmake


class ArduinoToolChain(CPPToolChain):
    '''Arduino commands'''
    group = 'arduino'

    def __init__(self, bii):
        super(ArduinoToolChain, self).__init__(bii)
        self.hive_disk_image = self.bii.hive_disk_image
        self.arduino = Arduino(bii, self.hive_disk_image)

    def monitor(self, *parameters):
        '''Open serial monitor
        This is a small utility to send and receive text messages over the serial port'''
        parser = argparse.ArgumentParser(description=self.monitor.__doc__,
                                         prog="bii %s:monitor" % self.group)
        parser.parse_args(*parameters)
        try:
            port = self.arduino.refresh_port()
            monitor(self, ClientHiveManager(self.bii), port)
        except Exception as e:
            raise BiiException('Cannot open serial monitor: %s' % str(e))

    def upload(self, *parameters):
        '''Upload a firmware in Arduino'''
        parser = argparse.ArgumentParser(description=self.upload.__doc__,
                                         prog="bii %s:upload" % self.group)
        parser.add_argument('firmware', type=str, nargs="?", help='firmwares to upload')
        parser.add_argument("--ssh", type=str, nargs="?", default=argparse.SUPPRESS,
                            help='Upload by ssh. You can specify the IP (default 192.168.240.1)')
        args = parser.parse_args(*parameters)

        # Refresh the arduino port. Check if user's entered arduino settings
        # FIXME: Leonardo board could fail sometimes because of its port reset
        super(ArduinoToolChain, self).build()  # Here initialize arduino settings if it doesn't exist
        if 'ssh' in args:
            ip = args.ssh or "192.168.240.1"
            self.arduino.ssh_upload(args.firmware, ip)
        else:
            self.arduino.refresh_port()
            self.arduino.upload(args.firmware)

        self.bii.user_io.out.success('Upload finished')

    def configure(self, *parameters):
        '''HIDDEN not show configure from cmake_tool_chain '''
        raise BiiException('''Use "cpp:configure"''')

    def build(self, *parameters):
        '''HIDDEN'''
        raise BiiException(''' Build your program with:

  > bii cpp:build

NOTE: Before building an Arduino project you should configure your project (just once):

    1. "bii arduino:settings": Configure IDE, board, etc
    2. "bii configure -t arduino": Activate toolchain

''')

    def settings(self, *parameters):
        '''Configure project settings for arduino'''
        parser = argparse.ArgumentParser(description=self.settings.__doc__,
                                         prog="bii %s:settings" % self.group)
        parser.add_argument('--sdk', help='SDK directory. Write "default" if you want biicode'
                                 ' tries to find some default directory')
        parser.add_argument("--board", help="Arduino board's name")
        parser.add_argument("--port", help='Port where your Arduino is connected')
        parser.add_argument("--need_reset", choices=['true', 'false'],
                            help="True or False if your port'd need to be reseted")
        args = parser.parse_args(*parameters)  # for -h

        settings = self.hive_disk_image.settings
        if any([args.sdk, args.board, args.port, args.need_reset]):
            arduino_settings_args(self.bii.user_io, args, settings)
        else:
            arduino_settings_wizard(self.bii.user_io, settings)
        self.hive_disk_image.settings = settings
        install_arduino_toolchain(self.bii)
        regenerate_arduino_settings_cmake(self.bii)
